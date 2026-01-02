from typing import Union, Optional
import cv2
import numpy as np
from time import sleep
from threading import Thread
from PyQt5.QtCore import QThread, pyqtSignal
from CameraCore.camera_identity import CameraIdentity
from Utils.messenger import show_message

ROTATE_90_CLOCKWISE = 0
ROTATE_180 = 1
ROTATE_90_COUNTERCLOCKWISE = 2
ROTATE_INEFFECTIVE = 3

USE_VIRTUAL_CAMERA = True
# USE_VIRTUAL_CAMERA = False

# VIRTUAL_CAMERA_PATH = "./PinsCtrlData/Temp/Demo/0 - 2024-05-17 10-13-24-737.avi"
# VIRTUAL_CAMERA_PATH = "./PinsCtrlData/Temp/Demo/0 - 2024-07-08 09-26-53-037.avi"
# VIRTUAL_CAMERA_PATH = "./PinsCtrlData/Temp/Demo/0 - 2024-07-08 09-26-35-260.avi"

# VIRTUAL_CAMERA_PATH = "../PinsCtrlData/Temp/Demo/0 - 2024-05-17 10-13-24-737.avi"
VIRTUAL_CAMERA_PATH = "../PinsCtrlData/Temp/Demo/0 - 2024-07-08 09-26-53-037.avi"
# VIRTUAL_CAMERA_PATH = "../PinsCtrlData/Temp/Demo/0 - 2024-07-08 09-26-35-260.avi"


