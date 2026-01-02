# -*- coding: utf-8 -*-#
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *


class MainWnd(QWidget):
    def __init__(self, parent=None):
        super(MainWnd, self).__init__(parent)

        self.move(0, 0)

        icons = sorted(self.getEnumStrings(QStyle, QStyle.StandardPixmap).items())
        layout = QGridLayout(self)

        colNums = 5  # 每行显示的图标数目#
        for i, iconInfo in enumerate(icons[1:]):
            btn = QPushButton(QApplication.style().standardIcon(i), ' {} - {}'.format(*iconInfo))
            btn.setStyleSheet('QPushButton{text-align:left; height:30}')
            layout.addWidget(btn, int(i / colNums), i % colNums)

        self.setWindowTitle('Qt内置图标显示')
        self.setWindowIcon(QApplication.style().standardIcon(0))

    def getEnumStrings(self, cls, enum):
        s = {}
        for key in dir(cls):
            value = getattr(cls, key)
            if isinstance(value, enum):
                s['{:02d}'.format(value)] = key
        return s


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWnd()
    w.show()
    sys.exit(app.exec_())