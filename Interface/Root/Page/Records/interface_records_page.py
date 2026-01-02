from os import remove as os_remove, path as os_path
from subprocess import run as subprocess_run
from PyQt5.QtWidgets import QWidget, QMenu, QAction, QTableWidgetItem, QApplication, QStyle, QMessageBox
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import Qt

from UI.Root.Page.Records.ui_records_page import Ui_Form as Ui_RecordsPage

from Utils.database_operator import DatabaseOperator, get_lines_with_all, get_parts_with_all
from Utils.messenger import Messenger
from User.config_static import CF_RECORDS_TABLE_HEADER


class InterfaceRecordsPage(QWidget, Ui_RecordsPage):
    def __init__(self, db_operator: DatabaseOperator):
        super().__init__()

        self.db_operator = db_operator  # 数据库

        self.setupUi(self)  # 初始化窗口

        self.tableRecords.init_table(table_headers=CF_RECORDS_TABLE_HEADER)     # 表格标题

        self.tableRecords.sortItems(0, Qt.DescendingOrder)      # 降序排列

        self.current_page = self.spinBoxPage.value() - 1    # 当前页，从0开始
        self.page_rows = self.spinBoxPageRows.value()       # 每页行数
        self.total_pages = -1                               # 总页数

        self.filter_dict = dict()   # 筛选条件

        # 设置comboBox
        self.comboBoxLine.set_items(get_items_callback=self.get_lines)
        self.comboBoxPart.set_items(get_items_callback=self.get_parts)
        self.comboBoxLocation.addItems(["ALL", "LEFT", "RIGHT"])

        # 绑定信号
        # table右键
        self.tableRecords.customContextMenuRequested.connect(lambda pos: self.show_left_click_menu(pos=pos))
        # 点击下拉框箭头
        self.comboBoxLine.showPopupSignal.connect(lambda: self.comboBoxLine.set_items(get_items_callback=self.get_lines))
        self.comboBoxPart.showPopupSignal.connect(lambda: self.comboBoxPart.set_items(get_items_callback=self.get_parts))
        # 下拉框激活
        self.comboBoxLine.activated.connect(lambda text: self.filter_changed())
        self.comboBoxLine.activated.connect(lambda: self.comboBoxPart.set_items(get_items_callback=self.get_parts))
        self.comboBoxPart.activated.connect(lambda text: self.filter_changed())
        self.comboBoxLocation.activated.connect(lambda text: self.filter_changed())
        # 单选框
        self.checkBoxResult.clicked.connect(self.filter_changed)
        # 翻页
        self.spinBoxPage.valueChanged.connect(self.page_changed)
        self.spinBoxPageRows.valueChanged.connect(self.page_rows_changed)
        self.buttonBack.clicked.connect(self.page_back)
        self.buttonNext.clicked.connect(self.page_next)

        # 初始化每页行数
        self.set_page_rows(page_rows=self.page_rows)

    def show_left_click_menu(self, pos: QPoint):
        # 获取单元格
        item = self.tableRecords.itemAt(pos)

        if item is not None:
            # 设置菜单
            menu = QMenu()

            style = QApplication.style()

            open_origin_action = QAction('打开相机原始图片', menu)
            open_origin_action.setIcon(style.standardIcon(QStyle.SP_FileDialogDetailedView))
            open_origin_action.triggered.connect(lambda: self.open_image(item=item, flag=1))
            menu.addAction(open_origin_action)

            open_detection_action = QAction('打开检测结果图片', menu)
            open_detection_action.setIcon(style.standardIcon(QStyle.SP_FileDialogContentsView))
            open_detection_action.triggered.connect(lambda: self.open_image(item=item, flag=0))
            menu.addAction(open_detection_action)

            delete_action = QAction('删除', menu)
            delete_action.setIcon(style.standardIcon(QStyle.SP_TrashIcon))
            delete_action.triggered.connect(lambda: self.delete_records(item=item))
            menu.addAction(delete_action)

            # 显示菜单
            global_pos = self.tableRecords.mapToGlobal(pos)
            menu.exec(global_pos)

    def set_page_rows(self, page_rows: int):
        """
        设置每页行数
        :param page_rows:
        :return:
        """
        # 获得总页数
        self.total_pages, _, _ = self.db_operator.get_detection_records_pages(page_rows=page_rows, filter_dict=self.filter_dict)

        # 显示总页数
        self.labelPages.setText(str(self.total_pages))

        if self.total_pages <= 0:
            self.spinBoxPage.setMaximum(1)
            self.current_page = 0
        else:
            self.spinBoxPage.setMaximum(self.total_pages)
            if self.current_page > self.total_pages - 1:
                self.current_page = self.total_pages - 1

        self.spinBoxPage.setValue(self.current_page + 1)

    def page_back(self):
        if self.current_page <= 0:
            return
        self.current_page -= 1
        self.spinBoxPage.setValue(self.current_page + 1)
        self.fill_in_table()

    def page_next(self):
        if self.current_page >= self.total_pages - 1:
            return
        self.current_page += 1
        self.spinBoxPage.setValue(self.current_page + 1)
        self.fill_in_table()

    def page_changed(self, value: int):
        self.current_page = value - 1
        self.fill_in_table()

    def page_rows_changed(self, value: int):
        self.page_rows = value
        self.set_page_rows(page_rows=self.page_rows)
        self.fill_in_table()

    def filter_changed(self):
        self.filter_dict["Line"] = self.comboBoxLine.currentText().strip().upper()
        self.filter_dict["Part"] = self.comboBoxPart.currentText().strip().upper()
        self.filter_dict["Location"] = self.comboBoxLocation.currentText().strip().upper()
        self.filter_dict["Result"] = "FALSE" if self.checkBoxResult.isChecked() else "ALL"
        self.set_page_rows(page_rows=self.page_rows)
        self.fill_in_table()

    def fill_in_table(self):
        records = self.db_operator.get_all_detection_records(demand_list=CF_RECORDS_TABLE_HEADER.values(), filter_dict=self.filter_dict,
                                                             page_rows=self.page_rows, page=self.current_page)

        for record in records:
            record["When"] = str(record["When"])
            record["Result"] = "正确" if record["Result"] else "错误"

        self.tableRecords.fill_in(contents=records)

    def get_lines(self) -> list:
        return get_lines_with_all(self.db_operator)

    def get_parts(self) -> list:
        line = self.comboBoxLine.currentText().strip().upper()
        return get_parts_with_all(self.db_operator, line)

    def delete_records(self, item: QTableWidgetItem):
        # 获取所有选中的行
        selected_rows = self.tableRecords.selectionModel().selectedRows()

        for row in selected_rows:
            r = row.row()
            selected_id = self.tableRecords.get_item_data(row=r, header_value="ID")

            # 删除图片
            res = self.db_operator.get_detection_records(demand_list=["DetectionPicture", "OriginPicture"], filter_dict={"ID": selected_id})
            if os_path.exists(res["DetectionPicture"]):
                os_remove(res["DetectionPicture"])
            if os_path.exists(res["OriginPicture"]):
                os_remove(res["OriginPicture"])

            # 删除数据库
            self.db_operator.delete_detection_records(filter_dict={"ID": selected_id})

        self.set_page_rows(page_rows=self.page_rows)    # 更新页码
        self.fill_in_table()                            # 填表

    def open_image(self, item: QTableWidgetItem, flag: int):
        row = item.row()
        selected_id = self.tableRecords.get_item_data(row=row, header_value="ID")
        if flag == 0:
            demand_list = ["DetectionPicture"]
        else:
            demand_list = ["OriginPicture"]
        image_path = self.db_operator.get_detection_records(demand_list=demand_list, filter_dict={"ID": selected_id})[demand_list[0]]
        # 检查文件是否存在
        if os_path.exists(image_path):
            # 打开图片
            subprocess_run(['start', image_path], shell=True)
        else:
            message = {"level": 'WARNING', "title": '警告', "text": '需求图片不存在！',
                       "informative_text": '是否删除该条记录？', 'detailed_text': "需求图片地址：[%s]" % image_path}
            res = Messenger.show_message_box(widget=self, message=message, buttons={"YES": QMessageBox.YesRole, "NO": QMessageBox.NoRole})
            if res == 0:
                # 删除数据库
                self.db_operator.delete_detection_records(filter_dict={"ID": selected_id})
                self.set_page_rows(page_rows=self.page_rows)  # 更新页码
                self.fill_in_table()  # 填表
