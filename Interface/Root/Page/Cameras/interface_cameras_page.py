from typing import Optional
import yaml

from PyQt5.QtWidgets import QWidget, QTableWidgetItem, QToolTip, QMenu, QAction, QDialog
from PyQt5.QtCore import pyqtSignal, QPoint
from PyQt5.QtGui import QCursor, QIcon

from UI.Root.Page.Cameras.ui_cameras_page import Ui_Form as Ui_CamerasPage
from UI.Root.Page.Cameras.ui_set_camera_identity import Ui_Dialog as Ui_SetCameraIdentity

from CameraCore.camera_identity import CameraIdentity

from Utils.database_operator import DatabaseOperator

from User.config_static import CF_CAMERAS_TABLE_HEADER, CF_APP_ICON, CF_DYNAMIC_CONFIG_PATH


class InterfaceCamerasPage(QWidget, Ui_CamerasPage):

    openSignal = pyqtSignal(dict)

    def __init__(self, db_operator: DatabaseOperator):
        super().__init__()

        # 数据库
        self.db_operator = db_operator

        # 初始化窗口
        self.setupUi(self)

        # 初始化表格
        self.tableCameras.init_table(
            table_headers=CF_CAMERAS_TABLE_HEADER,
            header_resize=1,            # 根据表格大小自适应
            selection=1,                # 单选
        )

        # 绑定信号
        # tabel右键
        self.tableCameras.customContextMenuRequested.connect(lambda pos: self.show_left_click_menu(pos=pos))
        # tabel双击
        self.tableCameras.itemDoubleClicked.connect(lambda item: self.open(item=item))
        # table选择改变
        self.tableCameras.itemSelectionChanged.connect(self.set_button_open_enabled)
        # tabel鼠标进入
        self.tableCameras.itemEntered.connect(lambda item: self.show_item_text(item=item))
        # 按钮
        self.buttonOpen.clicked.connect(lambda item: self.open(item=None))

    def show_left_click_menu(self, pos: QPoint):
        """
        右键菜单
        :param pos:
        :return:
        """
        # 设置菜单
        menu = QMenu()

        # 获取单元格
        item = self.tableCameras.itemAt(pos)

        if item is not None:
            set_action = QAction('设置相机身份', menu)
            set_action.triggered.connect(lambda: self.set_camera_identity(item=item))
            menu.addAction(set_action)

            del_action = QAction('删除相机', menu)
            del_action.triggered.connect(lambda: self.delete_camera(item=item))
            menu.addAction(del_action)

        add_action = QAction('添加相机', menu)
        add_action.triggered.connect(lambda: self.set_camera_identity(item=None))
        menu.addAction(add_action)

        # 转换为全局坐标
        global_pos = self.tableCameras.mapToGlobal(pos)
        # 显示菜单
        menu.exec(global_pos)

    def set_camera_identity(self, item: Optional[QTableWidgetItem]):
        """
        设置相机身份
        :param item:
        :return:
        """
        if item is not None:
            row = item.row()
            message = {
                "IP": self.tableCameras.get_item_data(row=row, header_value="IP"),
                "Port": self.tableCameras.get_item_data(row=row, header_value="Port"),
                "User": self.tableCameras.get_item_data(row=row, header_value="User"),
                "Password": self.tableCameras.get_item_data(row=row, header_value="Password"),
                "Line": self.tableCameras.get_item_data(row=row, header_value="Line"),
                "Location": self.tableCameras.get_item_data(row=row, header_value="Location"),
                "Side": self.tableCameras.get_item_data(row=row, header_value="Side"),
            }
        else:
            message = dict()

        # 显示对话框
        self.show_set_camera_identity_dialog(message)

    def show_set_camera_identity_dialog(self, message: dict):
        """
        显示对话框
        :param message:
        :return:
        """
        # 对话框
        dialog = QDialog()
        # 设置窗口图标
        dialog.setWindowIcon(QIcon(CF_APP_ICON))

        ui = Ui_SetCameraIdentity()
        ui.setupUi(dialog)

        # 从 yaml 文件中获取配置
        with open(CF_DYNAMIC_CONFIG_PATH, encoding='ascii', errors='ignore') as f:
            dynamic_config = yaml.safe_load(f)
        lines = dynamic_config['lines']

        ui.comboBoxLine.addItems(lines)
        ui.comboBoxLocation.addItems(["RIGHT", "LEFT"])
        ui.comboBoxSide.addItems(["RIGHT", "LEFT"])

        ui.lineEditIp.setText(message.get("IP", ""))
        ui.lineEditPort.setText(message.get("Port", ""))
        ui.lineEditUser.setText(message.get("User", ""))
        ui.lineEditPassword.setText(message.get("Password", ""))

        ui.comboBoxLine.setCurrentText(message.get("Line", ""))
        ui.comboBoxLocation.setCurrentText(message.get("Location", ""))
        ui.comboBoxSide.setCurrentText(message.get("Side", ""))

        if dialog.exec_() == 1:
            # 获取文本
            line = ui.comboBoxLine.currentText().strip().upper()
            location = ui.comboBoxLocation.currentText().strip().upper()
            side = ui.comboBoxSide.currentText().strip().upper()

            ip = ui.lineEditIp.get_text().strip()
            port = ui.lineEditPort.get_text().strip()
            user = ui.lineEditUser.get_text().strip()
            password = ui.lineEditPassword.get_text().strip()

            if port.isdigit() and CameraIdentity.is_ip_valid(ip):
                # 生成序列号
                serial_number = CameraIdentity.generate_serial_number(ip=ip, port=port)

                # 设置数据库
                self.db_operator.set_camera_identity(demand_dict={"Line": line, "Location": location, "Side": side, "User": user, "Password": password},
                                                     filter_dict={"SerialNumber": serial_number})

                # 更新表格
                self.fill_in_table()

    def delete_camera(self, item: QTableWidgetItem):
        """
        删除相机
        :param item:
        :return:
        """
        row = item.row()
        ip = self.tableCameras.get_item_data(row=row, header_value="IP")
        port = self.tableCameras.get_item_data(row=row, header_value="Port")
        # 生成序列号
        serial_number = CameraIdentity.generate_serial_number(ip=ip, port=port)
        # 删除
        self.db_operator.delete_camera_identity(filter_dict={"SerialNumber": serial_number})
        # 更新表格
        self.fill_in_table()

    def fill_in_table(self):
        """
        填充表格
        :return:
        """
        # 从数据库获取相机信息
        cameras_identity = self.db_operator.get_camera_identity(
            demand_list=list(),
            filter_dict=dict(),
            is_fetchall=True,
        )

        # 清空表格
        self.tableCameras.clear_all()

        # 禁止自动排序,防止显示混乱和不全
        self.tableCameras.setSortingEnabled(False)

        # 设置表格行数
        self.tableCameras.setRowCount(len(cameras_identity))

        for row, camera_identity in enumerate(cameras_identity):

            # 通过 serial number 解析获得 ip 和 port
            ip, port = CameraIdentity.decode_serial_number(serial_number=camera_identity["SerialNumber"])

            # 向表格中写入数据
            for column in range(self.tableCameras.columnCount()):

                # 获取表头内容
                header_text = self.tableCameras.horizontalHeaderItem(column).text()
                header_key = self.tableCameras.headers[header_text]

                if header_key in camera_identity.keys():
                    self.tableCameras.set_table_item(data=camera_identity[header_key], row=row, column=column)
                elif header_key == "DeviceIndex":
                    self.tableCameras.set_table_item(data=str(row), row=row, column=column)
                elif header_key == "IP":
                    self.tableCameras.set_table_item(data=ip, row=row, column=column)
                elif header_key == "Port":
                    self.tableCameras.set_table_item(data=str(port), row=row, column=column)

        # 使能自动排序
        self.tableCameras.setSortingEnabled(True)

    def open(self, item: Optional[QTableWidgetItem] = None):
        """
        发送打开相机数据
        :param item:
        :return:
        """
        if item is None:
            # 获取所有选中的行
            selected_rows = self.tableCameras.selectionModel().selectedRows()
            # 获取第一行
            if selected_rows:
                row = selected_rows[0].row()
            else:
                return
        else:
            row = item.row()

        message = {
            "Line": self.tableCameras.get_item_data(row=row, header_value="Line"),
            "Location": self.tableCameras.get_item_data(row=row, header_value="Location"),
            "Side": self.tableCameras.get_item_data(row=row, header_value="Side"),
            "IP": self.tableCameras.get_item_data(row=row, header_value="IP"),
            "Port": self.tableCameras.get_item_data(row=row, header_value="Port"),
            "User": self.tableCameras.get_item_data(row=row, header_value="User"),
            "Password": self.tableCameras.get_item_data(row=row, header_value="Password"),
        }

        self.openSignal.emit(message)

    def set_button_open_enabled(self):
        """
        使能open按键
        :return:
        """
        # 获取所有选中的行
        selected_rows = self.tableCameras.selectionModel().selectedRows()
        # 根据选中行, 判断禁用打开相机按钮
        self.buttonOpen.setEnabled(bool(selected_rows))

    def show_item_text(self, item: QTableWidgetItem):
        """
        显示item信息
        :param item:
        :return:
        """
        if item is None:
            return
        # # 获得QTableWidgetItem文本
        # text = item.text()
        # # 获取文本宽度
        # # text_width_1 = QFontMetrics(item.font()).boundingRect(text).width()     # 不带格式,会小一点
        # text_width = QFontMetrics(item.font()).width(text)                      # 带格式,会大一点
        # # 获得 QTableWidgetItem 列宽
        # column_width = self.tableCameras.columnWidth(item.column())
        # # 如果 文本宽度 大于 列宽, 也就是所文字会显示不全
        # if text_width > column_width:
        #     # 在当前鼠标位置上显示 tooltip
        #     QToolTip.showText(QCursor.pos(), text, self.tableCameras)
        QToolTip.showText(QCursor.pos(), item.text(), self.tableCameras)
