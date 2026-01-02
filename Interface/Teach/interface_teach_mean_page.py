from typing import Optional
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal

from UI.Teach.ui_teach_mean_page import Ui_Form as Ui_TeachMeanPage


class InterfaceTeachMeanPage(QWidget, Ui_TeachMeanPage):

    saveSignal = pyqtSignal(dict)
    nextSignal = pyqtSignal(dict)
    backSignal = pyqtSignal()
    refreshSignal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        self.shift: float = 0
        self.mean_threshold: float = 0.01

        # 初始化窗口
        self.setupUi(self)

        self.horizontalSliderShift.set_show_callback(
            show_value_callback=self.labelShiftValue.setText,
            show_minimum_callback=self.labelShiftMinValue.setText,
            show_maximum_callback=self.labelShiftMaxValue.setText
        )
        self.horizontalSliderShift.set_show_format(convert=True, scale=0.01, constant=0, step=1, digits=2)
        self.horizontalSliderShift.valueChanged.connect(self.shiftChanged)

        self.horizontalSliderMean.set_show_callback(
            show_value_callback=self.labelMeanValue.setText,
            show_minimum_callback=self.labelMeanMinValue.setText,
            show_maximum_callback=self.labelMeanMaxValue.setText
        )
        self.horizontalSliderMean.set_show_format(convert=True, scale=0.01, constant=0, step=1, digits=2)
        self.horizontalSliderMean.valueChanged.connect(self.meanThresholdChanged)

    def showOriginToggled(self, value: bool):
        message = self.generate_message(value)
        self.refreshSignal.emit(message)

    def shiftChanged(self, value: int):
        self.shift = self.horizontalSliderShift.convert_2_user_value(slider_value=value)
        self.horizontalSliderShift.show_user_value(user_value=self.shift)
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def meanThresholdChanged(self, value: int):
        self.mean_threshold = self.horizontalSliderMean.convert_2_user_value(slider_value=value)
        self.horizontalSliderMean.show_user_value(user_value=self.mean_threshold)
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def save(self):
        message = self.generate_message()
        self.saveSignal.emit(message)

    def next(self):
        message = self.generate_message()
        self.nextSignal.emit(message)

    def back(self):
        self.backSignal.emit()

    def init(self, shift: float, mean_threshold: float):
        """
        初始化页面
        :return:
        """
        self.shift = shift
        self.mean_threshold = mean_threshold

        self.horizontalSliderShift.set_user_value(user_value=self.shift)
        self.horizontalSliderMean.set_user_value(user_value=self.mean_threshold)

    def generate_message(self, value: Optional[bool] = None) -> dict:
        message = {"SectionShift": self.shift,
                   "SectionMeanThreshold": self.mean_threshold,
                   "ShowOrigin": self.checkBoxShowOrigin.isChecked() if value is None else value
                   }
        return message


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QWidget, QApplication

    app = QApplication(sys.argv)

    interface = InterfaceTeachMeanPage()

    interface.init(shift=0.1, mean_threshold=0.01)

    interface.show()

    sys.exit(app.exec_())
