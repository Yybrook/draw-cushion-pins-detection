from sys import argv, exit
from os import remove as os_remove
import numpy as np
from typing import Union
from datetime import datetime
import yaml
import cv2
import argparse

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPixmap

from Interface.Teach.interface_teach import InterfaceTeach

from Utils.database_operator import DatabaseOperator, DATABASE_SYMBOL_ODBC
from Utils.image_presenter import Presenter
# from Utils.serializer import MySerializer
from User.config_static import CF_RUNNING_SEQUENCE_FILE, CF_RUNNING_TEACH_FLAG, CF_DYNAMIC_CONFIG_PATH


class MainTeach:
    def __init__(self, arguments: dict):
        # 解析参数
        self.arguments = self.decode_arguments(arguments)

        # 动态参数
        with open(CF_DYNAMIC_CONFIG_PATH, encoding='ascii', errors='ignore') as f:
            self.dynamic_config = yaml.safe_load(f)

        # 数据库
        self.db_operator = DatabaseOperator(symbol=DATABASE_SYMBOL_ODBC)
        # 连接数据库
        is_connected = self.db_operator.connect(path=self.dynamic_config["access_database_path"])
        if not is_connected:
            raise Exception("open access database failed")

        # 创建Interface实例
        self.interface_teach = InterfaceTeach(
            frame_data=self.arguments["frame_data"],
            part=self.arguments["part"],
            serial_number=self.arguments["serial_number"],
            line=self.arguments["line"],
            location=self.arguments["location"],
            side=self.arguments["side"],
            activate_page=self.arguments["page"],
            db_operator=self.db_operator,
            )

        # 连接信号
        self.interface_teach.closeSignal.connect(lambda: os_remove(self.arguments["file_path"]))
        self.interface_teach.savePictureSignal.connect(lambda message: self.save_image(image=self.interface_teach.process_pixmap, message=message))

    # *********************************  解析参数  ******************************* #
    @staticmethod
    def decode_arguments(arguments: dict) -> dict:
        """
        解析输入的参数
        :param arguments:
        :return:
        """
        # 零件号
        part = arguments.get("part", "XXX")
        # # 相机序列号
        # serial_number = arguments["serial_number"]
        # # 相机位置
        # line = arguments["line"]
        # location = arguments["location"]
        # side = arguments["side"]

        # 激活页
        page = arguments.get("page", "0")
        if not page.isdigit():
            raise Exception("page [{}] is illegal".format(page))
        page = int(page)

        # 图片
        file_path = arguments["file_path"]
        # 图片后缀
        suffix = file_path.split(".")[-1]
        # 读取图片
        if suffix.lower() == "npy":
            frame_data = np.load(file_path)
        elif suffix.lower() == "jpg" or suffix.lower() == "png" or suffix.lower() == "bmp":
            frame_data = cv2.imread(file_path)
        else:
            raise Exception("file type [{}] is illegal".format(suffix))

        arguments["part"] = part
        arguments["page"] = page
        arguments["frame_data"] = frame_data

        return arguments

    def save_image(self, image: Union[np.ndarray, QPixmap], message: dict):
        """
        保存图片
        :param image:
        :param message:
        :return:
        """
        now = datetime.now().strftime('%G%m%d%H%M%S%f')
        image_name = "MyProcessPicture_%s_%s_%s_%s.jpg" % (message["SerialNumber"], message["Part"], message["Line"], now)
        Presenter.save_image(image=image, parent=self.interface_teach, image_name=image_name)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--part", required=True)
    ap.add_argument("-sn", "--serial_number", required=True)
    ap.add_argument("-l", "--line", required=True)
    ap.add_argument("-lo", "--location", required=True)
    ap.add_argument("-s", "--side", required=True)
    ap.add_argument("-f", "--file_path", required=True)
    ap.add_argument("-pg", "--page", default="0", required=False)

    parsed_args = vars(ap.parse_args())

    app = QApplication(argv)

    my_teach = MainTeach(arguments=parsed_args)

    # 显示界面
    my_teach.interface_teach.show()

    ret = app.exec_()

    # 关闭数据库
    my_teach.db_operator.close()

    exit(ret)
