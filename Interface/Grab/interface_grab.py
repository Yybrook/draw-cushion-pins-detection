import cv2
import numpy as np
from typing import Optional

from PyQt5.QtWidgets import QMainWindow, QLabel, QMenu, QAction, QGraphicsOpacityEffect, QApplication, QStyle
from PyQt5.QtCore import pyqtSignal, Qt, QPoint
from PyQt5.QtGui import QPixmap, QResizeEvent, QIcon

from CameraCore.camera_identity import CameraIdentity
from UI.Grab.ui_grab import Ui_MainWindow as Ui_Grab
from Utils.image_presenter import Presenter
# from Utils.messenger import Messenger
from Utils.database_operator import DatabaseOperator
from User.config_static import (CF_NULL_PICTURE, CF_APP_TITLE, CF_APP_ICON, TB_CAMERAS_IDENTITY)


class InterfaceGrab(QMainWindow, Ui_Grab):

    # 信号
    grabOrNotSignal = pyqtSignal(bool)
    closeCameraSignal = pyqtSignal()
    detectSignal = pyqtSignal(dict)
    teachSignal = pyqtSignal(dict)
    partTeachSignal = pyqtSignal(dict)
    setParametersSignal = pyqtSignal()
    connectAlgorithmSignal = pyqtSignal(bool)
    savePictureSignal = pyqtSignal(dict)

    def __init__(self, camera_identity: CameraIdentity, db_operator: DatabaseOperator):
        super().__init__()

        # 相机身份
        self.camera_identity = camera_identity

        # 数据库
        self.db_operator = db_operator

        # 初始化窗口
        self.setupUi(self)

        # 零件号
        self.part = ''

        # 空图片
        self.null_image = cv2.imread(CF_NULL_PICTURE)
        # 原始图片
        self.before_pixmap = None
        self.after_pixmap = None

        # 布局
        self.imageLabels_layoutSpacing = 4

        self.setWindowTitle('%s-Grab' % CF_APP_TITLE)   # 设置窗口标题
        self.setWindowIcon(QIcon(CF_APP_ICON))          # 设置窗口图标

        # 设置title
        # 相机[*] 产线[#] 位置[$]
        title = self.title.text()
        if self.camera_identity.address != "":
            title = title.replace("*", self.camera_identity.address)
        line = self.camera_identity.get_attached_attribute(key="line")
        if line != "":
            title = title.replace("#", line)
        location = self.camera_identity.get_attached_attribute(key="location")
        if location != "":
            title = title.replace("$", location)
        self.title.setText(title)

        # 连接信号
        # label右键点击
        self.labelBefore.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelBefore.customContextMenuRequested.connect(self.show_left_click_menu_in_before)

        self.labelAfter.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelAfter.customContextMenuRequested.connect(self.show_left_click_menu_in_after)
        # 下拉框
        self.comboBoxPart.currentTextChanged.connect(self.current_part_changed)
        self.comboBoxPart.showPopupSignal.connect(lambda: self.comboBoxPart.set_items(get_items_callback=self.get_parts))
        # 按钮
        self.buttonGrab.toggled[bool].connect(self.grab_or_not)
        self.buttonColse.clicked.connect(self.close_camera)
        self.buttonDetect.clicked.connect(self.detect)
        self.buttonTeach.clicked.connect(self.teach)
        self.buttonPartTeach.clicked.connect(self.part_teach)

        # 样式
        style = QApplication.style()
        self.buttonGrab.setIcon(style.standardIcon(QStyle.SP_MediaStop))
        self.buttonColse.setIcon(style.standardIcon(QStyle.SP_LineEditClearButton))

        # 设置透明度的值，0.0到1.0，最小值0是透明，1是不透明
        self.opacity = QGraphicsOpacityEffect()

        # 显示图片
        self.hide_detection()

        # 菜单
        self.menu = QMenu()
        # 设置相机参数
        set_action = QAction('设置相机参数', self.menu)
        set_action.setIcon(style.standardIcon(QStyle.SP_BrowserReload))
        set_action.triggered.connect(lambda: self.setParametersSignal.emit())
        self.menu.addAction(set_action)

        # 链接图片处理算法
        self.connect_action = QAction('链接图片处理算法', self.menu)
        self.connect_action.setCheckable(True)
        self.connect_action.setChecked(False)
        self.connect_action.toggled.connect(self.connectAlgorithmSignal.emit)
        self.menu.addAction(self.connect_action)

    def detect(self):
        """
        进行检验
        :return:
        """
        self.hide_detection()
        self.part = self.comboBoxPart.currentText().strip()
        if self.part != "":
            message = {
                "Part": self.part,
                "SerialNumber": self.camera_identity.serial_number,
                "Location": self.camera_identity.get_attached_attribute(key="location"),
                "Side": self.camera_identity.get_attached_attribute(key="side"),
                "Line": self.camera_identity.get_attached_attribute(key="line"),
            }
            self.detectSignal.emit(message)

    def teach(self):
        """
        进行示教
        :return:
        """
        part = self.comboBoxPart.currentText().strip()
        message = {
            "Part": part,
            "SerialNumber": self.camera_identity.serial_number,
            "Location": self.camera_identity.get_attached_attribute(key="location"),
            "Side": self.camera_identity.get_attached_attribute(key="side"),
            "Line": self.camera_identity.get_attached_attribute(key="line"),
        }
        self.teachSignal.emit(message)

    def part_teach(self):
        """
        仅示教零件
        :return:
        """
        part = self.comboBoxPart.currentText().strip()
        message = {
            "Part": part,
            "SerialNumber": self.camera_identity.serial_number,
            "Location": self.camera_identity.get_attached_attribute(key="location"),
            "Side": self.camera_identity.get_attached_attribute(key="side"),
            "Line": self.camera_identity.get_attached_attribute(key="line"),
        }
        self.partTeachSignal.emit(message)

    def close_camera(self):
        """
        关闭相机/页面
        :return:
        """
        self.close()

    def grab_or_not(self, is_checked: bool):
        """
        取流或停止
        :param is_checked:
        :return:
        """
        self.grabOrNotSignal.emit(is_checked)
        style = QApplication.style()
        if is_checked:
            self.buttonGrab.setText("停止取流")
            self.buttonGrab.setIcon(style.standardIcon(QStyle.SP_MediaStop))
            self.comboBoxPart.setEnabled(True)
            self.current_part_changed(self.comboBoxPart.currentText().strip())
            self.buttonTeach.setEnabled(True)
            self.buttonPartTeach.setEnabled(True)

        else:
            self.buttonGrab.setText("开始取流")
            self.buttonGrab.setIcon(style.standardIcon(QStyle.SP_MediaPlay))
            self.comboBoxPart.setEnabled(False)
            self.buttonDetect.setEnabled(False)
            self.buttonTeach.setEnabled(False)
            self.buttonPartTeach.setEnabled(False)

    def current_part_changed(self, text: str):
        """
        零件号改变
        :param text:
        :return:
        """
        self.buttonDetect.setEnabled(bool(text))

    def show_left_click_menu_in_before(self, pos: QPoint):
        """
        右键菜单
        :param pos:
        :return:
        """
        # 链接图片处理算法
        camera_exist = self.db_operator.verify_camera_existence(
            table_name=TB_CAMERAS_IDENTITY,
            serial_number=self.camera_identity.serial_number
        )
        self.connect_action.setEnabled(camera_exist)

        global_pos = self.labelBefore.mapToGlobal(pos)
        self.menu.exec(global_pos)

    def show_left_click_menu_in_after(self, pos: QPoint):
        """
        右键菜单
        :param pos:
        :return:
        """
        message = {
            "Part": self.part,
            "SerialNumber": self.camera_identity.serial_number,
            "Line": self.camera_identity.get_attached_attribute(key="line"),
        }

        # 样式
        style = QApplication.style()

        menu = QMenu()

        save_action = QAction('保存图片', menu)
        save_action.setIcon(style.standardIcon(QStyle.SP_DialogSaveButton))
        save_action.triggered.connect(lambda: self.savePictureSignal.emit(message))

        menu.addAction(save_action)

        global_pos = self.labelAfter.mapToGlobal(pos)
        menu.exec(global_pos)

    def get_parts(self) -> list:
        """
        获取所有零件号
        :return:
        """
        line = self.camera_identity.get_attached_attribute(key="line"),
        return self.db_operator.get_parts(line)

    def to_resize(self):
        """
        调整尺寸
        :return:
        """
        # 获取尺寸
        widget_width = self.imageLabels.size().width()
        widget_height = self.imageLabels.size().height()
        line_3_width = self.line_3.size().width()
        # 计算尺寸
        labelBefore_width: int = int((widget_width - self.imageLabels_layoutSpacing * 2 - line_3_width) / 2)
        labelAfter_x: int = labelBefore_width + self.imageLabels_layoutSpacing * 2 + line_3_width
        # 调整 labelBefore 大小
        self.labelBefore.resize(labelBefore_width, widget_height)
        # 调整 line_3 位置和大小
        self.line_3.move(labelBefore_width + self.imageLabels_layoutSpacing, 0)
        self.line_3.resize(line_3_width, widget_height)
        # 调整 labelAfter 位置和大小
        self.labelAfter.move(labelAfter_x, 0)
        self.labelAfter.resize(widget_width - labelAfter_x, widget_height)

        # 缩放图片
        self.scale_image(pixmap=self.before_pixmap, label=self.labelBefore)
        self.scale_image(pixmap=self.after_pixmap, label=self.labelAfter)

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

    def show_camera_frame(self, data: dict):
        """
        在 labelBefore 上显示相机画面
        :param data:
        :return:
        """
        frame: np.ndarray = data["frame_data"]
        # camera_info: dict = data["camera_info"]
        # serial_number = camera_info["serial_number"]
        self.before_pixmap = self.show_image(label=self.labelBefore, image=frame)

    def show_detect_frame(self, frame: np.ndarray):
        """
        在 labelAfter 上显示相机画面
        :param frame:
        :return:
        """
        self.after_pixmap = self.show_image(label=self.labelAfter, image=frame)

    def show_detect_result(self, result: bool):
        """
        显示检测结果
        :param result:
        :return:
        """
        if result:
            self.labelDetectionResult.setText("检测结果：正确")
            self.labelDetectionResult.setStyleSheet("font: 75 12pt '微软雅黑'; color: rgb(85, 170, 127);")
        else:
            self.labelDetectionResult.setText("检测结果：错误")
            self.labelDetectionResult.setStyleSheet("font: 75 12pt '微软雅黑'; color: rgb(255, 85, 127);")
        # 设置透明度的值，0.0到1.0，最小值0是透明，1是不透明
        self.opacity.setOpacity(1)
        self.labelDetectionResult.setGraphicsEffect(self.opacity)

    def show_detection(self, result: bool, frame: np.ndarray):
        """
        显示检测结果画面
        :param result:
        :param frame:
        :return:
        """
        self.show_detect_result(result)
        self.show_detect_frame(frame)

    def hide_detection(self):
        """
        隐藏检测结果画面
        :return:
        """
        # 设置透明度的值，0.0到1.0，最小值0是透明，1是不透明
        self.opacity.setOpacity(0)
        self.labelDetectionResult.setGraphicsEffect(self.opacity)
        self.show_detect_frame(self.null_image)

    def resizeEvent(self, event: QResizeEvent):
        self.to_resize()
        return super().resizeEvent(event)

    def show(self):
        """
        显示界面
        :return:
        """
        super().show()
        # 调整尺寸
        self.to_resize()

    def closeEvent(self, event):
        """
        关闭界面事件
        :param event:
        :return:
        """
        self.closeCameraSignal.emit()
        return super().closeEvent(event)
