from os import path
from winreg import OpenKey, QueryValueEx, HKEY_CURRENT_USER
from PyQt5.QtWidgets import QDialog, QFileDialog, QMenu, QAction, QStyle, QTableWidgetItem, QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QPoint

from UI.Root.ui_import_cards import Ui_Dialog as Ui_ImportCards
from UI.Root.ui_replace_data import Ui_Dialog as Ui_Replace
from Interface.Root.Page.Parts.interface_part_detail import InterfacePartDetail

from Utils.excel_reader import ExcelReader
from Utils.serializer import MySerializer
from Utils.database_operator import DatabaseOperator
from User.config_static import (CF_APP_ICON, CF_PINSMAP_CODES_LIST, CF_IMPORT_TABLE_HEADER, TB_PARTS_PINSMAP,
                                CF_DATA_REPLACE_ONCE, CF_DATA_REPLACE_ALL, CF_DATA_REPLACE_NONE)


class InterfaceImportCards(QDialog, Ui_ImportCards):

    def __init__(self, db_operator: DatabaseOperator):
        super().__init__()

        # 数据库
        self.db_operator = db_operator

        # 初始化窗口
        self.setupUi(self)

        # 设置下拉框
        self.comboBoxPin.addItems(CF_PINSMAP_CODES_LIST)
        self.comboBoxNull.addItems(CF_PINSMAP_CODES_LIST)
        self.comboBoxFree.addItems(CF_PINSMAP_CODES_LIST)
        self.comboBoxDowel.addItems(CF_PINSMAP_CODES_LIST)

        # 初始化表格
        self.tableParts.init_table(
            table_headers=CF_IMPORT_TABLE_HEADER,
            header_resize=1,  # 根据表格大小自适应
            selection=1,  # 单选
        )
        # 禁止自动排序
        self.tableParts.setSortingEnabled(False)

        # 工艺卡文件
        self.files = list()

        # 标志
        self.replace_flag: int = CF_DATA_REPLACE_ONCE

        # 连接信号
        # 按键
        self.buttonImport.clicked.connect(self.import_files)
        self.buttonDecode.clicked.connect(self.decode_files)
        # 下拉框
        self.comboBoxPin.currentIndexChanged.connect(self.code_changed)
        self.comboBoxNull.currentIndexChanged.connect(self.code_changed)
        self.comboBoxFree.currentIndexChanged.connect(self.code_changed)
        self.comboBoxDowel.currentIndexChanged.connect(self.code_changed)
        # 表格右键菜单
        self.tableParts.customContextMenuRequested.connect(lambda pos: self.show_left_click_menu(pos=pos))

        # 设置窗口图标
        self.setWindowIcon(QIcon(CF_APP_ICON))

    def init_interface(self):
        """
        初始化界面
        :return:
        """
        # self.files = list()
        # self.buttonDecode.setEnabled(False)
        # self.tableParts.clear_all()
        # 下拉框初始化
        self.comboBoxPin.setCurrentIndex(1)
        self.comboBoxNull.setCurrentIndex(0)
        self.comboBoxFree.setCurrentIndex(0)
        self.comboBoxDowel.setCurrentIndex(4)

    def decode_files(self):
        """
        解析工艺文件
        :return:
        """
        # 清除 textBrowserInfo
        self.textBrowserInfo.clear()

        rows = self.spinBoxRows.value()
        columns = self.spinBoxColumns.value()
        codes = {
            'Pin': self.comboBoxPin.currentText(),
            'Null': self.comboBoxNull.currentText(),
            'Dowel': self.comboBoxDowel.currentText()
        }
        if self.comboBoxFree.currentIndex() != 0:
            codes['Free'] = self.comboBoxFree.currentText()

        # 实例化excel reader
        reader = ExcelReader(rows=rows, columns=columns, decode_codes=codes)

        for file in self.files:
            res, data = reader.decode_file(file_path=file)
            # 失败
            if not res:
                info = "[解析错误] 文件[%s] 错误详细[%s]" % (path.basename(file), data)
                self.show_info(info=info)
                continue

            # 去重
            res = self.duplicated(data=data)
            if res:
                info = "[重复导入] 文件[%s] 生产线[%s] 零件[%s]" % (path.basename(file), data["Line"], data["Part"])
                self.show_info(info=info)
                continue

            # 写入数据
            self.fill_in_table(data=data)

        # 复位
        self.files = list()
        self.buttonDecode.setEnabled(False)

    def fill_in_table(self, data: dict):
        """
        填充表格
        :param data:
        :return:
        """
        # 总行数
        current_rows = self.tableParts.rowCount()

        if current_rows > 0:
            # id + 1
            data["ID"] = self.tableParts.get_item_data(row=current_rows - 1, header_value="ID") + 1
        else:
            data["ID"] = 1

        # 插入行
        self.tableParts.insertRow(current_rows)
        # 写入数据
        for column in range(self.tableParts.columnCount()):
            # 获取表头内容
            header_text = self.tableParts.horizontalHeaderItem(column).text()
            head_key = self.tableParts.headers[header_text]
            # 设置item
            item = self.tableParts.set_table_item(data=data[head_key], row=current_rows, column=column)
            if head_key == "ID":
                # 序列化
                str_pins_map = MySerializer.serialize(data["PinsMap"])
                item.setData(Qt.UserRole, str_pins_map)

    def show_info(self, info: str):
        """
        向 textBrowser 中显示 info
        :param info:
        :return:
        """
        # 文本框逐条添加数据
        self.textBrowserInfo.append(info)
        # 光标移动至底部
        self.textBrowserInfo.moveCursor(self.textBrowserInfo.textCursor().End)

    def duplicated(self, data: dict):
        """
        去重
        :param data:
        :return:
        """
        part = data["Part"]
        line = data["Line"]
        rows = self.tableParts.rowCount()

        if rows <= 0:
            return False

        for row in range(rows):
            if (part == self.tableParts.get_item_data(row=row, header_value="Part") and
                    line == self.tableParts.get_item_data(row=row, header_value="Line")):
                return True
        else:
            return False

    def show_left_click_menu(self, pos: QPoint):
        """
        右键菜单
        :param pos:
        :return:
        """
        # 获取单元格
        item = self.tableParts.itemAt(pos)

        if item is not None:
            # 设置菜单
            menu = QMenu()

            style = QApplication.style()

            detail_action = QAction('显示详细', menu)
            detail_action.setIcon(style.standardIcon(QStyle.SP_FileDialogDetailedView))
            detail_action.triggered.connect(lambda: self.show_part_detail(item=item))
            menu.addAction(detail_action)

            delete_action = QAction('删除', menu)
            delete_action.setIcon(style.standardIcon(QStyle.SP_TrashIcon))
            delete_action.triggered.connect(self.delete_parts)
            menu.addAction(delete_action)

            # 显示菜单
            global_pos = self.tableParts.mapToGlobal(pos)
            menu.exec(global_pos)

    def delete_parts(self):
        """
        在表格中删除零件
        :return:
        """
        rows = list()
        # 获取所有选中的行
        selected_rows = self.tableParts.selectionModel().selectedRows()
        for row in selected_rows:
            r = row.row()
            rows.append(r)
        # 排序
        rows.sort(reverse=True)
        # 删除
        for r in rows:
            self.tableParts.removeRow(r)

        # 修改id
        if rows:
            row_count = self.tableParts.rowCount()
            for r in range(rows[-1], row_count):
                self.tableParts.set_item_data(data=r + 1, row=r, header_value="ID")

    def show_part_detail(self, item: QTableWidgetItem):
        """
        显示零件详细
        :param item:
        :return:
        """
        row = item.row()
        details = dict()
        for col, value in enumerate(self.tableParts.headers.values()):
            details[value] = self.tableParts.item(row, col).data(Qt.DisplayRole)
            if value == "ID":
                details["PinsMap"] = self.tableParts.item(row, col).data(Qt.UserRole)

        # 显示零件详细对话框
        dialog_detail = InterfacePartDetail(details=details)
        dialog_detail.saveSignal.connect(self.update_part_details)
        dialog_detail.show()
        dialog_detail.exec_()

    def update_part_details(self, message: dict):
        """
        在表格中更新零件详细
        :param message:
        :return:
        """
        str_pins_map = message["PinsMap"]
        selected_id = message["ID"]
        row = selected_id - 1
        self.tableParts.set_item_data(data=str_pins_map, row=row, header_value="ID", role=Qt.UserRole)

    def save_2_database(self):
        """
        保存至数据库
        :return:
        """
        row_count = self.tableParts.rowCount()
        for r in range(row_count):
            pins_map = self.tableParts.get_item_data(row=r, header_value="ID", role=Qt.UserRole)
            part = self.tableParts.get_item_data(row=r, header_value="Part")
            line = self.tableParts.get_item_data(row=r, header_value="Line")
            rows = self.tableParts.get_item_data(row=r, header_value="Rows")
            columns = self.tableParts.get_item_data(row=r, header_value="Columns")

            is_exist = self.db_operator.verify_part_existence(table_name=TB_PARTS_PINSMAP, part=part, line=line)

            demand_dict = {"Rows": rows, "Columns": columns, "PinsMap": pins_map}
            filter_dict = {"Part": part, "Line": line}

            # 有重复数据 询问
            if is_exist and self.replace_flag == CF_DATA_REPLACE_ONCE:
                # 对话框
                self.show_replace_dialog(line=line, part=part, demand_dict=demand_dict, filter_dict=filter_dict)
            # 有重复数据 更新
            elif is_exist and self.replace_flag == CF_DATA_REPLACE_ALL:
                self.db_operator.update_table(table_name=TB_PARTS_PINSMAP, demand_dict=demand_dict, filter_dict=filter_dict)
            # 有重复数据 不更新
            elif is_exist and self.replace_flag == CF_DATA_REPLACE_NONE:
                pass
            # 没有重复数据 插入数据
            else:
                demand_dict.update(filter_dict)
                self.db_operator.insert_to_table(table_name=TB_PARTS_PINSMAP, demand=demand_dict)

    def show_replace_dialog(self, line: str, part: str, demand_dict: dict, filter_dict: dict):
        """
        显示确认替换对话框
        :param line:
        :param part:
        :param demand_dict:
        :param filter_dict:
        :return:
        """
        dialog = QDialog()
        # 设置窗口图标
        dialog.setWindowIcon(QIcon(CF_APP_ICON))

        # 实例化对话框
        ui = Ui_Replace()
        # 初始化
        ui.setupUi(dialog)
        ui.labelLine.setText(line)
        ui.labelPart.setText(part)

        # 连接信号
        ui.buttonNo.clicked.connect(dialog.close)
        ui.buttonNo2All.clicked.connect(lambda: self.set_2_replace(dialog=dialog, demand_dict=demand_dict, filter_dict=filter_dict, replace_flag=CF_DATA_REPLACE_NONE))
        ui.buttonYes.clicked.connect(lambda: self.set_2_replace(dialog=dialog, demand_dict=demand_dict, filter_dict=filter_dict, replace_flag=CF_DATA_REPLACE_ONCE))
        ui.buttonYes2All.clicked.connect(lambda: self.set_2_replace(dialog=dialog, demand_dict=demand_dict, filter_dict=filter_dict, replace_flag=CF_DATA_REPLACE_ALL))

        dialog.exec_()

    def set_2_replace(self, dialog: QDialog, demand_dict: dict, filter_dict: dict, replace_flag: int):
        """
        替换至数据库
        :param dialog:
        :param demand_dict:
        :param filter_dict:
        :param replace_flag:
        :return:
        """
        # 转换全局变量
        self.replace_flag = replace_flag
        if replace_flag >= 0:
            # 更新
            self.db_operator.update_table(table_name=TB_PARTS_PINSMAP, demand_dict=demand_dict, filter_dict=filter_dict)
        # 关闭
        dialog.close()

    def verify_decode_state(self):
        """
        验证解析按钮的状态
        :return:
        """
        pin_code = self.comboBoxPin.currentIndex()
        null_code = self.comboBoxNull.currentIndex()
        dowel_code = self.comboBoxDowel.currentIndex()

        if pin_code != 0 and null_code != 0 and dowel_code != 0 and self.files:
            self.buttonDecode.setEnabled(True)
        else:
            self.buttonDecode.setEnabled(False)

    def code_changed(self, index: int):
        """
        下拉框变化的槽函数
        :param index:
        :return:
        """
        self.verify_decode_state()

    def import_files(self):
        """
        导入文件
        :return:
        """
        # 获取桌面路径
        key = OpenKey(HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
        desktop = QueryValueEx(key, "Desktop")[0]
        # 显示文件选择对话框
        self.files, _ = QFileDialog.getOpenFileNames(self, '选择零件工艺卡', desktop, 'EXCEL文件 (*.xlsx)')
        # 验证状态
        self.verify_decode_state()

    def accept(self):
        # 保存到数据库
        self.save_2_database()
        return super().accept()

    def show(self):
        # 初始化
        self.init_interface()
        return super().show()
