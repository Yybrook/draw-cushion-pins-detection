from os import remove as os_remove
from time import sleep
from PyQt5.QtWidgets import QMainWindow, QStackedLayout, QStyle, QApplication
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import pyqtSignal

from UI.ui_root import Ui_MainWindow as Ui_Root
from Interface.interface_cameras_page import InterfaceCamerasPage
from Interface.interface_parts_page import InterfacePartsPage
from Interface.interface_records_page import InterfaceRecordsPage
from Interface.interface_socket_page import InterfaceSocketPage
from Interface.interface_import_cards import InterfaceImportCards

from Utils.messenger import Messenger
from Utils.database_operator import DatabaseOperator
from User.config_static import (CF_ROOT_CAMERAS_PAGE, CF_ROOT_PARTS_PAGE, CF_ROOT_RECORDS_PAGE,
                                CF_RUNNING_ROOT_FLAG, CF_RUNNING_SEQUENCE_FILE,
                                CF_APP_TITLE, CF_APP_ICON, CF_CAMERA_PICTURE, CF_PART_PICTURE, CF_RECORD_PICTURE)


class InterfaceRoot(QMainWindow, Ui_Root):

    aboutSignal = pyqtSignal()
    readMeSignal = pyqtSignal()

    def __init__(self, db_operator: DatabaseOperator):
        super().__init__()

        self.db_operator = db_operator  # 数据库

        self.setupUi(self)  # 初始化窗口

        self.style = QApplication.style()       # 样式

        self.setWindowTitle('%s-Root' % CF_APP_TITLE)   # 设置窗口标题
        self.setWindowIcon(QIcon(CF_APP_ICON))  # 设置窗口图标

        # 实例化分页面
        self.cameras_page = InterfaceCamerasPage(db_operator=self.db_operator)
        self.parts_page = InterfacePartsPage(db_operator=self.db_operator)
        self.records_page = InterfaceRecordsPage(db_operator=self.db_operator)
        self.socket_page = InterfaceSocketPage(db_operator=self.db_operator)

        # 堆叠布局
        self.stackedLayout = QStackedLayout(self.widget)
        self.stackedLayout.addWidget(self.cameras_page)
        self.stackedLayout.addWidget(self.parts_page)
        self.stackedLayout.addWidget(self.records_page)
        self.stackedLayout.addWidget(self.socket_page)

        # 绑定信号
        # 页面切换
        self.stackedLayout.currentChanged.connect(self.current_page_changed)
        # 按钮
        self.buttonCameras.clicked.connect(self.show_cameras_page)
        self.buttonParts.clicked.connect(self.show_parts_page)
        self.buttonRecords.clicked.connect(self.show_records_page)
        self.buttonSocket.clicked.connect(self.show_socket_page)
        # socket 状态
        self.socket_page.serverCreatedSignal.connect(self.show_server_status)
        self.socket_page.clientOnlineSignal.connect(lambda address: self.show_client_status(address=address, is_online=True))
        self.socket_page.clientOfflineSignal.connect(lambda address: self.show_client_status(address=address, is_online=False))

        # 菜单
        style = QApplication.style()
        self.actionImport.setIcon(style.standardIcon(QStyle.SP_FileDialogStart))
        self.actionQuit.setIcon(style.standardIcon(QStyle.SP_LineEditClearButton))
        self.actionReadMe.setIcon(style.standardIcon(QStyle.SP_FileIcon))
        self.actionAbout.setIcon(style.standardIcon(QStyle.SP_MessageBoxInformation))

        self.actionImport.triggered.connect(self.import_cards)
        self.actionQuit.triggered.connect(self.close)
        self.actionReadMe.triggered.connect(self.readMeSignal.emit)
        self.actionAbout.triggered.connect(self.aboutSignal.emit)

        self.show_server_status(flag=bool(self.socket_page.socket_operator.server))

        self.buttonCameras.setIcon(QIcon(QPixmap(CF_CAMERA_PICTURE)))
        self.buttonParts.setIcon(QIcon(QPixmap(CF_PART_PICTURE)))
        self.buttonRecords.setIcon(QIcon(QPixmap(CF_RECORD_PICTURE)))

    def current_page_changed(self, index: int):
        """
        切换当前页
        :param index:
        :return:
        """
        if index == CF_ROOT_CAMERAS_PAGE:
            # self.cameras_page.enum()
            self.cameras_page.tableCameras.clear_all()
        elif index == CF_ROOT_PARTS_PAGE:
            self.parts_page.fill_in_table()
        elif index == CF_ROOT_RECORDS_PAGE:
            self.records_page.fill_in_table()

    def show_cameras_page(self):
        self.stackedLayout.setCurrentWidget(self.cameras_page)

    def show_parts_page(self):
        self.stackedLayout.setCurrentWidget(self.parts_page)

    def show_records_page(self):
        self.stackedLayout.setCurrentWidget(self.records_page)

    def show_socket_page(self):
        self.stackedLayout.setCurrentWidget(self.socket_page)

    def import_cards(self):

        dialog = InterfaceImportCards(db_operator=self.db_operator)

        dialog.show()
        dialog.exec_()

    def show_server_status(self, flag: bool):
        if flag:
            self.buttonSocket.setIcon(self.style.standardIcon(QStyle.SP_DialogYesButton))
        else:
            self.buttonSocket.setIcon(self.style.standardIcon(QStyle.SP_DialogNoButton))

    def show_client_status(self, address: tuple, is_online: bool):
        ip, port = address
        if is_online:
            prefix = '[远程客户端 已连接]'
        else:
            prefix = '[远程客户端 已断开]'

        self.statusBar.showMessage("%s  IP=%s  Port=%d" % (prefix, ip, port), 4000)  # 状态栏

    def closeEvent(self, event):

        with open(CF_RUNNING_SEQUENCE_FILE, 'r', encoding='utf-8') as sequence_file:
            flag = int(sequence_file.readline())
            if flag != CF_RUNNING_ROOT_FLAG:
                m = {"level": 'WARNING', "title": '警告', "text": '请先关闭次级界面！',
                     "informative_text": '', 'detailed_text': ''}
                Messenger.show_QMessageBox(widget=None, message=m, QLabelMinWidth=200)
                event.ignore()
                return

        # 关闭socket服务器
        self.socket_page.socket_operator.stop_listen()
        sleep(0.5)

        os_remove(CF_RUNNING_SEQUENCE_FILE)    # 删除文件

        return super().closeEvent(event)
