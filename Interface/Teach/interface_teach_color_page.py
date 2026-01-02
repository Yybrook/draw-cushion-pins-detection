from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal

from UI.Teach.ui_teach_color_page import Ui_Form as Ui_TeachColorPage

from Interface.my_promote_widget import MyQSlider


def emitParametersChangedSignal(func):
    """
    emit 装饰器
    :param func:
    :return:
    """
    def _decorator(self, *args, **kwargs):
        func(self, *args, **kwargs)

        # 发送信号
        parameters = self.generate_message()

        if parameters != self.parameters:
            self.parameters = parameters
            self.refreshSignal.emit(parameters)

    return _decorator


class InterfaceTeachColorPage(QWidget, Ui_TeachColorPage):

    nextSignal = pyqtSignal(dict)
    backSignal = pyqtSignal()
    refreshSignal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        self.region_direction = 0
        self.region_ratio = 0
        self.super_green_region = 0

        self.filter_d = 9
        self.filter_sigma_color = 75
        self.filter_sigma_space = 75

        # 区域2
        self.h_lower = 49
        self.h_upper = 119

        self.s_lower = 0
        self.s_upper = 255

        self.v_lower = 0
        self.v_upper = 255

        self.open_ksize = 3
        self.open_iterations = 1

        # 区域1
        self.h_lower_2 = 49
        self.h_upper_2 = 119

        self.s_lower_2 = 0
        self.s_upper_2 = 255

        self.v_lower_2 = 0
        self.v_upper_2 = 255

        self.open_ksize_2 = 3
        self.open_iterations_2 = 1

        self.parameters = dict()

        # 初始化窗口
        self.setupUi(self)

        self.label_14.setHidden(True)
        self.label_6.setHidden(True)
        self.label_7.setHidden(True)
        self.label_1.setHidden(True)
        self.labelFilterD.setHidden(True)
        self.labelFilterSigmaColor.setHidden(True)
        self.labelFilterSigmaSpace.setHidden(True)
        self.horizontalSliderFilterD.setHidden(True)
        self.horizontalSliderFilterSigmaColor.setHidden(True)
        self.horizontalSliderFilterSigmaSpace.setHidden(True)

        self.radioButtonWidth.toggled.connect(self.directionChanged)
        self.radioButtonHeight.toggled.connect(self.directionChanged)

        self.horizontalSliderRegionRatio.set_show_format(convert=True, scale=0.01, constant=0, step=1, digits=2)
        self.horizontalSliderRegionRatio.set_show_callback(show_value_callback=self.labelRegionRatio.setText)
        self.horizontalSliderRegionRatio.valueChanged.connect(self.regionRatioChanged)

        # self.radioButtonRegion_1.toggled.connect(self.superGreenRegionChanged)
        # self.radioButtonRegion_2.toggled.connect(self.superGreenRegionChanged)

        # self.horizontalSliderFilterD.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        # self.horizontalSliderFilterD.set_show_callback(show_value_callback=self.labelFilterD.setText)
        # self.horizontalSliderFilterD.valueChanged.connect(self.FilterDChanged)
        #
        # self.horizontalSliderFilterSigmaColor.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        # self.horizontalSliderFilterSigmaColor.set_show_callback(show_value_callback=self.labelFilterSigmaColor.setText)
        # self.horizontalSliderFilterSigmaColor.valueChanged.connect(self.FilterSigmaColorChanged)
        #
        # self.horizontalSliderFilterSigmaSpace.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        # self.horizontalSliderFilterSigmaSpace.set_show_callback(show_value_callback=self.labelFilterSigmaSpace.setText)
        # self.horizontalSliderFilterSigmaSpace.valueChanged.connect(self.FilterSigmaSpaceChanged)

        # 区域2
        self.horizontalSliderHLower.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        self.horizontalSliderHLower.set_show_callback(show_value_callback=self.labelHLower.setText)
        self.horizontalSliderHLower.valueChanged.connect(self.HLowerChanged)

        self.horizontalSliderHUpper.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        self.horizontalSliderHUpper.set_show_callback(show_value_callback=self.labelHUpper.setText)
        self.horizontalSliderHUpper.valueChanged.connect(self.HUpperChanged)

        self.horizontalSliderSLower.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        self.horizontalSliderSLower.set_show_callback(show_value_callback=self.labelSLower.setText)
        self.horizontalSliderSLower.valueChanged.connect(self.SLowerChanged)

        self.horizontalSliderSUpper.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        self.horizontalSliderSUpper.set_show_callback(show_value_callback=self.labelSUpper.setText)
        self.horizontalSliderSUpper.valueChanged.connect(self.SUpperChanged)

        self.horizontalSliderVLower.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        self.horizontalSliderVLower.set_show_callback(show_value_callback=self.labelVLower.setText)
        self.horizontalSliderVLower.valueChanged.connect(self.VLowerChanged)

        self.horizontalSliderVUpper.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        self.horizontalSliderVUpper.set_show_callback(show_value_callback=self.labelVUpper.setText)
        self.horizontalSliderVUpper.valueChanged.connect(self.VUpperChanged)

        self.horizontalSliderOpenKsize.set_show_format(convert=True, scale=1, constant=1, step=2, digits=0)
        self.horizontalSliderOpenKsize.set_show_callback(show_value_callback=self.labelOpenKsize.setText)
        self.horizontalSliderOpenKsize.valueChanged.connect(self.OpenKsizeChanged)

        self.horizontalSliderOpenIterations.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        self.horizontalSliderOpenIterations.set_show_callback(show_value_callback=self.labelOpenIterations.setText)
        self.horizontalSliderOpenIterations.valueChanged.connect(self.OpenIterationsChanged)

        # 区域1
        self.horizontalSliderHLower_2.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        self.horizontalSliderHLower_2.set_show_callback(show_value_callback=self.labelHLower_2.setText)
        self.horizontalSliderHLower_2.valueChanged.connect(self.HLowerChanged_2)

        self.horizontalSliderHUpper_2.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        self.horizontalSliderHUpper_2.set_show_callback(show_value_callback=self.labelHUpper_2.setText)
        self.horizontalSliderHUpper_2.valueChanged.connect(self.HUpperChanged_2)

        self.horizontalSliderSLower_2.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        self.horizontalSliderSLower_2.set_show_callback(show_value_callback=self.labelSLower_2.setText)
        self.horizontalSliderSLower_2.valueChanged.connect(self.SLowerChanged_2)

        self.horizontalSliderSUpper_2.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        self.horizontalSliderSUpper_2.set_show_callback(show_value_callback=self.labelSUpper_2.setText)
        self.horizontalSliderSUpper_2.valueChanged.connect(self.SUpperChanged_2)

        self.horizontalSliderVLower_2.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        self.horizontalSliderVLower_2.set_show_callback(show_value_callback=self.labelVLower_2.setText)
        self.horizontalSliderVLower_2.valueChanged.connect(self.VLowerChanged_2)

        self.horizontalSliderVUpper_2.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        self.horizontalSliderVUpper_2.set_show_callback(show_value_callback=self.labelVUpper_2.setText)
        self.horizontalSliderVUpper_2.valueChanged.connect(self.VUpperChanged_2)

        self.horizontalSliderOpenKsize_2.set_show_format(convert=True, scale=1, constant=1, step=2, digits=0)
        self.horizontalSliderOpenKsize_2.set_show_callback(show_value_callback=self.labelOpenKsize_2.setText)
        self.horizontalSliderOpenKsize_2.valueChanged.connect(self.OpenKsizeChanged_2)

        self.horizontalSliderOpenIterations_2.set_show_format(convert=False, scale=1, constant=0, step=1, digits=0)
        self.horizontalSliderOpenIterations_2.set_show_callback(show_value_callback=self.labelOpenIterations_2.setText)
        self.horizontalSliderOpenIterations_2.valueChanged.connect(self.OpenIterationsChanged_2)

    @emitParametersChangedSignal
    def directionChanged(self, value: bool):
        if self.radioButtonWidth.isChecked():
            self.region_direction = 0
        else:
            self.region_direction = 1

    # @emitParametersChangedSignal
    # def superGreenRegionChanged(self, value: bool):
    #     if self.radioButtonRegion_1.isChecked():
    #         self.super_green_region = 0
    #     else:
    #         self.super_green_region = 1

    @emitParametersChangedSignal
    def regionRatioChanged(self, value: int):
        # 转换为 用户信息
        self.region_ratio = self.horizontalSliderRegionRatio.convert_2_user_value(slider_value=value)
        # 显示 用户信息
        self.horizontalSliderRegionRatio.show_user_value(user_value=self.region_ratio)

    @staticmethod
    def lower_changed(value: int, slider: MyQSlider, upper_value: int):
        # 转换为 用户信息
        lower_value = slider.convert_2_user_value(slider_value=value)
        if lower_value >= upper_value:
            lower_value = upper_value - 1
            slider.set_user_value(lower_value)
        # 显示 用户信息
        slider.show_user_value(user_value=lower_value)
        return lower_value

    @staticmethod
    def upper_changed(value: int, slider: MyQSlider, lower_value: int):
        # 转换为 用户信息
        upper_value = slider.convert_2_user_value(slider_value=value)
        if upper_value <= lower_value:
            upper_value = lower_value + 1
            slider.set_user_value(upper_value)
        # 显示 用户信息
        slider.show_user_value(user_value=upper_value)
        return upper_value

    # 区域2
    @emitParametersChangedSignal
    def HLowerChanged(self, value: int):
        # 转换为 用户信息
        self.h_lower = self.lower_changed(value=value, slider=self.horizontalSliderHLower, upper_value=self.h_upper)

    @emitParametersChangedSignal
    def HUpperChanged(self, value: int):
        # 转换为 用户信息
        self.h_upper = self.upper_changed(value=value, slider=self.horizontalSliderHUpper, lower_value=self.h_lower)

    @emitParametersChangedSignal
    def SLowerChanged(self, value: int):
        # 转换为 用户信息
        self.s_lower = self.lower_changed(value=value, slider=self.horizontalSliderSLower, upper_value=self.s_upper)

    @emitParametersChangedSignal
    def SUpperChanged(self, value: int):
        # 转换为 用户信息
        self.s_upper = self.upper_changed(value=value, slider=self.horizontalSliderSUpper, lower_value=self.s_lower)

    @emitParametersChangedSignal
    def VLowerChanged(self, value: int):
        # 转换为 用户信息
        self.v_lower = self.lower_changed(value=value, slider=self.horizontalSliderVLower, upper_value=self.v_upper)

    @emitParametersChangedSignal
    def VUpperChanged(self, value: int):
        # 转换为 用户信息
        self.v_upper = self.upper_changed(value=value, slider=self.horizontalSliderVUpper, lower_value=self.v_lower)

    @emitParametersChangedSignal
    def OpenKsizeChanged(self, value: int):
        # 转换为 用户信息
        self.open_ksize = self.horizontalSliderOpenKsize.convert_2_user_value(slider_value=value)
        # 显示 用户信息
        self.horizontalSliderOpenKsize.show_user_value(user_value=self.open_ksize)

    @emitParametersChangedSignal
    def OpenIterationsChanged(self, value: int):
        # 转换为 用户信息
        self.open_iterations = self.horizontalSliderOpenIterations.convert_2_user_value(slider_value=value)
        # 显示 用户信息
        self.horizontalSliderOpenIterations.show_user_value(user_value=self.open_iterations)

    # 区域1
    @emitParametersChangedSignal
    def HLowerChanged_2(self, value: int):
        # 转换为 用户信息
        self.h_lower_2 = self.lower_changed(value=value, slider=self.horizontalSliderHLower_2, upper_value=self.h_upper_2)

    @emitParametersChangedSignal
    def HUpperChanged_2(self, value: int):
        # 转换为 用户信息
        self.h_upper_2 = self.upper_changed(value=value, slider=self.horizontalSliderHUpper_2, lower_value=self.h_lower_2)

    @emitParametersChangedSignal
    def SLowerChanged_2(self, value: int):
        # 转换为 用户信息
        self.s_lower_2 = self.lower_changed(value=value, slider=self.horizontalSliderSLower_2, upper_value=self.s_upper_2)

    @emitParametersChangedSignal
    def SUpperChanged_2(self, value: int):
        # 转换为 用户信息
        self.s_upper_2 = self.upper_changed(value=value, slider=self.horizontalSliderSUpper_2, lower_value=self.s_lower_2)

    @emitParametersChangedSignal
    def VLowerChanged_2(self, value: int):
        # 转换为 用户信息
        self.v_lower_2 = self.lower_changed(value=value, slider=self.horizontalSliderVLower_2, upper_value=self.v_upper_2)

    @emitParametersChangedSignal
    def VUpperChanged_2(self, value: int):
        # 转换为 用户信息
        self.v_upper_2 = self.upper_changed(value=value, slider=self.horizontalSliderVUpper_2, lower_value=self.v_lower_2)

    @emitParametersChangedSignal
    def OpenKsizeChanged_2(self, value: int):
        # 转换为 用户信息
        self.open_ksize_2 = self.horizontalSliderOpenKsize_2.convert_2_user_value(slider_value=value)
        # 显示 用户信息
        self.horizontalSliderOpenKsize_2.show_user_value(user_value=self.open_ksize_2)

    @emitParametersChangedSignal
    def OpenIterationsChanged_2(self, value: int):
        # 转换为 用户信息
        self.open_iterations_2 = self.horizontalSliderOpenIterations_2.convert_2_user_value(slider_value=value)
        # 显示 用户信息
        self.horizontalSliderOpenIterations_2.show_user_value(user_value=self.open_iterations_2)

    # @emitParametersChangedSignal
    # def FilterDChanged(self, value: int):
    #     # 转换为 用户信息
    #     self.filter_d = self.horizontalSliderFilterD.convert_2_user_value(slider_value=value)
    #     # 显示 用户信息
    #     self.horizontalSliderFilterD.show_user_value(user_value=self.filter_d)
    #
    # @emitParametersChangedSignal
    # def FilterSigmaColorChanged(self, value: int):
    #     # 转换为 用户信息
    #     self.filter_sigma_color = self.horizontalSliderFilterSigmaColor.convert_2_user_value(slider_value=value)
    #     # 显示 用户信息
    #     self.horizontalSliderFilterSigmaColor.show_user_value(user_value=self.filter_sigma_color)
    #
    # @emitParametersChangedSignal
    # def FilterSigmaSpaceChanged(self, value: int):
    #     # 转换为 用户信息
    #     self.filter_sigma_space = self.horizontalSliderFilterSigmaSpace.convert_2_user_value(slider_value=value)
    #     # 显示 用户信息
    #     self.horizontalSliderFilterSigmaSpace.show_user_value(user_value=self.filter_sigma_space)

    def generate_message(self):
        parameters = {
            "MaskRegionDirection": self.region_direction,
            "MaskRegionRatio": self.region_ratio,
            "SuperGreenMaskRegion": self.super_green_region,

            "BilateralFilterD": self.filter_d,
            "BilateralFilterSigmaColor": self.filter_sigma_color,
            "BilateralFilterSigmaSpace": self.filter_sigma_space,

            "HLower": self.h_lower,
            "HUpper": self.h_upper,

            "SLower": self.s_lower,
            "SUpper": self.s_upper,

            "VLower": self.v_lower,
            "VUpper": self.v_upper,

            "OpenKernelSize": self.open_ksize,
            "OpenIterations": self.open_iterations,

            "HLower_2": self.h_lower_2,
            "HUpper_2": self.h_upper_2,

            "SLower_2": self.s_lower_2,
            "SUpper_2": self.s_upper_2,

            "VLower_2": self.v_lower_2,
            "VUpper_2": self.v_upper_2,

            "OpenKernelSize_2": self.open_ksize_2,
            "OpenIterations_2": self.open_iterations_2,
        }
        return parameters

    def next(self):
        message = self.generate_message()
        self.nextSignal.emit(message)

    def back(self):
        self.backSignal.emit()

    def init(self, region_direction: int, region_ratio: float, super_green_region: int,
             filter_d: int, filter_sigma_color: int, filter_sigma_space: int,
             h_lower: int, h_upper: int, s_lower: int, s_upper: int, v_lower: int, v_upper: int,
             open_ksize: int, open_iterations: int,
             h_lower_2: int, h_upper_2: int, s_lower_2: int, s_upper_2: int, v_lower_2: int, v_upper_2: int,
             open_ksize_2: int, open_iterations_2: int,
             ):
        """
        初始化页面
        :return:
        """

        self.region_direction = region_direction
        self.region_ratio = region_ratio
        self.super_green_region = super_green_region

        self.filter_d = filter_d
        self.filter_sigma_color = filter_sigma_color
        self.filter_sigma_space = filter_sigma_space

        self.h_lower = h_lower
        self.h_upper = h_upper

        self.s_lower = s_lower
        self.s_upper = s_upper

        self.v_lower = v_lower
        self.v_upper = v_upper

        self.open_ksize = open_ksize
        self.open_iterations = open_iterations

        self.h_lower_2 = h_lower_2
        self.h_upper_2 = h_upper_2

        self.s_lower_2 = s_lower_2
        self.s_upper_2 = s_upper_2

        self.v_lower_2 = v_lower_2
        self.v_upper_2 = v_upper_2

        self.open_ksize_2 = open_ksize_2
        self.open_iterations_2 = open_iterations_2

        if self.region_direction == 0:
            self.radioButtonWidth.setChecked(True)
        else:
            self.radioButtonHeight.setChecked(True)

        # if self.super_green_region == 0:
        #     self.radioButtonRegion_1.setChecked(True)
        # else:
        #     self.radioButtonRegion_2.setChecked(True)

        self.horizontalSliderRegionRatio.set_user_value(user_value=self.region_ratio)

        # self.horizontalSliderFilterD.set_user_value(user_value=self.filter_d)
        # self.horizontalSliderFilterSigmaColor.set_user_value(user_value=self.filter_sigma_color)
        # self.horizontalSliderFilterSigmaSpace.set_user_value(user_value=self.filter_sigma_space)

        self.horizontalSliderHLower.set_user_value(user_value=self.h_lower)
        self.horizontalSliderHUpper.set_user_value(user_value=self.h_upper)

        self.horizontalSliderSLower.set_user_value(user_value=self.s_lower)
        self.horizontalSliderSUpper.set_user_value(user_value=self.s_upper)

        self.horizontalSliderVLower.set_user_value(user_value=self.v_lower)
        self.horizontalSliderVUpper.set_user_value(user_value=self.v_upper)

        self.horizontalSliderOpenKsize.set_user_value(user_value=self.open_ksize)
        self.horizontalSliderOpenIterations.set_user_value(user_value=self.open_iterations)

        self.horizontalSliderHLower_2.set_user_value(user_value=self.h_lower_2)
        self.horizontalSliderHUpper_2.set_user_value(user_value=self.h_upper_2)

        self.horizontalSliderSLower_2.set_user_value(user_value=self.s_lower_2)
        self.horizontalSliderSUpper_2.set_user_value(user_value=self.s_upper_2)

        self.horizontalSliderVLower_2.set_user_value(user_value=self.v_lower_2)
        self.horizontalSliderVUpper_2.set_user_value(user_value=self.v_upper_2)

        self.horizontalSliderOpenKsize_2.set_user_value(user_value=self.open_ksize_2)
        self.horizontalSliderOpenIterations_2.set_user_value(user_value=self.open_iterations_2)


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QWidget, QApplication

    app = QApplication(sys.argv)

    interface = InterfaceTeachColorPage()

    interface.init(
        region_direction=0, region_ratio=1.0, super_green_region=1,
        filter_d=9, filter_sigma_color=75, filter_sigma_space=75,
        h_lower=0, h_upper=255, s_lower=0, s_upper=255, v_lower=0, v_upper=255,
        open_ksize=3, open_iterations=1,
        h_lower_2=0, h_upper_2=255, s_lower_2=0, s_upper_2=255, v_lower_2=0, v_upper_2=255,
        open_ksize_2=3, open_iterations_2=1,
    )

    interface.show()

    sys.exit(app.exec_())
