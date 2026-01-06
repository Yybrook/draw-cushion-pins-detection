from threading import Thread
import json
import numpy as np
from time import sleep

from CameraCore.my_camera_t import MyCamera
from CameraCore.camera_err_header import CAMERA_ENUM_NONE
from MvImport.MvErrorDefine_const import MV_OK
from MvImport.CameraParams_const import MV_ACCESS_Exclusive

from main_grab import camera_save_process as grab_camera_save_process

from Utils.database_operator import DatabaseOperator, get_lines_with_all, get_parts_with_all
from Utils.serializer import MySerializer

from User.config_static import CF_PROJECT_ROLE, CF_TEACH_REFERENCE_SIDE


COMMAND_PREFIX = 'command'
COMMAND_STOP_LISTEN = 'stop listen'
COMMAND_ENUM = 'enum device'
COMMAND_OPEN_AND_DETECT = 'open and check'
COMMAND_LINES = 'enum line'
COMMAND_PARTS = 'enum part'

COMMAND_DOING = 'doing'

UID_PREFIX = 'userDefined'
LINE_PREFIX = 'line'
PART_PREFIX = 'model'


RESPONSE_PREFIX = 'result'
RESPONSE_ENUM_ERROR = 'enum error'
RESPONSE_ENUM_NONE = 'enum none'
RESPONSE_ENUM_SEPARATOR = "^_^"
RESPONSE_OPEN_CAMERA_SUCCESSFUL = 'open success'
RESPONSE_OPEN_CAMERA_FAILED = 'open failed'
RESPONSE_DETECTION_ERROR = 'check error'

RESPONSE_DETECTION_RIGHT = 'check right","picture":"{}'
RESPONSE_DETECTION_WRONG = 'check wrong","picture":"{}'

# RESPONSE_COMMAND_ILLEGAL = 'command illegal'
RESPONSE_COMMAND_ILLEGAL = 'check error'


