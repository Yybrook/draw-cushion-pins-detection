from typing import Union
import cv2
import numpy as np
import math
from typing import Optional
# from collections import Counter

from PyQt5.QtWidgets import QMainWindow, QStackedLayout, QLabel, QMenu, QAction, QApplication, QTableWidgetSelectionRange, QStyle
from PyQt5.QtCore import pyqtSignal, Qt, QObject, QEvent, QPoint
from PyQt5.QtGui import QPixmap, QResizeEvent, QIcon

from UI.Teach.ui_teach import Ui_MainWindow as Ui_Teach
from Interface.Teach.interface_teach_info_page import InterfaceTeachInfoPage
from Interface.Teach.interface_teach_keystone_page import InterfaceTeachKeystonePage
from Interface.Teach.interface_teach_color_page import InterfaceTeachColorPage
from Interface.Teach.interface_teach_division_page import InterfaceTeachDivisionPage
from Interface.Teach.interface_teach_binarization_page import InterfaceTeachBinarizationPage
from Interface.Teach.interface_teach_denoise_page import InterfaceTeachDenoisePage
from Interface.Teach.interface_teach_contours_page import InterfaceTeachContoursPage
from Interface.Teach.interface_teach_mean_page import InterfaceTeachMeanPage
from Interface.Teach.interface_teach_pins_map_page import InterfaceTeachPinsMapPage

from CameraCore.camera_identity import CameraIdentity
from FrameCore.frame_operator import FrameOperator
from Utils.image_presenter import Presenter
from Utils.database_operator import DatabaseOperator
from Utils.messenger import Messenger
from Utils.serializer import MySerializer
from User.config_static import (CF_TEACH_INFO_PAGE, CF_TEACH_KEYSTONE_PAGE, CF_TEACH_BINARIZATION_PAGE, CF_TEACH_COLOR_PAGE,
                                CF_TEACH_DENOISE_PAGE, CF_TEACH_DIVISION_PAGE, CF_TEACH_CONTOURS_PAGE, CF_TEACH_PINS_MAP_PAGE,
                                CF_TEACH_REFERENCE_SIDE, CF_RUNNING_SEQUENCE_FILE, CF_RUNNING_GRAB_FLAG, CF_RUNNING_TEACH_FLAG,
                                CF_APP_TITLE, CF_APP_ICON, CF_TEACH_MEAN_PAGE)


