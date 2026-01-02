from typing import Union
import cv2
import numpy as np
import math
from typing import Optional
from collections import Counter

from PyQt5.QtWidgets import QMainWindow, QStackedLayout, QLabel, QMenu, QAction, QApplication, QTableWidgetSelectionRange, QStyle
from PyQt5.QtCore import pyqtSignal, Qt, QObject, QEvent, QPoint
from PyQt5.QtGui import QPixmap, QResizeEvent, QIcon

from UI.ui_teach import Ui_MainWindow as Ui_Teach
from Interface.interface_teach_info_page import InterfaceTeachInfoPage
from Interface.interface_teach_keystone_page import InterfaceTeachKeystonePage
from Interface.interface_teach_division_page import InterfaceTeachDivisionPage
from Interface.interface_teach_binarization_page import InterfaceTeachBinarizationPage
from Interface.interface_teach_denoise_page import InterfaceTeachDenoisePage
from Interface.interface_teach_contours_page import InterfaceTeachContoursPage
from Interface.interface_teach_pins_map_page import InterfaceTeachPinsMapPage

from CameraCore.camera_identity import CameraIdentity
from Utils.frame_operator import FrameOperator
from Utils.image_presenter import Presenter
from Utils.database_operator import DatabaseOperator
from Utils.messenger import Messenger
from Utils.serializer import MySerializer
from User.config_static import (CF_TEACH_INFO_PAGE, CF_TEACH_KEYSTONE_PAGE, CF_TEACH_BINARIZATION_PAGE,
                                CF_TEACH_DENOISE_PAGE, CF_TEACH_DIVISION_PAGE, CF_TEACH_CONTOURS_PAGE, CF_TEACH_PINS_MAP_PAGE,
                                CF_TEACH_REFERENCE_SIDE, CF_RUNNING_SEQUENCE_FILE, CF_RUNNING_GRAB_FLAG, CF_RUNNING_TEACH_FLAG,
                                CF_APP_TITLE, CF_APP_ICON)


