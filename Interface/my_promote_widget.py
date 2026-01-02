from PyQt5.QtWidgets import QComboBox, QTableWidget, QHeaderView, QTableWidgetItem
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtCore import pyqtSignal, Qt


class MyQComboBox(QComboBox):

    showPopupSignal = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, event: QMouseEvent):
        super().mousePressEvent(event)

    def showPopup(self):
        self.showPopupSignal.emit()
        super().showPopup()

    def hidePopup(self):
        super().hidePopup()

    def set_items(self, get_items_callback):
        """
        用于更新items
        :param get_items_callback:
        :return:
        """
        items: list = get_items_callback()  # 获取数据

        text = self.currentText()

        self.clear()
        self.addItems(items)
        if text in items:
            self.setCurrentText(text)


class MyQTableWidget(QTableWidget):

    def __init__(self, *args, **kwargs):

        self.headers = dict()

        super().__init__(*args, **kwargs)

    def init_table(self, table_headers: dict):

        self.headers = table_headers

        # 设置表格列数
        column_count = len(self.headers)
        self.setColumnCount(column_count)

        # 设置表头
        header_list = [*self.headers]
        self.setHorizontalHeaderLabels(header_list)

        # 设置表格列宽
        # 根据表格大小自适应
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)  # 固定大小
        # self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)   # 交互式调整大小

        # 按第一列升序排列
        self.sortItems(0, Qt.AscendingOrder)

        # 激活鼠标事件
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        # # 设置多选
        # self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # # 设置单选
        # self.setSelectionMode(QAbstractItemView.SingleSelection)

    def clear_all(self):
        for row in range(self.rowCount()):
            self.removeRow(0)

    def fill_in(self, contents: list):
        self.clearSelection()  # 取消选择

        self.setSortingEnabled(False)       # 禁止自动排序,防止显示混乱和不全
        self.setRowCount(len(contents))     # 设置表格行数

        for row, content in enumerate(contents):
            for column in range(self.columnCount()):
                header_text = self.horizontalHeaderItem(column).text()   # 获取表头内容
                head_key = self.headers[header_text]
                # self.set_table_item(data=str(content[head_key]), row=row, column=column)     # 设置item
                self.set_table_item(data=content[head_key], row=row, column=column)  # 设置item

        self.setSortingEnabled(True)     # 使能自动排序

    def set_table_item(self, data, row: int, column: int, role: int = Qt.DisplayRole) -> QTableWidgetItem:
        """
        设置表格中的item
        :param data:
        :param row:
        :param column:
        :param role:
        :return:
        """
        item = QTableWidgetItem()               # 创建 TableWidgetItem
        item.setTextAlignment(Qt.AlignCenter)   # 对齐方式 居中
        item.setData(role, data)                # 设置显示数据
        self.setItem(row, column, item)         # 设置图标
        return item

    def get_item_data(self, row: int, header_value: str, role: int = Qt.DisplayRole):
        """
        获取item数据
        :param row:             item所在行
        :param header_value:    self.headers字典中的value
        :param role:
        :return:
        """
        try:
            column = list(self.headers.values()).index(header_value)
            data = self.item(row, column).data(role)
            return data
        except Exception as err:
            return None

    def set_item_data(self, data, row: int, header_value: str, role: int = Qt.DisplayRole):
        """
        设置item数据
        :param data:
        :param row:             item所在行
        :param header_value:    self.headers字典中的value
        :param role:
        :return:
        """
        try:
            column = list(self.headers.values()).index(header_value)
            item = self.item(row, column)
            item.setData(role, data)
            self.setItem(row, column, item)
            return item
        except Exception as err:
            return None
