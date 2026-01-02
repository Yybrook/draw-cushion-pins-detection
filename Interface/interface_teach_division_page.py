from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal

from UI.ui_teach_division_page import Ui_Form as Ui_TeachDivisionPage


class InterfaceTeachDivisionPage(QWidget, Ui_TeachDivisionPage):

    nextSignal = pyqtSignal(dict)
    backSignal = pyqtSignal()
    refreshSignal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        self.x_number: int = 0
        self.x_mini: int = 0
        self.x_maxi: int = 0
        self.y_number: int = 0
        self.y_mini: int = 0
        self.y_maxi: int = 0

        # 初始化窗口
        self.setupUi(self)

    def xNumberChanged(self, value: int):
        self.x_number = value
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def xMiniChanged(self, value: int):
        self.x_mini = value
        self.labelXMiniValue.setText(str(self.x_mini))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def xMaxiChanged(self, value: int):
        self.x_maxi = value
        self.labelXMaxiValue.setText(str(self.x_maxi))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def yNumberChanged(self, value: int):
        self.y_number = value
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def yMiniChanged(self, value: int):
        self.y_mini = value
        self.labelYMiniValue.setText(str(self.y_mini))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def yMaxiChanged(self, value: int):
        self.y_maxi = value
        self.labelYMaxiValue.setText(str(self.y_maxi))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def next(self):
        message = self.generate_message()
        self.nextSignal.emit(message)

    def back(self):
        self.backSignal.emit()

    def init(self, x_number: int, x_mini: int, x_maxi: int, y_number: int, y_mini: int, y_maxi: int, x_max: int, y_max: int):
        """
        初始化页面
        :return:
        """
        self.x_number = x_number
        self.x_mini = x_mini
        self.x_maxi = x_maxi
        self.y_number = y_number
        self.y_mini = y_mini
        self.y_maxi = y_maxi

        self.spinBoxXNumber.setValue(self.x_number)
        self.spinBoxYNumber.setValue(self.y_number)

        self.labelXMiniMaxValue.setText(str(x_max))
        self.labelXMaxiMaxValue.setText(str(x_max))
        self.labelYMiniMaxValue.setText(str(y_max))
        self.labelYMaxiMaxValue.setText(str(y_max))

        self.horizontalSliderXMini.setMaximum(x_max)
        self.horizontalSliderXMaxi.setMaximum(x_max)
        self.horizontalSliderYMini.setMaximum(y_max)
        self.horizontalSliderYMaxi.setMaximum(y_max)

        self.horizontalSliderXMini.setValue(self.x_mini)
        self.horizontalSliderXMaxi.setValue(self.x_maxi)
        self.horizontalSliderYMini.setValue(self.y_mini)
        self.horizontalSliderYMaxi.setValue(self.y_maxi)

    def generate_message(self) -> dict:
        message = {"XNumber": self.x_number,
                   "XMini": self.x_mini,
                   "XMaxi": self.x_maxi,
                   "YNumber": self.y_number,
                   "YMini": self.y_mini,
                   "YMaxi": self.y_maxi,
                   }
        return message
