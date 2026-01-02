import numpy as np

from PyQt5.QtWidgets import QDialog, QHeaderView, QMenu, QAction
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QPoint, pyqtSignal

from UI.Root.Page.Parts.ui_show_part_detail import Ui_Dialog as Ui_PartDetail

from Interface.Teach.interface_teach_pins_map_page import InterfaceTeachPinsMapPage

from Utils.serializer import MySerializer
from User.config_static import (CF_APP_ICON,
                                CF_COLOR_PINSMAP_PIN, CF_COLOR_PINSMAP_NULL, CF_COLOR_PINSMAP_FREE, CF_COLOR_PINSMAP_DOWEL)


class InterfacePartDetail(QDialog, Ui_PartDetail):

    saveSignal = pyqtSignal(dict)

    def __init__(self, details: dict):
        super().__init__()

        self.id = details["ID"]
        self.line = details["Line"]
        self.part = details["Part"]
        self.rows = details["Rows"]
        self.columns = details["Columns"]

        str_pins_map = details["PinsMap"]
        self.pins_map = MySerializer.deserialize(str_pins_map)  # 反序列化

        # 初始化窗口
        self.setupUi(self)

        # 设置窗口图标
        self.setWindowIcon(QIcon(CF_APP_ICON))

        # 表格
        # 显示表头
        self.tablePins.horizontalHeader().setVisible(True)
        self.tablePins.horizontalHeader().setVisible(True)

        # 根据表格大小自适应
        self.tablePins.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tablePins.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # 右键点击事件
        self.tablePins.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tablePins.customContextMenuRequested.connect(self.show_left_click_menu)

    def show_left_click_menu(self, pos: QPoint):
        """
        右键菜单
        :param pos:
        :return:
        """
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

        self.tablePins.clearSelection()  # 取消选中
        rows, columns = self.pins_map.shape[:2]
        # 刷新
        InterfaceTeachPinsMapPage.refresh_pins_map(rows=rows, columns=columns, pins_map=self.pins_map, tabel=self.tablePins)

    def init(self):

        self.lineEditLine.setText(self.line)
        self.lineEditPart.setText(self.part)
        self.lineEditRows.setText(str(self.rows))
        self.lineEditColumns.setText(str(self.columns))

        # 表格 行列数
        self.tablePins.setColumnCount(self.columns)
        self.tablePins.setRowCount(self.rows)

        # 表头
        self.tablePins.setHorizontalHeaderLabels([str(i) for i in range(0, self.columns)])
        self.tablePins.setVerticalHeaderLabels([str(i) for i in range(0, self.rows)])

        # 刷新表格
        InterfaceTeachPinsMapPage.refresh_pins_map(rows=self.rows, columns=self.columns, pins_map=self.pins_map, tabel=self.tablePins)

    def accept(self):
        str_pins_map = MySerializer.serialize(self.pins_map)  # 序列化

        message = {
            "ID": self.id,
            "Line": self.line,
            "Part": self.part,
            "Rows": self.rows,
            "Columns": self.columns,
            "PinsMap": str_pins_map
        }

        self.saveSignal.emit(message)

        return super().accept()

    def show(self):
        self.init()
        return super().show()
