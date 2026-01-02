from sys import argv as sys_argv, exit as sys_exit, version as sys_version, stderr as sys_stderr
from os import getpid as os_getpid
import json
import cv2
import yaml

from psutil import Process as psutilProcess, pids as psutilPids
from win32gui import SetForegroundWindow, FindWindow, ShowWindow, IsIconic, SetFocus
# from win32con import SW_SHOWMAXIMIZED, SW_SHOWMINIMIZED

from threading import Thread
from multiprocessing import Process, freeze_support
from subprocess import run as subprocess_run

from PyQt5.QtWidgets import QApplication, QDialog, QStyle
from PyQt5.QtGui import QIcon

from UI.Root.ui_about import Ui_Dialog as Ui_About
from Interface.Root.interface_root import InterfaceRoot
from Interface.Root.Page.Cameras.interface_cameras_page import InterfaceCamerasPage

from Utils.messenger import Messenger
from Utils.database_operator import DatabaseOperator, DATABASE_SYMBOL_ODBC
# from Utils.serializer import MySerializer
from Utils.image_presenter import Presenter
from Utils.script_runner import ScriptRunner

from User.config_static import (CF_APP_TITLE, CF_APP_ICON, CF_CAMERA_YY_PICTURE, CF_ID_PICTURE,
                                CF_CONTACTS, CF_VERSION, CF_CREATE_TIME, CF_README_PATH, CF_DYNAMIC_CONFIG_PATH, CF_GRAB_SCRIPT_FILE)


