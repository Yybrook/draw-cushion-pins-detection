import argparse
from sys import argv as sys_argv, exit as sys_exit, stderr as sys_stderr
import numpy as np
import cv2
from typing import Union
from os import path as os_path, makedirs as os_makedirs
from multiprocessing import Pipe
from threading import Thread
from datetime import datetime
import yaml
import json

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap

from Interface.Grab.interface_grab import InterfaceGrab

from CameraCore.camera_identity import CameraIdentity
from CameraCore.my_camera import MyCamera, ROTATE_INEFFECTIVE, ROTATE_180, ROTATE_90_CLOCKWISE, ROTATE_90_COUNTERCLOCKWISE, ImageBufferListener

from FrameCore.frame_operator import FrameOperator

from Utils.messenger import Messenger
from Utils.database_operator import DatabaseOperator, DATABASE_SYMBOL_ODBC
from Utils.serializer import MySerializer
from Utils.image_presenter import Presenter
from Utils.script_runner import ScriptRunner

from User.config_static import (CF_TEMP_TEACH_DIR, CF_RECORDS_ORIGIN_PICTURES_DIR, CF_RECORDS_DETECTION_PICTURES_DIR,
                                CF_TEACH_PINS_MAP_PAGE, CF_DYNAMIC_CONFIG_PATH, CF_TEACH_SCRIPT_FILE)


