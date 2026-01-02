import cv2
import numpy as np
from typing import Optional
from collections import Counter

from PyQt5.QtWidgets import QMainWindow, QLabel, QMenu, QAction, QGraphicsOpacityEffect, QApplication, QStyle
from PyQt5.QtCore import pyqtSignal, Qt, QPoint
from PyQt5.QtGui import QPixmap, QResizeEvent, QIcon

from CameraCore.camera_identity import CameraIdentity
from UI.ui_grab import Ui_MainWindow as Ui_Grab
from Utils.image_presenter import Presenter
from Utils.messenger import Messenger
from Utils.database_operator import DatabaseOperator
from User.config_static import (CF_NULL_PICTURE, CF_APP_TITLE, CF_APP_ICON,
                                CF_RUNNING_SEQUENCE_FILE, CF_RUNNING_ROOT_FLAG, CF_RUNNING_GRAB_FLAG, CF_RUNNING_TEACH_FLAG,
                                TB_CAMERAS_IDENTITY)


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

    def __init__(self, camera_identity: CameraIdentity, camera_location: dict, db_operator: DatabaseOperator):
        super().__init__()

        self.camera_identity: CameraIdentity = camera_identity  # 相机身份
        self.camera_location: dict = camera_location            # 相机位置信息
        self.db_operator = db_operator                          # 数据库

        self.setupUi(self)  # 初始化窗口

        self.setWindowTitle('%s-Grab' % CF_APP_TITLE)   # 设置窗口标题
        self.setWindowIcon(QIcon(CF_APP_ICON))          # 设置窗口图标

        # 空图片
        self.null_image = cv2.imread(CF_NULL_PICTURE)
        # 原始图片
        self.before_pixmap = None
        self.after_pixmap = None

        self.part = ''

        # 布局
        self.imageLabels_layoutSpacing = 4

        # 设置透明度的值，0.0到1.0，最小值0是透明，1是不透明
        self.opacity = QGraphicsOpacityEffect()
        # 样式
        self.style = QApplication.style()

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

        self.buttonGrab.setIcon(self.style.standardIcon(QStyle.SP_MediaStop))
        self.buttonColse.setIcon(self.style.standardIcon(QStyle.SP_LineEditClearButton))

        # 右键菜单
        self.menu = QMenu()
        # 设置相机参数
        set_action = QAction('设置相机参数', self.menu)
        set_action.setIcon(self.style.standardIcon(QStyle.SP_BrowserReload))
        set_action.triggered.connect(lambda: self.setParametersSignal.emit())
        self.menu.addAction(set_action)
        # 链接图片处理算法
        self.connect_action = QAction('链接图片处理算法', self.menu)
        self.connect_action.setCheckable(True)
        self.connect_action.setChecked(False)
        self.connect_action.toggled.connect(lambda value: self.connectAlgorithmSignal.emit(value))
        self.menu.addAction(self.connect_action)

    def detect(self):
        self.hide_detection()
        self.part = self.comboBoxPart.currentText()
        if self.part != "":
            message = {
                "Part": self.part,
                "SerialNumber": self.camera_identity.serial_number,
                "CameraLocation": self.camera_location
            }
            self.detectSignal.emit(message)

    def teach(self):
        part = self.comboBoxPart.currentText()
        message = {
            "Part": part,
            "SerialNumber": self.camera_identity.serial_number,
            "Uid": self.camera_identity.uid,
            "CameraLocation": self.camera_location
        }
        self.teachSignal.emit(message)

    def part_teach(self):
        part = self.comboBoxPart.currentText()
        message = {
            "Part": part,
            "SerialNumber": self.camera_identity.serial_number,
            "Uid": self.camera_identity.uid,
            "CameraLocation": self.camera_location
        }
        self.partTeachSignal.emit(message)

    def close_camera(self):
        self.close()

    def grab_or_not(self, is_checked: bool):
        self.grabOrNotSignal.emit(is_checked)
        if is_checked:
            self.buttonGrab.setText("停止取流")
            self.buttonGrab.setIcon(self.style.standardIcon(QStyle.SP_MediaStop))
            self.comboBoxPart.setEnabled(True)
            self.current_part_changed(self.comboBoxPart.currentText())
            self.buttonTeach.setEnabled(True)
            self.buttonPartTeach.setEnabled(True)

        else:
            self.buttonGrab.setText("开始取流")
            self.buttonGrab.setIcon(self.style.standardIcon(QStyle.SP_MediaPlay))
            self.comboBoxPart.setEnabled(False)
            self.buttonDetect.setEnabled(False)
            self.buttonTeach.setEnabled(False)
            self.buttonPartTeach.setEnabled(False)

    def current_part_changed(self, text: str):
        if text == "":
            self.buttonDetect.setEnabled(False)
        else:
            self.buttonDetect.setEnabled(True)

    def show_left_click_menu_in_before(self, pos: QPoint):
        res = self.db_operator.verify_camera_existence(table_name=TB_CAMERAS_IDENTITY, serial_number=self.camera_identity.serial_number)
        if res:
            # self.menu.actions()[1].setEnabled(True)
            self.connect_action.setEnabled(True)
        else:
            # self.menu.actions()[1].setEnabled(False)
            self.connect_action.setEnabled(False)
        global_pos = self.labelBefore.mapToGlobal(pos)
        self.menu.exec(global_pos)

    def show_left_click_menu_in_after(self, pos: QPoint):
        menu = QMenu()

        save_action = QAction('保存图片', menu)
        save_action.setIcon(self.style.standardIcon(QStyle.SP_DialogSaveButton))

        message = {"SerialNumber": self.camera_identity.serial_number,
                   "Uid": self.camera_identity.uid,
                   "Part": self.part,
                   "Line": self.camera_location["Line"]}

        save_action.triggered.connect(lambda: self.savePictureSignal.emit(message))

        menu.addAction(save_action)

        global_pos = self.labelAfter.mapToGlobal(pos)
        menu.exec(global_pos)

    def get_parts(self) -> list:
        line = self.camera_location["Line"]
        return self.db_operator.get_parts(line)

    def resizeEvent(self, event: QResizeEvent):
        self.to_resize()
        return super().resizeEvent(event)

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

    def show(self):
        """
        显示界面
        :return:
        """
        # 设置title
        # 相机[*] 产线[#] 位置[$]
        title = self.title.text()
        if self.camera_identity.serial_number != "":
            title = title.replace("*", self.camera_identity.serial_number)
        line = self.camera_location.get("Line")
        if line != "":
            title = title.replace("#", line)
        location = self.camera_location.get("Location")
        if location != "":
            title = title.replace("$", location)
        self.title.setText(title)

        self.hide_detection()  # 显示图片

        super().show()

        self.to_resize()  # 调整尺寸

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
        frame: np.ndarray = data["FrameData"]
        # serial_number = data["SerialNumber"]

        self.before_pixmap = self.show_image(label=self.labelBefore, image=frame)

    def show_detect_frame(self, frame: np.ndarray):
        """
        在 labelAfter 上显示相机画面
        :param frame:
        :return:
        """

        self.after_pixmap = self.show_image(label=self.labelAfter, image=frame)

    def show_detect_result(self, result: bool):
        # 设置透明度的值，0.0到1.0，最小值0是透明，1是不透明
        self.opacity.setOpacity(1)
        if result:
            self.labelDetectionResult.setText("检测结果：正确")
            self.labelDetectionResult.setStyleSheet("font: 75 12pt '微软雅黑'; color: rgb(85, 170, 127);")
        else:
            self.labelDetectionResult.setText("检测结果：错误")
            self.labelDetectionResult.setStyleSheet("font: 75 12pt '微软雅黑'; color: rgb(255, 85, 127);")
        self.labelDetectionResult.setGraphicsEffect(self.opacity)

    def show_detection(self, result: bool, frame: np.ndarray):
        self.show_detect_result(result)
        self.show_detect_frame(frame)

    def hide_detection(self):
        # 设置透明度的值，0.0到1.0，最小值0是透明，1是不透明
        self.opacity.setOpacity(0)
        self.labelDetectionResult.setGraphicsEffect(self.opacity)
        self.show_detect_frame(self.null_image)

    @staticmethod
    def verify_sequence() -> bool:
        """
        判断 running sequence
        :return:
        """
        with open(CF_RUNNING_SEQUENCE_FILE, 'r', encoding='utf-8') as sequence_file:
            sequence_flag = sequence_file.readline()

        if int(sequence_flag) > CF_RUNNING_GRAB_FLAG:
            flag_list = [int(i) for i in sequence_flag]
            flag_dict = Counter(flag_list)
            grab_num = flag_dict.get(CF_RUNNING_GRAB_FLAG, 0)
            teach_num = flag_dict.get(CF_RUNNING_TEACH_FLAG, 0)

            if teach_num > 0:
                message = {"level": 'WARNING', "title": '警告', "text": '请先关闭次级界面！',
                           "informative_text": '', "detailed_text": ''}
                Messenger.show_QMessageBox(widget=None, message=message, QLabelMinWidth=200)
                return False
            else:
                content = ''
                for i in range(grab_num - 1):
                    content += str(CF_RUNNING_GRAB_FLAG)
                for i in range(teach_num):
                    content += str(CF_RUNNING_TEACH_FLAG)

                with open(CF_RUNNING_SEQUENCE_FILE, 'w', encoding='utf-8') as sequence_file:
                    sequence_file.write(content)
        else:
            with open(CF_RUNNING_SEQUENCE_FILE, 'w', encoding='utf-8') as sequence_file:
                sequence_file.write(str(CF_RUNNING_ROOT_FLAG))

        return True

    def closeEvent(self, event):
        """
        关闭界面事件
        :param event:
        :return:
        """
        if not self.verify_sequence():
            event.ignore()
            return

        self.closeCameraSignal.emit()
        return super().closeEvent(event)
