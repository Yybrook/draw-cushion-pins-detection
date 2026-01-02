from sys import argv, exit
import numpy as np
import cv2
from typing import Union, Optional
from os import path as os_path, makedirs as os_makedirs
from multiprocessing import Pipe, Process
from threading import Thread
from datetime import datetime

from PyQt5.QtWidgets import QApplication, QDialog, QStyle, QMessageBox
from PyQt5.QtGui import QPixmap, QIcon

from Interface.interface_grab import InterfaceGrab
from UI.ui_authority import Ui_Dialog as Ui_Authority
from main_teach import show_teach

from MvImport.CameraParams_const import MV_ACCESS_Exclusive
from MvImport.MvErrorDefine_const import MV_OK
from CameraCore.camera_identity import CameraIdentity
from CameraCore.my_camera_t import MyCamera
from CameraCore.camera_operator import CameraOperator

from Utils.frame_operator import FrameOperator
from Utils.background_listener import ImageBufferListener
from Utils.messenger import Messenger
from Utils.database_operator import DatabaseOperator
from Utils.serializer import MySerializer
from Utils.image_presenter import Presenter

from User.config_static import (CF_TEMP_TEACH_DIR, CF_RECORDS_ORIGIN_PICTURES_DIR, CF_RECORDS_DETECTION_PICTURES_DIR,
                                CF_TEACH_PINS_MAP_PAGE,
                                CF_RUNNING_SEQUENCE_FILE, CF_RUNNING_GRAB_FLAG, CF_RUNNING_ROOT_FLAG, CF_APP_ICON, CF_TEACH_REFERENCE_SIDE,
                                CF_TEACH_AUTHORITY_PASSWORD)


def active_interface(arguments: dict):

    camera_identity = arguments["CameraIdentity"]
    camera_location = arguments["CameraLocation"]

    # 如果side为“LEFT”,相机视野旋转180度
    side = camera_location["Side"]
    if side == CF_TEACH_REFERENCE_SIDE:
        rotate_flag = 0
    else:
        rotate_flag = 2

    app = QApplication(argv)

    # 画面传输管道
    imgbuf_parent_conn, imgbuf_child_conn = Pipe(duplex=False)

    # 数据库
    db_operator = DatabaseOperator()

    # 创建相机实例
    my_camera = MyCamera(
        camera_identity=camera_identity,
        name=None,
        resize_ratio=None,
        rotate_flag=rotate_flag,
        access_mode=MV_ACCESS_Exclusive,
        msg_child_conn=None,
        imgbuf_child_conn=imgbuf_child_conn,
        frame_process_callback=None,
        save_process_callback=None,
        save_process_successful_callback=None,
        before_grab_callback=None,
        after_grab_callback=None,
        running_cameras_manager=None,
        running_cameras_lock=None,
    )

    # 创建Interface实例
    interface_camera_grab = InterfaceGrab(camera_identity=camera_identity, camera_location=camera_location, db_operator=db_operator)
    # 连接信号
    interface_camera_grab.grabOrNotSignal.connect(my_camera.grab_or_not)
    interface_camera_grab.closeCameraSignal.connect(my_camera.close_camera)

    interface_camera_grab.detectSignal.connect(lambda detect_message: do_detect(detect_message=detect_message, cam=my_camera, db_operator=db_operator,
                                                                                interface=interface_camera_grab,
                                                                                show_detection_callback=interface_camera_grab.show_detection))

    interface_camera_grab.teachSignal.connect(lambda teach_message: do_teach(teach_message=teach_message, cam=my_camera))

    interface_camera_grab.partTeachSignal.connect(lambda teach_message: do_part_teach(teach_message=teach_message, cam=my_camera, db_operator=db_operator,
                                                                                      interface=interface_camera_grab))

    interface_camera_grab.connectAlgorithmSignal.connect(lambda value: connect_process_algorithm(value=value, db_operator=db_operator, cam=my_camera))
    interface_camera_grab.setParametersSignal.connect(lambda: set_camera_parameters())
    interface_camera_grab.savePictureSignal.connect(lambda message: save_image(image=interface_camera_grab.after_pixmap,
                                                                               message=message, parent=interface_camera_grab))

    # 创建监听实例
    imgbuf_listener = ImageBufferListener(conn=imgbuf_parent_conn)
    # 连接信号
    imgbuf_listener.showImageBufferSignal.connect(lambda data: interface_camera_grab.show_camera_frame(data=data))
    # 开启多线程
    imgbuf_listener.start()

    # 多线程，打开相机并取流
    ret = my_camera.open_and_grab_in_thread()
    if ret == MV_OK:

        # 打开顺序文件
        with open(CF_RUNNING_SEQUENCE_FILE, 'r', encoding='utf-8') as sequence_file:
            sequence_flag = sequence_file.readline()

        if CF_RUNNING_ROOT_FLAG >= int(sequence_flag):
            with open(CF_RUNNING_SEQUENCE_FILE, 'w', encoding='utf-8') as sequence_file:
                sequence_file.write(str(CF_RUNNING_GRAB_FLAG))
        else:
            with open(CF_RUNNING_SEQUENCE_FILE, 'a', encoding='utf-8') as sequence_file:
                sequence_file.write(str(CF_RUNNING_GRAB_FLAG))

        # 显示界面
        interface_camera_grab.show()
        ret = app.exec_()

    else:
        m = {"level": 'ERROR', "title": '错误', "text": '打开相机错误！',
             "informative_text": '错误事项[%s]\r\n错误代码[%#X]' % (CameraOperator.err_code_map(err_code=ret), ret),
             "detailed_text": '打开相机进程异常退出'}
        Messenger.show_QMessageBox(widget=None, message=m, QLabelMinWidth=200)

    db_operator.close()
    exit(ret)


