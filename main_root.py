from sys import argv as sys_argv, exit as sys_exit, version as sys_version
from os import getpid as os_getpid
import cv2
from psutil import Process as psutilProcess, pids as psutilPids
from win32gui import SetForegroundWindow, FindWindow, ShowWindow, IsIconic, SetFocus
# from win32con import SW_SHOWMAXIMIZED, SW_SHOWMINIMIZED
from multiprocessing import Process, freeze_support
from subprocess import run as subprocess_run

from PyQt5.QtWidgets import QApplication, QDialog, QStyle
from PyQt5.QtGui import QIcon

from CameraCore.my_camera_t import MyCamera

from main_grab import show_grab

from UI.ui_about import Ui_Dialog as Ui_About
from Interface.interface_root import InterfaceRoot
from Interface.interface_cameras_page import InterfaceCamerasPage

from Utils.messenger import Messenger
from Utils.database_operator import DatabaseOperator
from Utils.serializer import MySerializer
from Utils.image_presenter import Presenter

from User.config_static import (CF_PROJECT_ROLE, CF_RUNNING_SEQUENCE_FILE, CF_RUNNING_ROOT_FLAG,
                                CF_APP_TITLE, CF_APP_ICON, CF_CAMERA_YY_PICTURE, CF_ID_PICTURE,
                                CF_CONTACTS, CF_VERSION, CF_CREATE_TIME, CF_README_PATH)


def show_about():
    my_version = CF_VERSION
    my_create_time = CF_CREATE_TIME

    # 3.6.13 |Anaconda, Inc.| (default, Mar 16 2021, 11:37:27) [MSC v.1916 64 bit (AMD64)]
    py_version = sys_version.split('|')[0].strip()
    # 3.4.1
    cv_version = cv2.__version__
    # 4.2.0.3
    sdk_version_int = int(MyCamera.MV_CC_GetSDKVersion())
    sdk_version = "%x.%x.%x.%x" % (sdk_version_int >> 24 & 0xFF, sdk_version_int >> 16 & 0xFF, sdk_version_int >> 8 & 0xFF, sdk_version_int & 0xFF)

    contacts = CF_CONTACTS

    image_id = cv2.imread(CF_ID_PICTURE)
    image_yy = cv2.imread(CF_CAMERA_YY_PICTURE)

    dialog = QDialog()
    dialog.setWindowIcon(QIcon(CF_APP_ICON))  # 设置窗口图标

    ui = Ui_About()
    ui.setupUi(dialog)

    Presenter.show_ndarray_in_QLabel(image_id, label=ui.labelImageA)
    Presenter.show_ndarray_in_QLabel(image_yy, label=ui.labelImageB)

    ui.labelA.setText(list(contacts.keys())[0])
    ui.labelEmailA.setText(list(contacts.values())[0])
    ui.labelB.setText(list(contacts.keys())[1])
    ui.labelEmailB.setText(list(contacts.values())[1])
    ui.labelC.setText(list(contacts.keys())[2])
    ui.labelEmailC.setText(list(contacts.values())[2])

    ui.labelVersionPython.setText(py_version)
    ui.labelVertionOpencv.setText(cv_version)
    ui.labelVersionMvs.setText(sdk_version)

    temp = ui.labelVersion.text()
    temp = temp.replace("#", my_version)
    temp = temp.replace("@", my_create_time)
    ui.labelVersion.setText(temp)

    style = QApplication.style()
    ui.buttonClose.setIcon(style.standardIcon(QStyle.SP_LineEditClearButton))
    ui.buttonClose.clicked.connect(dialog.close)
    dialog.exec_()


def show_readme():
    subprocess_run(['start', CF_README_PATH], shell=True)


def enum_cameras(interface: InterfaceCamerasPage):
    MyCamera.enum_cameras(filter_callback=lambda device_info: interface.filter_cameras(device_info=device_info),
                          fill_in_table_callback=lambda cameras_identity: interface.fill_in_table(cameras_identity=cameras_identity),
                          message_callback=lambda message: Messenger.show_QMessageBox(widget=interface, message=message))


