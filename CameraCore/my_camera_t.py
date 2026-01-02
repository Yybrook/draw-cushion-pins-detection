from typing import Optional, Union
import cv2
import numpy as np
import os
from datetime import datetime
from ctypes import c_ubyte, memset, byref, sizeof, create_string_buffer, cdll, CDLL
from threading import Thread
from multiprocessing import Pipe
from time import sleep

from MvImport.CameraParams_const import MV_GIGE_DEVICE, MV_ACCESS_Exclusive, MV_ACCESS_Control, MV_ACCESS_Monitor
from MvImport.CameraParams_header import (MV_CC_DEVICE_INFO_LIST, MV_CC_DEVICE_INFO, MV_FRAME_OUT_INFO_EX,
                                          MV_FRAME_OUT, MV_SAVE_IMAGE_TO_FILE_PARAM_EX, MV_Image_Jpeg, MV_Image_Png, MV_Image_Bmp)
from MvImport.MvErrorDefine_const import MV_OK
from MvImport.PixelType_header import PixelType_Gvsp_Mono8, PixelType_Gvsp_RGB8_Packed


from CameraCore.camera_operator import CameraOperator
from CameraCore.camera_identity import CameraIdentity
from CameraCore.camera_err_header import *
from CameraCore.communica_message_header import *

from Utils.messenger import Messenger

# libc = CDLL("libc.so.6")  # linux 使用memcpy函数  ??


VIRTUAL_CAMERA_SERIAL_NUMBER_PREFIX = "Vir"


