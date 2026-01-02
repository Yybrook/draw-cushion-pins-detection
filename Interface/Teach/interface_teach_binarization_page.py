from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal

from PyQt5.QtWidgets import QVBoxLayout
from UI.Teach.ui_teach_binarization_page import Ui_Form as Ui_TeachBinarizationPage

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib import pyplot as plt


class InterfaceTeachBinarizationPage(QWidget, Ui_TeachBinarizationPage):

    nextSignal = pyqtSignal(dict)
    backSignal = pyqtSignal()
    refreshSignal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        self.scale_alpha: float = 0.0
        self.scale_beta: int = 0

        self.gamma_c: float = 0.0
        self.gamma_power: float = 0.0

        self.log_c: float = 0.0

        self.thresh: int = 0

        self.scale_enable: bool = True
        self.gamma_enable: bool = False
        self.log_enable: bool = False

        self.auto_thresh: bool = False

        self.show_binarization: bool = True

        self.setupUi(self)      # 初始化窗口

        plt.rcParams['font.family'] = 'Microsoft YaHei'     # 字体
        self.figure = plt.figure(figsize=(5, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout()
        # self.toolbar = NavigationToolbar(self.canvas, self.widget)    # 工具箱
        # layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.widget.setLayout(layout)

    def scaleAlphaChanged(self, value: int):
        self.scale_alpha = value * 0.1
        self.labelScaleAlphaValue.setText("%.1f" % self.scale_alpha)
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def scaleBetaChanged(self, value: int):
        self.scale_beta = value
        self.labelScaleBetaValue.setText(str(self.scale_beta))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def scaleEnable(self, value: bool):
        self.scale_enable = value
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def gammaConstantChanged(self, value: int):
        self.gamma_c = value * 0.1
        self.labelGammaConstantValue.setText("%.1f" % self.gamma_c)
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def gammaPowerChanged(self, value: int):
        self.gamma_power = value * 0.1
        self.labelGammaPowerValue.setText("%.1f" % self.gamma_power)
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def gammaEnable(self, value: bool):
        self.gamma_enable = value
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def logConstantChanged(self, value: int):
        self.log_c = value * 0.1
        self.labelLogConstantValue.setText("%.1f" % self.log_c)
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def logEnable(self, value: bool):
        self.log_enable = value
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def threshChanged(self, value: int):
        self.thresh = value
        self.labelThreshValue.setText(str(self.thresh))
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def showBinarization(self, value: bool):
        self.show_binarization = value
        self.buttonNext.setEnabled(value)
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def next(self):
        message = self.generate_message()
        self.nextSignal.emit(message)

    def back(self):
        self.backSignal.emit()

    def autoThresh(self, value: bool):
        self.auto_thresh = value
        self.horizontalSliderThresh.setEnabled(not value)
        message = self.generate_message()
        self.refreshSignal.emit(message)

    def init(self, scale_alpha: float, scale_beta: int, gamma_c: float, gamma_power: float, log_c: float, thresh: int,
             scale_enable: bool, gamma_enable: bool, log_enable: bool, auto_thresh: bool):
        """
        初始化页面
        :return:
        """
        self.scale_alpha = scale_alpha
        self.scale_beta = scale_beta

        self.gamma_c = gamma_c
        self.gamma_power = gamma_power

        self.log_c = log_c

        self.thresh = thresh

        self.scale_enable = scale_enable
        self.gamma_enable = gamma_enable
        self.log_enable = log_enable
        self.auto_thresh = auto_thresh

        self.show_binarization = self.checkBoxShowBinarization.isChecked()

        self.horizontalSliderScaleAlpha.setValue(int(self.scale_alpha * 10))
        self.horizontalSliderScaleBeta.setValue(self.scale_beta)

        self.horizontalSliderGammaConstant.setValue(int(self.gamma_c * 10))
        self.horizontalSliderGammaPower.setValue(int(self.gamma_power * 10))

        self.horizontalSliderLogConstant.setValue(int(self.log_c * 10))

        self.horizontalSliderThresh.setValue(self.thresh)

        self.checkBoxScaleEnable.setChecked(self.scale_enable)
        self.checkBoxGammaEnable.setChecked(self.gamma_enable)
        self.checkBoxLogEnable.setChecked(self.log_enable)
        self.checkBoxAutoThresh.setChecked(self.auto_thresh)

    def generate_message(self) -> dict:
        message = {"ScaleAlpha": self.scale_alpha,
                   "ScaleBeta": self.scale_beta,
                   "GammaConstant": self.gamma_c,
                   "GammaPower": self.gamma_power,
                   "LogConstant": self.log_c,
                   "Thresh": self.thresh,
                   "ScaleEnable": self.scale_enable,
                   "GammaEnable": self.gamma_enable,
                   "LogEnable": self.log_enable,
                   "AutoThresh": self.auto_thresh,
                   "ShowBinarization": self.show_binarization,
                   }
        return message
