from threading import Thread
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal

from UI.ui_socket_page import Ui_Form as Ui_SocketPage

from Utils.database_operator import DatabaseOperator
from Utils.socket_operator import SocketOperator
from Utils.messenger import Messenger


class InterfaceSocketPage(QWidget, Ui_SocketPage):

    serverCreatedSignal = pyqtSignal(bool)
    clientOnlineSignal = pyqtSignal(tuple)
    clientOfflineSignal = pyqtSignal(tuple)

    def __init__(self, db_operator: DatabaseOperator):
        super().__init__()

        self.db_operator = db_operator  # 数据库

        self.setupUi(self)              # 初始化窗口

        self.ip = ""
        self.port = -1
        self.auto = False

        self.socket_operator = SocketOperator()

        # 链接信号
        self.comboBoxIp.currentTextChanged.connect(self.ip_changed)
        self.comboBoxIp.showPopupSignal.connect(self.init_ips)
        self.lineEditPort.textChanged.connect(self.port_changed)
        self.buttonStartOrStop.clicked.connect(self.start_or_stop)
        self.checkBoxAuto.toggled.connect(self.auto_changed)

        # 初始化下拉框
        self.init_ips()

        # 自动开始
        if self.auto:
            self.start_listen()

    def ip_changed(self, text: str):
        self.ip = text
        # 从数据库中获取 port 和 auto
        socket_config = self.db_operator.get_socket_config(ip=text)
        if socket_config:
            self.lineEditPort.setText(str(socket_config["Port"]))
            self.checkBoxAuto.setChecked(socket_config["Auto"])
        else:
            self.lineEditPort.clear()
            self.checkBoxAuto.setChecked(False)

    def port_changed(self, text: str):
        temp = text.strip()
        if temp.isdigit():
            self.port = int(temp)
            self.buttonStartOrStop.setEnabled(True)
        else:
            self.port = -1
            self.buttonStartOrStop.setEnabled(False)

    def auto_changed(self, flag: bool):
        self.auto = flag

    @staticmethod
    def get_ips(ips: list):
        ips.insert(0, "127.0.0.1")
        return ips

    def init_ips(self):
        # 获取有效ip
        ip, ips = SocketOperator.get_valid_ip()
        self.comboBoxIp.set_items(get_items_callback=lambda: self.get_ips(ips=ips))
        if ip is not None:
            self.comboBoxIp.setCurrentText(ip)

    def start_or_stop(self):
        text = self.buttonStartOrStop.text()
        if text == "开始":
            self.start_listen()
        else:
            self.stop_listen()

    def start_listen(self):
        parameters = {
            'ip': self.ip,
            'port': self.port,
            'server_created_successful_callback': self.server_created_successful,
            'server_created_failed_callback': self.server_created_failed,
            'server_closed_callback': self.server_closed,
            'client_online_callback': self.client_online,
            'client_offline_callback': self.client_offline
        }

        t = Thread(target=self.socket_operator.start_listen, kwargs=parameters)
        t.setDaemon(True)
        t.start()

    def stop_listen(self):
        self.socket_operator.stop_listen()

    def server_created_successful(self):
        self.buttonStartOrStop.setText("停止")

        self.comboBoxIp.setEnabled(False)
        self.lineEditPort.setEnabled(False)
        self.checkBoxAuto.setEnabled(False)

        self.db_operator.set_socket_config(ip=self.ip, port=self.port, auto=self.auto)

        self.serverCreatedSignal.emit(True)

    def server_closed(self):
        self.buttonStartOrStop.setText("开始")

        self.comboBoxIp.setEnabled(True)
        self.lineEditPort.setEnabled(True)
        self.checkBoxAuto.setEnabled(True)

        self.serverCreatedSignal.emit(False)

    def server_created_failed(self, error: str):
        message = {"level": 'ERROR', "title": '错误', "text": '创建TCP服务器失败！',
                   "informative_text": '', "detailed_text": error}
        Messenger.show_QMessageBox(widget=self, message=message, QLabelMinWidth=200)

    def client_online(self, address: tuple):
        self.clientOnlineSignal.emit(address)

    def client_offline(self, address: tuple):
        self.clientOfflineSignal.emit(address)
