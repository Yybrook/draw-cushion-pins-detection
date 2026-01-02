from typing import Optional

from PyQt5.QtWidgets import QWidget, QTableWidgetItem, QToolTip, QMenu, QAction, QDialog, QApplication, QStyle
from PyQt5.QtCore import pyqtSignal, Qt, QPoint
from PyQt5.QtGui import QCursor, QIcon

from UI.ui_cameras_page import Ui_Form as Ui_CamerasPage
from UI.ui_set_camera_location import Ui_Dialog as Ui_SetLocation

from Utils.database_operator import DatabaseOperator

from User.config_static import CF_CAMERAS_TABLE_HEADER, CF_PROJECT_ROLE, NULL_CAMERA_LOCATION, CF_APP_ICON


class InterfaceCamerasPage(QWidget, Ui_CamerasPage):

    openSignal = pyqtSignal(dict)
    enumSignal = pyqtSignal()

    def __init__(self, db_operator: DatabaseOperator):
        super().__init__()

        self.db_operator = db_operator  # 数据库

        self.setupUi(self)  # 初始化窗口

        self.tableCameras.init_table(table_headers=CF_CAMERAS_TABLE_HEADER)  # 初始化表格

        self.comboBoxFilter.addItems([CF_PROJECT_ROLE, "ALL", "NULL"])

        # 绑定信号
        # tabel右键
        self.tableCameras.customContextMenuRequested.connect(lambda pos: self.show_left_click_menu(pos=pos))
        # tabel双击
        self.tableCameras.itemDoubleClicked.connect(lambda item: self.open(item=item))
        # tabel鼠标进入
        self.tableCameras.itemEntered.connect(lambda item: self.show_item_text(item=item))
        # table选择改变
        self.tableCameras.itemSelectionChanged.connect(self.set_button_open_enabled)
        # 按钮
        self.buttonEnum.clicked.connect(self.enum)
        self.buttonOpen.clicked.connect(lambda: self.open())
        # 下拉框激活
        self.comboBoxFilter.activated[str].connect(self.enum)

    def show_left_click_menu(self, pos: QPoint):
        # 获取单元格
        item = self.tableCameras.itemAt(pos)

        if item is not None:
            # 设置菜单
            menu = QMenu()

            style = QApplication.style()

            set_action = QAction('设置相机位置', menu)
            set_action.setIcon(style.standardIcon(QStyle.SP_FileDialogNewFolder))
            set_action.triggered.connect(lambda: self.set_camera_location(item=item))
            menu.addAction(set_action)

            reset_action = QAction('清除相机位置', menu)
            reset_action.setIcon(style.standardIcon(QStyle.SP_DialogResetButton))
            reset_action.triggered.connect(lambda: self.reset_camera_location(item=item))
            menu.addAction(reset_action)

            # 显示菜单
            global_pos = self.tableCameras.mapToGlobal(pos)
            menu.exec(global_pos)

    def set_camera_location(self, item: QTableWidgetItem):
        row = item.row()
        message = {
            "SerialNumber": self.tableCameras.get_item_data(row=row, header_value="SerialNumber"),
            "Uid": self.tableCameras.get_item_data(row=row, header_value="Uid"),
            "Line": self.tableCameras.get_item_data(row=row, header_value="Line"),
            "Location": self.tableCameras.get_item_data(row=row, header_value="Location"),
            "Side": self.tableCameras.get_item_data(row=row, header_value="Side"),
            "Role": self.tableCameras.get_item_data(row=row, header_value="Role"),
        }
        self.show_dialog(message)

    def show_dialog(self, message: dict):
        serial_number = message.get("SerialNumber")

        # 对话框
        dialog = QDialog()
        dialog.setWindowIcon(QIcon(CF_APP_ICON))    # 设置窗口图标

        ui = Ui_SetLocation()
        ui.setupUi(dialog)
        ui.lineEditRole.setPlaceholderText(CF_PROJECT_ROLE)  # 占位符
        ui.comboBoxLocation.addItems(["RIGHT", "LEFT"])
        ui.comboBoxSide.addItems(["RIGHT", "LEFT"])

        ui.lineEditSerialNumber.setText(serial_number)
        ui.lineEditUid.setText(message.get("Uid"))
        ui.lineEditLine.setText(message.get("Line"))
        ui.comboBoxLocation.setCurrentText(message.get("Location"))
        ui.comboBoxSide.setCurrentText(message.get("Side"))
        ui.lineEditRole.setText(message.get("Role"))

        if dialog.exec_() == 1:
            # 获取文本
            line = ui.lineEditLine.text().strip().upper()
            location = ui.comboBoxLocation.currentText().strip().upper()
            side = ui.comboBoxSide.currentText().strip().upper()
            role = ui.lineEditRole.text().strip().upper()
            role = CF_PROJECT_ROLE if role == '' else role
            # 设置数据库
            self.db_operator.set_camera_identity(demand_dict={"Line": line, "Location": location, "Side": side, "Role": role},
                                                 filter_dict={"SerialNumber": serial_number})
            # 更新
            self.enum()

    def reset_camera_location(self, item: QTableWidgetItem):
        row = item.row()
        serial_number = self.tableCameras.get_item_data(row=row, header_value="SerialNumber")
        self.db_operator.delete_camera_identity(filter_dict={"SerialNumber": serial_number})
        self.enum()

    def enum(self):
        self.tableCameras.clear_all()       # 清空表格
        self.buttonOpen.setEnabled(False)   # 禁用 打开相机按钮
        self.enumSignal.emit()

    def open(self, item: Optional[QTableWidgetItem] = None):
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

        camera_location = {
            "Line": self.tableCameras.get_item_data(row=row, header_value="Line"),
            "Location": self.tableCameras.get_item_data(row=row, header_value="Location"),
            "Side": self.tableCameras.get_item_data(row=row, header_value="Side")
        }

        message = {
            "CameraIdentity": self.tableCameras.get_item_data(row=row, header_value="DeviceIndex", role=Qt.UserRole),
            "CameraLocation": camera_location,
            "Role": self.tableCameras.get_item_data(row=row, header_value="Role"),
        }
        self.openSignal.emit(message)

    def filter_cameras(self, device_info: dict, text: Optional[str] = None) -> bool:
        if text is None:
            text = self.comboBoxFilter.currentText().strip().upper()

        result = self.db_operator.get_camera_identity(demand_list=["Role"], filter_dict={"SerialNumber": device_info["SerialNumber"]})
        role = result.get("Role")
        if text == CF_PROJECT_ROLE and role == CF_PROJECT_ROLE:
            return True
        elif text == "ALL":
            return True
        elif text == "NULL" and (role is None or role == ""):
            return True
        return False

    def show_item_text(self, item: QTableWidgetItem):
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

    def set_button_open_enabled(self):
        """
        QTableWidget 中 itemSelectionChanged 的槽函数
        :return:
        """
        # 获取所有选中的行
        selected_rows = self.tableCameras.selectionModel().selectedRows()
        # 根据选中行, 判断禁用打开相机按钮
        if selected_rows:
            self.buttonOpen.setEnabled(True)
        else:
            self.buttonOpen.setEnabled(False)

    def fill_in_table(self, cameras_identity: list):

        # 禁止自动排序,防止显示混乱和不全
        self.tableCameras.setSortingEnabled(False)

        # 设置表格行数
        self.tableCameras.setRowCount(len(cameras_identity))

        for row, camera_identity in enumerate(cameras_identity):
            # 读取数据库
            result = NULL_CAMERA_LOCATION.copy()
            result.update(self.db_operator.get_camera_identity(demand_list=["Line", "Location", "Side", "Role"],
                                                               filter_dict={"SerialNumber": camera_identity.serial_number}))

            # 向表格中写入数据
            for column in range(self.tableCameras.columnCount()):

                # 获取表头内容
                header_text = self.tableCameras.horizontalHeaderItem(column).text()
                header_key = self.tableCameras.headers[header_text]

                if header_key in result.keys():
                    self.tableCameras.set_table_item(data=result[header_key], row=row, column=column)
                elif header_key == "DeviceIndex":
                    item = self.tableCameras.set_table_item(data=camera_identity.device_index, row=row, column=column)
                    item.setData(Qt.UserRole, camera_identity)
                elif header_key == "Uid":
                    self.tableCameras.set_table_item(data=camera_identity.uid, row=row, column=column)
                elif header_key == "SerialNumber":
                    self.tableCameras.set_table_item(data=camera_identity.serial_number, row=row, column=column)
                elif header_key == "CurrentIp":
                    self.tableCameras.set_table_item(data=camera_identity.current_ip, row=row, column=column)
                elif header_key == "ModelName":
                    self.tableCameras.set_table_item(data=camera_identity.model_name, row=row, column=column)

        # 使能自动排序
        self.tableCameras.setSortingEnabled(True)
