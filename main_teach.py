from sys import argv, exit
from os import remove as os_remove
import numpy as np
from typing import Union
from datetime import datetime
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap

from Interface.interface_teach import InterfaceTeach

from Utils.database_operator import DatabaseOperator
from Utils.image_presenter import Presenter
from Utils.serializer import MySerializer
from User.config_static import CF_RUNNING_SEQUENCE_FILE, CF_RUNNING_TEACH_FLAG


def save_image(image: Union[np.ndarray, QPixmap], message: dict, parent=None):
    now = datetime.now().strftime('%G%m%d%H%M%S%f')
    image_file = "MyProcessPicture_%s_%s_%s_%s.jpg" % (message["SerialNumber"], message["Part"], message["Line"], now)
    Presenter.save_image(image=image, parent=parent, image_name=image_file)


def active_interface(arguments: dict):
    camera_identity = arguments["CameraIdentity"]
    camera_location = arguments["CameraLocation"]
    frame_file = arguments["FrameFile"]
    frame_data = arguments["FrameData"]
    part = arguments["Part"]
    activate_page = arguments["ActivatePage"]

    # 写文件
    with open(CF_RUNNING_SEQUENCE_FILE, 'a', encoding='utf-8') as sequence_file:
        sequence_file.write(str(CF_RUNNING_TEACH_FLAG))

    db_operator = DatabaseOperator()

    app = QApplication(argv)

    # 创建Interface实例
    interface_teach = InterfaceTeach(frame_data=frame_data,
                                     camera_identity=camera_identity,
                                     camera_location=camera_location,
                                     part=part,
                                     db_operator=db_operator,
                                     activate_page=activate_page)

    # 连接信号
    interface_teach.closeSignal.connect(lambda: os_remove(frame_file))
    interface_teach.savePictureSignal.connect(lambda message: save_image(image=interface_teach.process_pixmap, message=message, parent=interface_teach))

    interface_teach.show()

    res = app.exec_()

    db_operator.close()

    exit(res)


def deserialize_arguments(serialize_arguments: dict):

    str_camera_identity = serialize_arguments["CameraIdentity"]
    str_camera_location = serialize_arguments["CameraLocation"]

    # 反序列化
    camera_identity = MySerializer.deserialize(str_camera_identity)
    camera_location = MySerializer.deserialize(str_camera_location)

    part = serialize_arguments["Part"]
    part = "XXX" if part is None else part

    page = serialize_arguments["Page"]
    activate_page = 0 if page is None else int(page)

    frame_file = serialize_arguments["FrameFile"]
    frame_data = np.load(frame_file)

    arguments = dict()
    arguments["CameraIdentity"] = camera_identity
    arguments["CameraLocation"] = camera_location
    arguments["Part"] = part
    arguments["ActivatePage"] = activate_page
    arguments["FrameFile"] = frame_file
    arguments["FrameData"] = frame_data

    return arguments


def show_teach(serialize_arguments: dict):
    # 解析参数
    arguments = deserialize_arguments(serialize_arguments)
    # 激活程序
    active_interface(arguments)