class InterfaceTeach(QMainWindow, Ui_Teach):
    # 关闭页面信号
    closeSignal = pyqtSignal()
    # 保存图片信号
    savePictureSignal = pyqtSignal(dict)

    def __init__(self, frame_data: np.ndarray, camera_identity: CameraIdentity, camera_location: dict, part: str,
                 db_operator: DatabaseOperator, activate_page: int = 0):
        super().__init__()

        self.frame_data = frame_data
        self.camera_identity = camera_identity
        self.camera_location = camera_location
        self.part = part
        self.activate_page = activate_page
        self.db_operator = db_operator  # 数据库

        self.setupUi(self)  # 初始化窗口

        self.setWindowTitle('%s-Teach' % CF_APP_TITLE)  # 设置窗口标题
        self.setWindowIcon(QIcon(CF_APP_ICON))  # 设置窗口图标

        # 实例化分页面
        self.info_page = InterfaceTeachInfoPage(db_operator=db_operator)
        self.keystone_page = InterfaceTeachKeystonePage()
        self.division_page = InterfaceTeachDivisionPage()
        self.binarization_page = InterfaceTeachBinarizationPage()
        self.denoise_page = InterfaceTeachDenoisePage()
        self.contours_page = InterfaceTeachContoursPage()
        self.pins_map_page = InterfaceTeachPinsMapPage(db_operator=db_operator)

        # 堆叠布局
        self.stackedLayout = QStackedLayout(self.widget)
        # 增加页面
        self.stackedLayout.addWidget(self.info_page)  # 0
        self.stackedLayout.addWidget(self.keystone_page)  # 1
        self.stackedLayout.addWidget(self.division_page)  # 2
        self.stackedLayout.addWidget(self.binarization_page)  # 3
        self.stackedLayout.addWidget(self.denoise_page)  # 4
        self.stackedLayout.addWidget(self.contours_page)  # 5
        self.stackedLayout.addWidget(self.pins_map_page)  # 6

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

        self.division_page.nextSignal.connect(self.division_next_button)
        self.division_page.backSignal.connect(self.division_back_button)
        self.division_page.refreshSignal.connect(lambda message: self.show_division_image(parameters=message))

        self.binarization_page.nextSignal.connect(self.binarization_next_button)
        self.binarization_page.backSignal.connect(self.binarization_back_button)
        self.binarization_page.refreshSignal.connect(lambda message: self.show_binarization_image(parameters=message))

        self.denoise_page.nextSignal.connect(self.denoise_next_button)
        self.denoise_page.backSignal.connect(self.denoise_back_button)
        self.denoise_page.refreshSignal.connect(lambda message: self.show_denoise_image(parameters=message))

        self.contours_page.saveSignal.connect(self.contours_save_button)
        self.contours_page.nextSignal.connect(self.contours_next_button)
        self.contours_page.backSignal.connect(self.contours_back_button)
        self.contours_page.refreshSignal.connect(lambda message: self.show_contours_image(parameters=message))

        self.pins_map_page.saveSignal.connect(self.pins_map_save_button)
        self.pins_map_page.nextSignal.connect(self.pins_map_next_button)
        self.pins_map_page.backSignal.connect(self.pins_map_back_button)
        self.pins_map_page.partChangedSignal.connect(self.part_edited)

        # 给标签加载事件过滤器
        self.labelImage.installEventFilter(self)

        # 获取数据
        self.process_parameters = self.db_operator.get_all_process_parameters(filter_dict={"SerialNumber": self.camera_identity.serial_number})

        # 初始化数据, 因为页面0没有切换
        self.info_page.init(camera_identity=self.camera_identity, camera_location=self.camera_location, part=self.part)

        # 显示的原始图片
        self.process_pixmap = None

        # 顶棒图片
        self.pins_map = None

        # 梯形矫正中接近点序号
        self.keystone_closed_point = None
        # 已透视变换标志
        self.keystone_perspectived: bool = False

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
            self.info_page.init(camera_identity=self.camera_identity, camera_location=self.camera_location, part=self.part)
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
        # 区域划分页面
        elif index == CF_TEACH_DIVISION_PAGE:
            # 设置最小尺寸
            self.widget.setMinimumWidth(800)
            # 置位 sidebar label
            self.set_sidebar_styleSheet(self.labelDivision, True)
            # 初始化
            shift = 88
            x_max = self.process_pixmap.width() - 1
            x_number = self.process_parameters.get("XNumber", 13)
            x_mini = self.process_parameters.get("XMini", shift)
            x_maxi = self.process_parameters.get("XMaxi", x_max - shift)
            y_max = self.process_pixmap.height() - 1
            y_number = self.process_parameters.get("YNumber", 27)
            y_mini = self.process_parameters.get("YMini", shift)
            y_maxi = self.process_parameters.get("YMaxi", y_max - shift)
            self.division_page.init(x_number=x_number, x_mini=x_mini, x_maxi=x_maxi, x_max=x_max,
                                    y_number=y_number, y_mini=y_mini, y_maxi=y_maxi, y_max=y_max)
            # 刷新界面
            QApplication.processEvents()
            # 显示图片
            self.show_division_image(x_number=x_number, x_mini=x_mini, x_maxi=x_maxi,
                                     y_number=y_number, y_mini=y_mini, y_maxi=y_maxi)
        # 二值化页面
        elif index == CF_TEACH_BINARIZATION_PAGE:
            # 设置最小尺寸
            self.widget.setMinimumWidth(800)
            # 置位 sidebar label
            self.set_sidebar_styleSheet(self.labelBinarization, True)
            # 初始化
            scale_alpha = self.process_parameters.get("ScaleAlpha", 4.0)
            scale_beta = self.process_parameters.get("ScaleBeta", 0)
            scale_enable = self.process_parameters.get("ScaleEnable", False)
            gamma_c = self.process_parameters.get("GammaConstant", 1.0)
            gamma_power = self.process_parameters.get("GammaPower", 1.0)
            gamma_enable = self.process_parameters.get("GammaEnable", False)
            log_c = self.process_parameters.get("LogConstant", 1.0)
            log_enable = self.process_parameters.get("LogEnable", False)
            thresh = self.process_parameters.get("Thresh", 80)
            auto_thresh = self.process_parameters.get("AutoThresh", True)
            self.binarization_page.init(scale_alpha, scale_beta, gamma_c, gamma_power, log_c, thresh,
                                        scale_enable, gamma_enable, log_enable, auto_thresh)
            # 刷新界面
            QApplication.processEvents()
            # 显示图片
            self.show_binarization_image(scale_alpha=scale_alpha, scale_beta=scale_beta, gamma_c=gamma_c, gamma_power=gamma_power, log_c=log_c, thresh=thresh,
                                         scale_enable=scale_enable, gamma_enable=gamma_enable, log_enable=log_enable, auto_thresh=auto_thresh,
                                         show_binarization=self.binarization_page.checkBoxShowBinarization.isChecked())
        # 去噪页面
        elif index == CF_TEACH_DENOISE_PAGE:
            # 设置最小尺寸
            self.widget.setMinimumWidth(800)
            # 置位 sidebar label
            self.set_sidebar_styleSheet(self.labelDenoise, True)
            # 初始化
            pixel_number = self.process_pixmap.width()
            eliminated_span = self.process_parameters.get("EliminatedSpan", 150)
            reserved_interval = self.process_parameters.get("ReservedInterval", 1)
            erode_shape = self.process_parameters.get("ErodeShape", 0)
            erode_ksize = self.process_parameters.get("ErodeKsize", 3)
            erode_iterations = self.process_parameters.get("ErodeIterations", 1)
            dilate_shape = self.process_parameters.get("DilateShape", 2)
            dilate_ksize = self.process_parameters.get("DilateKsize", 3)
            dilate_iterations = self.process_parameters.get("DilateIterations", 1)
            stripe_enable = self.process_parameters.get("StripeEnable", False)
            erode_enable = self.process_parameters.get("ErodeEnable", True)
            dilate_enable = self.process_parameters.get("DilateEnable", True)
            self.denoise_page.init(eliminated_span=eliminated_span, reserved_interval=reserved_interval,
                                   erode_shape=erode_shape, erode_ksize=erode_ksize, erode_iterations=erode_iterations,
                                   dilate_shape=dilate_shape, dilate_ksize=dilate_ksize, dilate_iterations=dilate_iterations,
                                   stripe_enable=stripe_enable, erode_enable=erode_enable, dilate_enable=dilate_enable,
                                   pixel_number=pixel_number)
            # 刷新界面
            QApplication.processEvents()
            # 显示图片
            self.show_denoise_image(eliminated_span=eliminated_span, reserved_interval=reserved_interval,
                                    erode_shape=erode_shape, erode_ksize=erode_ksize, erode_iterations=erode_iterations,
                                    dilate_shape=dilate_shape, dilate_ksize=dilate_ksize, dilate_iterations=dilate_iterations,
                                    stripe_enable=stripe_enable, erode_enable=erode_enable, dilate_enable=dilate_enable)
        # 寻找轮廓页面
        elif index == CF_TEACH_CONTOURS_PAGE:
            # 设置最小尺寸
            self.widget.setMinimumWidth(800)
            # 置位 sidebar label
            self.set_sidebar_styleSheet(self.labelContours, True)
            # 初始化
            min_area = self.process_parameters.get("MinArea", 50)
            max_area = self.process_parameters.get("MaxArea", 1500)
            max_roundness = self.process_parameters.get("MaxRoundness", 10)
            max_distance = self.process_parameters.get("MaxDistance", 10)

            x_number = self.process_parameters["XNumber"]
            x_mini = self.process_parameters["XMini"]
            x_maxi = self.process_parameters["XMaxi"]
            y_number = self.process_parameters["YNumber"]
            y_mini = self.process_parameters["YMini"]
            y_maxi = self.process_parameters["YMaxi"]
            min_area_ref, max_area_ref, area_max, distance_ref, distance_max = FrameOperator.calculate_ref_value(x_number=x_number, x_mini=x_mini, x_maxi=x_maxi,
                                                                                                                 y_number=y_number, y_mini=y_mini, y_maxi=y_maxi)

            self.contours_page.init(min_area=min_area, max_area=max_area, max_roundness=max_roundness, max_distance=max_distance,
                                    min_area_ref=min_area_ref, max_area_ref=max_area_ref, area_max=area_max,
                                    distance_ref=distance_ref, distance_max=distance_max)
            # 刷新界面
            QApplication.processEvents()
            # 显示图片
            self.show_contours_image(min_area=min_area, max_area=max_area, max_roundness=max_roundness, max_distance=max_distance,
                                     show_origin=self.contours_page.checkBoxShowOrigin.isChecked())
        # 零件示教页面
        elif index == CF_TEACH_PINS_MAP_PAGE:
            # 设置最小尺寸
            self.widget.setMinimumWidth(800)
            # 置位 sidebar label
            self.set_sidebar_styleSheet(self.labelPart, True)
            # 刷新界面
            QApplication.processEvents()
            # 初始化
            min_area = self.process_parameters["MinArea"]
            max_area = self.process_parameters["MaxArea"]
            max_roundness = self.process_parameters["MaxRoundness"]
            max_distance = self.process_parameters["MaxDistance"]
            x_number = self.process_parameters["XNumber"]
            y_number = self.process_parameters["YNumber"]
            # 显示图片  计算pins_map
            self.show_pins_map_image(min_area=min_area, max_area=max_area, max_roundness=max_roundness, max_distance=max_distance)
            self.pins_map_page.init(camera_location=self.camera_location, part=self.part, x_number=x_number, y_number=y_number, pins_map=self.pins_map)

    def info_next_button(self, message: dict):
        part = message["Part"]
        # 替换零件号
        if part != self.part:
            self.part = part
            title = self.title.text()
            right_bracket = title.rfind("[")
            new_title = title[:right_bracket] + '[%s]' % self.part
            self.title.setText(new_title)
        self.set_sidebar_styleSheet(self.labelInfo, False)  # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_INFO_PAGE + 1)  # 切换页面

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
        self.set_sidebar_styleSheet(self.labelKeystone, False)      # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_KEYSTONE_PAGE + 1)      # 切换页面

    def keystone_back_button(self):
        self.set_sidebar_styleSheet(self.labelKeystone, False)      # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_KEYSTONE_PAGE - 1)      # 切换页面

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

    def division_next_button(self, message: dict):
        self.process_parameters.update(message)
        self.set_sidebar_styleSheet(self.labelDivision, False)      # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_DIVISION_PAGE + 1)      # 切换页面

    def division_back_button(self):
        self.set_sidebar_styleSheet(self.labelDivision, False)      # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_DIVISION_PAGE - 1)      # 切换页面

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

    def binarization_next_button(self, message: dict):
        message.pop("ShowBinarization")
        self.process_parameters.update(message)
        self.set_sidebar_styleSheet(self.labelBinarization, False)  # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_BINARIZATION_PAGE + 1)  # 切换页面

    def binarization_back_button(self):
        self.set_sidebar_styleSheet(self.labelBinarization, False)      # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_BINARIZATION_PAGE - 1)      # 切换页面

    def show_binarization_image(self, **kwargs):
        """
        显示二值化图片
        :param kwargs:
        :return:
        """
        vertexes = [[self.process_parameters["P1X"], self.process_parameters["P1Y"]],
                    [self.process_parameters["P2X"], self.process_parameters["P2Y"]],
                    [self.process_parameters["P3X"], self.process_parameters["P3Y"]],
                    [self.process_parameters["P4X"], self.process_parameters["P4Y"]]]

        if "parameters" in kwargs:
            parameters = kwargs["parameters"]
            scale_alpha = parameters.get("ScaleAlpha")
            scale_beta = parameters.get("ScaleBeta")
            gamma_c = parameters.get("GammaConstant")
            gamma_power = parameters.get("GammaPower")
            log_c = parameters.get("LogConstant")
            thresh = parameters.get("Thresh")
            scale_enable = parameters.get("ScaleEnable")
            gamma_enable = parameters.get("GammaEnable")
            log_enable = parameters.get("LogEnable")
            auto_thresh = parameters.get("AutoThresh")
            show_binarization = parameters.get("ShowBinarization")
        else:
            scale_alpha = kwargs.get("scale_alpha")
            scale_beta = kwargs.get("scale_beta")
            gamma_c = kwargs.get("gamma_c")
            gamma_power = kwargs.get("gamma_power")
            log_c = kwargs.get("log_c")
            thresh = kwargs.get("thresh")
            scale_enable = kwargs.get("scale_enable")
            gamma_enable = kwargs.get("gamma_enable")
            log_enable = kwargs.get("log_enable")
            auto_thresh = kwargs.get("auto_thresh")
            show_binarization = kwargs.get("show_binarization")

        # 处理图片
        frame_data = FrameOperator.perspective_transform(self.frame_data, vertexes)
        binarization, gray = FrameOperator.binarization_transform(frame_data, scale_alpha, scale_beta, gamma_c, gamma_power, log_c, thresh,
                                                                  scale_enable, gamma_enable, log_enable, auto_thresh)

        # 计算直方图
        x, hist = FrameOperator.calculate_hist(gray)
        # 平滑曲线
        smooth_x, smooth_hist = FrameOperator.smooth_hist(x=x, hist=hist)
        # 找波谷
        valleys_x, valleys_hist, _, _ = FrameOperator.find_valleys_and_peaks(x=smooth_x, hist=smooth_hist, whitelist=['valley'])
        # 找参考值
        ref_thresh = FrameOperator.calculate_reference_thresh(valleys_x, _, _, _)
        # 显示参考值
        if ref_thresh is not None:
            self.binarization_page.labelRefThreshValue.setText(str(ref_thresh))
        else:
            self.binarization_page.labelRefThreshValue.setText("NA")

        if auto_thresh and ref_thresh is not None:
            self.binarization_page.labelThreshValue.setText(str(ref_thresh))
        else:
            self.binarization_page.labelThreshValue.setText(str(thresh))

        # 画直方图
        FrameOperator.draw_hist(canvas=self.binarization_page.canvas, x=x, hist=hist,
                                smooth_x=smooth_x, smooth_hist=smooth_hist, valleys_x=valleys_x, valleys_hist=valleys_hist)

        if show_binarization:
            self.show_process_frame(frame=binarization)
        else:
            self.show_process_frame(frame=gray)

    def denoise_next_button(self, message: dict):
        self.process_parameters.update(message)
        self.set_sidebar_styleSheet(self.labelDenoise, False)   # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_DENOISE_PAGE + 1)   # 切换页面

    def denoise_back_button(self):
        self.set_sidebar_styleSheet(self.labelDenoise, False)   # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_DENOISE_PAGE - 1)   # 切换页面

    def show_denoise_image(self, **kwargs):
        """
        显示去噪图片
        :param kwargs:
        :return:
        """
        vertexes = [[self.process_parameters["P1X"], self.process_parameters["P1Y"]],
                    [self.process_parameters["P2X"], self.process_parameters["P2Y"]],
                    [self.process_parameters["P3X"], self.process_parameters["P3Y"]],
                    [self.process_parameters["P4X"], self.process_parameters["P4Y"]]]
        scale_alpha = self.process_parameters["ScaleAlpha"]
        scale_beta = self.process_parameters["ScaleBeta"]
        scale_enable = self.process_parameters["ScaleEnable"]
        gamma_c = self.process_parameters["GammaConstant"]
        gamma_power = self.process_parameters["GammaPower"]
        gamma_enable = self.process_parameters["GammaEnable"]
        log_c = self.process_parameters["LogConstant"]
        log_enable = self.process_parameters["LogEnable"]
        thresh = self.process_parameters["Thresh"]
        auto_thresh = self.process_parameters["AutoThresh"]

        if "parameters" in kwargs:
            parameters = kwargs["parameters"]
            eliminated_span = parameters.get("EliminatedSpan")
            reserved_interval = parameters.get("ReservedInterval")
            erode_shape = parameters.get("ErodeShape")
            erode_ksize = parameters.get("ErodeKsize")
            erode_iterations = parameters.get("ErodeIterations")
            dilate_shape = parameters.get("DilateShape")
            dilate_ksize = parameters.get("DilateKsize")
            dilate_iterations = parameters.get("DilateIterations")
            stripe_enable = parameters.get("StripeEnable")
            erode_enable = parameters.get("ErodeEnable")
            dilate_enable = parameters.get("DilateEnable")
        else:
            eliminated_span = kwargs.get("eliminated_span")
            reserved_interval = kwargs.get("reserved_interval")
            erode_shape = kwargs.get("erode_shape")
            erode_ksize = kwargs.get("erode_ksize")
            erode_iterations = kwargs.get("erode_iterations")
            dilate_shape = kwargs.get("dilate_shape")
            dilate_ksize = kwargs.get("dilate_ksize")
            dilate_iterations = kwargs.get("dilate_iterations")
            stripe_enable = kwargs.get("stripe_enable")
            erode_enable = kwargs.get("erode_enable")
            dilate_enable = kwargs.get("dilate_enable")

        # 处理图片
        frame_data = FrameOperator.perspective_transform(self.frame_data, vertexes)
        frame_data, _ = FrameOperator.binarization_transform(frame_data, scale_alpha, scale_beta, gamma_c, gamma_power, log_c, thresh,
                                                             scale_enable, gamma_enable, log_enable, auto_thresh)
        frame_data = FrameOperator.denoise_transform(frame_data, eliminated_span, reserved_interval,
                                                     erode_shape, erode_ksize, erode_iterations,
                                                     dilate_shape, dilate_ksize, dilate_iterations,
                                                     stripe_enable, erode_enable, dilate_enable)
        self.show_process_frame(frame=frame_data)

    def contours_save_button(self, message: dict):
        message.pop("ShowOrigin")
        self.process_parameters.update(message)
        # 保存到数据库
        self.db_operator.set_process_parameters(filter_dict={"SerialNumber": self.camera_identity.serial_number}, demand_dict=self.process_parameters)
        Messenger.show_QMessageBox(widget=self, level='INFO', title="信息", text="算法参数保存成功",
                                   informative_text="", detailed_text="", QLabelMinWidth=200)

    def contours_next_button(self, message: dict):
        message.pop("ShowOrigin")
        self.process_parameters.update(message)
        self.set_sidebar_styleSheet(self.labelContours, False)  # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_CONTOURS_PAGE + 1)  # 切换页面

    def contours_back_button(self):
        self.set_sidebar_styleSheet(self.labelContours, False)  # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_CONTOURS_PAGE - 1)  # 切换页面

    def show_contours_image(self, **kwargs):
        vertexes = [[self.process_parameters["P1X"], self.process_parameters["P1Y"]],
                    [self.process_parameters["P2X"], self.process_parameters["P2Y"]],
                    [self.process_parameters["P3X"], self.process_parameters["P3Y"]],
                    [self.process_parameters["P4X"], self.process_parameters["P4Y"]]]
        scale_alpha = self.process_parameters["ScaleAlpha"]
        scale_beta = self.process_parameters["ScaleBeta"]
        scale_enable = self.process_parameters["ScaleEnable"]
        gamma_c = self.process_parameters["GammaConstant"]
        gamma_power = self.process_parameters["GammaPower"]
        gamma_enable = self.process_parameters["GammaEnable"]
        log_c = self.process_parameters["LogConstant"]
        log_enable = self.process_parameters["LogEnable"]
        thresh = self.process_parameters["Thresh"]
        auto_thresh = self.process_parameters["AutoThresh"]
        eliminated_span = self.process_parameters["EliminatedSpan"]
        reserved_interval = self.process_parameters["ReservedInterval"]
        erode_shape = self.process_parameters["ErodeShape"]
        erode_ksize = self.process_parameters["ErodeKsize"]
        erode_iterations = self.process_parameters["ErodeIterations"]
        dilate_shape = self.process_parameters["DilateShape"]
        dilate_ksize = self.process_parameters["DilateKsize"]
        dilate_iterations = self.process_parameters["DilateIterations"]
        stripe_enable = self.process_parameters["StripeEnable"]
        erode_enable = self.process_parameters["ErodeEnable"]
        dilate_enable = self.process_parameters["DilateEnable"]
        x_number = self.process_parameters["XNumber"]
        x_mini = self.process_parameters["XMini"]
        x_maxi = self.process_parameters["XMaxi"]
        y_number = self.process_parameters["YNumber"]
        y_mini = self.process_parameters["YMini"]
        y_maxi = self.process_parameters["YMaxi"]

        if "parameters" in kwargs:
            parameters = kwargs["parameters"]
            min_area = parameters.get("MinArea")
            max_area = parameters.get("MaxArea")
            max_roundness = parameters.get("MaxRoundness")
            max_distance = parameters.get("MaxDistance")
            show_origin = parameters.get("ShowOrigin")
        else:
            min_area = kwargs.get("min_area")
            max_area = kwargs.get("max_area")
            max_roundness = kwargs.get("max_roundness")
            max_distance = kwargs.get("max_distance")
            show_origin = kwargs.get("show_origin")

        # 处理图片
        origin_frame_data = FrameOperator.perspective_transform(self.frame_data, vertexes)  # 原始图片
        frame_data, _ = FrameOperator.binarization_transform(origin_frame_data, scale_alpha, scale_beta, gamma_c, gamma_power, log_c, thresh,
                                                             scale_enable, gamma_enable, log_enable, auto_thresh)
        frame_data = FrameOperator.denoise_transform(frame_data, eliminated_span, reserved_interval,
                                                     erode_shape, erode_ksize, erode_iterations,
                                                     dilate_shape, dilate_ksize, dilate_iterations,
                                                     stripe_enable, erode_enable, dilate_enable)
        contours_collection = FrameOperator.find_matched_contours(frame_data, min_area, max_area, max_roundness, max_distance,
                                                                  x_number, x_mini, x_maxi, y_number, y_mini, y_maxi)
        # 显示原始图片
        if show_origin:
            frame_data = FrameOperator.draw_matched_contours(origin_frame_data, contours_collection)
        # 不显示原始图片
        else:
            frame_data = FrameOperator.draw_matched_contours(frame_data, contours_collection)

        self.show_process_frame(frame=frame_data)

    def pins_map_save_button(self, message: dict):
        line = self.camera_location["Line"]
        side = self.camera_location["Side"]

        rows = message.get("Rows")
        columns = message.get("Columns")
        pins_map = message.get("PinsMap")

        # # 以右侧相机为基准
        # if side != CF_TEACH_REFERENCE_SIDE:
        #     pins_map = cv2.flip(pins_map, flipCode=0)       # 水平翻转
        str_pins_map = MySerializer.serialize(pins_map)     # 序列化

        # 保存至数据库
        self.db_operator.set_parts_pins_map(demand_dict={"Rows": rows, "Columns": columns, "PinsMap": str_pins_map},
                                            filter_dict={"Part": self.part, "Line": line})
        Messenger.show_QMessageBox(widget=self, level='INFO', title="信息", text="零件顶棒矩阵保存成功",
                                   informative_text="", detailed_text="", QLabelMinWidth=200)

    def pins_map_next_button(self):
        self.close()    # 关闭页面

    def pins_map_back_button(self):
        self.set_sidebar_styleSheet(self.labelPart, False)      # 复位 sidebar label
        self.stackedLayout.setCurrentIndex(CF_TEACH_PINS_MAP_PAGE - 1)  # 切换页面

    def show_pins_map_image(self, **kwargs):
        vertexes = [[self.process_parameters["P1X"], self.process_parameters["P1Y"]],
                    [self.process_parameters["P2X"], self.process_parameters["P2Y"]],
                    [self.process_parameters["P3X"], self.process_parameters["P3Y"]],
                    [self.process_parameters["P4X"], self.process_parameters["P4Y"]]]
        scale_alpha = self.process_parameters["ScaleAlpha"]
        scale_beta = self.process_parameters["ScaleBeta"]
        scale_enable = self.process_parameters["ScaleEnable"]
        gamma_c = self.process_parameters["GammaConstant"]
        gamma_power = self.process_parameters["GammaPower"]
        gamma_enable = self.process_parameters["GammaEnable"]
        log_c = self.process_parameters["LogConstant"]
        log_enable = self.process_parameters["LogEnable"]
        thresh = self.process_parameters["Thresh"]
        auto_thresh = self.process_parameters["AutoThresh"]
        eliminated_span = self.process_parameters["EliminatedSpan"]
        reserved_interval = self.process_parameters["ReservedInterval"]
        erode_shape = self.process_parameters["ErodeShape"]
        erode_ksize = self.process_parameters["ErodeKsize"]
        erode_iterations = self.process_parameters["ErodeIterations"]
        dilate_shape = self.process_parameters["DilateShape"]
        dilate_ksize = self.process_parameters["DilateKsize"]
        dilate_iterations = self.process_parameters["DilateIterations"]
        stripe_enable = self.process_parameters["StripeEnable"]
        erode_enable = self.process_parameters["ErodeEnable"]
        dilate_enable = self.process_parameters["DilateEnable"]
        x_number = self.process_parameters["XNumber"]
        x_mini = self.process_parameters["XMini"]
        x_maxi = self.process_parameters["XMaxi"]
        y_number = self.process_parameters["YNumber"]
        y_mini = self.process_parameters["YMini"]
        y_maxi = self.process_parameters["YMaxi"]

        if "parameters" in kwargs:
            parameters = kwargs["parameters"]
            min_area = parameters.get("MinArea")
            max_area = parameters.get("MaxArea")
            max_roundness = parameters.get("MaxRoundness")
            max_distance = parameters.get("MaxDistance")
        else:
            min_area = kwargs.get("min_area")
            max_area = kwargs.get("max_area")
            max_roundness = kwargs.get("max_roundness")
            max_distance = kwargs.get("max_distance")

        # 处理图片
        origin_frame_data = FrameOperator.perspective_transform(self.frame_data, vertexes)  # 原始图片
        frame_data, _ = FrameOperator.binarization_transform(origin_frame_data, scale_alpha, scale_beta, gamma_c, gamma_power, log_c, thresh,
                                                             scale_enable, gamma_enable, log_enable, auto_thresh)
        frame_data = FrameOperator.denoise_transform(frame_data, eliminated_span, reserved_interval,
                                                     erode_shape, erode_ksize, erode_iterations,
                                                     dilate_shape, dilate_ksize, dilate_iterations,
                                                     stripe_enable, erode_enable, dilate_enable)
        contours_collection = FrameOperator.find_matched_contours(frame_data, min_area, max_area, max_roundness, max_distance,
                                                                  x_number, x_mini, x_maxi, y_number, y_mini, y_maxi)
        # 显示原始图片
        frame_data = FrameOperator.draw_matched_contours(origin_frame_data, contours_collection)

        self.pins_map = FrameOperator.convert_contours_collection_to_array(contours_collection, x_number, y_number)
        self.show_process_frame(frame=frame_data)

        return self.pins_map

    def part_edited(self, part: str):
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
                        rect = QTableWidgetSelectionRange(row, col, row, col)       # 当前区域

                        selected_items = self.pins_map_page.tablePins.selectedItems()
                        for item in selected_items:
                            r = item.row()
                            c = item.column()
                            if row == r and col == c:
                                self.pins_map_page.tablePins.setRangeSelected(rect, False)  # 设置选区
                                break
                        else:
                            self.pins_map_page.tablePins.setRangeSelected(rect, True)   # 设置选区

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
                        obj.setCursor(Qt.OpenHandCursor)      # 设置鼠标
                        self.statusBar.showMessage("row: %d, column: %d" % (row, col), 2000)    # 状态栏
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

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        调整尺寸事件
        :param event:
        :return:
        """
        self.to_resize()
        return super().resizeEvent(event)

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

    def show(self):
        """
        显示界面
        :return:
        """
        # 设置title
        # 相机[*] 产线[#] 位置[$] 零件[-]
        title = self.title.text()
        if self.camera_identity.serial_number != "":
            title = title.replace("*", self.camera_identity.serial_number)

        line = self.camera_location["Line"]
        if line != "":
            title = title.replace("#", line)

        location = self.camera_location["Location"]
        if location != "":
            title = title.replace("$", location)

        if self.part != "":
            title = title.replace("@", self.part)

        self.title.setText(title)
        # 显示图片
        self.show_process_frame(self.frame_data)

        # 切换页面
        if 0 < self.activate_page < self.stackedLayout.count():
            self.stackedLayout.setCurrentIndex(self.activate_page)
            # 激活输入框
            if self.activate_page == CF_TEACH_PINS_MAP_PAGE:
                self.pins_map_page.comboBoxPart.setEnabled(True)
                self.pins_map_page.buttonBack.setHidden(True)

        super().show()

        # 调整尺寸
        self.to_resize()

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

    @staticmethod
    def verify_sequence():

        with open(CF_RUNNING_SEQUENCE_FILE, 'r', encoding='utf-8') as sequence_file:
            flag = sequence_file.readline()

        flag_list = [int(i) for i in flag]
        flag_dict = Counter(flag_list)
        grab_num = flag_dict.get(CF_RUNNING_GRAB_FLAG, 0)
        teach_num = flag_dict.get(CF_RUNNING_TEACH_FLAG, 0)

        content = ''
        for i in range(grab_num):
            content += str(CF_RUNNING_GRAB_FLAG)
        for i in range(teach_num - 1):
            content += str(CF_RUNNING_TEACH_FLAG)

        with open(CF_RUNNING_SEQUENCE_FILE, 'w', encoding='utf-8') as sequence_file:
            sequence_file.write(content)

    def closeEvent(self, event):
        """
        关闭界面事件
        :param event:
        :return:
        """
        self.verify_sequence()
        # 发送信号
        self.closeSignal.emit()
        return super().closeEvent(event)

    def show_left_click_menu(self, pos: QPoint):
        menu = QMenu()
        style = QApplication.style()

        save_action = QAction('保存图片', menu)
        save_action.setIcon(style.standardIcon(QStyle.SP_DialogSaveButton))

        message = {"SerialNumber": self.camera_identity.serial_number,
                   "Uid": self.camera_identity.uid,
                   "Part": self.part,
                   "Line": self.camera_location["Line"]}
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
