import cv2
import numpy as np
from typing import Optional, Union
from os import path as os_path
from winreg import OpenKey, QueryValueEx, HKEY_CURRENT_USER
from PIL import Image
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QImage, QPixmap


class Presenter:

    @staticmethod
    def show_ndarray_in_QLabel(image: np.ndarray, label: QLabel, is_rgb: bool = False):
        """"""

        # GRAY to BGR
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            if not is_rgb:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        pixmap = Presenter.ndarray_2_pixmap(image=image, is_rgb=True)
        # 显示图片
        show_width, show_height = Presenter.show_pixmap_in_QLabel(pixmap=pixmap, label=label)
        return pixmap, show_width, show_height

    @staticmethod
    def show_pixmap_in_QLabel(pixmap: QPixmap, label: QLabel, show_width: Optional[int] = None, show_height: Optional[int] = None):
        """

        :param pixmap:
        :param label:
        :param show_width:
        :param show_height:
        :return:
        """
        # 计算显示尺寸
        if show_width is None or show_height is None:
            # 图片尺寸
            image_height = pixmap.height()
            image_width = pixmap.width()

            # 标签尺寸
            label_height = label.size().height()
            label_width = label.size().width()

            # 显示尺寸
            image_ratio = image_width / image_height
            label_ratio = label_width / label_height
            if image_ratio < label_ratio:
                show_height = label_height
                show_width = show_height * image_ratio
            else:
                show_width = label_width
                show_height = show_width / image_ratio
        # 在标签中显示图片
        label.setPixmap(pixmap.scaled(show_width, show_height))

        return show_width, show_height

    @staticmethod
    def pixmap_2_ndarray(pixmap: QPixmap) -> np.ndarray:
        """
        转 pixmap 到 ndarray
        :param pixmap:
        :return:
        """
        image = Image.fromqpixmap(pixmap)
        frame = np.array(image)
        return frame

    @staticmethod
    def ndarray_2_pixmap(image: np.ndarray, is_rgb: bool = False):
        """

        :param image:
        :param is_rgb:
        :return:
        """
        # 图片尺寸
        image_height = image.shape[0]
        image_width = image.shape[1]

        # GRAY
        if image.ndim == 2:
            f = QImage.Format_Indexed8
            # 转换为QImage
            q_image = QImage(image.data, image_width, f)
        # BGR
        else:
            if is_rgb:
                f = QImage.Format_RGB888
            else:
                f = QImage.Format_BGR888
            # 通道数
            channel = image.shape[2]  # 3
            # 转换为QImage
            q_image = QImage(image.data, image_width, image_height, image_width * channel, f)

        # 转换为QPixmap
        pixmap = QPixmap.fromImage(q_image)
        return pixmap

    @staticmethod
    def save_image(image: Union[np.ndarray, QPixmap], image_name: str, parent=None):

        # 获取桌面路径
        key = OpenKey(HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
        desktop = QueryValueEx(key, "Desktop")[0]

        image_path = os_path.join(desktop, image_name)

        path, file_type = QFileDialog.getSaveFileName(parent, "保存图片", image_path, "(*.jpg);;(*.png);;(*.bpm);;(*.npy)")
        if path:
            if file_type == "(*.npy)":
                # 转ndarray
                if isinstance(image, QPixmap):
                    image = Presenter.pixmap_2_ndarray(pixmap=image)
                np.save(path, image)  # 保存为二进制文件
            else:
                if isinstance(image, np.ndarray):
                    cv2.imwrite(path, image)
                else:
                    image.save(path)