class MyCamera:

    def __init__(self,
                 camera_identity: CameraIdentity,  # 相机身份
                 resize_ratio: Optional[float] = None,  # 缩放比例
                 rotate_flag: int = ROTATE_INEFFECTIVE,  # 旋转标记, 3 -> 不旋转, 0 -> 顺时针90度, 1 -> 顺时针180度, 2 -> 逆时针90度
                 command_child_conn=None,  # 管道,向控制进程交换消息
                 imgbuf_child_conn=None,  # 管道,向显示进程传输相机画面,单向
                 **kwargs,
                 ):
        # 相机身份
        self.camera_identity = camera_identity

        # 图片处理
        # 缩放比例
        self.resize_ratio: Optional[float] = None
        self.set_resize_ratio(resize_ratio=resize_ratio)
        # 旋转标记
        self.rotate_flag: int = ROTATE_INEFFECTIVE
        self.set_rotate_flag(rotate_flag=rotate_flag)

        # 通信
        self.imgbuf_child_conn = imgbuf_child_conn  # 管道,向显示进程传输相机画面,单向
        self.command_child_conn = command_child_conn  # 管道,向控制进程交换消息

        # 线程名称
        self.thread_name = kwargs.get("thread_name")
        # 运行相机列表 和 锁
        self.__running_cameras_list = kwargs.get("running_cameras_list")
        self.__running_cameras_lock = kwargs.get("running_cameras_lock")

        # video capture 对象
        self.camera = None

        self.width = None
        self.height = None
        # self.fps = None

        # 取流传入的参数
        self.grab_params = dict()

        # 相机动作
        # 打开标志
        self.__open_flag = False
        # 取流标志
        self.__grab_flag = False
        # 保存图片
        self.__to_save = False
        # 停止取流
        self.__to_stop = False
        # 退出标志
        self.__to_exit = False

        # 帧数据处理回调函数
        self.frame_operator_callback = None
        # 保存图片回调函数
        self.save_picture_callback = None

    def __operate_frame(self, frame_data: np.ndarray):
        """
        处理帧数据
        :param frame_data:
        :return:
        """
        # 改变图像大小
        if self.resize_ratio is not None and self.resize_ratio != 1.0:
            frame_data = cv2.resize(
                frame_data, None, None,
                fx=self.resize_ratio,
                fy=self.resize_ratio,
                interpolation=cv2.INTER_AREA
            )

        # 旋转图片
        if self.rotate_flag == ROTATE_90_CLOCKWISE:
            frame_data = cv2.rotate(frame_data, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotate_flag == ROTATE_180:
            frame_data = cv2.rotate(frame_data, cv2.ROTATE_180)
        elif self.rotate_flag == ROTATE_90_COUNTERCLOCKWISE:
            frame_data = cv2.rotate(frame_data, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # 保存原始图片
        if self.__to_save:
            camera_info = {
                "serial_number": self.camera_identity.serial_number,
            }
            t = Thread(
                target=self.save_picture_callback,
                kwargs={
                    "frame_data": frame_data,
                    "camera_info": camera_info,
                },
                daemon=True
            )
            t.start()
            self.__to_save = False

        # 处理图片
        if self.frame_operator_callback is not None:
            camera_info = {
                "serial_number": self.camera_identity.serial_number,
            }
            frame_data = self.frame_operator_callback(
                frame_data=frame_data,
                camera_info=camera_info,
            )

        # 通过pipe管道向GUI进程传输图像画面
        if self.imgbuf_child_conn is not None:
            message = {
                "frame_data": frame_data,
                "camera_info": {
                    "serial_number": self.camera_identity.serial_number,
                },
            }
            try:
                self.imgbuf_child_conn.send(message)
            except Exception as err:
                # TODO image buffer 管道发送异常处理
                message = {
                    "level": 'WARNING',
                    "title": '警告',
                    "text": 'image buffer 管道发送异常！',
                    "informative_text": "错误[{}]".format(err),
                    "detailed_text": ''
                }

    def open_camera(self, **kwargs):
        """
        打开相机
        :param kwargs:
        :return:
        """
        if not USE_VIRTUAL_CAMERA:
            self.camera = cv2.VideoCapture(self.camera_identity.url)
        else:
            self.camera = cv2.VideoCapture(VIRTUAL_CAMERA_PATH)

        # 验证视频是否成功打开
        if not self.camera.isOpened():
            raise Exception("Unable to capture [{}]".format(self.camera_identity.address))

        # 宽度
        self.width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        # 高度
        self.height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # # 帧率
        # self.fps = self.capture.get(cv2.CAP_PROP_FPS)

        self.__open_flag = True
        self.__grab_flag = False
        self.__to_save = False
        self.__to_stop = False
        self.__to_exit = False

        message_callback = kwargs.get("message_callback")
        self.open_device_successful_callback(
            message_callback=message_callback
        )

        after_opened_callback = kwargs.get("after_opened_callback")
        if after_opened_callback is not None:
            after_opened_callback(serial_number=self.camera_identity.serial_number)

    def _do_grab(self, **kwargs):
        """
        相机取流
        :param kwargs:
        :return:
        """
        # 相机未打开
        if not self.__open_flag:
            return

        # 相机已经取流
        if self.__grab_flag:
            return

        # frame_operator_callback = kwargs.get("frame_operator_callback")
        # save_picture_callback = kwargs.get("save_picture_callback")
        before_grab_callback = kwargs.get("before_grab_callback")
        after_grab_callback = kwargs.get("after_grab_callback")
        reset_frame_operator_callback = kwargs.get("reset_frame_operator_callback")
        message_callback = kwargs.get("message_callback")

        self.start_grab_successful_callback(
            message_callback=message_callback
        )

        # 开始取流前的回调函数
        if before_grab_callback is not None:
            before_grab_callback(serial_number=self.camera_identity.serial_number)

        # 加入 running_cameras 列表
        if self.__running_cameras_lock is not None and self.__running_cameras_list is not None:
            with self.__running_cameras_lock:
                self.__running_cameras_list.append(self.camera_identity.serial_number)

        self.__grab_flag = True
        self.__to_save = False
        self.__to_stop = False
        self.__to_exit = False

        while True:

            if self.__to_exit:
                break

            # 停止取流
            if self.__to_stop:
                sleep(0.1)
                continue

            if not self.camera.isOpened():
                break

            res, frame_data = self.camera.read()
            if not res:
                break

            # # 在子线程中处理帧数据
            # t = Thread(
            #     target=self.__operate_frame,
            #     kwargs={
            #         "frame_data": frame_data,
            #     },
            #     daemon=True
            # )
            # t.start()

            # 在主线程中处理帧数据
            self.__operate_frame(
                frame_data=frame_data,
            )

        # 释放摄像头资源
        # self.camera.release()

        self.stop_grab_successful_callback(
            message_callback=message_callback
        )

        self.__grab_flag = False
        self.__to_save = False
        self.__to_stop = False
        self.__to_exit = False

        # 取流结束
        # 移除 running_cameras
        if self.__running_cameras_lock is not None and self.__running_cameras_list is not None:
            with self.__running_cameras_lock:
                self.__running_cameras_list.remove(self.camera_identity.serial_number)

        # 复位帧画面处理回调函数
        if reset_frame_operator_callback is not None:
            reset_frame_operator_callback(serial_number=self.camera_identity.serial_number)

        # 结束取流后的回调函数
        if after_grab_callback is not None:
            after_grab_callback(serial_number=self.camera_identity.serial_number)

    def grab_in_thread(self, **kwargs):
        """
        在多线程中取流
        :return:
        """
        if kwargs:
            self.grab_params.update(kwargs)

        # 取流
        t = Thread(
            target=self._do_grab,
            kwargs=self.grab_params,
            name=self.thread_name,
            # daemon=True,
        )
        t.start()

    def release_grab(self, timeout=2, **kwargs):
        """
        停止取流取流
        :param kwargs:      message_callback = kwargs.get("message_callback")
        :param timeout:
        :return:
        """
        self.__to_exit = True

        i = 0
        sleep_interval = 0.1
        times = timeout // sleep_interval
        while True:
            sleep(sleep_interval)

            if not self.__grab_flag:
                break

            i += 1
            if i >= times:
                message_callback = kwargs.get("message_callback")
                self.stop_grabbing_failed_callback(
                    err_str="停止取流超时",
                    message_callback=message_callback
                )

    def close_camera(self, **kwargs):
        """
        关闭相机
        :return:
        """
        message_callback = kwargs.get("message_callback")
        # 停止取流
        self.release_grab(timeout=2, message_callback=message_callback)

        # 释放摄像头资源
        self.camera.release()
        self.__grab_flag = False

        self.close_device_successful_callback(
            message_callback=message_callback
        )

    # *********************************  设置参数  ******************************* #
    def set_resize_ratio(self, resize_ratio: Union[int, float, None]):
        """
        设置缩放比例
        :param resize_ratio:
        :return:
        """
        if resize_ratio is None:
            self.resize_ratio = None
            return

        try:
            resize_ratio = float(resize_ratio)
        except:
            resize_ratio = None
        self.resize_ratio = resize_ratio

    def set_rotate_flag(self, rotate_flag: int):
        """
        设置旋转标志
        :param rotate_flag:
        :return:
        """
        if rotate_flag != ROTATE_90_CLOCKWISE and rotate_flag != ROTATE_180 and rotate_flag != ROTATE_90_COUNTERCLOCKWISE:
            self.rotate_flag = ROTATE_INEFFECTIVE
        else:
            self.rotate_flag = rotate_flag

    def set_save_picture_callback(self, save_picture_callback):
        self.save_picture_callback = save_picture_callback

    def set_frame_operator_callback(self, frame_operator_callback):
        self.frame_operator_callback = frame_operator_callback

    def set_to_save(self, flag: bool):
        """
        设置保存标志
        :param flag:
        :return:
        """
        self.__to_save = flag

    # *********************************  message  ******************************* #
    @show_message(attributes="camera_identity")
    def open_device_successful_callback(self, **kwargs):
        """
        打开设备成功的回调函数
        :param kwargs:      message_callback = kwargs.get("message_callback")
        :return:
        """
        message = {
            "level": 'INFO',
            "title": '信息',
            "text": '相机打开成功！',
            "informative_text": '',
            "detailed_text": ''
        }
        return message

    @show_message(attributes="camera_identity")
    def start_grab_successful_callback(self, **kwargs):
        """

        :param kwargs:      message_callback = kwargs.get("message_callback")
        :return:
        """
        message = {
            "level": 'INFO',
            "title": '信息',
            "text": '相机开始取流成功！',
            "informative_text": '',
            "detailed_text": ''
        }
        return message

    @show_message(attributes="camera_identity")
    def stop_grab_successful_callback(self, **kwargs):
        """

        :param kwargs:      message_callback = kwargs.get("message_callback")
        :return:
        """
        message = {
            "level": 'INFO',
            "title": '信息',
            "text": '相机停止取流成功！',
            "informative_text": '',
            "detailed_text": ''
        }
        return message

    @show_message(attributes="camera_identity")
    def stop_grabbing_failed_callback(self, err_str: str, **kwargs):
        """
        停止取流失败的回调函数
        :param err_str:
        :param kwargs:      message_callback = kwargs.get("message_callback")
        :return:
        """
        informative_text = '错误事项[%s]' % (err_str,)
        message = {
            "level": 'ERROR',
            "title": '错误',
            "text": '相机停止取流错误！',
            "informative_text": informative_text,
            "detailed_text": ''
        }
        return message

    @show_message(attributes="camera_identity")
    def close_device_successful_callback(self, **kwargs):
        """
        打开设备成功的回调函数
        :param kwargs:      message_callback = kwargs.get("message_callback")
        :return:
        """
        message = {
            "level": 'INFO',
            "title": '信息',
            "text": '相机关闭成功！',
            "informative_text": '',
            "detailed_text": ''
        }
        return message


class ImgBufListener:
    def __init__(self, imgbuf_parent_conn, **kwargs):
        """

        :param imgbuf_parent_conn:
        :param kwargs:              message_callback = kwargs.get("message_callback")
        """
        super().__init__()

        self.imgbuf_parent_conn = imgbuf_parent_conn
        self.message_callback = kwargs.get("message_callback")

        # 线程退出标志
        self.__to_exit = False

    def set_to_exit(self, flag: bool):
        """
        设置推出标志
        :param flag:
        :return:
        """
        self.__to_exit = flag

    def listen(self, operate_imgbuf_message_callback):
        """
        循环接受管道信息
        :param operate_imgbuf_message_callback:
        :return:
        """
        while True:

            if self.__to_exit:
                break

            try:
                # 判断管道中是否有数据
                if not self.imgbuf_parent_conn.poll():
                    continue

                # 接收数据
                message = self.imgbuf_parent_conn.recv()

                # 解析数据
                if isinstance(message, dict) and "camera_info" in message and "frame_data" in message:
                    if operate_imgbuf_message_callback is not None:
                        operate_imgbuf_message_callback(message=message)

            except Exception as err:
                if self.message_callback is not None:
                    message = {
                        "level": 'ERROR',
                        "title": '错误',
                        "text": 'image buffer 管道处理异常！',
                        "informative_text": "错误[{}]".format(err),
                        "detailed_text": ''
                    }
                    self.message_callback(message=message)

        if self.message_callback is not None:
            message = {
                "level": 'INFO',
                "title": '信息',
                "text": 'image buffer 管道监听结束！',
                "informative_text": '',
                "detailed_text": ''
            }
            self.message_callback(message=message)


class ImageBufferListener(QThread, ImgBufListener):
    # 信号
    showImageBufferSignal = pyqtSignal(dict)

    def __init__(self, imgbuf_parent_conn, **kwargs):
        """

        :param imgbuf_parent_conn:
        :param parent:
        :param kwargs:          message_callback = kwargs.get("message_callback")
        """
        super().__init__(imgbuf_parent_conn=imgbuf_parent_conn, **kwargs)

    def operate_imgbuf_message(self, message):
        """
        发送信号
        :param message:
        :return:
        """
        self.showImageBufferSignal.emit(message)

    def run(self):
        self.listen(operate_imgbuf_message_callback=self.operate_imgbuf_message)
