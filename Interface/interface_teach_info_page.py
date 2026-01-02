from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import pyqtSignal

from UI.ui_teach_info_page import Ui_Form as Ui_TeachInfoPage

from CameraCore.camera_identity import CameraIdentity

from Utils.database_operator import DatabaseOperator
from User.config_static import CF_PART_NUMBER_IGNORE_SYMBOLS


class InterfaceTeachInfoPage(QWidget, Ui_TeachInfoPage):

    nextSignal = pyqtSignal(dict)
    partChangedSignal = pyqtSignal(str)

    def __init__(self, db_operator: DatabaseOperator):
        super().__init__()

        self.db_operator = db_operator

        self.setupUi(self)  # 初始化窗口

        self.camera_identity: CameraIdentity = CameraIdentity()
        self.camera_location: dict = dict()
        self.part: str = ''

        # 绑定信号
        self.comboBoxPart.currentTextChanged.connect(self.current_part_changed)
        self.comboBoxPart.showPopupSignal.connect(lambda: self.comboBoxPart.set_items(get_items_callback=self.get_parts))

    def next(self):
        # 发送信号
        message = {"Part": self.part}
        self.nextSignal.emit(message)

    def current_part_changed(self, text):
        self.part = text.strip().upper()
        for s in CF_PART_NUMBER_IGNORE_SYMBOLS:
            self.part = self.part.replace(s, "")

        if self.part == "":
            self.buttonNext.setEnabled(False)
        else:
            self.buttonNext.setEnabled(True)

        self.partChangedSignal.emit(self.part)

    def get_parts(self):
        parts = self.db_operator.get_parts(line=self.camera_location["Line"])
        if self.part != "" and self.part not in parts:
            parts.insert(0, self.part)
        return parts

    def init(self, camera_identity: CameraIdentity, camera_location: dict, part: str):

        self.camera_identity = camera_identity
        self.camera_location = camera_location
        self.part = part

        # 初始化 lineEdit
        self.lineEditSerialNumber.setText(self.camera_identity.serial_number)
        self.lineEditUid.setText(self.camera_identity.uid)
        self.lineEditLine.setText(self.camera_location["Line"])
        self.lineEditLocation.setText(self.camera_location["Location"])
        self.lineEditSide.setText(self.camera_location["Side"])
        self.comboBoxPart.setEditText(self.part)
