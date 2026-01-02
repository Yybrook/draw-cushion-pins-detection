from PyQt5.QtWidgets import QWidget, QMenu, QAction, QTableWidgetItem, QApplication, QStyle
from PyQt5.QtCore import QPoint

from UI.Root.Page.Parts.ui_parts_page import Ui_Form as Ui_PartsPage
from Interface.Root.Page.Parts.interface_part_detail import InterfacePartDetail

from Utils.database_operator import DatabaseOperator, get_lines_with_all
from User.config_static import CF_PARTS_TABLE_HEADER


class InterfacePartsPage(QWidget, Ui_PartsPage):

    def __init__(self, db_operator: DatabaseOperator):
        super().__init__()

        # 数据库
        self.db_operator = db_operator

        # 初始化窗口
        self.setupUi(self)

        # 表格标题
        self.tableParts.init_table(table_headers=CF_PARTS_TABLE_HEADER)

        # 筛选条件
        self.filter_dict = dict()

        # 设置comboBox
        self.comboBoxLine.set_items(get_items_callback=self.get_lines)

        # 绑定信号
        # table右键
        self.tableParts.customContextMenuRequested.connect(lambda pos: self.show_left_click_menu(pos=pos))
        # 点击下拉框箭头
        self.comboBoxLine.showPopupSignal.connect(lambda: self.comboBoxLine.set_items(get_items_callback=self.get_lines))
        # 下拉框激活
        self.comboBoxLine.activated[str].connect(self.filter_changed)

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
            delete_action.triggered.connect(lambda: self.delete_parts(item=item))
            menu.addAction(delete_action)

            # 显示菜单
            global_pos = self.tableParts.mapToGlobal(pos)
            menu.exec(global_pos)

    def fill_in_table(self):
        """
        tian
        :return:
        """
        parts = self.db_operator.get_all_parts_pins_map(
            demand_list=["ID", "Part", "Line"],
            filter_dict=self.filter_dict
        )
        self.tableParts.fill_in(contents=parts)

    def filter_changed(self, text: str):
        """
        筛选改变
        :param text:
        :return:
        """
        self.filter_dict["Line"] = text.strip().upper()
        self.fill_in_table()

    def get_lines(self) -> list:
        """
        获取所有生产线
        :return:
        """
        return get_lines_with_all(self.db_operator)

    def delete_parts(self, item: QTableWidgetItem):
        """
        删除零件
        :param item:
        :return:
        """
        # 获取所有选中的行
        selected_rows = self.tableParts.selectionModel().selectedRows()

        for row in selected_rows:
            r = row.row()
            selected_id = self.tableParts.get_item_data(row=r, header_value="ID")
            self.db_operator.delete_parts_pins_map(filter_dict={"ID": selected_id})     # 删除数据库

        # 填表
        self.fill_in_table()

    def show_part_detail(self, item: QTableWidgetItem):
        """
        显示零件详细
        :param item:
        :return:
        """
        row = item.row()
        selected_id = self.tableParts.get_item_data(row=row, header_value="ID")
        details = self.db_operator.get_parts_pins_map(demand_list=["ID", "Part", "Line", "Rows", "Columns", "PinsMap"], filter_dict={"ID": selected_id})

        dialog = InterfacePartDetail(details=details)

        dialog.saveSignal.connect(self.save_part_details)

        dialog.show()
        dialog.exec_()

    def save_part_details(self, message: dict):
        """
        保存零件详细
        :param message:
        :return:
        """
        str_pins_map = message["PinsMap"]
        part = message["Part"]
        line = message["Line"]
        self.db_operator.set_parts_pins_map(demand_dict={"PinsMap": str_pins_map}, filter_dict={"Part": part, "Line": line})
