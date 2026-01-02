import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QColor, QFont, QIcon, QPixmap
from PyQt5.QtCore import Qt, QSize
import random
# import resource


# self.setTextAlignment(Qt.AlignHCenter |  Qt.AlignVCenter)
def x2RGB(x, min_=0, max_=1):  # 浮点数到RGB颜色的一种映射
    r = (x - min_) / (max_ - min_)
    if r >= 0.75:
        return (255, int(255 * (1 - r) * 4), 0)
    elif r >= 0.5:
        return (int(255 * (r - 0.5) * 4), 255, 0)
    elif r >= 0.25:
        return (0, 255, int(255 * (0.5 - r) * 4))
    elif r >= 0:
        return (0, int(255 * r * 4), 255)
    # else:
    # return(255,255,255)# white


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("表格控件示例")
        self.create_table()
        self.create_map()
        self.setup_centralWidget()
        self.statusBar().showMessage("ready")
        # self.setWindowIcon(QIcon(":ICON/ICON/retest.png"))
        self.resize(500, 500)

    def create_table(self):
        self.table = QTableWidget()
        # self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # SelectedClicked #AllEditTriggers
        self.table.setEditTriggers(QAbstractItemView.AllEditTriggers)

        HorizontalHeaderLabels = ["Input",
                                  "Good\nQty.", "Yield", "SpecFail\nQty.", "SpecFail\n%",
                                  "TotalFail\nQty.", "TotalFail\n%", "单元格控件"]  # \n换行
        columns = len(HorizontalHeaderLabels)
        self.table.setRowCount(3)
        self.table.setColumnCount(columns)
        self.table.setHorizontalHeaderLabels(HorizontalHeaderLabels)
        self.table.setVerticalHeaderLabels(["显示文本颜色", "显示图标", "空空如也"])
        headItem = self.table.horizontalHeaderItem(2)
        headItem.setIcon(QIcon(":ICON/ICON/retest.png"))  # 设置headItem的图标
        self.headerWidth = (40, 40, 50, 52, 54, 52, 54, 70)

        # .setSortingEnabled (self, bool enable)

        for i in range(columns - 1):
            self.table.setColumnWidth(i, self.headerWidth[i])
            item = QTableWidgetItem("示例数据%d" % i)
            item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)  # 设置文本的对齐
            # 设置QTableWidgetItem 的前景色（字体颜色）
            item.setForeground(QColor("red"))
            self.table.setItem(0, i, item)
            item1 = QTableWidgetItem()
            item1.setIcon(QIcon(":ICON/ICON/next.png"))  # 设置Item的图标
            self.table.setItem(1, i, item1)

        # setCellWidget (self, int row, int column, QWidget widget)
        self.table.setCellWidget(0, columns - 1, QSpinBox())
        self.table.setCellWidget(1, columns - 1, QCheckBox("知否知否"))
        cb = QComboBox()
        cb.addItems(["绿肥", "红瘦"])
        self.table.setCellWidget(2, columns - 1, cb)

    def create_map(self):
        self.map = QTableWidget()
        rows, cols = 100, 100
        self.map.setRowCount(rows)
        self.map.setColumnCount(cols)
        # self.map.verticalHeader().hide() # 隐藏表头
        # self.map.horizontalHeader().setDisabled(True) #不让用户改列宽
        # 设置表格为自适应的伸缩模式，即可根据窗口的大小来改变网格的大小
        self.map.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.map.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # self.map.verticalHeader().setDisabled(True) #不让用户改行高
        self.map.setEditTriggers(QAbstractItemView.NoEditTriggers)  # 禁止修改内容

        self.map.cellClicked[int, int].connect(self.map_cellClicked)  # 连接单元格点击信号和槽
        for i in range(rows):
            for j in range(cols):
                x = random.random()
                rgb = x2RGB(x)
                item = QTableWidgetItem()
                item.setBackground(QColor(rgb[0], rgb[1], rgb[2]))
                self.map.setItem(i, j, item)

    def map_cellClicked(self, i, j):
        # item = self.map.item(i,j) 或
        item = self.map.currentItem()
        bgColor = item.background().color()
        r, g, b = bgColor.red(), bgColor.green(), bgColor.blue(),
        self.statusBar().showMessage("行:%d, 列:%d  RGB:(%d,%d,%d)"
                                     % (i + 1, j + 1, r, g, b), 1000)  # 状态栏在3000ms内显示信息

    def setup_centralWidget(self):
        # 设置主窗口中心部件
        self.tabWidget = QTabWidget()
        self.tabWidget.addTab(self.table, "Table ")
        self.tabWidget.addTab(self.map, " Map   ")
        self.setCentralWidget(self.tabWidget)  # 指定主窗口中心部件

    def clean(self):
        self.table.clearContents()  # 清除内容
        self.map.clear()  # 清除内容和格式


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())