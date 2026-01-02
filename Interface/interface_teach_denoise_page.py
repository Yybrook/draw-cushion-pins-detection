from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal

from UI.ui_teach_denoise_page import Ui_Form as Ui_TeachDenoisePage


class InterfaceTeachDenoisePage(QWidget, Ui_TeachDenoisePage):

    nextSignal = pyqtSignal(dict)
    backSignal = pyqtSignal()
    refreshSignal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        self.eliminated_span: int = 0
        self.reserved_interval: int = 0
        self.erode_shape: int = 0
        self.erode_ksize: int = 0
        self.erode_iterations: int = 0
        self.dilate_shape: int = 0
        self.dilate_ksize: int = 0
        self.dilate_iterations: int = 0

        self.stripe_enable: bool = False
        self.erode_enable: bool = False
        self.dilate_enable: bool = False

        self.setupUi(self)      # 初始化窗口

        self.comboBoxErodeShape.addItems(["MORPH_RECT", "MORPH_CROSS", "MORPH_ELLIPSE"])
        self.comboBoxDilateShape.addItems(["MORPH_RECT", "MORPH_CROSS", "MORPH_ELLIPSE"])

    def next(self):
        message = self.generate_message()
        self.nextSignal.emit(message)

    def back(self):
        self.backSignal.emit()

    def eliminatedSpanChanged(self, value: int):
        self.eliminated_span = value
        self.labelEliminatedSpanValue.setText(str(self.eliminated_span))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def reservedIntervalChanged(self, value: int):
        self.reserved_interval = value
        self.labelReservedIntervalValue.setText(str(self.reserved_interval))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def erodeShapeChanged(self, value: int):
        self.erode_shape = value
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def erodeKsizeChanged(self, value: int):
        self.erode_ksize = value * 2 + 1
        self.labelErodeKsizeValue.setText(str(self.erode_ksize))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def erodeIterationsChanged(self, value: int):
        self.erode_iterations = value
        self.labelErodeIterationsValue.setText(str(self.erode_iterations))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def dilateShapeChanged(self, value: int):
        self.dilate_shape = value
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def dilateKsizeChanged(self, value: int):
        self.dilate_ksize = value * 2 + 1
        self.labelDilateKsizeValue.setText(str(self.dilate_ksize))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def dilateIterationsChanged(self, value: int):
        self.dilate_iterations = value
        self.labelDilateIterationsValue.setText(str(self.dilate_iterations))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def stripeEnableToggled(self, value: bool):
        self.stripe_enable = value
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def erodeEnableToggled(self, value: bool):
        self.erode_enable = value
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def dilateEnableToggled(self, value: bool):
        self.dilate_enable = value
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def init(self, eliminated_span: int, reserved_interval: int,
             erode_shape: int, erode_ksize: int, erode_iterations: int,
             dilate_shape: int, dilate_ksize: int, dilate_iterations: int,
             stripe_enable: bool, erode_enable: bool, dilate_enable: bool,
             pixel_number: int):

        self.eliminated_span = eliminated_span
        self.reserved_interval = reserved_interval
        self.erode_shape = erode_shape
        self.erode_ksize = erode_ksize
        self.erode_iterations = erode_iterations
        self.dilate_shape = dilate_shape
        self.dilate_ksize = dilate_ksize
        self.dilate_iterations = dilate_iterations
        self.stripe_enable = stripe_enable
        self.erode_enable = erode_enable
        self.dilate_enable = dilate_enable

        self.labelEliminatedSpanRefValue.setText(str(pixel_number // 6))

        self.horizontalSliderEliminatedSpan.setMaximum(pixel_number)
        self.horizontalSliderEliminatedSpan.setValue(self.eliminated_span)

        self.horizontalSliderReservedInterval.setMaximum(pixel_number)
        self.horizontalSliderReservedInterval.setValue(self.reserved_interval)

        self.horizontalSliderErodeKsize.setValue(int((self.erode_ksize - 1) / 2))
        self.horizontalSliderErodeIterations.setValue(self.erode_iterations)

        self.horizontalSliderDilateKsize.setValue(int((self.dilate_ksize - 1) / 2))
        self.horizontalSliderDilateIterations.setValue(self.dilate_iterations)

        self.comboBoxErodeShape.setCurrentIndex(self.erode_shape)
        self.comboBoxDilateShape.setCurrentIndex(self.dilate_shape)

        self.checkBoxStripeEnable.setChecked(self.stripe_enable)
        self.checkBoxErodeEnable.setChecked(self.erode_enable)
        self.checkBoxDilateEnable.setChecked(self.dilate_enable)

    def generate_message(self) -> dict:
        message = {"EliminatedSpan": self.eliminated_span,
                   "ReservedInterval": self.reserved_interval,
                   "ErodeShape": self.erode_shape,
                   "ErodeKsize": self.erode_ksize,
                   "ErodeIterations": self.erode_iterations,
                   "DilateShape": self.dilate_shape,
                   "DilateKsize": self.dilate_ksize,
                   "DilateIterations": self.dilate_iterations,
                   "StripeEnable": self.stripe_enable,
                   "ErodeEnable": self.erode_enable,
                   "DilateEnable": self.dilate_enable}
        return message
