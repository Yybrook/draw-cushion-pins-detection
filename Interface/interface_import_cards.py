from os import path
from winreg import OpenKey, QueryValueEx, HKEY_CURRENT_USER
from PyQt5.QtWidgets import QDialog, QFileDialog, QMenu, QAction, QStyle, QTableWidgetItem, QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QPoint

from UI.ui_import_cards import Ui_Dialog as Ui_ImportCards
from Interface.interface_part_detail import InterfacePartDetail
from UI.ui_replace_data import Ui_Dialog as Ui_Replace

from Utils.excel_reader import ExcelReader
from Utils.serializer import MySerializer
from Utils.database_operator import DatabaseOperator
from User.config_static import (CF_APP_ICON, CF_PINSMAP_CODES_LIST, CF_IMPORT_TABLE_HEADER, TB_PARTS_PINSMAP,
                                CF_DATA_REPLACE_ONCE, CF_DATA_REPLACE_ALL, CF_DATA_REPLACE_NONE)


class InterfaceImportCards(QDialog, Ui_ImportCards):

    def __init__(self, db_operator: DatabaseOperator):
        super().__init__()

        self.db_operator = db_operator

        self.files = list()

        self.setupUi(self)  # 初始化窗口

        self.replace_flag: int = CF_DATA_REPLACE_ONCE

        self.setWindowIcon(QIcon(CF_APP_ICON))  # 设置窗口图标

        # 设置下拉框
        self.comboBoxPin.addItems(CF_PINSMAP_CODES_LIST)
        self.comboBoxNull.addItems(CF_PINSMAP_CODES_LIST)
        self.comboBoxFree.addItems(CF_PINSMAP_CODES_LIST)
        self.comboBoxDowel.addItems(CF_PINSMAP_CODES_LIST)

        self.tableParts.init_table(table_headers=CF_IMPORT_TABLE_HEADER)  # 表格标题
        self.tableParts.setSortingEnabled(False)      # 禁止自动排序

        # 连接信号
        self.buttonImport.clicked.connect(self.import_files)
        self.buttonDecode.clicked.connect(self.decode_files)

        self.comboBoxPin.currentIndexChanged.connect(self.code_changed)
        self.comboBoxNull.currentIndexChanged.connect(self.code_changed)
        self.comboBoxFree.currentIndexChanged.connect(self.code_changed)
        self.comboBoxDowel.currentIndexChanged.connect(self.code_changed)

        self.tableParts.customContextMenuRequested.connect(lambda pos: self.show_left_click_menu(pos=pos))

    def init(self):

        # self.files = list()

        self.comboBoxPin.setCurrentIndex(1)
        self.comboBoxNull.setCurrentIndex(0)
        self.comboBoxFree.setCurrentIndex(0)
        self.comboBoxDowel.setCurrentIndex(4)

        # self.buttonDecode.setEnabled(False)

        # self.tableParts.clear_all()

    def decode_files(self):

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

    def show_info(self, info: str):
        self.textBrowserInfo.append(info)  # 文本框逐条添加数据
        self.textBrowserInfo.moveCursor(self.textBrowserInfo.textCursor().End)  # 文本框显示到底部

    def fill_in_table(self, data: dict):
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
            header_text = self.tableParts.horizontalHeaderItem(column).text()  # 获取表头内容
            head_key = self.tableParts.headers[header_text]
            # 设置item
            item = self.tableParts.set_table_item(data=data[head_key], row=current_rows, column=column)
            if head_key == "ID":
                str_pins_map = MySerializer.serialize(data["PinsMap"])      # 序列化
                item.setData(Qt.UserRole, str_pins_map)

    def duplicated(self, data: dict):
        part = data["Part"]
        line = data["Line"]
        rows = self.tableParts.rowCount()
        if rows > 0:
            for row in range(rows):
                if (part == self.tableParts.get_item_data(row=row, header_value="Part") and
                        line == self.tableParts.get_item_data(row=row, header_value="Line")):
                    return True
        else:
            return False

    def show_left_click_menu(self, pos: QPoint):
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
        row = item.row()
        details = dict()
        for col, value in enumerate(self.tableParts.headers.values()):
            details[value] = self.tableParts.item(row, col).data(Qt.DisplayRole)
            if value == "ID":
                details["PinsMap"] = self.tableParts.item(row, col).data(Qt.UserRole)

        dialog_detail = InterfacePartDetail(details=details)

        dialog_detail.saveSignal.connect(self.update_part_details)

        dialog_detail.show()
        dialog_detail.exec_()

    def update_part_details(self, message: dict):
        str_pins_map = message["PinsMap"]
        selected_id = message["ID"]
        row = selected_id - 1
        self.tableParts.set_item_data(data=str_pins_map, row=row, header_value="ID", role=Qt.UserRole)

    def save_2_database(self):

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
                self.db_operator.insert_to_table(table_name=TB_PARTS_PINSMAP, demand_dict=demand_dict)

    def show_replace_dialog(self, line: str, part: str, demand_dict: dict, filter_dict: dict):
        dialog = QDialog()
        dialog.setWindowIcon(QIcon(CF_APP_ICON))  # 设置窗口图标

        ui = Ui_Replace()
        ui.setupUi(dialog)
        ui.labelLine.setText(line)
        ui.labelPart.setText(part)

        ui.buttonNo.clicked.connect(dialog.close)
        ui.buttonNo2All.clicked.connect(lambda: self.set_2_replace(dialog=dialog, demand_dict=demand_dict, filter_dict=filter_dict, replace_flag=CF_DATA_REPLACE_NONE))
        ui.buttonYes.clicked.connect(lambda: self.set_2_replace(dialog=dialog, demand_dict=demand_dict, filter_dict=filter_dict, replace_flag=CF_DATA_REPLACE_ONCE))
        ui.buttonYes2All.clicked.connect(lambda: self.set_2_replace(dialog=dialog, demand_dict=demand_dict, filter_dict=filter_dict, replace_flag=CF_DATA_REPLACE_ALL))

        dialog.exec_()

    def set_2_replace(self, dialog: QDialog, demand_dict: dict, filter_dict: dict, replace_flag: int):
        # 转换全局变量
        self.replace_flag = replace_flag
        if replace_flag >= 0:
            # 更新
            self.db_operator.update_table(table_name=TB_PARTS_PINSMAP, demand_dict=demand_dict, filter_dict=filter_dict)
        # 关闭
        dialog.close()

    def accept(self):
        # 保存到数据库
        self.save_2_database()
        return super().accept()

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
        self.verify_decode_state()

    def import_files(self):
        # 获取桌面路径
        key = OpenKey(HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
        desktop = QueryValueEx(key, "Desktop")[0]

        self.files, _ = QFileDialog.getOpenFileNames(self, '选择零件工艺卡', desktop, 'EXCEL文件 (*.xlsx)')
        self.verify_decode_state()

    def show(self):
        self.init()

        return super().show()
