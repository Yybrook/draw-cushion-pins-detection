import numpy as np

from PyQt5.QtWidgets import QWidget, QMenu, QAction, QHeaderView, QTableWidgetItem, QTableWidget
from PyQt5.QtCore import pyqtSignal, Qt, QPoint
from PyQt5.QtGui import QBrush, QColor

from UI.ui_teach_pins_map_page import Ui_Form as Ui_TeachPinsMapPage
from Utils.database_operator import DatabaseOperator
from User.config_static import (CF_COLOR_PINSMAP_PIN, CF_COLOR_PINSMAP_NULL, CF_COLOR_PINSMAP_FREE, CF_COLOR_PINSMAP_DOWEL,
                                CF_PART_NUMBER_IGNORE_SYMBOLS)


class InterfaceTeachPinsMapPage(QWidget, Ui_TeachPinsMapPage):
    saveSignal = pyqtSignal(dict)
    nextSignal = pyqtSignal()
    backSignal = pyqtSignal()
    partChangedSignal = pyqtSignal(str)

    def __init__(self, db_operator: DatabaseOperator):
        super().__init__()

        self.db_operator = db_operator

        self.camera_location: dict = dict()
        self.part: str = ""
        self.x_number: int = 0  # columns
        self.y_number: int = 0  # rows
        self.pins_map = None

        self.setupUi(self)      # 初始化窗口

        # 显示表头
        self.tablePins.horizontalHeader().setVisible(True)
        self.tablePins.horizontalHeader().setVisible(True)

        # 根据表格大小自适应
        self.tablePins.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tablePins.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # 连接信号
        # 下拉框
        self.comboBoxPart.currentTextChanged.connect(self.current_part_changed)
        self.comboBoxPart.showPopupSignal.connect(lambda: self.comboBoxPart.set_items(get_items_callback=self.get_parts))
        # 右键点击事件
        self.tablePins.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tablePins.customContextMenuRequested.connect(self.show_left_click_menu)

    def get_parts(self):
        parts = self.db_operator.get_parts(line=self.camera_location["Line"])
        if self.part != "" and self.part not in parts:
            parts.insert(0, self.part)
        return parts

    def current_part_changed(self, text):
        self.part = text.strip().upper()
        for s in CF_PART_NUMBER_IGNORE_SYMBOLS:
            self.part = self.part.replace(s, "")

        if self.part == "":
            self.buttonSave.setEnabled(False)
        else:
            self.buttonSave.setEnabled(True)

        self.partChangedSignal.emit(self.part)

    def show_left_click_menu(self, pos: QPoint):

        # 获取单元格
        items = self.tablePins.selectedItems()
        if items:
            menu = QMenu()

            set_as_pins_action = QAction('设置为顶棒', menu)
            set_as_null_action = QAction('设置为空', menu)
            set_as_free_action = QAction('可选顶棒或空', menu)
            set_as_dowel_action = QAction('设置为定位销', menu)

            set_as_pins_action.triggered.connect(lambda: self.set_as_something(items=items, flag=0))
            set_as_null_action.triggered.connect(lambda: self.set_as_something(items=items, flag=1))
            set_as_free_action.triggered.connect(lambda: self.set_as_something(items=items, flag=2))
            set_as_dowel_action.triggered.connect(lambda: self.set_as_something(items=items, flag=3))

            menu.addAction(set_as_pins_action)
            menu.addAction(set_as_null_action)
            menu.addAction(set_as_free_action)
            menu.addAction(set_as_dowel_action)

            global_pos = self.tablePins.mapToGlobal(pos)
            menu.exec(global_pos)

    def set_as_something(self, items, flag: int,
                         pin_color: tuple = CF_COLOR_PINSMAP_PIN, null_color: tuple = CF_COLOR_PINSMAP_NULL,
                         free_color: tuple = CF_COLOR_PINSMAP_FREE, dowel_color: tuple = CF_COLOR_PINSMAP_DOWEL):
        if flag == 1:
            color = null_color
        elif flag == 2:
            color = free_color
        elif flag == 3:
            color = dowel_color
        else:
            color = pin_color

        for item in items:
            row = item.row()
            col = item.column()
            self.pins_map[row, col] = np.array(color, np.uint8)

        self.tablePins.clearSelection()     # 取消选中
        self.refresh_pins_map(rows=self.y_number, columns=self.x_number, pins_map=self.pins_map, tabel=self.tablePins)  # 刷新

    def back(self):
        self.backSignal.emit()

    def next(self):
        self.nextSignal.emit()

    def save(self):
        message = {
            "Rows": self.y_number,
            "Columns": self.x_number,
            "PinsMap": self.pins_map
        }
        self.saveSignal.emit(message)

    def init(self, camera_location: dict, part: str, x_number: int, y_number: int, pins_map: np.ndarray):
        self.camera_location = camera_location
        self.part = part
        self.x_number = x_number  # 列
        self.y_number = y_number  # 行
        self.pins_map = pins_map

        if self.part == "":
            self.buttonSave.setEnabled(False)
        else:
            self.buttonSave.setEnabled(True)

        # 初始化 lineEdit
        self.lineEditLine.setText(self.camera_location.get("Line"))
        self.lineEditLocation.setText(self.camera_location.get("Location"))
        self.comboBoxPart.setEditText(self.part)
        self.lineEditRow.setText(str(self.y_number))
        self.lineEditColumn.setText(str(self.x_number))

        # 表格 行列数
        self.tablePins.setColumnCount(self.x_number)
        self.tablePins.setRowCount(self.y_number)

        # 表头
        # self.tablePins.setHorizontalHeaderLabels([str(i) for i in range(0, self.x_number)])
        # self.tablePins.setVerticalHeaderLabels([str(i) for i in range(0, self.y_number)])
        self.tablePins.setHorizontalHeaderLabels([str(i - self.x_number // 2) for i in range(0, self.x_number)])
        self.tablePins.setVerticalHeaderLabels([str(i - self.y_number // 2) for i in range(0, self.y_number)])

        self.refresh_pins_map(rows=self.y_number, columns=self.x_number, pins_map=self.pins_map, tabel=self.tablePins)

    @staticmethod
    def refresh_pins_map(rows: int, columns: int, pins_map: np.ndarray, tabel: QTableWidget):
        for c in range(0, columns):
            for r in range(0, rows):
                item = QTableWidgetItem()               # 创建 TableWidgetItem
                item.setTextAlignment(Qt.AlignCenter)   # 对齐方式 居中
                # 设置颜色
                color = pins_map[r, c]
                q_color = QColor(color[2], color[1], color[0])
                item.setBackground(QBrush(q_color))
                tabel.setItem(r, c, item)               # 设置item
