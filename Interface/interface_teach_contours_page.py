from typing import Optional
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal

from UI.ui_teach_contours_page import Ui_Form as Ui_TeachContoursPage


class InterfaceTeachContoursPage(QWidget, Ui_TeachContoursPage):

    saveSignal = pyqtSignal(dict)
    nextSignal = pyqtSignal(dict)
    backSignal = pyqtSignal()
    refreshSignal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        self.min_area: int = 0
        self.max_area: int = 0
        self.max_roundness: int = 0
        self.max_distance: int = 0

        # 初始化窗口
        self.setupUi(self)

    def showOriginToggled(self, value: bool):
        message = self.generate_message(value)
        self.refreshSignal.emit(message)

    def minAreaChanged(self, value: int):
        self.min_area = value
        self.labelMinAreaValue.setText(str(self.min_area))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def maxAreaChanged(self, value: int):
        self.max_area = value
        self.labelMaxAreaValue.setText(str(self.max_area))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def maxRoundnessChanged(self, value: int):
        self.max_roundness = value
        self.labelMaxRoundnessValue.setText(str(self.max_roundness))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def maxDistanceChanged(self, value: int):
        self.max_distance = value
        self.labelMaxDistanceValue.setText(str(self.max_distance))
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

    def init(self, min_area: int, max_area: int, max_roundness: int, max_distance: int,
             min_area_ref: int, max_area_ref: int, area_max: int, distance_ref: int, distance_max: int):
        """
        初始化页面
        :return:
        """
        self.min_area = min_area
        self.max_area = max_area
        self.max_roundness = max_roundness
        self.max_distance = max_distance

        self.horizontalSliderMinArea.setMaximum(area_max)
        self.horizontalSliderMaxArea.setMaximum(area_max)
        self.labelMinAreaMaxValue.setText(str(area_max))
        self.labelMaxAreaMaxValue.setText(str(area_max))
        self.labelMinAreaRefValue.setText(str(min_area_ref))
        self.labelMaxAreaRefValue.setText(str(max_area_ref))

        self.horizontalSliderMaxDistance.setMaximum(distance_max)
        self.labelMaxDistanceMaxValue.setText(str(distance_max))
        self.labelMaxDistanceRefValue.setText(str(distance_ref))

        self.horizontalSliderMinArea.setValue(self.min_area)
        self.horizontalSliderMaxArea.setValue(self.max_area)
        self.horizontalSliderMaxRoundness.setValue(self.max_roundness)
        self.horizontalSliderMaxDistance.setValue(self.max_distance)

    def generate_message(self, value: Optional[bool] = None) -> dict:
        message = {"MinArea": self.min_area,
                   "MaxArea": self.max_area,
                   "MaxRoundness": self.max_roundness,
                   "MaxDistance": self.max_distance,
                   "ShowOrigin": self.checkBoxShowOrigin.isChecked() if value is None else value
                   }
        return message
