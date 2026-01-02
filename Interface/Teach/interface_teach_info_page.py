from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal

from UI.Teach.ui_teach_info_page import Ui_Form as Ui_TeachInfoPage

from CameraCore.camera_identity import CameraIdentity

from Utils.database_operator import DatabaseOperator
from User.config_static import CF_PART_NUMBER_IGNORE_SYMBOLS


class InterfaceTeachInfoPage(QWidget, Ui_TeachInfoPage):

    nextSignal = pyqtSignal(dict)
    partChangedSignal = pyqtSignal(str)

    def __init__(self, db_operator: DatabaseOperator):
        super().__init__()

        # 数据库
        self.db_operator = db_operator

        self.part = ""
        self.serial_number = ""
        self.line = ""
        self.location = ""
        self.side = ""

        # 初始化窗口
        self.setupUi(self)

        # 绑定信号
        self.comboBoxPart.currentTextChanged.connect(self.current_part_changed)
        self.comboBoxPart.showPopupSignal.connect(lambda: self.comboBoxPart.set_items(get_items_callback=self.get_parts))

    def next(self):
        """
        下一步按键
        :return:
        """
        # 发送信号
        message = {"Part": self.part}
        self.nextSignal.emit(message)

    def current_part_changed(self, text):
        """
        下拉框 改变零件号
        :param text:
        :return:
        """
        self.part = text.strip().upper()
        for s in CF_PART_NUMBER_IGNORE_SYMBOLS:
            self.part = self.part.replace(s, "")

        self.buttonNext.setEnabled(bool(self.part))

        self.partChangedSignal.emit(self.part)

    def get_parts(self):
        """
        下拉框 获取该生产线所有零件号
        :return:
        """
        parts = self.db_operator.get_parts(line=self.line)
        if self.part != "" and self.part not in parts:
            parts.insert(0, self.part)
        return parts

    def init(self, part: str, serial_number: str, line: str, location: str, side: str):
        """
        初始化 info 页面v
        :param part:
        :param serial_number:
        :param line:
        :param location:
        :param side:
        :return:
        """
        self.part = part
        self.serial_number = serial_number
        self.line = line
        self.location = location
        self.side = side

        # 初始化 lineEdit
        self.lineEditSerialNumber.setText(self.serial_number)
        self.lineEditLine.setText(self.line)
        self.lineEditLocation.setText(self.location)
        self.lineEditSide.setText(self.side)
        self.comboBoxPart.setEditText(self.part)