class MainGrab:
    def __init__(self, arguments: dict):
        # 解析参数
        self.arguments = self.decode_arguments(arguments)

        # 动态参数
        with open(CF_DYNAMIC_CONFIG_PATH, encoding='ascii', errors='ignore') as f:
            self.dynamic_config = yaml.safe_load(f)

        # 数据库
        self.db_operator = DatabaseOperator(symbol=DATABASE_SYMBOL_ODBC)
        # 连接数据库
        is_connected = self.db_operator.connect(path=self.dynamic_config["access_database_path"])
        if not is_connected:
            raise Exception("open access database failed")

        # 相机身份
        self.arguments["inst"] = self.dynamic_config["camera_inst"]
        self.camera_identity = CameraIdentity(**arguments)

        # 创建画面传输管道
        imgbuf_parent_conn, imgbuf_child_conn = Pipe(duplex=False)

        # 创建相机实例
        self.my_camera = MyCamera(
            camera_identity=self.camera_identity,   # 相机身份
            resize_ratio=None,                      # 缩放比例
            rotate_flag=self.dynamic_config["camera_rotate"],     # 旋转标记,
            command_child_conn=None,                # 管道,向控制进程交换消息
            imgbuf_child_conn=imgbuf_child_conn,  # 管道,向显示进程传输相机画面,单向
            thread_name="camera_{}".format(self.camera_identity.serial_number),
            running_cameras_list=None,
            running_cameras_lock=None,
        )

        # 创建Interface实例
        self.interface_camera_grab = InterfaceGrab(
            camera_identity=self.camera_identity,
            db_operator=self.db_operator
        )
        # 绑定信号
        self.bind_function_2_interface()

        # 创建监听实例
        self.imgbuf_listener = ImageBufferListener(
            imgbuf_parent_conn=imgbuf_parent_conn,
            message_callback=Messenger.print
        )
        # 连接信号
        self.imgbuf_listener.showImageBufferSignal.connect(lambda data: self.interface_camera_grab.show_camera_frame(data=data))
        # 开启多线程
        self.imgbuf_listener.start()

        # 创建文件夹
        try:
            os_makedirs(CF_TEMP_TEACH_DIR)
        except:
            pass

    # *********************************  解析参数  ******************************* #
    @staticmethod
    def decode_arguments(arguments: dict) -> dict:
        """
        解析输入的参数
        :param arguments:
        :return:
        """
        line: str = arguments["line"]
        location: str = arguments["location"]
        side: str = arguments["side"]

        ip: str = arguments["ip"]
        port: str = arguments["port"]
        user: str = arguments["user"]
        password: str = arguments["password"]

        if not CameraIdentity.is_ip_valid(ip=ip):
            raise Exception("illegal ip address")

        if not port.isdigit():
            raise Exception("illegal port")

        return arguments

    # *********************************  界面设置  ******************************* #
    def bind_function_2_interface(self):
        """
        绑定信号
        :return:
        """
        # 连接信号
        # 按键
        self.interface_camera_grab.grabOrNotSignal.connect(self.do_grab_or_not)
        self.interface_camera_grab.closeCameraSignal.connect(lambda: self.my_camera.close_camera(message_callback=Messenger.print))

        # 检测或示教
        self.interface_camera_grab.detectSignal.connect(self.do_detect)
        self.interface_camera_grab.teachSignal.connect(self.do_teach)
        self.interface_camera_grab.partTeachSignal.connect(self.do_part_teach)

        # 菜单
        self.interface_camera_grab.connectAlgorithmSignal.connect(self.bind_process_algorithm)
        self.interface_camera_grab.setParametersSignal.connect(self.set_camera_parameters)
        self.interface_camera_grab.savePictureSignal.connect(lambda message: self.save_image(image=self.interface_camera_grab.after_pixmap, message=message))

    # *********************************  相机操作  ******************************* #
    def do_grab_or_not(self, is_checked: bool):
        """
        取流 或 停止
        :param is_checked:
        :return:
        """
        if is_checked:
            self.my_camera.grab_in_thread(
                # frame_operator_callback=None,
                # save_picture_callback=None,
                before_grab_callback=None,
                after_grab_callback=None,
                reset_frame_operator_callback=None,
                message_callback=Messenger.print,
            )
        else:
            self.my_camera.release_grab(
                message_callback=Messenger.print,
            )

    def camera_save_process(self, flag: int, frame_data: np.ndarray, camera_info: dict, message: dict):
        """
        相机保存过程的回调函数
        :param flag:
        :param frame_data:
        :param camera_info:
        :param message:
        :return:
        """
        if flag == 1:
            p = {"frame": frame_data,
                 "message": message,
                 "show_detection_callback": self.interface_camera_grab.show_detection,
                 "record_detection_callback": lambda record_message, origin_frame, detection_frame: self.record_detection(
                     record_message=record_message,
                     origin_frame=origin_frame,
                     detection_frame=detection_frame
                 )}
            target = FrameOperator.offline_process_algorithm
        elif flag == 2:
            p = {"message": message, "frame_data": frame_data}
            target = self.show_teach_interface

        else:
            raise ValueError("illegal flag")

        t = Thread(
            target=target,
            kwargs=p,
            daemon=True
        )
        t.start()

    def set_camera_parameters(self):
        """
        设置相机参数
        :return:
        """
        message = {
            'level': "INFO",
            'title': "信息",
            'text': "该相机没有设置参数功能",
            'informative_text': "",
            'detailed_text': ""
        }
        Messenger.show_message_box(
            widget=self.interface_camera_grab,
            message=message,
        )

    # *********************************  检测  ******************************* #
    def do_detect(self, detect_message: dict):
        """
        进行检测
        :param detect_message:
        :return:
        """
        part = detect_message["Part"]
        serial_number = detect_message["SerialNumber"]
        line = detect_message["Line"]

        # 获取数据
        process_parameters = self.db_operator.get_all_process_parameters(filter_dict={"SerialNumber": serial_number})
        if not process_parameters:
            message = {
                "level": 'WARNING',
                "title": '警告',
                "text": '相机还未进行检测算法的参数示教！',
                "informative_text": '',
                'detailed_text': '请先对相机进行示教'
            }
            Messenger.show_message_box(widget=self.interface_camera_grab, message=message, cancel_button=self.camera_identity)
            return

        # 获取基准pins_map
        pins_map = self.db_operator.get_parts_pins_map(
            filter_dict={"Part": part, "Line": line},
            demand_list=["PinsMap",]
        )
        if pins_map:
            pins_map["PinsMap"] = MySerializer.deserialize(pins_map["PinsMap"])     # 反序列化
            message = dict(**detect_message, **process_parameters, **pins_map)      # 合并字典
            # 设置 save_process_callback 回调函数
            self.my_camera.set_save_picture_callback(
                save_picture_callback=lambda frame_data, camera_info: self.camera_save_process(
                    flag=1,
                    frame_data=frame_data,
                    camera_info=camera_info,
                    message=message
                )
            )
            # 置位保存图片
            self.my_camera.set_to_save(True)

    def record_detection(self, record_message: dict, origin_frame: np.ndarray, detection_frame: np.ndarray):
        """
        记录检测结果
        :param record_message:
        :param origin_frame:
        :param detection_frame:
        :return:
        """
        part = record_message["Part"]
        line = record_message["Line"]
        location = record_message["Location"]

        record_message["When"] = datetime.now()
        time = record_message["When"].strftime('%G%m%d%H%M%S%f')

        record_message["DetectionPicture"] = os_path.join(CF_RECORDS_DETECTION_PICTURES_DIR, "Detection_%s_%s_%s_%s.jpg" % (line, part, location, time))
        record_message["OriginPicture"] = os_path.join(CF_RECORDS_ORIGIN_PICTURES_DIR, "Origin_%s_%s_%s_%s.jpg" % (line, part, location, time))

        cv2.imwrite(record_message["DetectionPicture"], detection_frame)
        cv2.imwrite(record_message["OriginPicture"], origin_frame)

        self.db_operator.set_detection_records(demand_dict=record_message)

    def bind_process_algorithm(self, flag: bool):
        """
        连接图片处理算法
        :param flag:
        :return:
        """
        # TODO 当重新对相机进行示教后，当前的链接算法参数功能不会更新当前相机示教参数
        if flag:
            serial_number = self.my_camera.camera_identity.serial_number
            # 获取数据
            process_parameters = self.db_operator.get_all_process_parameters(filter_dict={"SerialNumber": serial_number})
            if process_parameters:
                self.my_camera.set_frame_operator_callback(
                    frame_operator_callback=lambda frame_data, camera_info: FrameOperator.online_process_algorithm(
                        frame=frame_data,
                        algorithm_parameters=process_parameters
                    )
                )
                return
        else:
            self.my_camera.set_frame_operator_callback(frame_operator_callback=None)

    def save_image(self, image: Union[np.ndarray, QPixmap], message: dict):
        """
        保存图片
        :param image:
        :param message:
        :return:
        """
        now = datetime.now().strftime('%G%m%d%H%M%S%f')
        image_name = "MyDetectionPicture_%s_%s_%s_%s.jpg" % (message["SerialNumber"], message["Part"], message["Line"], now)
        Presenter.save_image(image=image, image_name=image_name, parent=self.interface_camera_grab)

    # *********************************  示教  ******************************* #
    def do_teach(self, teach_message: dict):
        """
        进行示教
        :param teach_message:
        :return:
        """
        # 设置 save_process_callback 回调函数
        self.my_camera.set_save_picture_callback(
            save_picture_callback=lambda frame_data, camera_info: self.camera_save_process(
                flag=2,
                frame_data=frame_data,
                camera_info=camera_info,
                message=teach_message
            )
        )
        # 置位保存图片
        self.my_camera.set_to_save(True)

    def do_part_teach(self, teach_message: dict):
        """
        进行零件示教
        :param teach_message:
        :return:
        """
        serial_number = teach_message["SerialNumber"]
        # 获取数据
        process_parameters = self.db_operator.get_all_process_parameters(filter_dict={"SerialNumber": serial_number})
        if not process_parameters:
            message = {
                "level": 'WARNING',
                "title": '警告',
                "text": '相机还未进行检测算法的参数示教！',
                "informative_text": '',
                'detailed_text': '请先对相机进行示教'
            }
            Messenger.show_message_box(widget=self.interface_camera_grab, message=message, cancel_button=self.camera_identity)
            return

        # 添加起始页
        teach_message["Page"] = CF_TEACH_PINS_MAP_PAGE

        # 进行示教
        self.do_teach(teach_message=teach_message)

    def show_teach_interface(self, message: dict, frame_data: np.ndarray):
        """
        显示示教界面
        :param message:
        :param frame_data:
        :return:
        """

        part = message["Part"]
        if part == "":
            part = "XXX"

        serial_number = message["SerialNumber"]
        line = message["Line"]
        location = message["Location"]
        side = message["Side"]
        page = message.get("Page", 0)

        now = datetime.now().strftime('%G%m%d%H%M%S%f')
        file_name = r"Origin_{now}_{serial_number}_{line}_{location}_{part}.npy".format(
            now=now,
            serial_number=serial_number,
            line=line,
            location=location,
            part=part
        )
        file_path = os_path.join(CF_TEMP_TEACH_DIR, file_name)
        # 保存为二进制文件
        np.save(file_path, frame_data)

        # TODO 运行 python 脚本
        script_parameters = {
            "part": part,
            "serial_number": serial_number,
            "line": line,
            "location": location,
            "side": side,
            "file_path": file_path,
            "page": str(page),
        }
        # 运行 python 脚本
        # C:/Users/yy/anaconda3/envs/py36/python.exe ./main_teach.py --part XXX --serial_number 1921680030042528 --line 5-100 --location RIGHT --side LEFT --file_path .\PinsCtrlData\Temp\Teach\Origin_20240617141715504448_1921680030042528_5-100_RIGHT_XXX.npy --page 0
        subprocess = self.run_teach_script(
            python_path=self.dynamic_config["python_path"],
            script_path=CF_TEACH_SCRIPT_FILE,
            parameters=script_parameters,
        )

        # 开启标准输出监听
        t1 = Thread(
            target=ScriptRunner.get_output_from_subprocess,
            kwargs={
                "subprocess": subprocess,
                "decode_output_callback": self.decode_subprocess_stdout,
            },
            daemon=True
        )
        t1.start()

        t2 = Thread(
            target=ScriptRunner.get_error_from_subprocess,
            kwargs={
                "subprocess": subprocess,
                "decode_error_callback": self.decode_subprocess_error
            },
            daemon=True
        )
        t2.start()

    @staticmethod
    def run_teach_script(python_path: str, script_path: str, parameters: dict):
        """
        运行 grab 脚本
        :param python_path:
        :param script_path:
        :param parameters:
        :return:
        """
        teach_script = ScriptRunner.create_python_script(
            python_path=python_path,
            script_path=script_path,
            parameters=parameters,
        )
        subprocess = ScriptRunner.run_script(
            script=teach_script,
            password=None,
            parameters=None,
            terminal=False,
            is_linux=False
        )

        return subprocess

    @staticmethod
    def decode_subprocess_stdout(pid: int, message: str, command_prefix: str = "command|", role: str = "teach"):
        """
        解析子进程的 stdout
        :param pid:
        :param message:
        :param command_prefix:
        :param role:
        :return:
        """
        # # 发送的字符串 带有 \r\n 转义字符
        # sys.stdout.write("[{}] {}\n".format(subprocess_symbol, message))
        # # 刷新缓冲区，用于立即发送
        # sys.stdout.flush()
        # TODO 处理从其他进程接受的指令
        try:
            if message.startswith(command_prefix):
                prefix_len = len(command_prefix)
                data = json.loads(message[prefix_len:])
                print("[{role} command][{pid}] {data}".format(role=role, pid=pid, data=data))
            else:
                print("[{role} message][{pid}] {message}".format(role=role, pid=pid, message=message))
        except:
            pass

    @staticmethod
    def decode_subprocess_error(pid: int, message: str, role: str = "teach"):
        """
        解析子进程的 stderr
        :param pid:
        :param message:
        :param role:
        :return:
        """
        # TODO 处理从其他进程接受的错误
        # 发送的字符串 带有 \r\n 转义字符
        try:
            sys_stderr.write("[{role} error][{pid}] {message}".format(role=role, pid=pid, message=message))
            # 刷新缓冲区，用于立即发送
            sys_stderr.flush()
        except:
            pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-l", "--line", required=True)
    ap.add_argument("-lo", "--location", required=True)
    ap.add_argument("-s", "--side", required=True)
    ap.add_argument("-i", "--ip", required=True)
    ap.add_argument("-p", "--port", required=True)
    ap.add_argument("-u", "--user", required=True)
    ap.add_argument("-pwd", "--password", required=True)
    parsed_args = vars(ap.parse_args())

    app = QApplication(sys_argv)

    my_grab = MainGrab(arguments=parsed_args)

    # 打开相机
    my_grab.my_camera.open_camera(
        after_opened_callback=None,
        message_callback=Messenger.print,
    )
    # 进行取流
    my_grab.my_camera.grab_in_thread(
        # frame_operator_callback=None,
        # save_picture_callback=None,
        before_grab_callback=None,
        after_grab_callback=None,
        reset_frame_operator_callback=None,
        message_callback=Messenger.print,
    )

    # 显示界面
    my_grab.interface_camera_grab.show()

    ret = app.exec_()

    # 关闭数据库
    my_grab.db_operator.close()

    sys_exit(ret)