def open_camera(message: dict, interface=None):
    role = message.get("Role")
    camera_location = message.get("CameraLocation")
    camera_identity = message.get("CameraIdentity")

    flag = True
    informative_text = ''
    detailed_text = ''
    if not (isinstance(role, str) and role.strip().upper() == CF_PROJECT_ROLE):
        informative_text = '错误事项[相机角色不匹配]'
        detailed_text = '相机角色需求[%s]' % (CF_PROJECT_ROLE,)
        flag = False
    line = camera_location.get("Line")
    if not (isinstance(line, str) and line.strip().upper() != ""):
        informative_text = '错误事项[生产线未设置]'
        detailed_text = '请右击设置相机位置身份'
        flag = False
    location = camera_location.get("Location")
    if not (isinstance(location, str) and location.strip().upper() != ""):
        informative_text = '错误事项[相机位置未设置]'
        detailed_text = '请右击设置相机位置身份'
        flag = False
    side = camera_location.get("Side")
    if not (isinstance(side, str) and side.strip().upper() != ""):
        informative_text = '错误事项[相机方向未设置]'
        detailed_text = '请右击设置相机位置身份'
        flag = False

    if not flag:
        message = {"level": 'WARNING', "title": '警告', "text": '打开相机错误！',
                   "informative_text": informative_text, 'detailed_text': detailed_text}
        Messenger.show_QMessageBox(widget=interface, message=message, QLabelMinWidth=200)
        return

    # 序列化
    str_camera_identity = MySerializer.serialize(camera_identity)
    str_camera_location = MySerializer.serialize(camera_location)

    # 多进程
    serialize_arguments = {"CameraIdentity": str_camera_identity, "CameraLocation": str_camera_location}
    p = Process(target=show_grab, kwargs={"serialize_arguments": serialize_arguments})
    # p.daemon = True
    p.start()


def double_running() -> bool:
    """
    验证是否为重复运行
    :return:
    """
    my_pid = os_getpid()
    my_p_name = psutilProcess(my_pid).name()

    # 得到每个PID进程信息,并将PID名称转换成字符串
    pids = psutilPids()
    for pid in pids:
        if pid != my_pid and psutilProcess(pid).name() == my_p_name:
            return True

    return False


def foreground_root(window_caption: str, window_class: str = "Qt5152QWindowIcon"):
    """
    设置前置窗口
    :param window_caption:
    :param window_class:
    :return:
    """
    # 查找窗口句柄
    hwnd = FindWindow(window_class, window_caption)
    if hwnd != 0:
        # # 若最小化，则将其显示
        # if IsIconic(hwnd):
        #     ShowWindow(hwnd, SW_SHOWMAXIMIZED)  # 最大化
        #     ShowWindow(hwnd, SW_SHOWMINIMIZED)  # 最小化
        SetForegroundWindow(hwnd)   # 设置前置窗口
        # SetFocus(hwnd)  # 设置聚焦窗口


if __name__ == '__main__':

    # 需要，否则无法打包
    freeze_support()

    # 校验双开
    if double_running():
        foreground_root(window_caption='%s-Root' % CF_APP_TITLE)
        sys_exit()

    # 重置标志
    with open(CF_RUNNING_SEQUENCE_FILE, 'w', encoding='utf-8') as sequence_file:
        sequence_file.write(str(CF_RUNNING_ROOT_FLAG))

    db_opt = DatabaseOperator()

    app = QApplication(sys_argv)
    interface_root = InterfaceRoot(db_operator=db_opt)

    interface_root.cameras_page.openSignal.connect(lambda message: open_camera(message=message, interface=interface_root))
    interface_root.cameras_page.enumSignal.connect(lambda: enum_cameras(interface=interface_root.cameras_page))
    interface_root.readMeSignal.connect(show_readme)
    interface_root.aboutSignal.connect(show_about)

    interface_root.show()

    res = app.exec_()

    db_opt.close()

    sys_exit(res)