class MainRoot:
    def __init__(self):
        # 动态参数
        with open(CF_DYNAMIC_CONFIG_PATH, encoding='ascii', errors='ignore') as f:
            self.dynamic_config = yaml.safe_load(f)

        # 实例化数据库
        self.db_operator = DatabaseOperator(symbol=DATABASE_SYMBOL_ODBC)
        # 连接数据库
        is_connected = self.db_operator.connect(path=self.dynamic_config["access_database_path"])
        if not is_connected:
            raise Exception("open access database failed")

        # 实例化界面
        self.interface_root = InterfaceRoot(db_operator=self.db_operator)

        # 连接信号
        self.interface_root.cameras_page.openSignal.connect(self.open_camera)
        self.interface_root.readMeSignal.connect(self.show_readme)
        self.interface_root.aboutSignal.connect(self.show_about)

    def open_camera(self, message: dict):
        """
        打开相机
        :param message:
        :return:
        """
        if not self.valid_open_arguments(arguments=message):
            return

        script_parameters = {
            "line": message.get("Line"),
            "location": message.get("Location"),
            "side": message.get("Side"),
            "ip": message.get("IP"),
            "port": message.get("Port"),
            "user": message.get("User"),
            "password": message.get("Password"),
        }

        # 运行 python 脚本
        # C:/Users/yy/anaconda3/envs/py36/python.exe ./main_grab_rgb.py --line 5-100 --location RIGHT --side LEFT --ip 192.168.3.4 --port 2528 --user service --password Schuler.2019
        subprocess = self.run_grab_script(
            python_path=self.dynamic_config["python_path"],
            script_path=CF_GRAB_SCRIPT_FILE,
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
    def run_grab_script(python_path: str, script_path: str, parameters: dict):
        """
        运行 grab 脚本
        :param python_path:
        :param script_path:
        :param parameters:
        :return:
        """
        grab_script = ScriptRunner.create_python_script(
            python_path=python_path,
            script_path=script_path,
            parameters=parameters,
        )
        subprocess = ScriptRunner.run_script(
            script=grab_script,
            password=None,
            parameters=None,
            terminal=False,
            is_linux=False
        )

        return subprocess

    @staticmethod
    def decode_subprocess_stdout(pid: int, message: str, command_prefix: str = "command|", role: str = "grab"):
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
    def decode_subprocess_error(pid: int, message: str, role: str = "grab"):
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

    def valid_open_arguments(self, arguments: dict):
        """
        验证打开相机的参数
        :param arguments:
        :return:
        """
        line = arguments.get("Line")
        location = arguments.get("Location")
        side = arguments.get("Side")
        ip = arguments.get("IP")
        port = arguments.get("Port")
        user = arguments.get("User")
        password = arguments.get("Password")

        flag = True
        informative_text = ''
        detailed_text = '请右击设置相机位置身份'

        if flag and not (isinstance(line, str) and line.strip().upper() != ""):
            informative_text = '错误事项[生产线未设置]'
            flag = False

        if flag and not (isinstance(location, str) and location.strip().upper() != ""):
            informative_text = '错误事项[相机位置未设置]'
            flag = False

        if flag and not (isinstance(side, str) and side.strip().upper() != ""):
            informative_text = '错误事项[相机方向未设置]'
            flag = False

        if flag and not (isinstance(ip, str) and ip.strip() != ""):
            informative_text = '错误事项[相机IP地址未设置]'
            flag = False

        if flag and not (isinstance(port, str) and port.strip() != ""):
            informative_text = '错误事项[相机端口号未设置]'
            flag = False

        if flag and not (isinstance(port, str) and port.isdigit()):
            informative_text = '错误事项[相机端口号格式错误]'
            flag = False

        if flag and not (isinstance(user, str) and user.strip() != ""):
            informative_text = '错误事项[相机用户未设置]'
            flag = False

        if flag and not (isinstance(password, str) and password.strip() != ""):
            informative_text = '错误事项[相机密码未设置]'
            flag = False

        if not flag:
            Messenger.show_message_box(
                widget=self.interface_root,
                message={"level": 'WARNING', "title": '警告', "text": '打开相机错误！',
                         "informative_text": informative_text, 'detailed_text': detailed_text}
            )

        return flag

    @staticmethod
    def show_about():
        """
        显示关于对话框
        :return:
        """
        my_version = CF_VERSION
        my_create_time = CF_CREATE_TIME

        # 3.6.13 |Anaconda, Inc.| (default, Mar 16 2021, 11:37:27) [MSC v.1916 64 bit (AMD64)]
        py_version = sys_version.split('|')[0].strip()
        # 3.4.1
        cv_version = cv2.__version__

        # 联系人
        contacts = CF_CONTACTS

        # 图片
        image_id = cv2.imread(CF_ID_PICTURE)
        image_yy = cv2.imread(CF_CAMERA_YY_PICTURE)

        # 创建对话框
        dialog = QDialog()
        # 设置窗口图标
        dialog.setWindowIcon(QIcon(CF_APP_ICON))

        ui = Ui_About()
        ui.setupUi(dialog)

        # 显示图片
        Presenter.show_ndarray_in_QLabel(image_id, label=ui.labelImageA)
        Presenter.show_ndarray_in_QLabel(image_yy, label=ui.labelImageB)

        # 显示联系人
        ui.labelA.setText(list(contacts.keys())[0])
        ui.labelEmailA.setText(list(contacts.values())[0])
        ui.labelB.setText(list(contacts.keys())[1])
        ui.labelEmailB.setText(list(contacts.values())[1])
        ui.labelC.setText(list(contacts.keys())[2])
        ui.labelEmailC.setText(list(contacts.values())[2])

        # 显示版本号
        ui.labelVersionPython.setText(py_version)
        ui.labelVertionOpencv.setText(cv_version)

        temp = ui.labelVersion.text()
        temp = temp.replace("#", my_version)
        temp = temp.replace("@", my_create_time)
        ui.labelVersion.setText(temp)

        style = QApplication.style()
        ui.buttonClose.setIcon(style.standardIcon(QStyle.SP_LineEditClearButton))
        ui.buttonClose.clicked.connect(dialog.close)
        dialog.exec_()

    @staticmethod
    def show_readme():
        """
        显示readme
        :return:
        """
        subprocess_run(['start', CF_README_PATH], shell=True)


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
        SetForegroundWindow(hwnd)  # 设置前置窗口
        # SetFocus(hwnd)  # 设置聚焦窗口


if __name__ == '__main__':

    # 需要，否则无法打包
    freeze_support()

    # 校验双开
    if double_running():
        foreground_root(window_caption='%s-Root' % CF_APP_TITLE)
        sys_exit()

    app = QApplication(sys_argv)

    my_root = MainRoot()

    # 显示界面
    my_root.interface_root.show()

    res = app.exec_()

    # 关闭数据库
    my_root.db_operator.close()

    sys_exit(res)