def do_detect(detect_message: dict, cam: MyCamera, db_operator: DatabaseOperator, interface, show_detection_callback):
    part = detect_message["Part"]
    serial_number = detect_message["SerialNumber"]
    camera_location = detect_message["CameraLocation"]
    # 获取数据
    process_parameters = db_operator.get_all_process_parameters(filter_dict={"SerialNumber": serial_number})
    if not process_parameters:
        message = {"level": 'WARNING', "title": '警告', "text": '相机还未进行检测算法的参数示教！', "informative_text": '', 'detailed_text': '请先对相机进行示教'}
        Messenger.show_QMessageBox(widget=interface, message=message, QLabelMinWidth=200)
        return

    # 获取基准pins_map
    pins_map = db_operator.get_parts_pins_map(filter_dict={"Part": part, "Line": camera_location["Line"]}, demand_list=["PinsMap",])
    if pins_map:
        pins_map["PinsMap"] = MySerializer.deserialize(pins_map["PinsMap"])     # 反序列化
        message = dict(**detect_message, **process_parameters, **pins_map)      # 合并字典
        # 设置 save_process_callback 回调函数
        cam.save_process_callback = lambda frame_data, parameters: camera_save_process(flag=1, frame_data=frame_data, parameters=parameters, message=message,
                                                                                       db_operator=db_operator, show_detection_callback=show_detection_callback)
        cam.set_to_save(True)   # 置位保存图片


def do_authority(password: str = "123"):
    dialog = QDialog()
    dialog.setWindowIcon(QIcon(CF_APP_ICON))  # 设置窗口图标

    ui = Ui_Authority()
    ui.setupUi(dialog)

    # 添加密码验证结果变量
    password_correct = False

    style = QApplication.style()
    ui.buttonConform.setIcon(style.standardIcon(QStyle.SP_DialogYesButton))
    ui.buttonClose.setIcon(style.standardIcon(QStyle.SP_LineEditClearButton))

    # 修改确认按钮逻辑
    def on_confirm():
        nonlocal password_correct
        if ui.lineEditPassword.text() == password:
            password_correct = True
            dialog.close()
        else:
            Messenger.show_QMessageBox(widget=dialog, level="WARNING", title="警告", text="权限校验错误", informative_text="密码错误", detailed_text="", QLabelMinWidth=300)
            ui.lineEditPassword.clear()
            ui.lineEditPassword.setFocus()

    ui.buttonConform.clicked.connect(on_confirm)
    ui.buttonClose.clicked.connect(dialog.close)

    # 支持回车键确认
    ui.lineEditPassword.returnPressed.connect(on_confirm)

    dialog.exec_()
    return password_correct


def do_teach(teach_message: dict, cam: MyCamera):
    # 先进行权限验证
    if not do_authority(password=CF_TEACH_AUTHORITY_PASSWORD):
        return

    # 设置 save_process_callback 回调函数
    cam.save_process_callback = lambda frame_data, parameters: camera_save_process(flag=2, frame_data=frame_data, parameters=parameters, message=teach_message)
    cam.set_to_save(True)   # 置位保存图片


def do_part_teach(teach_message: dict, cam: MyCamera, db_operator: DatabaseOperator, interface):
    # 先进行权限验证
    if not do_authority(password=CF_TEACH_AUTHORITY_PASSWORD):
        return

    serial_number = teach_message["SerialNumber"]
    # 获取数据
    process_parameters = db_operator.get_all_process_parameters(filter_dict={"SerialNumber": serial_number})
    if not process_parameters:
        message = {"level": 'WARNING', "title": '警告', "text": '相机还未进行检测算法的参数示教！', "informative_text": '', 'detailed_text': '请先对相机进行示教'}
        Messenger.show_QMessageBox(widget=interface, message=message, QLabelMinWidth=200)
        return

    teach_message["Page"] = CF_TEACH_PINS_MAP_PAGE  # 添加起始页

    # 设置 save_process_callback 回调函数
    cam.save_process_callback = lambda frame_data, parameters: camera_save_process(flag=2, frame_data=frame_data, parameters=parameters, message=teach_message)
    cam.set_to_save(True)   # 置位保存图片


