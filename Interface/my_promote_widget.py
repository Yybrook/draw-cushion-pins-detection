from typing import Optional
from PyQt5.QtWidgets import QComboBox, QTableWidget, QHeaderView, QTableWidgetItem, QAbstractItemView, QSlider, QLineEdit, QSpinBox
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtCore import pyqtSignal, Qt


class MyQComboBox(QComboBox):

    showPopupSignal = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, event: QMouseEvent):
        return super().mousePressEvent(event)

    def showPopup(self):
        self.showPopupSignal.emit()
        return super().showPopup()

    def hidePopup(self):
        return super().hidePopup()

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

    def get_current_text(self):
        text = self.currentText().strip()
        if text:
            return text
        placeholder_text = self.placeholderText().strip()
        if placeholder_text:
            return placeholder_text
        else:
            return text


class MyQTableWidget(QTableWidget):

    def __init__(self, *args, **kwargs):

        self.headers = dict()

        super().__init__(*args, **kwargs)

    def init_table(self, table_headers: dict, **kwargs):
        """

        :param table_headers:
        :param kwargs:          header_resize = kwargs.get("header_resize", 1)
                                selection = kwargs.get("selection", 1)
        :return:
        """

        self.headers = table_headers

        # 设置表格列数
        column_count = len(self.headers)
        self.setColumnCount(column_count)

        # 设置表头
        header_list = [*self.headers]
        self.setHorizontalHeaderLabels(header_list)

        # 按第一列升序排列
        self.sortItems(0, Qt.AscendingOrder)

        # 激活鼠标事件
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        # 设置表格列宽
        header_resize = kwargs.get("header_resize", 1)
        if header_resize == 0:
            self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)   # 交互式调整大小
        elif header_resize == 1:
            self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)       # 根据表格大小自适应
        elif header_resize == 2:
            self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)         # 固定大小
        elif header_resize == 3:
            self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        selection = kwargs.get("selection", 1)
        if selection == 1:
            self.setSelectionMode(QAbstractItemView.SingleSelection)    # 单选
        elif selection == 2:
            self.setSelectionMode(QAbstractItemView.MultiSelection)     # 多选
        elif selection == 3:
            self.setSelectionMode(QAbstractItemView.ExtendedSelection)  # 多选

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


class MyQLineEdit(QLineEdit):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_text(self) -> str:
        text = self.text().strip()
        if text:
            return text
        placeholder_text = self.placeholderText().strip()
        if placeholder_text:
            return placeholder_text
        else:
            return text


class MyQSlider(QSlider):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.show_value_callback = None
        self.show_minimum_callback = None
        self.show_maximum_callback = None

        self.convert: bool = False  # 是否需要变换
        self.scale: float = 1       # 放大系数
        self.step: float = 1        # 步距
        self.constant: float = 0    # 常数
        self.digits: int = 0        # 小数位位数

        # self.valueChanged.connect(lambda value: self.value_changed(value=value, signal=None))

    def set_show_callback(self, show_value_callback, show_minimum_callback=None, show_maximum_callback=None):
        self.show_value_callback = show_value_callback
        self.show_minimum_callback = show_minimum_callback
        self.show_maximum_callback = show_maximum_callback

    def set_show_format(self, convert: bool, scale: float, constant: float, step: float, digits: int):
        self.convert = convert  # 是否需要变换
        self.scale = scale  # 放大系数
        self.step = step  # 步距
        self.constant = constant  # 常数
        self.digits = digits  # 小数位位数

        if self.show_minimum_callback is not None:
            if self.convert:
                show_min = self.minimum() * self.step * self.scale + self.constant
            else:
                show_min = self.minimum()
            show_min = self.convert_value_2_show(show_min)
            self.show_minimum_callback(show_min)

        if self.show_maximum_callback is not None:
            if self.convert:
                show_max = self.maximum() * self.step * self.scale + self.constant
            else:
                show_max = self.maximum()
            show_max = self.convert_value_2_show(show_max)
            self.show_maximum_callback(show_max)

    def convert_2_slider_value(self, user_value: float) -> int:
        if self.convert:
            slider_value = round(((user_value - self.constant) / (self.scale * self.step)))
            return slider_value
        else:
            return round(user_value)

    def convert_2_user_value(self, slider_value: int) -> float:
        if self.convert:
            user_value = slider_value * self.step * self.scale + self.constant
            return user_value
        else:
            return slider_value

    def set_user_value(self, user_value: Optional[float]):
        if user_value is None:
            value = self.minimum()
        else:
            value = self.convert_2_slider_value(user_value)
        self.setValue(value)

    def setValue(self, value: int):
        user_value = self.convert_2_user_value(value)
        self.show_user_value(user_value=user_value)
        return super().setValue(value)

    def convert_value_2_show(self, value):
        if self.digits == 0:
            show = "%d" % round(value)
        elif self.digits == 1:
            show = "%.1f" % value
        elif self.digits == 2:
            show = "%.2f" % value
        elif self.digits == 3:
            show = "%.3f" % value
        elif self.digits == 4:
            show = "%.4f" % value
        else:
            show = "%.5f" % value
        return show

    def show_user_value(self, user_value):

        if self.show_value_callback is not None:
            show = self.convert_value_2_show(user_value)
            self.show_value_callback(show)

    def slider_moved(self, value: int, signal: pyqtSignal):
        # 转换为 用户信息
        user_value = self.convert_2_user_value(slider_value=value)
        # 发送信号
        signal.emit(user_value)

    def value_changed(self, value: int, signal: Optional[pyqtSignal]):
        # 转换为 用户信息
        user_value = self.convert_2_user_value(slider_value=value)
        # 显示 用户信息
        self.show_user_value(user_value=user_value)
        # 发送信号
        if signal is not None:
            signal.emit(user_value)


class MyQSpinBox(QSpinBox):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def set_value(self, **kwargs):
        if "value" in kwargs:
            value = kwargs["value"]
        elif "nCurValue" in kwargs:
            value = kwargs["nCurValue"]
        else:
            value = None

        if "minimum" in kwargs:
            minimum = kwargs["minimum"]
        elif "nMin" in kwargs:
            minimum = kwargs["nMin"]
        else:
            minimum = None

        if "maximum" in kwargs:
            maximum = kwargs["maximum"]
        elif "nMax" in kwargs:
            maximum = kwargs["nMax"]
        else:
            maximum = None

        if "step" in kwargs:
            step = kwargs["step"]
        elif "nInc" in kwargs:
            step = kwargs["nInc"]
        else:
            step = None

        if value is not None:
            self.setValue(value)
        if minimum is not None:
            self.setMinimum(minimum)
        if maximum is not None:
            self.setMaximum(maximum)
        if step is not None:
            self.setSingleStep(step)