class InterfaceTeach(QMainWindow, Ui_Teach):
    # 关闭页面信号
    closeSignal = pyqtSignal()
    # 保存图片信号
    savePictureSignal = pyqtSignal(dict)

    def __init__(self, frame_data: np.ndarray, part: str,
                 serial_number: str, line: str, location: str, side: str,
                 db_operator: DatabaseOperator, activate_page: int = 0):
        super().__init__()

        # self.camera_identity = camera_identity
        # self.camera_location = camera_location

        # 示教图片
        self.frame_data = frame_data

        # 零件号
        self.part = part

        # 相机序列号
        self.serial_number = serial_number
        # 相机位置
        self.line = line
        self.location = location
        self.side = side

        # 激活页
        self.activate_page = activate_page

        # 数据库
        self.db_operator = db_operator
        # 获取处理数据
        self.process_parameters = self.db_operator.get_all_process_parameters(filter_dict={"SerialNumber": self.serial_number})

        # 初始化窗口
        self.setupUi(self)

        # 实例化分页面
        self.info_page = InterfaceTeachInfoPage(db_operator=db_operator)
        self.keystone_page = InterfaceTeachKeystonePage()
        self.color_page = InterfaceTeachColorPage()
        self.division_page = InterfaceTeachDivisionPage()
        # self.binarization_page = InterfaceTeachBinarizationPage()
        # self.denoise_page = InterfaceTeachDenoisePage()
        # self.contours_page = InterfaceTeachContoursPage()
        self.mean_page = InterfaceTeachMeanPage()
        self.pins_map_page = InterfaceTeachPinsMapPage(db_operator=db_operator)

        # 堆叠布局
        self.stackedLayout = QStackedLayout(self.widget)
        # 增加页面
        self.stackedLayout.addWidget(self.info_page)  # 0
        self.stackedLayout.addWidget(self.keystone_page)  # 1
        self.stackedLayout.addWidget(self.color_page)  # 2
        self.stackedLayout.addWidget(self.division_page)  # 3
        # self.stackedLayout.addWidget(self.binarization_page)  # 3
        # self.stackedLayout.addWidget(self.denoise_page)  # 4
        # self.stackedLayout.addWidget(self.contours_page)  # 5
        self.stackedLayout.addWidget(self.mean_page)  # 4
        self.stackedLayout.addWidget(self.pins_map_page)  # 5

        # 绑定信号
        # 切换页面
        self.stackedLayout.currentChanged.connect(lambda index: self.current_page_changed(index=index))

        # label右键点击
        self.labelImage.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelImage.customContextMenuRequested.connect(self.show_left_click_menu)

        self.info_page.nextSignal.connect(self.info_next_button)
        self.info_page.partChangedSignal.connect(self.part_edited)

        self.keystone_page.nextSignal.connect(self.keystone_next_button)
        self.keystone_page.backSignal.connect(self.keystone_back_button)
        self.keystone_page.pointRefreshSignal.connect(self.show_perspective_vertexes)
        self.keystone_page.keystoneOrNotSignal.connect(self.do_keystoneOrNot)

        self.color_page.nextSignal.connect(self.color_next_button)
        self.color_page.backSignal.connect(self.color_back_button)
        self.color_page.refreshSignal.connect(lambda message: self.show_color_image(parameters=message))

        self.division_page.nextSignal.connect(self.division_next_button)
        self.division_page.backSignal.connect(self.division_back_button)
        self.division_page.refreshSignal.connect(lambda message: self.show_division_image(parameters=message))

        # self.binarization_page.nextSignal.connect(self.binarization_next_button)
        # self.binarization_page.backSignal.connect(self.binarization_back_button)
        # self.binarization_page.refreshSignal.connect(lambda message: self.show_binarization_image(parameters=message))
        #
        # self.denoise_page.nextSignal.connect(self.denoise_next_button)
        # self.denoise_page.backSignal.connect(self.denoise_back_button)
        # self.denoise_page.refreshSignal.connect(lambda message: self.show_denoise_image(parameters=message))
        #
        # self.contours_page.saveSignal.connect(self.contours_save_button)
        # self.contours_page.nextSignal.connect(self.contours_next_button)
        # self.contours_page.backSignal.connect(self.contours_back_button)
        # self.contours_page.refreshSignal.connect(lambda message: self.show_contours_image(parameters=message))

        self.mean_page.saveSignal.connect(self.mean_save_button)
        self.mean_page.nextSignal.connect(self.mean_next_button)
        self.mean_page.backSignal.connect(self.mean_back_button)
        self.mean_page.refreshSignal.connect(lambda message: self.show_mean_image(parameters=message))

        self.pins_map_page.saveSignal.connect(self.pins_map_save_button)
        self.pins_map_page.nextSignal.connect(self.pins_map_next_button)
        self.pins_map_page.backSignal.connect(self.pins_map_back_button)
        self.pins_map_page.partChangedSignal.connect(self.part_edited)

        # 给标签加载事件过滤器
        self.labelImage.installEventFilter(self)
        # self.labelImage.removeEventFilter(self)

        # 显示的原始图片
        self.process_pixmap = None
        # 顶棒图片
        self.pins_map = None

        # 梯形矫正中接近点序号
        self.keystone_closed_point = None
        # 已透视变换标志
        self.keystone_perspectived = False

        # 页面显示相关
        # 设置窗口标题
        self.setWindowTitle('%s-Teach' % CF_APP_TITLE)
        # 设置窗口图标
        self.setWindowIcon(QIcon(CF_APP_ICON))

        # 设置title
        # 相机[*] 产线[#] 位置[$] 零件[-]
        title = self.title.text()
        if self.serial_number != "":
            title = title.replace("*", self.serial_number)
        if self.line != "":
            title = title.replace("#", self.line)
        if self.location != "":
            title = title.replace("$", self.location)
        if self.part != "":
            title = title.replace("@", self.part)
        self.title.setText(title)

        if self.activate_page == 0:
            # 初始化数据, 因为页面0没有切换
            self.info_page.init(
                part=self.part,
                serial_number=self.serial_number,
                line=self.line,
                location=self.location,
                side=self.side
            )

    def current_page_changed(self, index: int):
        # info页面
        if index == CF_TEACH_INFO_PAGE:
            # 设置最小尺寸
            self.widget.setMinimumWidth(400)
            # 置位 sidebar label
            self.set_sidebar_styleSheet(self.labelInfo, True)
            # 刷新界面
            QApplication.processEvents()
            # 初始化数据
            self.info_page.init(
                part=self.part,
                serial_number=self.serial_number,
                line=self.line,
                location=self.location,
                side=self.side
            )
            # 显示图片
            self.show_process_frame(self.frame_data)
        # 梯形矫正页面
        elif index == CF_TEACH_KEYSTONE_PAGE:
            # 设置最小尺寸
            self.widget.setMinimumWidth(400)
            # 置位 sidebar label
            self.set_sidebar_styleSheet(self.labelKeystone, True)
            # 刷新界面
            QApplication.processEvents()
            # 初始化数据
            shift = 100
            vertexes = [[self.process_parameters.get("P1X", shift), self.process_parameters.get("P1Y", shift)],
                        [self.process_parameters.get("P2X", self.frame_data.shape[1] - shift), self.process_parameters.get("P2Y", shift)],
                        [self.process_parameters.get("P3X", self.frame_data.shape[1] - shift), self.process_parameters.get("P3Y", self.frame_data.shape[0] - shift)],
                        [self.process_parameters.get("P4X", shift), self.process_parameters.get("P4Y", self.frame_data.shape[0] - shift)]]
            vertexes = np.array(vertexes, np.int32)
            self.keystone_page.init(vertexes=vertexes, frame_size=self.frame_data.shape[:2])
            # 显示图片
            self.show_perspective_vertexes(vertexes)
            # 初始化按钮
            self.keystone_perspectived = False
            self.keystone_page.buttonKeystone.setText("梯形校正")
            self.keystone_page.buttonKeystone.setChecked(False)
            self.keystone_page.buttonNext.setEnabled(False)
        # 颜色提取
        elif index == CF_TEACH_COLOR_PAGE:
            # 设置最小尺寸
            self.widget.setMinimumWidth(800)
            # 置位 sidebar label
            self.set_sidebar_styleSheet(self.labelColor, True)
            # 初始化
            para = {
                "region_direction": self.process_parameters.get("MaskRegionDirection", 0),
                "region_ratio": self.process_parameters.get("MaskRegionRatio", 0.3),
                "super_green_region": self.process_parameters.get("SuperGreenMaskRegion", 1),
                "filter_d": self.process_parameters.get("BilateralFilterD", 9),
                "filter_sigma_color": self.process_parameters.get("BilateralFilterSigmaColor", 75),
                "filter_sigma_space": self.process_parameters.get("BilateralFilterSigmaSpace", 75),

                "h_lower": self.process_parameters.get("HLower", 36),
                "h_upper": self.process_parameters.get("HUpper", 119),
                "s_lower": self.process_parameters.get("SLower", 0),
                "s_upper": self.process_parameters.get("SUpper", 255),
                "v_lower": self.process_parameters.get("VLower", 0),
                "v_upper": self.process_parameters.get("VUpper", 127),
                "open_ksize": self.process_parameters.get("OpenKernelSize", 3),
                "open_iterations": self.process_parameters.get("OpenIterations", 1),

                "h_lower_2": self.process_parameters.get("HLower_2", 36),
                "h_upper_2": self.process_parameters.get("HUpper_2", 119),
                "s_lower_2": self.process_parameters.get("SLower_2", 0),
                "s_upper_2": self.process_parameters.get("SUpper_2", 255),
                "v_lower_2": self.process_parameters.get("VLower_2", 0),
                "v_upper_2": self.process_parameters.get("VUpper_2", 127),
                "open_ksize_2": self.process_parameters.get("OpenKernelSize_2", 3),
                "open_iterations_2": self.process_parameters.get("OpenIterations_2", 1)
            }
            self.color_page.init(**para)
            # 刷新界面
            QApplication.processEvents()
            # 显示图片
            self.show_color_image(**para)

        # 区域划分页面
        elif index == CF_TEACH_DIVISION_PAGE:
            # 设置最小尺寸
            self.widget.setMinimumWidth(800)
            # 置位 sidebar label
            self.set_sidebar_styleSheet(self.labelDivision, True)
            # 初始化
            shift = 88
            x_max = self.process_pixmap.width() - 1
            x_number = self.process_parameters.get("XNumber", 27)
            x_mini = self.process_parameters.get("XMini", shift)
            x_maxi = self.process_parameters.get("XMaxi", x_max - shift)
            y_max = self.process_pixmap.height() - 1
            y_number = self.process_parameters.get("YNumber", 13)
            y_mini = self.process_parameters.get("YMini", shift)
            y_maxi = self.process_parameters.get("YMaxi", y_max - shift)
            self.division_page.init(x_number=x_number, x_mini=x_mini, x_maxi=x_maxi, x_max=x_max,
                                    y_number=y_number, y_mini=y_mini, y_maxi=y_maxi, y_max=y_max)
            # 刷新界面
            QApplication.processEvents()
            # 显示图片
            self.show_division_image(x_number=x_number, x_mini=x_mini, x_maxi=x_maxi,
                                     y_number=y_number, y_mini=y_mini, y_maxi=y_maxi)
        # # 二值化页面
        # elif index == CF_TEACH_BINARIZATION_PAGE:
        #     # 设置最小尺寸
        #     self.widget.setMinimumWidth(800)
        #     # 置位 sidebar label
        #     self.set_sidebar_styleSheet(self.labelBinarization, True)
        #     # 初始化
        #     scale_alpha = self.process_parameters.get("ScaleAlpha", 4.0)
        #     scale_beta = self.process_parameters.get("ScaleBeta", 0)
        #     scale_enable = self.process_parameters.get("ScaleEnable", False)
        #     gamma_c = self.process_parameters.get("GammaConstant", 1.0)
        #     gamma_power = self.process_parameters.get("GammaPower", 1.0)
        #     gamma_enable = self.process_parameters.get("GammaEnable", False)
        #     log_c = self.process_parameters.get("LogConstant", 1.0)
        #     log_enable = self.process_parameters.get("LogEnable", False)
        #     thresh = self.process_parameters.get("Thresh", 80)
        #     auto_thresh = self.process_parameters.get("AutoThresh", True)
        #     self.binarization_page.init(scale_alpha, scale_beta, gamma_c, gamma_power, log_c, thresh,
        #                                 scale_enable, gamma_enable, log_enable, auto_thresh)
        #     # 刷新界面
        #     QApplication.processEvents()
        #     # 显示图片
        #     self.show_binarization_image(scale_alpha=scale_alpha, scale_beta=scale_beta, gamma_c=gamma_c, gamma_power=gamma_power, log_c=log_c, thresh=thresh,
        #                                  scale_enable=scale_enable, gamma_enable=gamma_enable, log_enable=log_enable, auto_thresh=auto_thresh,
        #                                  show_binarization=self.binarization_page.checkBoxShowBinarization.isChecked())
        # # 去噪页面
        # elif index == CF_TEACH_DENOISE_PAGE:
        #     # 设置最小尺寸
        #     self.widget.setMinimumWidth(800)
        #     # 置位 sidebar label
        #     self.set_sidebar_styleSheet(self.labelDenoise, True)
        #     # 初始化
        #     pixel_number = self.process_pixmap.width()
        #     eliminated_span = self.process_parameters.get("EliminatedSpan", 150)
        #     reserved_interval = self.process_parameters.get("ReservedInterval", 1)
        #     erode_shape = self.process_parameters.get("ErodeShape", 0)
        #     erode_ksize = self.process_parameters.get("ErodeKsize", 3)
        #     erode_iterations = self.process_parameters.get("ErodeIterations", 1)
        #     dilate_shape = self.process_parameters.get("DilateShape", 2)
        #     dilate_ksize = self.process_parameters.get("DilateKsize", 3)
        #     dilate_iterations = self.process_parameters.get("DilateIterations", 1)
        #     stripe_enable = self.process_parameters.get("StripeEnable", False)
        #     erode_enable = self.process_parameters.get("ErodeEnable", True)
        #     dilate_enable = self.process_parameters.get("DilateEnable", True)
        #     self.denoise_page.init(eliminated_span=eliminated_span, reserved_interval=reserved_interval,
        #                            erode_shape=erode_shape, erode_ksize=erode_ksize, erode_iterations=erode_iterations,
        #                            dilate_shape=dilate_shape, dilate_ksize=dilate_ksize, dilate_iterations=dilate_iterations,
        #                            stripe_enable=stripe_enable, erode_enable=erode_enable, dilate_enable=dilate_enable,
        #                            pixel_number=pixel_number)
        #     # 刷新界面
        #     QApplication.processEvents()
        #     # 显示图片
        #     self.show_denoise_image(eliminated_span=eliminated_span, reserved_interval=reserved_interval,
        #                             erode_shape=erode_shape, erode_ksize=erode_ksize, erode_iterations=erode_iterations,
        #                             dilate_shape=dilate_shape, dilate_ksize=dilate_ksize, dilate_iterations=dilate_iterations,
        #                             stripe_enable=stripe_enable, erode_enable=erode_enable, dilate_enable=dilate_enable)
        # # 寻找轮廓页面
        # elif index == CF_TEACH_CONTOURS_PAGE:
        #     # 设置最小尺寸
        #     self.widget.setMinimumWidth(800)
        #     # 置位 sidebar label
        #     self.set_sidebar_styleSheet(self.labelContours, True)
        #     # 初始化
        #     min_area = self.process_parameters.get("MinArea", 50)
        #     max_area = self.process_parameters.get("MaxArea", 1500)
        #     max_roundness = self.process_parameters.get("MaxRoundness", 10)
        #     max_distance = self.process_parameters.get("MaxDistance", 10)
        #
        #     x_number = self.process_parameters["XNumber"]
        #     x_mini = self.process_parameters["XMini"]
        #     x_maxi = self.process_parameters["XMaxi"]
        #     y_number = self.process_parameters["YNumber"]
        #     y_mini = self.process_parameters["YMini"]
        #     y_maxi = self.process_parameters["YMaxi"]
        #     min_area_ref, max_area_ref, area_max, distance_ref, distance_max = FrameOperator.calculate_ref_value(x_number=x_number, x_mini=x_mini, x_maxi=x_maxi,
        #                                                                                                          y_number=y_number, y_mini=y_mini, y_maxi=y_maxi)
        #
        #     self.contours_page.init(min_area=min_area, max_area=max_area, max_roundness=max_roundness, max_distance=max_distance,
        #                             min_area_ref=min_area_ref, max_area_ref=max_area_ref, area_max=area_max,
        #                             distance_ref=distance_ref, distance_max=distance_max)
        #     # 刷新界面
        #     QApplication.processEvents()
        #     # 显示图片
        #     self.show_contours_image(min_area=min_area, max_area=max_area, max_roundness=max_roundness, max_distance=max_distance,
        #                              show_origin=self.contours_page.checkBoxShowOrigin.isChecked())

        # mean页面
        elif index == CF_TEACH_MEAN_PAGE:
            # 设置最小尺寸
            self.widget.setMinimumWidth(800)
            # 置位 sidebar label
            self.set_sidebar_styleSheet(self.labelContours, True)
            # 初始化
            shift = self.process_parameters.get("SectionShift", 0.1)
            mean_threshold = self.process_parameters.get("SectionMeanThreshold", 0.01)

            self.mean_page.init(shift=shift, mean_threshold=mean_threshold)
            # 刷新界面
            QApplication.processEvents()
            # 显示图片
            self.show_mean_image(
                shift=shift, mean_threshold=mean_threshold,
                show_origin=self.mean_page.checkBoxShowOrigin.isChecked()
            )
        # 零件示教页面
        elif index == CF_TEACH_PINS_MAP_PAGE:
            # 设置最小尺寸
            self.widget.setMinimumWidth(1600)
            # 置位 sidebar label
            self.set_sidebar_styleSheet(self.labelPart, True)
            # 刷新界面
            QApplication.processEvents()
            # 初始化
            x_number = self.process_parameters["XNumber"]
            y_number = self.process_parameters["YNumber"]
            # 显示图片  计算pins_map
            self.show_pins_map_image()
            self.pins_map_page.init(
                line=self.line, location=self.location,
                part=self.part,
                x_number=x_number, y_number=y_number,
                pins_map=self.pins_map
            )

    def info_next_button(self, message: dict):
        part = message["Part"]
        # 替换零件号
        if part != self.part:
            self.part = part
            title = self.title.text()
            right_bracket = title.rfind("[")
            new_title = title[:right_bracket] + '[%s]' % self.part
            self.title.setText(new_title)
        # 复位 sidebar label
        self.set_sidebar_styleSheet(self.labelInfo, False)
        # 切换页面
        self.stackedLayout.setCurrentIndex(CF_TEACH_INFO_PAGE + 1)

    def keystone_next_button(self, vertexes: np.ndarray):
        # 获取vertexes
        self.process_parameters["P1X"] = int(vertexes[0, 0])
        self.process_parameters["P1Y"] = int(vertexes[0, 1])
        self.process_parameters["P2X"] = int(vertexes[1, 0])
        self.process_parameters["P2Y"] = int(vertexes[1, 1])
        self.process_parameters["P3X"] = int(vertexes[2, 0])
        self.process_parameters["P3Y"] = int(vertexes[2, 1])
        self.process_parameters["P4X"] = int(vertexes[3, 0])
        self.process_parameters["P4Y"] = int(vertexes[3, 1])
        self.set_sidebar_styleSheet(self.labelKeystone, False)  # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_KEYSTONE_PAGE + 1)  # 切换页面

    def keystone_back_button(self):
        self.set_sidebar_styleSheet(self.labelKeystone, False)  # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_KEYSTONE_PAGE - 1)  # 切换页面

    def do_keystoneOrNot(self, message: dict):
        flag = message["Flag"]
        vertexes = message["Vertexes"]
        self.keystone_perspectived = flag
        if flag:
            self.show_perspectived_image(vertexes)
        else:
            self.show_perspective_vertexes(vertexes)

    def show_perspective_vertexes(self, vertexes: Union[np.ndarray, list]):
        """
        显示梯形校正顶点图片
        :param vertexes:
        :return:
        """
        # 处理图片
        frame_data = FrameOperator.draw_vertexes(self.frame_data, vertexes)
        self.show_process_frame(frame=frame_data)

    def show_perspectived_image(self, vertexes: Union[np.ndarray, list]):
        """
        显示梯形校正后的图片
        :param vertexes:
        :return:
        """
        # 处理图片
        frame_data = FrameOperator.perspective_transform(self.frame_data, vertexes)
        self.show_process_frame(frame=frame_data)

    def color_next_button(self, message: dict):
        self.process_parameters.update(message)
        self.set_sidebar_styleSheet(self.labelColor, False)  # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_COLOR_PAGE + 1)  # 切换页面

    def color_back_button(self):
        self.set_sidebar_styleSheet(self.labelColor, False)  # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_COLOR_PAGE - 1)  # 切换页面

    def show_color_image(self, **kwargs):
        """
        显示去噪图片
        :param kwargs:
        :return:
        """
        vertexes = [[self.process_parameters["P1X"], self.process_parameters["P1Y"]],
                    [self.process_parameters["P2X"], self.process_parameters["P2Y"]],
                    [self.process_parameters["P3X"], self.process_parameters["P3Y"]],
                    [self.process_parameters["P4X"], self.process_parameters["P4Y"]]]

        if "parameters" in kwargs:
            parameters = kwargs["parameters"]
            region_direction = parameters.get("MaskRegionDirection")
            region_ratio = parameters.get("MaskRegionRatio")
            super_green_region = parameters.get("SuperGreenMaskRegion")

            filter_d = parameters.get("BilateralFilterD")
            filter_sigma_color = parameters.get("BilateralFilterSigmaColor")
            filter_sigma_space = parameters.get("BilateralFilterSigmaSpace")

            h_lower_1 = parameters.get("HLower")
            h_upper_1 = parameters.get("HUpper")
            s_lower_1 = parameters.get("SLower")
            s_upper_1 = parameters.get("SUpper")
            v_lower_1 = parameters.get("VLower")
            v_upper_1 = parameters.get("VUpper")

            open_ksize_1 = parameters.get("OpenKernelSize")
            open_iterations_1 = parameters.get("OpenIterations")

            h_lower_2 = parameters.get("HLower_2")
            h_upper_2 = parameters.get("HUpper_2")
            s_lower_2 = parameters.get("SLower_2")
            s_upper_2 = parameters.get("SUpper_2")
            v_lower_2 = parameters.get("VLower_2")
            v_upper_2 = parameters.get("VUpper_2")

            open_ksize_2 = parameters.get("OpenKernelSize_2")
            open_iterations_2 = parameters.get("OpenIterations_2")
        else:
            region_direction = kwargs.get("region_direction")
            region_ratio = kwargs.get("region_ratio")
            super_green_region = kwargs.get("super_green_region")

            filter_d = kwargs.get("filter_d")
            filter_sigma_color = kwargs.get("filter_sigma_color")
            filter_sigma_space = kwargs.get("filter_sigma_space")

            h_lower_1 = kwargs.get("h_lower")
            h_upper_1 = kwargs.get("h_upper")
            s_lower_1 = kwargs.get("s_lower")
            s_upper_1 = kwargs.get("s_upper")
            v_lower_1 = kwargs.get("v_lower")
            v_upper_1 = kwargs.get("v_upper")

            open_ksize_1 = kwargs.get("open_ksize")
            open_iterations_1 = kwargs.get("open_iterations")

            h_lower_2 = kwargs.get("h_lower_2")
            h_upper_2 = kwargs.get("h_upper_2")
            s_lower_2 = kwargs.get("s_lower_2")
            s_upper_2 = kwargs.get("s_upper_2")
            v_lower_2 = kwargs.get("v_lower_2")
            v_upper_2 = kwargs.get("v_upper_2")

            open_ksize_2 = kwargs.get("open_ksize_2")
            open_iterations_2 = kwargs.get("open_iterations_2")

        # 处理图片
        frame_data = FrameOperator.perspective_transform(self.frame_data, vertexes)
        green_mask = FrameOperator.get_color_mask_for_green(
            frame=frame_data,
            region_direction=region_direction, region_ratio=region_ratio, super_green_region=super_green_region,
            hsv_lower_2=[h_lower_1, s_lower_1, v_lower_1], hsv_upper_2=[h_upper_1, s_upper_1, v_upper_1],
            ksize_2=open_ksize_1, iterations_2=open_iterations_1,
            hsv_lower_1=[h_lower_2, s_lower_2, v_lower_2], hsv_upper_1=[h_upper_2, s_upper_2, v_upper_2],
            ksize_1=open_ksize_2, iterations_1=open_iterations_2,
        )
        frame_data = FrameOperator.draw_color_extract(
            frame=frame_data, extract_mask=green_mask,
            region_direction=region_direction, region_ratio=region_ratio,
            draw_region_line=True, thickness=4
        )
        self.show_process_frame(frame=frame_data)

    def division_next_button(self, message: dict):
        self.process_parameters.update(message)
        self.set_sidebar_styleSheet(self.labelDivision, False)  # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_DIVISION_PAGE + 1)  # 切换页面

    def division_back_button(self):
        self.set_sidebar_styleSheet(self.labelDivision, False)  # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_DIVISION_PAGE - 1)  # 切换页面

    def show_division_image(self, **kwargs):
        """
        显示去噪图片
        :param kwargs:
        :return:
        """
        vertexes = [[self.process_parameters["P1X"], self.process_parameters["P1Y"]],
                    [self.process_parameters["P2X"], self.process_parameters["P2Y"]],
                    [self.process_parameters["P3X"], self.process_parameters["P3Y"]],
                    [self.process_parameters["P4X"], self.process_parameters["P4Y"]]]

        if "parameters" in kwargs:
            parameters = kwargs["parameters"]
            x_number = parameters.get("XNumber")
            x_mini = parameters.get("XMini")
            x_maxi = parameters.get("XMaxi")
            y_number = parameters.get("YNumber")
            y_mini = parameters.get("YMini")
            y_maxi = parameters.get("YMaxi")
        else:
            x_number = kwargs.get("x_number")
            x_mini = kwargs.get("x_mini")
            x_maxi = kwargs.get("x_maxi")
            y_number = kwargs.get("y_number")
            y_mini = kwargs.get("y_mini")
            y_maxi = kwargs.get("y_maxi")

        # 处理图片
        frame_data = FrameOperator.perspective_transform(self.frame_data, vertexes)
        frame_data = FrameOperator.draw_division(frame_data, x_number, x_mini, x_maxi, y_number, y_mini, y_maxi)
        self.show_process_frame(frame=frame_data)

    # def binarization_next_button(self, message: dict):
    #     message.pop("ShowBinarization")
    #     self.process_parameters.update(message)
    #     self.set_sidebar_styleSheet(self.labelBinarization, False)  # 复位 sidebar label
    #     self.stackedLayout.setCurrentIndex(CF_TEACH_BINARIZATION_PAGE + 1)  # 切换页面
    #
    # def binarization_back_button(self):
    #     self.set_sidebar_styleSheet(self.labelBinarization, False)      # 复位 sidebar label
    #     self.stackedLayout.setCurrentIndex(CF_TEACH_BINARIZATION_PAGE - 1)      # 切换页面
    #
    # def show_binarization_image(self, **kwargs):
    #     """
    #     显示二值化图片
    #     :param kwargs:
    #     :return:
    #     """
    #     vertexes = [[self.process_parameters["P1X"], self.process_parameters["P1Y"]],
    #                 [self.process_parameters["P2X"], self.process_parameters["P2Y"]],
    #                 [self.process_parameters["P3X"], self.process_parameters["P3Y"]],
    #                 [self.process_parameters["P4X"], self.process_parameters["P4Y"]]]
    #
    #     if "parameters" in kwargs:
    #         parameters = kwargs["parameters"]
    #         scale_alpha = parameters.get("ScaleAlpha")
    #         scale_beta = parameters.get("ScaleBeta")
    #         gamma_c = parameters.get("GammaConstant")
    #         gamma_power = parameters.get("GammaPower")
    #         log_c = parameters.get("LogConstant")
    #         thresh = parameters.get("Thresh")
    #         scale_enable = parameters.get("ScaleEnable")
    #         gamma_enable = parameters.get("GammaEnable")
    #         log_enable = parameters.get("LogEnable")
    #         auto_thresh = parameters.get("AutoThresh")
    #         show_binarization = parameters.get("ShowBinarization")
    #     else:
    #         scale_alpha = kwargs.get("scale_alpha")
    #         scale_beta = kwargs.get("scale_beta")
    #         gamma_c = kwargs.get("gamma_c")
    #         gamma_power = kwargs.get("gamma_power")
    #         log_c = kwargs.get("log_c")
    #         thresh = kwargs.get("thresh")
    #         scale_enable = kwargs.get("scale_enable")
    #         gamma_enable = kwargs.get("gamma_enable")
    #         log_enable = kwargs.get("log_enable")
    #         auto_thresh = kwargs.get("auto_thresh")
    #         show_binarization = kwargs.get("show_binarization")
    #
    #     # 处理图片
    #     frame_data = FrameOperator.perspective_transform(self.frame_data, vertexes)
    #     binarization, gray = FrameOperator.binarization_transform(frame_data, scale_alpha, scale_beta, gamma_c, gamma_power, log_c, thresh,
    #                                                               scale_enable, gamma_enable, log_enable, auto_thresh)
    #
    #     # 计算直方图
    #     x, hist = FrameOperator.calculate_hist(gray)
    #     # 平滑曲线
    #     smooth_x, smooth_hist = FrameOperator.smooth_hist(x=x, hist=hist)
    #     # 找波谷
    #     valleys_x, valleys_hist, _, _ = FrameOperator.find_valleys_and_peaks(x=smooth_x, hist=smooth_hist, whitelist=['valley'])
    #     # 找参考值
    #     ref_thresh = FrameOperator.calculate_reference_thresh(valleys_x, _, _, _)
    #     # 显示参考值
    #     if ref_thresh is not None:
    #         self.binarization_page.labelRefThreshValue.setText(str(ref_thresh))
    #     else:
    #         self.binarization_page.labelRefThreshValue.setText("NA")
    #
    #     if auto_thresh and ref_thresh is not None:
    #         self.binarization_page.labelThreshValue.setText(str(ref_thresh))
    #     else:
    #         self.binarization_page.labelThreshValue.setText(str(thresh))
    #
    #     # 画直方图
    #     FrameOperator.draw_hist(canvas=self.binarization_page.canvas, x=x, hist=hist,
    #                             smooth_x=smooth_x, smooth_hist=smooth_hist, valleys_x=valleys_x, valleys_hist=valleys_hist)
    #
    #     if show_binarization:
    #         self.show_process_frame(frame=binarization)
    #     else:
    #         self.show_process_frame(frame=gray)
    #
    # def denoise_next_button(self, message: dict):
    #     self.process_parameters.update(message)
    #     self.set_sidebar_styleSheet(self.labelDenoise, False)   # 复位 sidebar label
    #     self.stackedLayout.setCurrentIndex(CF_TEACH_DENOISE_PAGE + 1)   # 切换页面
    #
    # def denoise_back_button(self):
    #     self.set_sidebar_styleSheet(self.labelDenoise, False)   # 复位 sidebar label
    #     self.stackedLayout.setCurrentIndex(CF_TEACH_DENOISE_PAGE - 1)   # 切换页面
    #
    # def show_denoise_image(self, **kwargs):
    #     """
    #     显示去噪图片
    #     :param kwargs:
    #     :return:
    #     """
    #     vertexes = [[self.process_parameters["P1X"], self.process_parameters["P1Y"]],
    #                 [self.process_parameters["P2X"], self.process_parameters["P2Y"]],
    #                 [self.process_parameters["P3X"], self.process_parameters["P3Y"]],
    #                 [self.process_parameters["P4X"], self.process_parameters["P4Y"]]]
    #     scale_alpha = self.process_parameters["ScaleAlpha"]
    #     scale_beta = self.process_parameters["ScaleBeta"]
    #     scale_enable = self.process_parameters["ScaleEnable"]
    #     gamma_c = self.process_parameters["GammaConstant"]
    #     gamma_power = self.process_parameters["GammaPower"]
    #     gamma_enable = self.process_parameters["GammaEnable"]
    #     log_c = self.process_parameters["LogConstant"]
    #     log_enable = self.process_parameters["LogEnable"]
    #     thresh = self.process_parameters["Thresh"]
    #     auto_thresh = self.process_parameters["AutoThresh"]
    #
    #     if "parameters" in kwargs:
    #         parameters = kwargs["parameters"]
    #         eliminated_span = parameters.get("EliminatedSpan")
    #         reserved_interval = parameters.get("ReservedInterval")
    #         erode_shape = parameters.get("ErodeShape")
    #         erode_ksize = parameters.get("ErodeKsize")
    #         erode_iterations = parameters.get("ErodeIterations")
    #         dilate_shape = parameters.get("DilateShape")
    #         dilate_ksize = parameters.get("DilateKsize")
    #         dilate_iterations = parameters.get("DilateIterations")
    #         stripe_enable = parameters.get("StripeEnable")
    #         erode_enable = parameters.get("ErodeEnable")
    #         dilate_enable = parameters.get("DilateEnable")
    #     else:
    #         eliminated_span = kwargs.get("eliminated_span")
    #         reserved_interval = kwargs.get("reserved_interval")
    #         erode_shape = kwargs.get("erode_shape")
    #         erode_ksize = kwargs.get("erode_ksize")
    #         erode_iterations = kwargs.get("erode_iterations")
    #         dilate_shape = kwargs.get("dilate_shape")
    #         dilate_ksize = kwargs.get("dilate_ksize")
    #         dilate_iterations = kwargs.get("dilate_iterations")
    #         stripe_enable = kwargs.get("stripe_enable")
    #         erode_enable = kwargs.get("erode_enable")
    #         dilate_enable = kwargs.get("dilate_enable")
    #
    #     # 处理图片
    #     frame_data = FrameOperator.perspective_transform(self.frame_data, vertexes)
    #     frame_data, _ = FrameOperator.binarization_transform(frame_data, scale_alpha, scale_beta, gamma_c, gamma_power, log_c, thresh,
    #                                                          scale_enable, gamma_enable, log_enable, auto_thresh)
    #     frame_data = FrameOperator.denoise_transform(frame_data, eliminated_span, reserved_interval,
    #                                                  erode_shape, erode_ksize, erode_iterations,
    #                                                  dilate_shape, dilate_ksize, dilate_iterations,
    #                                                  stripe_enable, erode_enable, dilate_enable)
    #     self.show_process_frame(frame=frame_data)
    #
    # def contours_save_button(self, message: dict):
    #     message.pop("ShowOrigin")
    #     self.process_parameters.update(message)
    #     # 保存到数据库
    #     self.db_operator.set_process_parameters(filter_dict={"SerialNumber": self.camera_identity.serial_number}, demand_dict=self.process_parameters)
    #     Messenger.show_QMessageBox(widget=self, level='INFO', title="信息", text="算法参数保存成功",
    #                                informative_text="", detailed_text="", QLabelMinWidth=200)
    #
    # def contours_next_button(self, message: dict):
    #     message.pop("ShowOrigin")
    #     self.process_parameters.update(message)
    #     self.set_sidebar_styleSheet(self.labelContours, False)  # 复位 sidebar label
    #     self.stackedLayout.setCurrentIndex(CF_TEACH_CONTOURS_PAGE + 1)  # 切换页面
    #
    # def contours_back_button(self):
    #     self.set_sidebar_styleSheet(self.labelContours, False)  # 复位 sidebar label
    #     self.stackedLayout.setCurrentIndex(CF_TEACH_CONTOURS_PAGE - 1)  # 切换页面
    #
    # def show_contours_image(self, **kwargs):
    #     vertexes = [[self.process_parameters["P1X"], self.process_parameters["P1Y"]],
    #                 [self.process_parameters["P2X"], self.process_parameters["P2Y"]],
    #                 [self.process_parameters["P3X"], self.process_parameters["P3Y"]],
    #                 [self.process_parameters["P4X"], self.process_parameters["P4Y"]]]
    #     scale_alpha = self.process_parameters["ScaleAlpha"]
    #     scale_beta = self.process_parameters["ScaleBeta"]
    #     scale_enable = self.process_parameters["ScaleEnable"]
    #     gamma_c = self.process_parameters["GammaConstant"]
    #     gamma_power = self.process_parameters["GammaPower"]
    #     gamma_enable = self.process_parameters["GammaEnable"]
    #     log_c = self.process_parameters["LogConstant"]
    #     log_enable = self.process_parameters["LogEnable"]
    #     thresh = self.process_parameters["Thresh"]
    #     auto_thresh = self.process_parameters["AutoThresh"]
    #     eliminated_span = self.process_parameters["EliminatedSpan"]
    #     reserved_interval = self.process_parameters["ReservedInterval"]
    #     erode_shape = self.process_parameters["ErodeShape"]
    #     erode_ksize = self.process_parameters["ErodeKsize"]
    #     erode_iterations = self.process_parameters["ErodeIterations"]
    #     dilate_shape = self.process_parameters["DilateShape"]
    #     dilate_ksize = self.process_parameters["DilateKsize"]
    #     dilate_iterations = self.process_parameters["DilateIterations"]
    #     stripe_enable = self.process_parameters["StripeEnable"]
    #     erode_enable = self.process_parameters["ErodeEnable"]
    #     dilate_enable = self.process_parameters["DilateEnable"]
    #     x_number = self.process_parameters["XNumber"]
    #     x_mini = self.process_parameters["XMini"]
    #     x_maxi = self.process_parameters["XMaxi"]
    #     y_number = self.process_parameters["YNumber"]
    #     y_mini = self.process_parameters["YMini"]
    #     y_maxi = self.process_parameters["YMaxi"]
    #
    #     if "parameters" in kwargs:
    #         parameters = kwargs["parameters"]
    #         min_area = parameters.get("MinArea")
    #         max_area = parameters.get("MaxArea")
    #         max_roundness = parameters.get("MaxRoundness")
    #         max_distance = parameters.get("MaxDistance")
    #         show_origin = parameters.get("ShowOrigin")
    #     else:
    #         min_area = kwargs.get("min_area")
    #         max_area = kwargs.get("max_area")
    #         max_roundness = kwargs.get("max_roundness")
    #         max_distance = kwargs.get("max_distance")
    #         show_origin = kwargs.get("show_origin")
    #
    #     # 处理图片
    #     origin_frame_data = FrameOperator.perspective_transform(self.frame_data, vertexes)  # 原始图片
    #     frame_data, _ = FrameOperator.binarization_transform(origin_frame_data, scale_alpha, scale_beta, gamma_c, gamma_power, log_c, thresh,
    #                                                          scale_enable, gamma_enable, log_enable, auto_thresh)
    #     frame_data = FrameOperator.denoise_transform(frame_data, eliminated_span, reserved_interval,
    #                                                  erode_shape, erode_ksize, erode_iterations,
    #                                                  dilate_shape, dilate_ksize, dilate_iterations,
    #                                                  stripe_enable, erode_enable, dilate_enable)
    #     contours_collection = FrameOperator.find_matched_contours(frame_data, min_area, max_area, max_roundness, max_distance,
    #                                                               x_number, x_mini, x_maxi, y_number, y_mini, y_maxi)
    #     # 显示原始图片
    #     if show_origin:
    #         frame_data = FrameOperator.draw_matched_contours(origin_frame_data, contours_collection)
    #     # 不显示原始图片
    #     else:
    #         frame_data = FrameOperator.draw_matched_contours(frame_data, contours_collection)
    #
    #     self.show_process_frame(frame=frame_data)

    def mean_save_button(self, message: dict):
        message.pop("ShowOrigin")
        self.process_parameters.update(message)
        # 保存到数据库
        self.db_operator.set_process_parameters(
            filter_dict={"SerialNumber": self.serial_number},
            demand_dict=self.process_parameters
        )
        Messenger.show_message_box(
            widget=self,
            message={"level": 'INFO', "title": '信息', "text": '算法参数保存成功',
                     "informative_text": "", 'detailed_text': ""}
        )

    def mean_next_button(self, message: dict):
        message.pop("ShowOrigin")
        self.process_parameters.update(message)
        self.set_sidebar_styleSheet(self.labelContours, False)  # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_MEAN_PAGE + 1)  # 切换页面

    def mean_back_button(self):
        self.set_sidebar_styleSheet(self.labelContours, False)  # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_MEAN_PAGE - 1)  # 切换页面

    def show_mean_image(self, **kwargs):
        vertexes = [[self.process_parameters["P1X"], self.process_parameters["P1Y"]],
                    [self.process_parameters["P2X"], self.process_parameters["P2Y"]],
                    [self.process_parameters["P3X"], self.process_parameters["P3Y"]],
                    [self.process_parameters["P4X"], self.process_parameters["P4Y"]]]

        region_direction = self.process_parameters["MaskRegionDirection"]
        region_ratio = self.process_parameters["MaskRegionRatio"]
        super_green_region = self.process_parameters["SuperGreenMaskRegion"]
        filter_d = self.process_parameters["BilateralFilterD"]
        filter_sigma_color = self.process_parameters["BilateralFilterSigmaColor"]
        filter_sigma_space = self.process_parameters["BilateralFilterSigmaSpace"]

        h_lower_2 = self.process_parameters["HLower_2"]
        h_upper_2 = self.process_parameters["HUpper_2"]
        s_lower_2 = self.process_parameters["SLower_2"]
        s_upper_2 = self.process_parameters["SUpper_2"]
        v_lower_2 = self.process_parameters["VLower_2"]
        v_upper_2 = self.process_parameters["VUpper_2"]
        open_ksize_2 = self.process_parameters["OpenKernelSize_2"]
        open_iterations_2 = self.process_parameters["OpenIterations_2"]

        h_lower_1 = self.process_parameters["HLower"]
        h_upper_1 = self.process_parameters["HUpper"]
        s_lower_1 = self.process_parameters["SLower"]
        s_upper_1 = self.process_parameters["SUpper"]
        v_lower_1 = self.process_parameters["VLower"]
        v_upper_1 = self.process_parameters["VUpper"]
        open_ksize_1 = self.process_parameters["OpenKernelSize"]
        open_iterations_1 = self.process_parameters["OpenIterations"]

        x_number = self.process_parameters["XNumber"]
        x_mini = self.process_parameters["XMini"]
        x_maxi = self.process_parameters["XMaxi"]
        y_number = self.process_parameters["YNumber"]
        y_mini = self.process_parameters["YMini"]
        y_maxi = self.process_parameters["YMaxi"]

        if "parameters" in kwargs:
            parameters = kwargs["parameters"]
            shift = parameters.get("SectionShift")
            mean_threshold = parameters.get("SectionMeanThreshold")
            show_origin = parameters.get("ShowOrigin")
        else:
            shift = kwargs.get("shift")
            mean_threshold = kwargs.get("mean_threshold")
            show_origin = kwargs.get("ShowOrigin")

        # 处理图片
        # 原始图片
        origin_frame_data = FrameOperator.perspective_transform(self.frame_data, vertexes)
        # 获得颜色掩膜
        green_mask = FrameOperator.get_color_mask_for_green(
            frame=origin_frame_data,
            region_direction=region_direction, region_ratio=region_ratio, super_green_region=super_green_region,
            hsv_lower_2=[h_lower_1, s_lower_1, v_lower_1], hsv_upper_2=[h_upper_1, s_upper_1, v_upper_1],
            ksize_2=open_ksize_1, iterations_2=open_iterations_1,
            hsv_lower_1=[h_lower_2, s_lower_2, v_lower_2], hsv_upper_1=[h_upper_2, s_upper_2, v_upper_2],
            ksize_1=open_ksize_2, iterations_1=open_iterations_2,
        )
        # 划分
        x_division, _, _ = FrameOperator.get_sorted_division(number=x_number, mini=x_mini, maxi=x_maxi)
        y_division, _, _ = FrameOperator.get_sorted_division(number=y_number, mini=y_mini, maxi=y_maxi)
        # 求切片颜色平均值
        pins_map = FrameOperator.aaa(
            frame=green_mask,
            x_division=x_division, y_division=y_division,
            x_number=x_number, x_mini=x_mini, x_maxi=x_maxi,
            y_number=y_number, y_mini=y_mini, y_maxi=y_maxi,
            shift=shift, threshold=mean_threshold,
        )

        # 不显示原始图片
        if not show_origin:
            origin_frame_data = FrameOperator.draw_color_extract(
                frame=origin_frame_data, extract_mask=green_mask,
                region_direction=region_direction, region_ratio=region_ratio,
                draw_region_line=False
            )

        draw = FrameOperator.draw_mean_threshold(
            frame=origin_frame_data, pins_map=pins_map,
            x_division=x_division, y_division=y_division,
            shift=shift
        )
        self.show_process_frame(frame=draw)

    def pins_map_save_button(self, message: dict):
        line = self.line
        side = self.side

        rows = message.get("Rows")
        columns = message.get("Columns")
        pins_map = message.get("PinsMap")

        # 以右侧相机为基准
        if side != CF_TEACH_REFERENCE_SIDE:
            pins_map = cv2.flip(pins_map, flipCode=0)       # 水平翻转
        str_pins_map = MySerializer.serialize(pins_map)     # 序列化

        # 保存至数据库
        self.db_operator.set_parts_pins_map(
            demand_dict={"Rows": rows, "Columns": columns, "PinsMap": str_pins_map},
            filter_dict={"Part": self.part, "Line": line}
        )

        Messenger.show_message_box(
            widget=self,
            message={"level": 'INFO', "title": '信息', "text": '零件顶棒矩阵保存成功',
                     "informative_text": "", 'detailed_text': ""}
        )

    def pins_map_next_button(self):
        self.close()    # 关闭页面

    def pins_map_back_button(self):
        self.set_sidebar_styleSheet(self.labelPart, False)      # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_PINS_MAP_PAGE - 1)  # 切换页面

    def show_pins_map_image(self):
        vertexes = [[self.process_parameters["P1X"], self.process_parameters["P1Y"]],
                    [self.process_parameters["P2X"], self.process_parameters["P2Y"]],
                    [self.process_parameters["P3X"], self.process_parameters["P3Y"]],
                    [self.process_parameters["P4X"], self.process_parameters["P4Y"]]]
        region_direction = self.process_parameters["MaskRegionDirection"]
        region_ratio = self.process_parameters["MaskRegionRatio"]
        super_green_region = self.process_parameters["SuperGreenMaskRegion"]
        filter_d = self.process_parameters["BilateralFilterD"]
        filter_sigma_color = self.process_parameters["BilateralFilterSigmaColor"]
        filter_sigma_space = self.process_parameters["BilateralFilterSigmaSpace"]

        h_lower_2 = self.process_parameters["HLower_2"]
        h_upper_2 = self.process_parameters["HUpper_2"]
        s_lower_2 = self.process_parameters["SLower_2"]
        s_upper_2 = self.process_parameters["SUpper_2"]
        v_lower_2 = self.process_parameters["VLower_2"]
        v_upper_2 = self.process_parameters["VUpper_2"]
        open_ksize_2 = self.process_parameters["OpenKernelSize_2"]
        open_iterations_2 = self.process_parameters["OpenIterations_2"]

        h_lower_1 = self.process_parameters["HLower"]
        h_upper_1 = self.process_parameters["HUpper"]
        s_lower_1 = self.process_parameters["SLower"]
        s_upper_1 = self.process_parameters["SUpper"]
        v_lower_1 = self.process_parameters["VLower"]
        v_upper_1 = self.process_parameters["VUpper"]
        open_ksize_1 = self.process_parameters["OpenKernelSize"]
        open_iterations_1 = self.process_parameters["OpenIterations"]

        x_number = self.process_parameters["XNumber"]
        x_mini = self.process_parameters["XMini"]
        x_maxi = self.process_parameters["XMaxi"]
        y_number = self.process_parameters["YNumber"]
        y_mini = self.process_parameters["YMini"]
        y_maxi = self.process_parameters["YMaxi"]

        shift = self.process_parameters["SectionShift"]
        mean_threshold = self.process_parameters["SectionMeanThreshold"]

        # 处理图片
        # 原始图片
        origin_frame_data = FrameOperator.perspective_transform(self.frame_data, vertexes)
        # 获得颜色掩膜
        green_mask = FrameOperator.get_color_mask_for_green(
            frame=origin_frame_data,
            region_direction=region_direction, region_ratio=region_ratio, super_green_region=super_green_region,
            hsv_lower_2=[h_lower_1, s_lower_1, v_lower_1], hsv_upper_2=[h_upper_1, s_upper_1, v_upper_1],
            ksize_2=open_ksize_1, iterations_2=open_iterations_1,
            hsv_lower_1=[h_lower_2, s_lower_2, v_lower_2], hsv_upper_1=[h_upper_2, s_upper_2, v_upper_2],
            ksize_1=open_ksize_2, iterations_1=open_iterations_2,
        )
        # 划分
        x_division, _, _ = FrameOperator.get_sorted_division(number=x_number, mini=x_mini, maxi=x_maxi)
        y_division, _, _ = FrameOperator.get_sorted_division(number=y_number, mini=y_mini, maxi=y_maxi)
        # 求切片颜色平均值
        pins_map = FrameOperator.aaa(
            frame=green_mask,
            x_division=x_division, y_division=y_division,
            x_number=x_number, x_mini=x_mini, x_maxi=x_maxi,
            y_number=y_number, y_mini=y_mini, y_maxi=y_maxi,
            shift=shift, threshold=mean_threshold,
        )

        show_origin = True
        # 不显示原始图片
        if not show_origin:
            origin_frame_data = FrameOperator.draw_color_extract(
                frame=origin_frame_data, extract_mask=green_mask,
                region_direction=region_direction, region_ratio=region_ratio,
                draw_region_line=False
            )

        draw = FrameOperator.draw_mean_threshold(
            frame=origin_frame_data, pins_map=pins_map,
            x_division=x_division, y_division=y_division,
            shift=shift
        )

        self.show_process_frame(frame=draw)

        self.pins_map = pins_map
        return self.pins_map

    def part_edited(self, part: str):
        """
        零件号被编辑
        :param part:
        :return:
        """
        # 替换零件号
        if part == "":
            self.part = ""
            show = '@'
            self.pins_map_page.buttonSave.setEnabled(False)
        else:
            self.part = part
            show = self.part
            self.pins_map_page.buttonSave.setEnabled(True)

        title = self.title.text()
        right_bracket = title.rfind("[")
        new_title = title[:right_bracket] + '[%s]' % show
        self.title.setText(new_title)

    @staticmethod
    def get_closed_point(pos: QPoint, label: QLabel, pixmap: QPixmap, points: Union[np.ndarray, list], proximity: int = 20) -> tuple:
        """
        获取接近点序号以及鼠标在图片空间的坐标
        :param pos:
        :param label:
        :param pixmap:
        :param points:
        :param proximity:
        :return:
        """
        # 获取points的个数
        if isinstance(points, list):
            points = np.array(points, np.int32)
        # 将鼠标映射到图片中
        x, y = InterfaceTeach.map_2_pixmap_pos(pos=pos, label=label, pixmap=pixmap)
        # 计算距离
        # r, c = points.shape
        # point = np.tile(np.array([x, y], np.int32), (r, 1))
        point = np.array([x, y], np.int32)
        sub = point - points
        dis = np.hypot(sub[:, 0], sub[:, 1])
        # 筛选
        tar = np.argwhere(dis <= proximity)
        if tar.size != 0:
            return tar[0, 0], (x, y)
        else:
            return None, (x, y)

    @staticmethod
    def map_2_pixmap_pos(pos: QPoint, label: QLabel, pixmap: QPixmap) -> tuple:
        """
        将鼠标坐标映射到图片空间
        :param pos:
        :param label:
        :param pixmap:
        :return:
        """
        show_pixmap = label.pixmap()

        ratio_height = pixmap.height() / show_pixmap.height()
        ratio_width = pixmap.width() / show_pixmap.width()

        shift_height = int((label.size().height() - show_pixmap.height()) / 2)
        shift_width = int((label.size().width() - show_pixmap.width()) / 2)

        image_x = round((pos.x() - shift_width) * ratio_width)
        image_y = round((pos.y() - shift_height) * ratio_height)

        return image_x, image_y

    def get_pins_map_region(self, pos: QPoint, label: QLabel, pixmap: QPixmap, canter: int = 10):

        # 将鼠标映射到图片中
        x, y = InterfaceTeach.map_2_pixmap_pos(pos=pos, label=label, pixmap=pixmap)

        # 获取区域划分
        x_number = self.process_parameters["XNumber"]
        x_mini = self.process_parameters["XMini"]
        x_maxi = self.process_parameters["XMaxi"]
        y_number = self.process_parameters["YNumber"]
        y_mini = self.process_parameters["YMini"]
        y_maxi = self.process_parameters["YMaxi"]

        x_division, _, _ = FrameOperator.get_sorted_division(x_number, x_mini, x_maxi)
        y_division, _, _ = FrameOperator.get_sorted_division(y_number, y_mini, y_maxi)

        # 过滤 在边界外
        if x < x_mini or x > x_maxi or y < y_mini or y > y_maxi:
            return None

        # 获取中间值  float32
        x_center = (x_division[1:] + x_division[:-1]) / 2
        y_center = (y_division[1:] + y_division[:-1]) / 2

        # 计算下标
        # 方法1
        x_sub = np.abs(x_division - x)
        x_index = (np.argsort(x_sub)[:2].sum() - 1) // 2
        y_sub = np.abs(y_division - y)
        y_index = (np.argsort(y_sub)[:2].sum() - 1) // 2
        # # 方法2
        # # 修正边界
        # if x == x_maxi:
        #     x = x_maxi - 1
        # if y == y_maxi:
        #     y = y_maxi - 1
        # x_index = np.where(x_division <= x)[0][-1]
        # y_index = np.where(y_division <= y)[0][-1]

        # 按中心距进行筛选
        x_diff = x_center[x_index] - x
        y_diff = y_center[y_index] - y
        square_dis = math.pow(x_diff, 2) + math.pow(y_diff, 2)
        if square_dis > math.pow(canter, 2):
            return None

        return x_index, y_index

    def to_resize(self):
        """
        调整尺寸
        :return:
        """
        # 缩放图片
        self.scale_image(pixmap=self.process_pixmap, label=self.labelImage)

    @staticmethod
    def scale_image(pixmap: Optional[QPixmap], label: QLabel):
        """
        缩放图片
        :param pixmap:
        :param label:
        :return:
        """
        if pixmap is not None:
            Presenter.show_pixmap_in_QLabel(pixmap=pixmap, label=label)

    @staticmethod
    def show_image(label: QLabel, image: np.ndarray):
        """
        在 Qlabel 中显示图像
        :param label:
        :param image:
        :return:
        """
        pixmap, _, _ = Presenter.show_ndarray_in_QLabel(image=image, label=label)
        return pixmap

    def show_process_frame(self, frame: np.ndarray):
        """
        在 labelImage 上显示处理画面
        :param frame:
        :return:
        """
        self.process_pixmap = self.show_image(label=self.labelImage, image=frame)

    def show_left_click_menu(self, pos: QPoint):
        """
        右键菜单
        :param pos:
        :return:
        """
        menu = QMenu()

        save_action = QAction('保存图片', menu)

        style = QApplication.style()
        save_action.setIcon(style.standardIcon(QStyle.SP_DialogSaveButton))

        message = {
            "SerialNumber": self.serial_number,
            "Part": self.part,
            "Line": self.line
        }
        save_action.triggered.connect(lambda: self.savePictureSignal.emit(message))

        menu.addAction(save_action)

        global_pos = self.labelImage.mapToGlobal(pos)
        menu.exec(global_pos)

    @staticmethod
    def set_sidebar_styleSheet(label: QLabel, is_active: bool):
        """
        设置边框 label 的 styleSheet
        :param label:
        :param is_active:
        :return:
        """
        if is_active:
            label.setStyleSheet("font: 75 12pt \"微软雅黑\";\ntext-decoration: underline;\ncolor: rgb(0, 170, 255);")
        else:
            label.setStyleSheet("font: 75 12pt \"微软雅黑\";\ncolor: rgb(0, 0, 0);")

    def eventFilter(self, obj: QObject, event: QEvent):
        """
        事件过滤器
        :param obj:
        :param event:
        :return:
        """
        if obj == self.labelImage:
            # 按下鼠标左键
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                # 梯形校正页面
                if self.stackedLayout.currentIndex() == CF_TEACH_KEYSTONE_PAGE and not self.keystone_perspectived:
                    # 获取接近点序号
                    point, _ = self.get_closed_point(pos=event.pos(), label=obj, pixmap=self.process_pixmap, points=self.keystone_page.vertexes)
                    if point is not None:
                        # 赋值
                        self.keystone_closed_point = point
                        # 设置鼠标
                        obj.setCursor(Qt.ClosedHandCursor)
                    return True
                elif self.stackedLayout.currentIndex() == CF_TEACH_PINS_MAP_PAGE:
                    region = self.get_pins_map_region(pos=event.pos(), label=obj, pixmap=self.process_pixmap)
                    if region is not None:
                        col, row = region
                        rect = QTableWidgetSelectionRange(row, col, row, col)  # 当前区域

                        selected_items = self.pins_map_page.tablePins.selectedItems()
                        for item in selected_items:
                            r = item.row()
                            c = item.column()
                            if row == r and col == c:
                                self.pins_map_page.tablePins.setRangeSelected(rect, False)  # 设置选区
                                break
                        else:
                            self.pins_map_page.tablePins.setRangeSelected(rect, True)  # 设置选区

                    return True
            # 释放鼠标左键
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                # 梯形校正页面
                if self.stackedLayout.currentIndex() == CF_TEACH_KEYSTONE_PAGE and not self.keystone_perspectived:
                    # 复位
                    self.keystone_closed_point = None
                    # 恢复鼠标
                    obj.unsetCursor()
                    return True
            # 鼠标移动 没有按鼠标
            elif event.type() == QEvent.MouseMove and event.buttons() == Qt.NoButton:
                # 梯形校正页面
                if self.stackedLayout.currentIndex() == CF_TEACH_KEYSTONE_PAGE and not self.keystone_perspectived:
                    # 获取接近点序号
                    point, _ = self.get_closed_point(pos=event.pos(), label=obj, pixmap=self.process_pixmap, points=self.keystone_page.vertexes)
                    # 设置鼠标
                    if point is None:
                        obj.unsetCursor()
                    else:
                        obj.setCursor(Qt.OpenHandCursor)
                    return True
                elif self.stackedLayout.currentIndex() == CF_TEACH_PINS_MAP_PAGE:
                    region = self.get_pins_map_region(pos=event.pos(), label=obj, pixmap=self.process_pixmap)
                    if region is not None:
                        col, row = region
                        obj.setCursor(Qt.OpenHandCursor)  # 设置鼠标
                        self.statusBar.showMessage("row: %d, column: %d" % (row, col), 2000)  # 状态栏
                    else:
                        obj.unsetCursor()
                    return True
            # 鼠标移动 按着鼠标左键
            elif event.type() == QEvent.MouseMove and event.buttons() == Qt.LeftButton:
                # 梯形校正页面
                if self.stackedLayout.currentIndex() == CF_TEACH_KEYSTONE_PAGE and not self.keystone_perspectived:
                    # 映射到图片空间
                    x, y = self.map_2_pixmap_pos(pos=event.pos(), label=obj, pixmap=self.process_pixmap)
                    if self.keystone_closed_point == 0:
                        self.keystone_page.spinBoxP1X.setValue(x)
                        self.keystone_page.spinBoxP1Y.setValue(y)
                    elif self.keystone_closed_point == 1:
                        self.keystone_page.spinBoxP2X.setValue(x)
                        self.keystone_page.spinBoxP2Y.setValue(y)
                    elif self.keystone_closed_point == 2:
                        self.keystone_page.spinBoxP3X.setValue(x)
                        self.keystone_page.spinBoxP3Y.setValue(y)
                    elif self.keystone_closed_point == 3:
                        self.keystone_page.spinBoxP4X.setValue(x)
                        self.keystone_page.spinBoxP4Y.setValue(y)
                    return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        调整尺寸事件
        :param event:
        :return:
        """
        self.to_resize()
        return super().resizeEvent(event)

    def show(self):
        """
        显示界面
        :return:
        """

        # 切换页面
        if 0 < self.activate_page < self.stackedLayout.count():
            self.stackedLayout.setCurrentIndex(self.activate_page)
            # 激活输入框
            if self.activate_page == CF_TEACH_PINS_MAP_PAGE:
                self.pins_map_page.comboBoxPart.setEnabled(True)
                self.pins_map_page.buttonBack.setHidden(True)
        elif self.activate_page == 0:
            # 显示图片
            self.show_process_frame(self.frame_data)

        super().show()

        # 调整尺寸
        self.to_resize()

    def closeEvent(self, event):
        """
        关闭界面事件
        :param event:
        :return:
        """
        # 发送信号
        self.closeSignal.emit()
        return super().closeEvent(event)