def camera_save_process(flag: int, frame_data: np.ndarray, parameters: dict, message: dict,
                        db_operator: Optional[DatabaseOperator] = None, show_detection_callback=None):
    """
    相机保存过程的回调函数
    :param flag:
    :param frame_data:
    :param parameters:
    :param message:
    :param db_operator:
    :param show_detection_callback:
    :return:
    """
    if flag == 1 and db_operator is not None:
        p = {"frame": frame_data,
             "message": message,
             "show_detection_callback": show_detection_callback,
             "record_detection_callback": lambda record_message, origin_frame, detection_frame: record_detection(record_message=record_message,
                                                                                                                 origin_frame=origin_frame,
                                                                                                                 detection_frame=detection_frame,
                                                                                                                 db_operator=db_operator)}
        target = FrameOperator.offline_process_algorithm
    else:
        p = {"message": message, "frame_data": frame_data}
        target = show_teach_interface

    t = Thread(target=target, kwargs=p)
    t.setDaemon(True)
    t.start()


def show_teach_interface(message: dict, frame_data: np.ndarray):
    part = message["Part"]
    serial_number = message["SerialNumber"]
    uid = message["Uid"]
    camera_location = message["CameraLocation"]
    page = message.get("Page", 0)

    camera_identity = CameraIdentity(serial_number=serial_number, uid=uid)

    now = datetime.now().strftime('%G%m%d%H%M%S%f')

    if "\n" in part:
        part_format = part.replace("\n", "-")
    else:
        part_format = part
    file_path = os_path.join(CF_TEMP_TEACH_DIR, r"Origin_%s_%s_%s_%s.npy" % (now, camera_location["Line"], camera_location["Location"], part_format))
    np.save(file_path, frame_data)  # 保存为二进制文件

    # 序列化
    str_camera_identity = MySerializer.serialize(camera_identity)
    str_camera_location = MySerializer.serialize(camera_location)

    # 多进程
    serialize_arguments = {"CameraIdentity": str_camera_identity, 'CameraLocation': str_camera_location,
                           'Part': part, 'FrameFile': file_path, "Page": page}
    p = Process(target=show_teach, kwargs={"serialize_arguments": serialize_arguments})
    p.daemon = True
    p.start()


def record_detection(record_message: dict, origin_frame: np.ndarray, detection_frame: np.ndarray, db_operator: DatabaseOperator):
    part = record_message["Part"]
    line = record_message["Line"]
    location = record_message["Location"]

    record_message["When"] = datetime.now()
    time = record_message["When"].strftime('%G%m%d%H%M%S%f')

    record_message["DetectionPicture"] = os_path.join(CF_RECORDS_DETECTION_PICTURES_DIR, "Detection_%s_%s_%s_%s.jpg" % (line, part, location, time))
    record_message["OriginPicture"] = os_path.join(CF_RECORDS_ORIGIN_PICTURES_DIR, "Origin_%s_%s_%s_%s.jpg" % (line, part, location, time))

    os_makedirs(CF_RECORDS_DETECTION_PICTURES_DIR, exist_ok=True)
    os_makedirs(CF_RECORDS_ORIGIN_PICTURES_DIR, exist_ok=True)

    cv2.imwrite(record_message["DetectionPicture"], detection_frame)
    cv2.imwrite(record_message["OriginPicture"], origin_frame)

    # db_operator = DatabaseOperator()
    db_operator.set_detection_records(demand_dict=record_message)
    # db_operator.close()


def connect_process_algorithm(value: bool, db_operator: DatabaseOperator, cam: MyCamera):
    # TODO 当重新对相机进行示教后，当前的链接算法参数功能不会更新当前相机示教参数
    if value:
        serial_number = cam.camera_identity.serial_number
        # 获取数据
        process_parameters = db_operator.get_all_process_parameters(filter_dict={"SerialNumber": serial_number})
        if process_parameters:
            cam.frame_process_callback = lambda frame_data, parameters: FrameOperator.online_process_algorithm(frame=frame_data, algorithm_parameters=process_parameters)
    else:
        cam.frame_process_callback = None


def set_camera_parameters():
    # TODO 需要添加设置相机内部参数功能
    Messenger.show_QMessageBox(widget=None, level="INFO", title="信息", text="设置相机参数功能尚未开发", informative_text="敬请期待", detailed_text="", QLabelMinWidth=300)


def save_image(image: Union[np.ndarray, QPixmap], message: dict, parent=None):
    now = datetime.now().strftime('%G%m%d%H%M%S%f')
    image_file = "MyDetectionPicture_%s_%s_%s_%s.jpg" % (message["SerialNumber"], message["Part"], message["Line"], now)
    Presenter.save_image(image=image, parent=parent, image_name=image_file)


def deserialize_arguments(serialize_arguments: dict) -> dict:
    str_camera_identity = serialize_arguments["CameraIdentity"]
    str_camera_location = serialize_arguments["CameraLocation"]

    # 反序列化
    camera_identity = MySerializer.deserialize(str_camera_identity)
    camera_location = MySerializer.deserialize(str_camera_location)
    return {"CameraIdentity": camera_identity, "CameraLocation": camera_location}


def show_grab(serialize_arguments: dict):
    # 解析参数
    arguments = deserialize_arguments(serialize_arguments)
    # 激活程序
    active_interface(arguments)