class MyCamera(CameraOperator):
    # 全局变量,列表,存放枚举到的 cameras_identity
    enum_cameras_identity: list = list()

    # 锁
    # lock = Lock()

    def __init__(self,
                 camera_identity: CameraIdentity,       # 相机身份
                 name: Optional[str] = None,
                 resize_ratio: Optional[float] = None,  # 缩放比例
                 rotate_flag: Optional[int] = None,     # 旋转标记, 0 -> 不旋转, 1 -> 顺时针90度, 2 -> 顺时针180度, 3 -> 逆时针90度
                 access_mode: int = MV_ACCESS_Exclusive,    # 组播方式
                 msg_child_conn=None,                   # 管道,向控制进程交换消息
                 imgbuf_child_conn=None,                # 管道,向显示进程传输相机画面,单向
                 *args, **kwargs
                 ):

        super().__init__()
        # 线程名称
        self.name = name

        # 相机身份
        self.camera_identity: CameraIdentity = camera_identity

        # 图片处理
        self.resize_ratio: Optional[float] = resize_ratio  # 缩放比例
        # 旋转标记, 0 -> 不旋转, 1 -> 顺时针90度, 2 -> 顺时针180度, 3 -> 逆时针90度
        self.rotate_flag: Optional[int] = rotate_flag
        # 组播方式
        self.access_mode: int = access_mode

        # 通信
        self.imgbuf_child_conn = imgbuf_child_conn      # 管道,向显示进程传输相机画面,单向
        self.msg_child_conn = msg_child_conn            # 管道,向控制进程交换消息

        # 回调函数
        # 图片处理回调函数
        self.frame_process_callback = kwargs.get("frame_process_callback")
        # 抓取图片处理回调函数
        self.save_process_callback = kwargs.get("save_process_callback")
        # 抓取图片处理成功函数
        self.save_process_successful_callback = kwargs.get("save_process_successful_callback")
        # 开始取流前的回调函数
        self.before_grab_callback = kwargs.get("before_grab_callback")
        # 结束取流后的回调函数
        self.after_grab_callback = kwargs.get("after_grab_callback")
        # running_cameras 的Manager数据共享对象
        self.running_cameras_manager = kwargs.get("running_cameras_manager")
        # running_cameras 的锁
        self.running_cameras_lock = kwargs.get("running_cameras_lock")

        # 相机状态标志
        # 打开标志
        self.open_flag: bool = False
        # 取流标志
        self.grab_flag: bool = False

        # 相机动作
        # 保存图片
        self.to_save: bool = False
        # 停止取流
        self.to_stop: bool = False

        # 退出进程动作
        self.to_exit: bool = False

    # 标志位
    def get_open_flag(self) -> bool:
        """
        获取打开标志
        :return:
        """
        return self.open_flag

    def set_open_flag(self, flag):
        """
        设置打开标志
        :param flag:
        :return:
        """
        self.open_flag = flag

    def get_grab_flag(self) -> bool:
        """
        获取取流标志
        :return:
        """
        return self.grab_flag

    def set_grab_flag(self, flag):
        """
        设置取流标志
        :param flag:
        :return:
        """
        self.grab_flag = flag

    def get_to_stop(self) -> bool:
        """
        获取停止取流
        :return:
        """
        return self.to_stop

    def set_to_stop(self, flag):
        """
        设置停止取流
        :param flag:
        :return:
        """
        self.to_stop = flag

    def get_to_save(self) -> bool:
        """
        获取保存图片
        :return:
        """
        return self.to_save

    def set_to_save(self, flag):
        """
        设置保存图片
        :param flag:
        :return:
        """
        self.to_save = flag

    def get_to_exit(self) -> bool:
        """
        获取退出进程标志
        :return:
        """
        return self.to_exit

    def set_to_exit(self, flag):
        """
        设置退出进程标志
        :param flag:
        :return:
        """
        self.to_exit = flag

    # 全局变量 枚举列表
    @staticmethod
    def reset_enum_cameras_identity():
        """
        复位枚举到的 cameras_identity
        :return:
        """
        MyCamera.enum_cameras_identity.clear()

    @staticmethod
    def get_enum_cameras_identity() -> list:
        """
        获取枚举到的 cameras_identity
        :return:
        """
        return MyCamera.enum_cameras_identity

    @staticmethod
    def add_enum_cameras_identity(camera_identity: CameraIdentity):
        """
        追加枚举到的 cameras_identity
        :param camera_identity:
        :return:
        """
        MyCamera.enum_cameras_identity.append(camera_identity)

    # 枚举相机在主进程中运行
    @staticmethod
    def enum_cameras(*args, **kwargs) -> int:
        """
        枚举相机
        :return:
        """
        filter_callback = kwargs.get("filter_callback")
        fill_in_table_callback = kwargs.get("fill_in_table_callback")
        message_callback = kwargs.get("message_callback")

        MyCamera.reset_enum_cameras_identity()

        return MyCamera.enum_devices(device_type=MV_GIGE_DEVICE,
                                     enum_err_callback=
                                     lambda err_code, err_str: MyCamera.enum_err_callback(err_code=err_code, err_str=err_str, message_callback=message_callback),
                                     enum_none_callback=
                                     lambda err_code, err_str: MyCamera.enum_none_callback(err_code=err_code, err_str=err_str, message_callback=message_callback),
                                     enum_successful_callback=
                                     lambda device_info_list, device_num: MyCamera.enum_successful_callback(device_info_list=device_info_list,
                                                                                                            device_num=device_num,
                                                                                                            filter_callback=filter_callback,
                                                                                                            fill_in_table_callback=fill_in_table_callback,
                                                                                                            message_callback=message_callback))

    @staticmethod
    def enum_err_callback(err_code: int, err_str: str, *args, **kwargs):
        """
        枚举错误回调函数
        :param err_code:
        :param err_str:
        :return:
        """
        message_callback = kwargs.get("message_callback")

        level = 'ERROR'
        title = '错误'
        text = '枚举相机错误！'
        informative_text = '错误事项[%s]，错误代码[%#X]' % (err_str, err_code)
        detailed_text = ''

        if message_callback is not None:
            message = {"level": level, "title": title, "text": text, "informative_text": informative_text, "detailed_text": detailed_text}
            message_callback(message=message)

    @staticmethod
    def enum_none_callback(err_code: int, err_str: str, *args, **kwargs):
        """
        没有枚举到设备回调函数
        :param err_code:
        :param err_str:
        :return:
        """
        message_callback = kwargs.get("message_callback")

        level = 'WARNING'
        title = '警告'
        text = '枚举相机错误！'
        informative_text = '错误事项[%s]，错误代码[%#X]' % (err_str, err_code)
        detailed_text = '建议检查相关设备IP地址和网络连接'

        if message_callback is not None:
            message = {"level": level, "title": title, "text": text, "informative_text": informative_text, "detailed_text": detailed_text}
            message_callback(message=message)

    @staticmethod
    def enum_successful_callback(device_info_list: MV_CC_DEVICE_INFO_LIST, device_num: int, *args, **kwargs):
        """
        枚举成功回调函数
        :param device_info_list:
        :param device_num:
        :param args:
        :param kwargs:
        :return:
        """
        filter_callback = kwargs.get("filter_callback")
        fill_in_table_callback = kwargs.get("fill_in_table_callback")
        # message_callback = kwargs.get("message_callback")
        #
        # level = 'INFO'
        # title = '信息'
        # text = '枚举相机成功！'
        # informative_text = '相机数量 [%d]' % (device_num,)
        # detailed_text = ''

        for index in range(device_num):
            # 解析设备信息
            st_device_info: MV_CC_DEVICE_INFO = MyCamera.get_st_device_info(device_info_list=device_info_list, device_index=index)
            device_info: dict = MyCamera.decode_device_info(st_device_info=st_device_info, device_index=index)

            if filter_callback is not None:
                if filter_callback(device_info=device_info):
                    camera_identity: CameraIdentity = CameraIdentity(st_device_info=st_device_info,
                                                                     device_index=device_info.get("DeviceIndex"),
                                                                     uid=device_info.get("Uid"),
                                                                     serial_number=device_info.get("SerialNumber"),
                                                                     current_ip=device_info.get("CurrentIp"),
                                                                     model_name=device_info.get("ModelName"))
                    MyCamera.add_enum_cameras_identity(camera_identity=camera_identity)
                    # detailed_text = detailed_text + '\n' + str(camera_identity)
            else:
                camera_identity: CameraIdentity = CameraIdentity(st_device_info=st_device_info,
                                                                 device_index=device_info.get("DeviceIndex"),
                                                                 uid=device_info.get("Uid"),
                                                                 serial_number=device_info.get("SerialNumber"),
                                                                 current_ip=device_info.get("CurrentIp"),
                                                                 model_name=device_info.get("ModelName"))
                MyCamera.add_enum_cameras_identity(camera_identity=camera_identity)
                # detailed_text = detailed_text + '\n' + str(camera_identity)

        # 向表格中填入枚举结果
        if fill_in_table_callback is not None:
            fill_in_table_callback(cameras_identity=MyCamera.enum_cameras_identity)

        # if message_callback is not None:
        #     message = {"level": level, "title": title, "text": text, "informative_text": informative_text, "detailed_text": detailed_text}
        #     message_callback(message=message)

    # 以下在子进程中运行
    def background_listening(self):
        """
        监听管道
        :return:
        """
        if self.msg_child_conn is not None:
            while not self.get_to_exit():
                sleep(0.1)
                try:
                    # 判断管道中是否有数据
                    if not self.msg_child_conn.poll():
                        continue
                    # 接收数据
                    data = self.msg_child_conn.recv()
                    # 解析数据
                    if isinstance(data, dict):
                        self.set_parameters(commands=data)
                    elif isinstance(data, int):
                        self.set_commands(command=data)
                except Exception as err:
                    level = 'ERROR'
                    title = '错误'
                    text = '子管道意外关闭！'
                    informative_text = str(err)
                    detailed_text = ''
                    Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

            self.msg_child_conn.close()
        else:
            while not self.get_to_exit():
                sleep(0.1)

        level = 'INFO'
        title = '信息'
        text = '进程结束！'
        informative_text = ''
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def open_camera(self, access_mode: int = MV_ACCESS_Exclusive, multicast_ip: Union[str, list, None] = None, multicast_port: int = 1042) -> int:
        """
        打开相机
        :param access_mode:
        :param multicast_ip:    字符串类型 -> "239.192.1.1"  列表类型 -> ["239", "192", "1", "1"]  None -> 根据相机IP设置
        :param multicast_port:
        :return:
        """
        if not self.get_open_flag():
            # 创建句柄
            st_device_info = self.camera_identity.st_device_info
            ret = self.create_handle(st_device_info=st_device_info,
                                     create_handle_failed_callback=self.create_handle_failed_callback)
            if ret != MV_OK:
                return ret

            # 打开设备
            ret = self.open_device(access_mode=access_mode,
                                   open_device_failed_callback=self.open_device_failed_callback,
                                   open_device_successful_callback=self.open_device_successful_callback)
            if ret != MV_OK:
                return ret

            # 优化网络最佳包大小
            # 虚拟相机不可用
            if VIRTUAL_CAMERA_SERIAL_NUMBER_PREFIX not in self.camera_identity.serial_number:
                ret = self.optimize_PacketSize(get_value_failed_callback=self.get_PacketSize_failed_callback,
                                               set_value_successful_callback=self.set_PacketSize_successful_callback,
                                               set_value_failed_callback=self.set_PacketSize_failed_callback)
                if ret != MV_OK:
                    # 关闭设备
                    self.close_device()
                    # 释放句柄
                    self.destroy_handle()
                    return ret

            # 设置组播
            if access_mode == MV_ACCESS_Control or access_mode == MV_ACCESS_Monitor:
                if multicast_ip is None:
                    multicast_ip = ["239", "192", "1", self.camera_identity.current_ip.split('.')[3]]
                ret = self.set_multicast_TransmissionType(ip=multicast_ip, port=multicast_port,
                                                          set_multicast_successful_callback=self.set_multicast_successful_callback,
                                                          set_multicast_failed_callback=self.set_multicast_failed_callback)
                if ret != MV_OK:
                    # 关闭设备
                    self.close_device()
                    # 释放句柄
                    self.destroy_handle()
                    return ret

            self.set_open_flag(True)    # 打开标志
            self.set_grab_flag(False)   # 取流标志
            self.set_to_stop(False)     # 停止取流动作

            return ret

        else:
            ret = CAMERA_REPEAT_OPEN
            self.open_device_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
            return ret

    def create_handle_failed_callback(self, err_code: int, err_str: str):
        """
        枚举错误回调函数
        :param err_code:
        :param err_str:
        :return:
        """
        level = 'ERROR'
        title = '错误'
        text = '相机创建句柄错误！'
        informative_text = '错误事项[%s]，错误代码[%#X]' % (err_str, err_code)
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def open_device_failed_callback(self, err_code: int, err_str: str):
        """
        枚举错误回调函数
        :param err_code:
        :param err_str:
        :return:
        """
        level = 'ERROR'
        title = '错误'
        text = '相机打开错误！'
        informative_text = '错误事项[%s]，错误代码[%#X]' % (err_str, err_code)
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def open_device_successful_callback(self):
        level = 'INFO'
        title = '信息'
        text = '相机打开成功！'
        informative_text = ''
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def set_multicast_failed_callback(self, err_code: int, err_str: str):
        """
        设置组播错误
        :param err_code:
        :param err_str:
        :return:
        """
        level = 'ERROR'
        title = '错误'
        text = '相机设置组播错误！'
        informative_text = '错误事项[%s]，错误代码[%#X]' % (err_str, err_code)
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def set_multicast_successful_callback(self):
        """
        设置组播成功
        :return:
        """
        level = 'INFO'
        title = '信息'
        text = '相机设置组播成功！'
        informative_text = ''
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def set_PacketSize_successful_callback(self):
        """
        设置网络最佳包大小成功
        :return:
        """
        level = 'INFO'
        title = '信息'
        text = '相机设置网络最佳包大小成功！'
        informative_text = ''
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def set_PacketSize_failed_callback(self, err_code: int, err_str: str):
        """
        设置网络最佳包大小错误
        :param err_code:
        :param err_str:
        :return:
        """
        level = 'ERROR'
        title = '错误'
        text = '相机设置网络最佳包大小错误！'
        informative_text = '错误事项[%s]，错误代码[%#X]' % (err_str, err_code)
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def get_PacketSize_failed_callback(self, err_code: int, err_str: str):
        """
        获取网络最佳包大小错误
        :param err_code:
        :param err_str:
        :return:
        """
        level = 'ERROR'
        title = '错误'
        text = '相机获取网络最佳包大小错误！'
        informative_text = '错误事项[%s]，错误代码[%#X]' % (err_str, err_code)
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def grab(self) -> int:
        """
        开始取流
        :return:
        """
        # 判断相机被打开,并且没有开始取流
        if self.get_open_flag() and not self.get_grab_flag():

            # 方法2 -> 获取数据包大小
            # res = self.get_PayloadSize()
            # if res['ret'] != MV_OK:
            #     return res['ret']
            # payload_size = int(res['nCurValue'])

            # 开始取流
            ret = self.start_grabbing(start_grabbing_successful_callback=self.start_grabbing_successful_callback,
                                      start_grabbing_failed_callback=self.start_grabbing_failed_callback)
            if ret != MV_OK:
                return ret

            # 开始取流前的回调函数
            if self.before_grab_callback is not None:
                self.before_grab_callback()

            # 加入 running_cameras
            if self.running_cameras_lock is not None and self.running_cameras_manager is not None:
                with self.running_cameras_lock:
                    self.running_cameras_manager.append(self.camera_identity.serial_number)

            self.set_grab_flag(True)    # 取流标志
            self.set_to_stop(False)     # 停止取流动作

            # 持续取流
            self.do_grabbing()

            # 移除 running_cameras
            if self.running_cameras_lock is not None and self.running_cameras_manager is not None:
                with self.running_cameras_lock:
                    self.running_cameras_manager.remove(self.camera_identity.serial_number)

            # 结束取流后的回调函数
            if self.after_grab_callback is not None:
                self.after_grab_callback()

            # 停止取流
            ret = self.stop_grabbing(stop_grabbing_successful_callback=self.stop_grabbing_successful_callback,
                                     stop_grabbing_failed_callback=self.stop_grabbing_failed_callback)

            self.set_grab_flag(False)   # 取流标志
            self.set_to_stop(False)     # 停止取流动作

            return ret
        else:
            if not self.get_open_flag():
                ret = CAMERA_NOT_OPEN
            else:
                ret = CAMERA_REPEAT_GRABBING
            self.start_grabbing_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
            return ret

    # 帧处理函数
    def do_grabbing(self, millisecond: int = 1000):
        """
        持续取流
        :param millisecond:
        :return:
        """
        # 方法1 -> 创建图像结构体
        st_frame_out: MV_FRAME_OUT = MV_FRAME_OUT()
        memset(byref(st_frame_out), 0, sizeof(st_frame_out))
        # 方法2 -> 创建图像帧结构体
        # st_frame_out_info = MV_FRAME_OUT_INFO_EX()
        # memset(byref(st_frame_out_info), 0, sizeof(st_frame_out_info))
        # 图像帧数据指针
        # p_data = (c_ubyte * payload_size)()

        # 图像缓存
        frame_buf = None

        while True:
            # 停止取流动作
            if self.get_to_stop():
                break

            # 方法1 -> 获取图像缓存
            ret = self.MV_CC_GetImageBuffer(st_frame_out, millisecond)
            # 方法2 -> 获取图像缓存到 p_data
            # ret = self.MV_CC_GetOneFrameTimeout(p_data, payload_size, st_frame_out_info, 10)
            if ret != MV_OK:
                # err_str = self.err_code_map(err_code=ret)
                # print("[%s] -> get no data, error: [%#X, %s] " % (self.camera_identity.uid, ret, err_str))
                continue

            # 开辟图像流缓存空间大小
            st_frame_out_info: MV_FRAME_OUT_INFO_EX = st_frame_out.stFrameInfo
            if frame_buf is None:
                frame_buf = (c_ubyte * st_frame_out_info.nFrameLen)()

            # 将 p_data 复制到 frame_buf
            # windows
            # 方法1
            cdll.msvcrt.memcpy(byref(frame_buf), st_frame_out.pBufAddr, st_frame_out_info.nFrameLen)
            # # 方法2
            # # cdll.msvcrt.memcpy(byref(frame_buf), p_data, st_frame_out_info.nFrameLen)
            # linux。在linux中, 没有cdll.msvcrt.memcpy, 使用libc = CDLL("libc.so.6").memcpy代替
            # # 方法1
            # libc.memcpy(byref(frame_buf), st_frame_out.pBufAddr, st_frame_out_info.nFrameLen)
            # # 方法2
            # # libc.memcpy(byref(frame_buf), p_data, st_frame_out_info.nFrameLen)

            width = st_frame_out_info.nWidth  # 图片宽度
            height = st_frame_out_info.nHeight  # 图片高度
            '''
            frombuffer -> 将data以流的形式读入转化成nparray对象
                          numpy.frombuffer(buffer, dtype=float, count=-1, offset=0)
                          参数:
                            buffer: 缓冲区，它表示暴露缓冲区接口的对象。
                            dtype： 代表返回的数据类型数组的数据类型。默认值为0。
                            count： 代表返回的ndarray的长度。默认值为-1。
                            offset：偏移量，代表读取的起始位置。默认值为0。
            '''
            # numpy 数组长度为 [nWidth * nHeight], 数据类型为np.uint8
            frame_data: np.ndarray = np.frombuffer(frame_buf, count=st_frame_out_info.nFrameLen, dtype=np.uint8, offset=0)

            # 将一维数组转化为三维数组
            # # 灰度图
            # frame_data = np.reshape(frame_data, (height, width))
            # 将一维数组转化为三维数组
            # 灰度图
            if st_frame_out_info.enPixelType == PixelType_Gvsp_Mono8:
                frame_data = np.reshape(frame_data, (height, width))
            # RGB
            elif st_frame_out_info.enPixelType == PixelType_Gvsp_RGB8_Packed:
                frame_data = np.reshape(frame_data, (height, width, -1))
                frame_data = cv2.cvtColor(src=frame_data, code=cv2.COLOR_RGB2BGR)
            else:
                raise Exception("pixel type[%d] has not supported" % st_frame_out_info.enPixelType)
            # 开始加锁
            # MyCamera.lock.acquire()

            # 改变图像大小
            if self.resize_ratio is not None and self.resize_ratio != 1.0:
                frame_data = cv2.resize(frame_data, None, None, fx=self.resize_ratio, fy=self.resize_ratio, interpolation=cv2.INTER_AREA)

            # 旋转图片
            if self.rotate_flag == 1:
                frame_data = cv2.rotate(frame_data, cv2.ROTATE_90_CLOCKWISE)
            elif self.rotate_flag == 2:
                frame_data = cv2.rotate(frame_data, cv2.ROTATE_180)
            elif self.rotate_flag == 3:
                frame_data = cv2.rotate(frame_data, cv2.ROTATE_90_COUNTERCLOCKWISE)

            # 保存图片
            if self.get_to_save():
                parameters = {"SerialNumber": self.camera_identity.serial_number, "Uid": self.camera_identity.uid}
                self.save_process_callback(frame_data=frame_data, parameters=parameters)
                self.set_to_save(False)

            # 处理帧数据
            if self.frame_process_callback is not None:
                # parameters = {"st_frame_out_info": st_frame_out_info}
                parameters = dict()
                frame_data = self.frame_process_callback(frame_data=frame_data, parameters=parameters)

            # 通过pipe管道向GUI进程传输图像画面
            if self.imgbuf_child_conn is not None:
                self.imgbuf_child_conn.send({"SerialNumber": self.camera_identity.serial_number, "FrameData": frame_data})

            # 释放锁
            # MyCamera.lock.release()

            # 方法1 -> 释放缓存
            self.MV_CC_FreeImageBuffer(st_frame_out)

        # 关闭相机后处理变量
        if frame_buf is not None:
            del frame_buf
        # 方法2
        # del p_data

    def release_grab(self) -> int:
        """
        释放持续取流
        :return:
        """
        # 相机打开,并且已经开始取流
        if self.get_open_flag() and self.get_grab_flag():
            self.set_to_stop(True)      # 停止取流动作
            return MV_OK
        else:
            if not self.get_open_flag():
                ret = CAMERA_NOT_OPEN
            else:
                ret = CAMERA_NOT_GRABBING
            self.stop_grabbing_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
            return ret

    def start_grabbing_successful_callback(self):
        level = 'INFO'
        title = '信息'
        text = '相机开始取流成功！'
        informative_text = ''
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def start_grabbing_failed_callback(self, err_code: int, err_str: str):
        """
        枚举错误回调函数
        :param err_code:
        :param err_str:
        :return:
        """
        level = 'ERROR'
        title = '错误'
        text = '相机开始取流错误！'
        informative_text = '错误事项[%s]，错误代码[%#X]' % (err_str, err_code)
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def stop_grabbing_successful_callback(self):
        """
        枚举错误回调函数
        :return:
        """
        level = 'INFO'
        title = '信息'
        text = '相机停止取流成功！'
        informative_text = ''
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def stop_grabbing_failed_callback(self, err_code: int, err_str: str):
        """
        枚举错误回调函数
        :param err_code:
        :param err_str:
        :return:
        """
        level = 'ERROR'
        title = '错误'
        text = '相机停止取流错误！'
        informative_text = '错误事项[%s]，错误代码[%#X]' % (err_str, err_code)
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def open_and_grab_in_thread(self) -> int:
        """
        打开相机，在多线程中取流
        :return:
        """
        # 打开相机
        ret = self.open_camera(access_mode=self.access_mode)
        if ret == MV_OK:
            # 取流
            self.grab_in_thread()
        return ret

    def grab_in_thread(self):
        """
        在多线程中取流
        :return:
        """
        t0 = Thread(target=self.grab, name=self.name)
        # t0.setDaemon(True)
        # t0.setDaemon(False)
        t0.start()

    def grab_or_not(self, flag: bool):
        """
        取流或停止取流
        :param flag:
        :return:
        """
        if flag:
            self.grab_in_thread()
        else:
            self.release_grab()

    def close_camera(self) -> int:
        """
        关闭相机
        :return:
        """
        if self.get_open_flag():

            if self.get_grab_flag():
                # 停止取流动作
                self.set_to_stop(True)
                while self.get_grab_flag():
                    sleep(0.1)

            # 关闭设备
            self.close_device(close_device_failed_callback=self.close_device_failed_callback,
                              close_device_successful_callback=self.close_device_successful_callback)
            # 释放句柄
            self.destroy_handle(destroy_handle_failed_callback=self.destroy_handle_failed_callback,
                                destroy_handle_successful_callback=self.destroy_handle_successful_callback)
            # 退出进程动作
            self.set_to_exit(True)
            # 打开标志
            self.set_open_flag(False)

            return MV_OK
        else:
            ret = CAMERA_NOT_OPEN
            self.close_device_failed_callback(err_code=ret, err_str=self.err_code_map(err_code=ret))
            return ret

    def close_device_failed_callback(self, err_code: int, err_str: str):
        """
        关闭相机错误回调函数
        :param err_code:
        :param err_str:
        :return:
        """
        level = 'ERROR'
        title = '错误'
        text = '相机关闭错误！'
        informative_text = '错误事项[%s]，错误代码[%#X]' % (err_str, err_code)
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def close_device_successful_callback(self):
        """
        关闭相机成功回调函数
        :return:
        """
        level = 'INFO'
        title = '信息'
        text = '相机关闭成功！'
        informative_text = ''
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def destroy_handle_failed_callback(self, err_code: int, err_str: str):
        """
        销毁句柄错误回调函数
        :param err_code:
        :param err_str:
        :return:
        """
        level = 'ERROR'
        title = '错误'
        text = '相机销毁句柄错误！'
        informative_text = '错误事项[%s]，错误代码[%#X]' % (err_str, err_code)
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def destroy_handle_successful_callback(self):
        """
        销毁句柄错误回调函数
        :return:
        """
        level = 'INFO'
        title = '信息'
        text = '相机销毁句柄成功！'
        informative_text = ''
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def save_picture(self, saved_folder: str, *args, **kwargs) -> bool:
        """
        保存图片
        :param saved_folder:
        :param args:
        :param kwargs:
        :return:
        """
        if "frame_data" in kwargs:
            frame_data = kwargs["frame_data"]

            # 保证文件夹存在
            if not os.path.exists(saved_folder):
                os.makedirs(saved_folder)

            # 保存路径和格式
            now_time: str = datetime.now().strftime('%G' + '%m' + "%d" + "%H" + "%M" + "%S" + "%f")
            image_type = kwargs.get("image_type")
            if isinstance(image_type, str):
                file_format = image_type.lower()
                if file_format != "png" and file_format != "bmp":
                    file_format = "jpg"
            else:
                file_format = "jpg"
            pic_name: str = "Camera_%s_%s.%s" % (self.camera_identity.uid, now_time, file_format)
            saved_path: str = os.path.join(saved_folder, pic_name)

            # 图片质量
            quality = kwargs.get("quality")
            if isinstance(quality, int) and 0 < quality <= 100:
                cv2.imwrite(saved_path, frame_data, [cv2.IMWRITE_JPEG_QUALITY, quality])
            else:
                cv2.imwrite(saved_path, frame_data)

            save_picture_successful_callback = kwargs.get("save_picture_successful_callback")
            if save_picture_successful_callback is not None:
                save_picture_successful_callback(saved_path=saved_path)

            return True

        if "pBufAddr" in kwargs and "st_frame_out_info" in kwargs:
            # 保证文件夹存在
            if not os.path.exists(saved_folder):
                os.makedirs(saved_folder)

            pBufAddr = kwargs["pBufAddr"]
            st_frame_out_info = kwargs["st_frame_out_info"]
            st_save_param = MV_SAVE_IMAGE_TO_FILE_PARAM_EX()

            # 图片尺寸和像素格式
            st_save_param.enPixelType = st_frame_out_info.enPixelType
            st_save_param.nWidth = st_frame_out_info.nWidth
            st_save_param.nHeight = st_frame_out_info.nHeight
            st_save_param.nDataLen = st_frame_out_info.nFrameLen

            # 图片数据
            # st_save_param.pData = cast(frame_buf, POINTER(c_ubyte))
            st_save_param.pData = pBufAddr

            # 文件格式
            image_type = kwargs.get("image_type")
            if isinstance(image_type, str):
                if image_type.lower() == "jpg":
                    enImageType = MV_Image_Jpeg
                    file_format = "jpg"
                elif image_type.lower() == "png":
                    enImageType = MV_Image_Png
                    file_format = "png"
                elif image_type.lower() == "bmp":
                    enImageType = MV_Image_Bmp
                    file_format = "bmp"
                else:
                    enImageType = MV_Image_Jpeg
                    file_format = "jpg"
            else:
                enImageType = MV_Image_Jpeg
                file_format = "jpg"
            st_save_param.enImageType = enImageType

            # 图片质量
            quality = kwargs.get("quality")
            if isinstance(quality, int) and 0 < quality <= 100:
                st_save_param.nQuality = quality
            else:
                st_save_param.nQuality = 80

            # 保存路径
            now_time: str = datetime.now().strftime('%G' + '%m' + "%d" + "%H" + "%M" + "%S" + "%f")
            pic_name: str = "Camera_%s_%s.%s" % (self.camera_identity.uid, now_time, file_format)
            saved_path: str = os.path.join(saved_folder, pic_name)
            st_save_param.pcImagePath = create_string_buffer(saved_path.encode())

            st_save_param.iMethodValue = 2

            # 保存
            self.MV_CC_SaveImageToFileEx(st_save_param)

            save_picture_successful_callback = kwargs.get("save_picture_successful_callback")
            if save_picture_successful_callback is not None:
                save_picture_successful_callback(saved_path=saved_path)

            return True

        save_picture_failed_callback = kwargs.get("save_picture_failed_callback")
        if save_picture_failed_callback is not None:
            save_picture_failed_callback(err_str="缺少图片数据")
        return False

    @staticmethod
    def image_callback(p_data, p_st_frame_out_info, p_user):
        """
        相机的回调函数，相机获得每一帧后会执行这个函数，
        在 register_image_callback 函数中会使用这个回调函数
        :param p_data:          相机帧数据指针     POINTER(c_ubyte)
        :param p_st_frame_out_info:    帧信息结构体      POINTER(MV_FRAME_OUT_INFO_EX)
        :param p_user:          用户自定义信息     int 或 None，在这里传入的是相机uid
        :return:
        """
        # # 读取指针
        # # 帧信息 MV_FRAME_OUT_INFO_EX结构体 指针
        # st_frame_out_info = cast(p_st_frame_out_info, POINTER(MV_FRAME_OUT_INFO_EX)).contents
        # # 帧数据指针，保存年每一帧的画面numpy数组，长度为st_frame_info.nFrameLen，类型为c_ubyte
        # data = cast(p_data, POINTER(c_ubyte * st_frame_out_info.nFrameLen)).contents
        # # 用户自定义信息
        # # str
        # user_data = str(cast(p_user, c_char_p).value, encoding="utf-8")
        # # int
        # # user_data = p_user
        pass

    def set_parameters(self, commands: dict):
        """
        设置相关参数
        :param commands:
        :return:
        """
        # 缩放比例
        if "resize_ratio" in commands:
            command = "resize_ratio"
            self.resize_ratio = float(commands[command])
            self.set_value_successful_callback(command=command)
        # 旋转标记
        if "rotate_flag" in commands:
            command = "rotate_flag"
            self.rotate_flag = int(commands[command])
            self.set_value_successful_callback(command=command)
        # 触发方式
        if "trigger_mode" in commands:
            command = "trigger_mode"
            trigger_mode = int(commands[command])
            self.set_TriggerMode(TriggerMode=trigger_mode,
                                 set_value_successful_callback=lambda: self.set_value_successful_callback(command=command),
                                 set_value_failed_callback=lambda err_code, err_str: self.set_value_failed_callback(err_code=err_code, err_str=err_str, command=command))
        # 触发源
        if "trigger_source" in commands:
            command = "trigger_source"
            trigger_source = int(commands[command])
            self.set_TriggerSource(TriggerSource=trigger_source,
                                   set_value_successful_callback=lambda: self.set_value_successful_callback(command=command),
                                   set_value_failed_callback=lambda err_code, err_str: self.set_value_failed_callback(err_code=err_code, err_str=err_str, command=command))
        # 曝光模式
        if "exposure_auto" in commands:
            command = "exposure_auto"
            exposure_auto = int(commands[command])
            self.set_ExposureAuto(ExposureAuto=exposure_auto,
                                  set_value_successful_callback=lambda: self.set_value_successful_callback(command=command),
                                  set_value_failed_callback=lambda err_code, err_str: self.set_value_failed_callback(err_code=err_code, err_str=err_str, command=command))
        # 曝光时间 us
        if "exposure_time" in commands:
            command = "exposure_time"
            exposure_time = float(commands[command])
            self.set_ExposureTime(ExposureTime=exposure_time,
                                  set_value_successful_callback=lambda: self.set_value_successful_callback(command=command),
                                  set_value_failed_callback=lambda err_code, err_str: self.set_value_failed_callback(err_code=err_code, err_str=err_str, command=command))
        # 增益
        if "gain" in commands:
            command = "gain"
            gain = float(commands[command])
            self.set_Gain(Gain=gain,
                          set_value_successful_callback=lambda: self.set_value_successful_callback(command=command),
                          set_value_failed_callback=lambda err_code, err_str: self.set_value_failed_callback(err_code=err_code, err_str=err_str, command=command))
        # 增益模式
        if "gain_auto" in commands:
            command = "gain_auto"
            gain_auto = int(commands[command])
            self.set_GainAuto(GainAuto=gain_auto,
                              set_value_successful_callback=lambda: self.set_value_successful_callback(command=command),
                              set_value_failed_callback=lambda err_code, err_str: self.set_value_failed_callback(err_code=err_code, err_str=err_str, command=command))

        # self.frame_data_operator.set_parameters(parameters=commands, camera_identity=self.camera_identity)

    def set_commands(self, command: int):
        """
        设置相机控制命令
        :param command:
        :return:
        """
        # 打开相机
        if command == CAMERA_OPEN_CAMERA:
            self.open_camera(access_mode=self.access_mode)
        # 关闭相机
        elif command == CAMERA_CLOSE_CAMERA:
            self.close_camera()
        # 开始取流
        elif command == CAMERA_START_GRABBING:
            self.grab_in_thread()
        # 停止取流
        elif command == CAMERA_STOP_GRABBING:
            self.release_grab()
        # 软触发
        elif command == CAMERA_TRIGGER:
            command_str = "trigger_software"
            self.set_TriggerSoftware(set_value_successful_callback=lambda: self.set_value_successful_callback(command=command_str),
                                     set_value_failed_callback=lambda err_code, err_str: self.set_value_failed_callback(err_code=err_code, err_str=err_str, command=command_str))
        # 保存图片
        elif command == CAMERA_SAVE:
            self.set_to_save(True)
            # command_str = "save"
            # self.set_TriggerSoftware(set_value_failed_callback=lambda err_code, err_str: self.set_value_failed_callback(err_code=err_code, err_str=err_str, command=command_str))

    def set_value_successful_callback(self, command: str):
        """
        设置设备参数成功回调函数
        :param command:
        :return:
        """
        level = 'INFO'
        title = '信息'
        informative_text = ''

        if command == "resize_ratio":
            text = '设置画面大小成功！'
            informative_text = '当前值 [%f]' % (self.resize_ratio,)
        elif command == "rotate_flag":
            text = '设置画面旋转成功！'
            informative_text = '当前值 [%d]' % (self.rotate_flag,)
        elif command == "trigger_mode":
            text = '设置触发模式成功！'
        elif command == "trigger_source":
            text = '设置触发源成功！'
        elif command == "trigger_software":
            text = '软触发成功！'
        elif command == "exposure_auto":
            text = '设置曝光模式成功！'
        elif command == "exposure_time":
            text = '设置曝光时间成功！'
        elif command == "gain":
            text = '设置增益成功！'
        elif command == "gain_auto":
            text = '设置增益模式成功！'
        else:
            text = '设置设备参数[%s]成功！' % (command,)

        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

    def set_value_failed_callback(self, err_code: int, err_str: str, command: str):
        """
        设置设备参数错误回调函数
        :param err_code:
        :param err_str:
        :param command:
        :return:
        """
        level = "ERROR"
        title = '错误'
        informative_text = '错误事项[%s]，错误代码[%#X]' % (err_str, err_code)

        if command == "resize_ratio":
            text = '设置画面大小错误！'
        elif command == "rotate_flag":
            text = '设置画面旋转错误！'
        elif command == "trigger_mode":
            text = '设置触发模式错误！'
        elif command == "trigger_source":
            text = '设置触发源错误！'
        elif command == "trigger_software":
            text = '软触发错误！'
        elif command == "exposure_auto":
            text = '设置曝光模式错误！'
        elif command == "exposure_time":
            text = '设置曝光时间错误！'
        elif command == "gain":
            text = '设置增益错误！'
        elif command == "gain_auto":
            text = '设置增益模式错误！'
        else:
            text = '设置设备参数[%s]错误！' % (command,)

        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)


