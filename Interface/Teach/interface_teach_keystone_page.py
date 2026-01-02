import numpy as np
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal

from UI.Teach.ui_teach_keystone_page import Ui_Form as Ui_TeachKeystonePage


class InterfaceTeachKeystonePage(QWidget, Ui_TeachKeystonePage):

    nextSignal = pyqtSignal(np.ndarray)
    backSignal = pyqtSignal()
    pointRefreshSignal = pyqtSignal(np.ndarray)
    keystoneOrNotSignal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        self.vertexes = np.zeros((4, 2), np.int32)  # 顶点坐标

        self.setupUi(self)      # 初始化窗口

    def P1XValueChanged(self, val: int):
        self.vertexes[0, 0] = val
        self.pointRefreshSignal.emit(self.vertexes)

    def P1YValueChanged(self, val: int):
        self.vertexes[0, 1] = val
        self.pointRefreshSignal.emit(self.vertexes)

    def P2XValueChanged(self, val: int):
        self.vertexes[1, 0] = val
        self.pointRefreshSignal.emit(self.vertexes)

    def P2YValueChanged(self, val: int):
        self.vertexes[1, 1] = val
        self.pointRefreshSignal.emit(self.vertexes)

    def P3XValueChanged(self, val: int):
        self.vertexes[2, 0] = val
        self.pointRefreshSignal.emit(self.vertexes)

    def P3YValueChanged(self, val: int):
        self.vertexes[2, 1] = val
        self.pointRefreshSignal.emit(self.vertexes)

    def P4XValueChanged(self, val: int):
        self.vertexes[3, 0] = val
        self.pointRefreshSignal.emit(self.vertexes)

    def P4YValueChanged(self, val: int):
        self.vertexes[3, 1] = val
        self.pointRefreshSignal.emit(self.vertexes)

    def keystoneOrNot(self, flag: bool):
        if flag:
            self.buttonKeystone.setText("恢复原图")
        else:
            self.buttonKeystone.setText("梯形校正")

        self.buttonNext.setEnabled(flag)

        message = {"Flag": flag, "Vertexes": self.vertexes}
        self.keystoneOrNotSignal.emit(message)

    def next(self):
        self.nextSignal.emit(self.vertexes)

    def back(self):
        self.backSignal.emit()

    def init(self, vertexes: np.ndarray, frame_size: tuple):
        """
        初始化页面
        :param vertexes:
        :param frame_size:
        :return:
        """
        self.vertexes = vertexes

        self.spinBoxP1X.setRange(0, frame_size[1])
        self.spinBoxP2X.setRange(0, frame_size[1])
        self.spinBoxP3X.setRange(0, frame_size[1])
        self.spinBoxP4X.setRange(0, frame_size[1])

        self.spinBoxP1Y.setRange(0, frame_size[0])
        self.spinBoxP2Y.setRange(0, frame_size[0])
        self.spinBoxP3Y.setRange(0, frame_size[0])
        self.spinBoxP4Y.setRange(0, frame_size[0])

        self.spinBoxP1X.setValue(self.vertexes[0, 0])
        self.spinBoxP1Y.setValue(self.vertexes[0, 1])
        self.spinBoxP2X.setValue(self.vertexes[1, 0])
        self.spinBoxP2Y.setValue(self.vertexes[1, 1])
        self.spinBoxP3X.setValue(self.vertexes[2, 0])
        self.spinBoxP3Y.setValue(self.vertexes[2, 1])
        self.spinBoxP4X.setValue(self.vertexes[3, 0])
        self.spinBoxP4Y.setValue(self.vertexes[3, 1])
