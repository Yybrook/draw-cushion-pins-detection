# from os import remove as os_remove
# from time import sleep
from PyQt5.QtWidgets import QMainWindow, QStackedLayout, QStyle, QApplication
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import pyqtSignal

from UI.Root.ui_root import Ui_MainWindow as Ui_Root
from Interface.Root.Page.Cameras.interface_cameras_page import InterfaceCamerasPage
from Interface.Root.Page.Parts.interface_parts_page import InterfacePartsPage
from Interface.Root.Page.Records.interface_records_page import InterfaceRecordsPage
# from Interface.Root.Page.Socket.interface_socket_page import InterfaceSocketPage
from Interface.Root.interface_import_cards import InterfaceImportCards

from Utils.messenger import Messenger
from Utils.database_operator import DatabaseOperator
from User.config_static import (CF_ROOT_CAMERAS_PAGE, CF_ROOT_PARTS_PAGE, CF_ROOT_RECORDS_PAGE,
                                # CF_RUNNING_ROOT_FLAG, CF_RUNNING_SEQUENCE_FILE,
                                CF_APP_TITLE, CF_APP_ICON, CF_CAMERA_PICTURE, CF_PART_PICTURE, CF_RECORD_PICTURE)


class InterfaceRoot(QMainWindow, Ui_Root):
    aboutSignal = pyqtSignal()
    readMeSignal = pyqtSignal()

    def __init__(self, db_operator: DatabaseOperator):
        super().__init__()

        # 数据库
        self.db_operator = db_operator

        # 初始化窗口
        self.setupUi(self)

        # 实例化分页面
        self.cameras_page = InterfaceCamerasPage(db_operator=self.db_operator)
        self.parts_page = InterfacePartsPage(db_operator=self.db_operator)
        self.records_page = InterfaceRecordsPage(db_operator=self.db_operator)
        # self.socket_page = InterfaceSocketPage(db_operator=self.db_operator)

        # 堆叠布局
        self.stackedLayout = QStackedLayout(self.widget)
        self.stackedLayout.addWidget(self.cameras_page)
        self.stackedLayout.addWidget(self.parts_page)
        self.stackedLayout.addWidget(self.records_page)
        # self.stackedLayout.addWidget(self.socket_page)

        # 绑定信号
        # 页面切换
        self.stackedLayout.currentChanged.connect(self.current_page_changed)
        # 按钮
        self.buttonCameras.clicked.connect(self.show_cameras_page)
        self.buttonParts.clicked.connect(self.show_parts_page)
        self.buttonRecords.clicked.connect(self.show_records_page)
        self.buttonSocket.clicked.connect(self.show_socket_page)
        # # socket 状态
        # self.socket_page.serverCreatedSignal.connect(self.show_server_status)
        # self.socket_page.clientOnlineSignal.connect(lambda address: self.show_client_status(address=address, is_online=True))
        # self.socket_page.clientOfflineSignal.connect(lambda address: self.show_client_status(address=address, is_online=False))
        # 菜单
        self.actionImport.triggered.connect(self.import_cards)
        self.actionQuit.triggered.connect(self.close)
        self.actionReadMe.triggered.connect(self.readMeSignal.emit)
        self.actionAbout.triggered.connect(self.aboutSignal.emit)

        # 显示tcp server 状态
        # self.show_server_status(flag=bool(self.socket_page.socket_operator.server))

        # 窗口标题
        self.setWindowTitle('%s-Root' % CF_APP_TITLE)

        # 图标
        # 窗口图标
        self.setWindowIcon(QIcon(CF_APP_ICON))

        # 按钮图标
        self.buttonCameras.setIcon(QIcon(QPixmap(CF_CAMERA_PICTURE)))
        self.buttonParts.setIcon(QIcon(QPixmap(CF_PART_PICTURE)))
        self.buttonRecords.setIcon(QIcon(QPixmap(CF_RECORD_PICTURE)))

        style = QApplication.style()
        self.buttonSocket.setIcon(style.standardIcon(QStyle.SP_DialogNoButton))

        # 菜单图标
        self.actionImport.setIcon(style.standardIcon(QStyle.SP_FileDialogStart))
        self.actionQuit.setIcon(style.standardIcon(QStyle.SP_LineEditClearButton))
        self.actionReadMe.setIcon(style.standardIcon(QStyle.SP_FileIcon))
        self.actionAbout.setIcon(style.standardIcon(QStyle.SP_MessageBoxInformation))

    def current_page_changed(self, index: int):
        """
        切换当前页
        :param index:
        :return:
        """
        if index == CF_ROOT_CAMERAS_PAGE:
            self.cameras_page.fill_in_table()
        elif index == CF_ROOT_PARTS_PAGE:
            self.parts_page.fill_in_table()
        elif index == CF_ROOT_RECORDS_PAGE:
            self.records_page.fill_in_table()

    def import_cards(self):
        """
        导入工艺卡片
        :return:
        """
        dialog = InterfaceImportCards(db_operator=self.db_operator)
        dialog.show()
        dialog.exec_()

    def show_server_status(self, flag: bool):
        """
        显示 tcp server 状态
        :param flag:
        :return:
        """
        style = QApplication.style()

        if flag:
            icon = style.standardIcon(QStyle.SP_DialogYesButton)
        else:
            icon = style.standardIcon(QStyle.SP_DialogNoButton)

        self.buttonSocket.setIcon(icon)

    def show_client_status(self, address: tuple, is_online: bool):
        """
        显示 tcp client 状态
        :param address:
        :param is_online:
        :return:
        """
        if is_online:
            prefix = '[远程客户端 已连接]'
        else:
            prefix = '[远程客户端 已断开]'

        # 设置状态栏
        ip, port = address
        self.statusBar.showMessage("{}  IP={}  Port={}".format(prefix, ip, port), 4000)

    def show_cameras_page(self):
        """
        显示相机页面
        :return:
        """
        self.stackedLayout.setCurrentWidget(self.cameras_page)

    def show_parts_page(self):
        """
        显示零件页面
        :return:
        """
        self.stackedLayout.setCurrentWidget(self.parts_page)

    def show_records_page(self):
        """
        显示记录页面
        :return:
        """
        self.stackedLayout.setCurrentWidget(self.records_page)

    def show_socket_page(self):
        """
        显示TCP配置页面
        :return:
        """
        # self.stackedLayout.setCurrentWidget(self.socket_page)
        message = {
            'level': "INFO",
            'title': "信息",
            'text': "远程功能未启用",
            'informative_text': "",
            'detailed_text': ""
        }
        Messenger.show_message_box(
            widget=self,
            message=message,
        )

    def closeEvent(self, event):
        """
        关闭事件
        :param event:
        :return:
        """
        # # 关闭socket服务器
        # self.socket_page.socket_operator.stop_listen()
        # sleep(0.5)

        return super().closeEvent(event)

    def show(self):
        self.cameras_page.fill_in_table()
        return super().show()