if __name__ == "__main__":

    import sys
    import matplotlib.pyplot as plt

    """
    # linux
    import termios
    def press_any_key_2_exit():
        fd = sys.stdin.fileno()
        old_ttyinfo = termios.tcgetattr(fd)
        new_ttyinfo = old_ttyinfo[:]
        new_ttyinfo[3] &= ~termios.ICANON
        new_ttyinfo[3] &= ~termios.ECHO
        # sys.stdout.write(msg)
        # sys.stdout.flush()
        termios.tcsetattr(fd, termios.TCSANOW, new_ttyinfo)
        try:
            os.read(fd, 7)
        except:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSANOW, old_ttyinfo)
    """

    def imshow(frame: np.ndarray, name: str = "", method: int = 2):
        """

        :param frame:
        :param name:
        :param method:
        :return:
        """
        '''
        fig = plt.figure(num=name,              # 图像编号或名称，数字为编号 ，字符串为名称
                         figsize=(5, 5),        # 指定figure的宽和高，单位为英寸
                         dpi=None,              # 指定绘图对象的分辨率，即每英寸多少个像素，缺省值为80
                         facecolor="white",     # 背景颜色
                         edgecolor="black",     # 边框颜色
                         frameon=True)          # 是否显示边框
        '''

        if method == 1:
            plt.clf()
            plt.title(name)
            plt.xticks([])
            plt.yticks([])
            if frame.ndim == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                plt.imshow(frame)
            else:
                plt.imshow(frame, cmap="gray")
            plt.pause(0.01)
        elif method == 2:
            cv2.imshow(name, frame)
            cv2.waitKey(10)
        else:
            pass

    def my_frame_process_callback(frame_data: np.ndarray, parameters: dict, *args, **kwargs):
        # 输出帧信息
        st_frame_out_info: Optional[MV_FRAME_OUT_INFO_EX] = parameters.get("st_frame_out_info")
        if st_frame_out_info is not None:
            print("{Frame} -> nWidth[%d]\tnHeight[%d]\tnFrameNum[%d]\n\t\tnDevTimeStampHigh[%d]\tnDevTimeStampLow[%d]\tnHostTimeStamp[%d]\n\t\tenPixelType[0x%x]" %
                  (st_frame_out_info.nWidth, st_frame_out_info.nHeight, st_frame_out_info.nFrameNum,
                   st_frame_out_info.nDevTimeStampHigh, st_frame_out_info.nDevTimeStampLow, st_frame_out_info.nHostTimeStamp,
                   st_frame_out_info.enPixelType))

        # 显示画面
        win_name = "Camera[%d]" % (my_cam.camera_identity.device_index,)
        imshow(frame=frame_data, name=win_name, method=2)

    # 获取python版本
    py_version = sys.version
    print('\t[信息]\tPYTHON版本\t[%s]' % (py_version,))

    # 获取SDK版本
    sdk_version_int = int(MyCamera.MV_CC_GetSDKVersion())
    sdk_version = "v%x.%x.%x.%x" % (sdk_version_int >> 24 & 0xFF, sdk_version_int >> 16 & 0xFF, sdk_version_int >> 8 & 0xFF, sdk_version_int & 0xFF)
    print('\t[信息]\t海康SDK版本\t[%s]' % (sdk_version,))

    # 枚举相机
    if MyCamera.enum_cameras(filter_callback=None) != MV_OK:
        MyCamera.reset_enum_cameras_identity()

    # 选择相机
    selected = input("\t[信息]\t请输入相机的序号:\t")
    if not selected.isdigit():
        print("\t[错误]\t输入序号非整型\t[程序异常退出]")
        sys.exit()
    selected = int(selected)
    if selected >= len(MyCamera.get_enum_cameras_identity()):
        print("\t[错误]\t输入序号超出\t[程序异常退出]")
        sys.exit()
    for c in MyCamera.get_enum_cameras_identity():
        if selected == c.device_index:
            cam_identity: CameraIdentity = c
            break
    else:
        print("\t[错误]\t没有匹配的相机(index == %d)\t[程序异常退出]" % (selected,))
        sys.exit()

    # 选择单播 或 组播
    transmission_type = input("\t[信息]\t请输入相机访问权限:\n\t\t** (C)ontrol\t->\t控制模式\n\t\t** (M)onitor\t->\t监控模式\n\t\t** (E)xclusive\t->\t独占模式\n\t")
    if transmission_type.upper() == 'M':
        acce_mode = MV_ACCESS_Monitor
    elif transmission_type.upper() == 'C':
        acce_mode = MV_ACCESS_Control
    elif transmission_type.upper() == 'E':
        acce_mode = MV_ACCESS_Exclusive
    else:
        print("\t[错误]\t输入相机访问权限超出\t[程序异常退出]")
        sys.exit()

    # 创建管道
    my_msg_parent_conn, my_msg_child_conn = Pipe(duplex=True)

    # 创建相机实例
    my_cam = MyCamera(
                      camera_identity=cam_identity,
                      msg_child_conn=my_msg_child_conn,
                      name=None,
                      resize_ratio=0.3,
                      rotate_flag=0,
                      access_mode=acce_mode,
                      imgbuf_child_conn=None,
                      frame_process_callback=my_frame_process_callback,
                      save_process_callback=None,
                      save_process_successful_callback=None,
                      before_grab_callback=None,
                      after_grab_callback=None,
                      running_cameras_manager=None,
                      running_cameras_lock=None,
                      )

    # 打开相机
    my_cam.open_camera()

    # 默认值
    my_cam.set_TriggerMode(TriggerMode=0)
    my_cam.set_AcquisitionFrameRateEnable(AcquisitionFrameRateEnable=True)
    my_cam.set_AcquisitionFrameRate(AcquisitionFrameRate=10)

    # 后台监听
    t = Thread(target=my_cam.background_listening)
    # t.setDaemon(True)
    t.start()

    # 在主进程中监听键盘输入
    print("\t[信息]\t指令:\n\t\t** (B)egin\t\t->\t开始取流\n\t\t** (E)nd\t\t->\t停止取流\n\t\t** (C)lose\t\t->\t关闭相机\n\t\t** (T)rigger\t->\t软触发\n")
    while True:
        my_command = input("\t[信息]\t请输入指令:\t")
        # 开始取流
        if my_command.lower() == "b":
            my_msg_parent_conn.send(CAMERA_START_GRABBING)
        # 停止取流
        elif my_command.lower() == "e":
            my_msg_parent_conn.send(CAMERA_STOP_GRABBING)
        # 关闭相机
        elif my_command.lower() == "c":
            my_msg_parent_conn.send(CAMERA_CLOSE_CAMERA)
            my_msg_parent_conn.close()

            while my_cam.get_open_flag():
                pass

            break
        # 软触发
        elif my_command.lower() == "t":
            my_msg_parent_conn.send(CAMERA_TRIGGER)
        else:
            print("\t[警告]\t输入指令无效\t")

    print("\t[信息]\t[程序正常退出]")