class MyCorrespondent(Thread):

    def __init__(self, server, conn, address, pop_conn_callback, client_offline_callback=None):
        super().__init__()

        self.server = server    # 服务端
        self.conn = conn        # 客户端
        self.address = address  # 客户端地址 (ip, port)

        self.pop_conn_callback = pop_conn_callback
        self.client_offline_callback = client_offline_callback

        self.flag = False       # detection 完成标志

        self.db_operator = DatabaseOperator()  # 数据库

    def receive_message(self):
        """
        接受并处理消息
        :return:
        """
        while True:
            try:
                # 最多接受1024个字节
                # decode解码，将接受的二进制转为字符
                data = self.conn.recv(1024).decode('utf-8')
                # 如果接收的消息长度不为0，则将其解码输出
                if data:
                    # print('[server] receive message: %s' % data)
                    res = self.decoder(data)
                    if not res:
                        # # 关闭客户端连接
                        # self.conn.close()
                        # 移除conn回调函数
                        # if self.pop_conn_callback is not None:
                        #     self.pop_conn_callback(address=self.address)
                        # 关闭server
                        self.server.close()
                        break
                # 当客户端断开连接时，会一直发送''空字符串，所以长度为0已下线
                else:
                    # print('[server] client off line')
                    # 客户端下线的回调函数
                    if self.client_offline_callback is not None:
                        self.client_offline_callback(address=self.address)
                    # 关闭客户端连接
                    self.conn.close()
                    # 移除conn回调函数
                    if self.pop_conn_callback is not None:
                        self.pop_conn_callback(address=self.address)
                    break
            except Exception as err:
                if "10053" in str(err):
                    break

        self.db_operator.close()    # 关闭数据库

    def decoder(self, data: str):
        """

        :param data:    为JSON格式
        :return:
        """
        try:
            data = json.loads(data)      # 将JSON字符串转为字典
        # data 不是JSON格式
        except json.decoder.JSONDecodeError:
            response = self.create_message(RESPONSE_PREFIX, RESPONSE_COMMAND_ILLEGAL)
            self.conn.send(response.encode('utf-8'))
            return True

        # json中没有'command'
        if COMMAND_PREFIX not in data:
            response = self.create_message(RESPONSE_PREFIX, RESPONSE_COMMAND_ILLEGAL)
            self.conn.send(response.encode('utf-8'))
            return True
        # 提取command的字典内容
        command = data[COMMAND_PREFIX]

        # 停止监听
        if command == COMMAND_STOP_LISTEN:
            # 接收
            # {"command":"stop listen"}
            # self.server.close()
            return False
        # 枚举相机
        elif command == COMMAND_ENUM:
            # 接收
            # {"command":"enum device"}
            # 响应
            # {"result":"enum error"}
            # {"result":"enum none"}
            # {"result":"uid1^_^uid2^_^uid3"}
            response = self.enum_cameras()
            self.conn.send(response.encode('utf-8'))
            return True
        elif command == COMMAND_LINES:
            # 接收
            # {"command":"enum line"}
            # 响应
            # {"result":"line1^_^line2^_^line3"}
            lines = get_lines_with_all(db_operator=self.db_operator)[1:]
            symbol = RESPONSE_ENUM_SEPARATOR
            message = symbol
            for line in lines:
                message += line + symbol
            response = self.create_message(RESPONSE_PREFIX, message[3:-3])
            self.conn.send(response.encode('utf-8'))
            return True
        elif command == COMMAND_PARTS:
            # 接收
            # {"command":"enum part","line":"line1"}
            # 响应
            # {"result":"part1^_^part2^_^part3"}
            selected_line = data[LINE_PREFIX]
            parts = get_parts_with_all(db_operator=self.db_operator, line=selected_line)[1:]
            symbol = RESPONSE_ENUM_SEPARATOR
            message = symbol
            for part in parts:
                message += part + symbol
            response = self.create_message(RESPONSE_PREFIX, message[3:-3])
            self.conn.send(response.encode('utf-8'))
            return True
        # 打开相机，检查，关闭相机
        elif command == COMMAND_OPEN_AND_DETECT:
            # 接收
            # {"command":"open and check","userDefined":"0","line":"5-100","model":"PART1"}
            # {"command":"open and check","userDefined":"Pin_5-200_Left","line":"5-100","model":"34D 809 606A"}
            # 响应
            # {"result":"check right","picture":"xxx.jpg"}
            # {"result":"check wrong","picture":"xxx.jpg"}
            # {"result":"open failed"}
            # {"result":"check error"}

            # 判断格式
            if UID_PREFIX not in data or PART_PREFIX not in data or LINE_PREFIX not in data:
                response = self.create_message(RESPONSE_PREFIX, RESPONSE_COMMAND_ILLEGAL)
                self.conn.send(response.encode('utf-8'))
                return True

            response = COMMAND_DOING
            self.conn.send(response.encode('utf-8'))

            # 提取uid
            selected_uid = data[UID_PREFIX]
            # 提取part
            selected_part = data[PART_PREFIX]
            # 提取line
            selected_line = data[LINE_PREFIX]

            response = self.open_and_detect_camera(uid=selected_uid, line=selected_line, part=selected_part, )
            self.conn.send(response.encode('utf-8'))
            return True
        else:
            return True

    def enum_cameras(self) -> str:
        res = MyCamera.enum_cameras(filter_callback=lambda device_info: MyCorrespondent.filter_cameras(device_info=device_info, db_operator=self.db_operator))
        if res == MV_OK:
            return self.create_message(RESPONSE_PREFIX, self.creat_enum_message())
        elif res == CAMERA_ENUM_NONE:
            return self.create_message(RESPONSE_PREFIX, RESPONSE_ENUM_NONE)
        else:
            return self.create_message(RESPONSE_PREFIX, RESPONSE_ENUM_ERROR)

    @staticmethod
    def creat_enum_message() -> str:
        symbol = RESPONSE_ENUM_SEPARATOR
        message = symbol
        cameras_identity = MyCamera.get_enum_cameras_identity()
        for identity in cameras_identity:
            uid = identity.uid
            message += uid + symbol
        return message[3:-3]

    @staticmethod
    def filter_cameras(device_info: dict, db_operator: DatabaseOperator) -> bool:
        result = db_operator.get_camera_identity(demand_list=["Role"], filter_dict={"SerialNumber": device_info["SerialNumber"]})
        role = result.get("Role")
        if role == CF_PROJECT_ROLE:
            return True
        return False

    def open_and_detect_camera(self, uid: str, line: str, part: str):

        cameras_identity = MyCamera.get_enum_cameras_identity()
        for identity in cameras_identity:
            if uid == identity.uid:
                break
        else:
            return self.create_message(RESPONSE_PREFIX, RESPONSE_OPEN_CAMERA_FAILED)

        # 获取相机位置
        camera_location = self.db_operator.get_camera_identity(demand_list=["Line", "Location", "Side"], filter_dict={"SerialNumber": identity.serial_number})
        # 如果side为“LEFT”,相机视野旋转180度
        side = camera_location["Side"]
        if side == CF_TEACH_REFERENCE_SIDE:
            rotate_flag = 0
        else:
            rotate_flag = 2

        my_camera = MyCamera(
            camera_identity=identity,
            name=None,
            resize_ratio=None,
            rotate_flag=rotate_flag,
            access_mode=MV_ACCESS_Exclusive,
            msg_child_conn=None,
            imgbuf_child_conn=None,
            frame_process_callback=None,
            save_process_callback=None,
            save_process_successful_callback=None,
            before_grab_callback=None,
            after_grab_callback=None,
            running_cameras_manager=None,
            running_cameras_lock=None,
        )

        # 多线程，打开相机并取流
        ret = my_camera.open_and_grab_in_thread()
        if ret != MV_OK:
            return self.create_message(RESPONSE_PREFIX, RESPONSE_OPEN_CAMERA_FAILED)

        # 方法1：延迟
        while not my_camera.get_grab_flag():
            sleep(0.1)
            pass

        ret = self.do_detect(camera=my_camera, line=line, part=part)
        if not ret:
            my_camera.close_camera()
            return self.create_message(RESPONSE_PREFIX, RESPONSE_DETECTION_ERROR)

        # 方法2：软触发

        # 死循环判断 关闭相机
        while not self.flag:
            sleep(0.1)
            pass
        my_camera.close_camera()

        # 获取最新记录
        record = self.db_operator.get_latest_detection_records(demand_list=["Result", "DetectionPicture"], filter_dict={"Part": part, "Line": line})
        if not record:
            return self.create_message(RESPONSE_PREFIX, RESPONSE_DETECTION_ERROR)

        # 判断结果
        if record["Result"]:
            msg = {
                RESPONSE_PREFIX: "check right",
                "picture": record["DetectionPicture"],
            }
        else:
            msg = {
                RESPONSE_PREFIX: "check wrong",
                "picture": record["DetectionPicture"],
            }

        response = json.dumps(msg)
        return response

    def do_detect(self, camera: MyCamera, line: str, part: str):
        self.flag = False

        serial_number = camera.camera_identity.serial_number
        detect_message = {
            "Part": part,
            "SerialNumber": serial_number
        }

        # 获取相机位置
        camera_location = self.db_operator.get_camera_identity(demand_list=["Line", "Location", "Side"], filter_dict={"SerialNumber": serial_number})
        if (not camera_location or
                camera_location.get("Line", '') != line or
                camera_location.get("Location", '') == '' or
                camera_location.get("Side", '') == ''):
            return False
        detect_message["CameraLocation"] = camera_location

        # 数据库获取图片处理参数
        process_parameters = self.db_operator.get_all_process_parameters(filter_dict={"SerialNumber": serial_number})
        if not process_parameters:
            return False

        # 数据库获取pins_map
        pins_map = self.db_operator.get_parts_pins_map(demand_list=["PinsMap", ], filter_dict={"Part": part, "Line": line})
        if not pins_map:
            return False

        pins_map["PinsMap"] = MySerializer.deserialize(pins_map["PinsMap"])     # 反序列化
        message = dict(**detect_message, **process_parameters, **pins_map)      # 合并字典

        # 设置 save_process_callback 回调函数
        camera.save_process_callback = lambda frame_data, parameters: self.camera_save_process(frame_data=frame_data, parameters=parameters, message=message,
                                                                                               db_operator=self.db_operator)
        camera.set_to_save(True)    # 置位保存图片

        return True

    def camera_save_process(self, frame_data: np.ndarray, parameters: dict, message: dict, db_operator: DatabaseOperator):
        grab_camera_save_process(flag=1, frame_data=frame_data, parameters=parameters, message=message,
                                 db_operator=db_operator, show_detection_callback=self.show_detection)

    def show_detection(self, result: bool, frame: np.ndarray):
        self.flag = True

    @staticmethod
    def create_message(prefix: str, message: str) -> str:
        data = '{"%s":"%s"}' % (prefix, message)
        return data

    def run(self):
        self.receive_message()
