import sys
from typing import Optional, Union
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox, QWidget, QApplication
from Utils.logger import Logger


MESSAGE_MUTE = -1
MESSAGE_STDOUT = 0
MESSAGE_BAR = 1
MESSAGE_BOX = 2
MESSAGE_LOG = 3


def show_message(attributes):
    """
    显示消息 装饰器
    :param attributes:
    :return:
    """
    def decorator(func):
        def _decorator(self, *args, **kwargs):
            message = func(self, *args, **kwargs)

            # 显示消息
            message_callback = kwargs.get("message_callback")
            if message_callback is not None:
                # 获取类属性
                if isinstance(attributes, str):
                    values = {
                        attributes: self.__dict__.get(attributes)
                    }
                elif isinstance(attributes, list) or isinstance(attributes, tuple):
                    values = dict()
                    for attr in attributes:
                        values[attr] = self.__dict__.get(attr)
                elif isinstance(attributes, dict):
                    values = attributes
                else:
                    values = dict()
                message_callback(message=message, **values)

        return _decorator

    return decorator


def show_message_static(func):
    """
    显示消息 装饰器
    :param func:
    :return:
    """
    def _decorator(*args, **kwargs):
        message = func(*args, **kwargs)
        # 显示消息
        message_callback = kwargs.get("message_callback")
        if message_callback is not None:
            message_callback(message=message)

    return _decorator


class Messenger(Logger):

    @staticmethod
    def show(show_type: Union[int, str], **kwargs):
        """

        :param show_type:
        :param kwargs:      0 -> message, camera_identity
                            2 -> message, widget, camera_identity, init, buttons
                            3 ->
        :return:
        """
        if show_type == MESSAGE_MUTE or (isinstance(show_type, str) and show_type.upper() == "MUTE"):
            return
        elif show_type == MESSAGE_STDOUT or (isinstance(show_type, str) and show_type.upper() == "STDOUT"):
            if "message" not in kwargs:
                kwargs["message"] = dict()
            Messenger.print(**kwargs)
        elif show_type == MESSAGE_BOX or (isinstance(show_type, str) and show_type.upper() == "BOX"):
            if "message" not in kwargs:
                kwargs["message"] = dict()
            if "widget" not in kwargs:
                kwargs["widget"] = None
            Messenger.show_message_box(**kwargs)
        elif show_type == MESSAGE_LOG or (isinstance(show_type, str) and show_type.upper() == "LOG"):
            if "message" not in kwargs:
                kwargs["message"] = dict()
            Messenger.output_log(**kwargs)
        else:
            raise Exception("illegal message grade")

    @staticmethod
    def print(message: dict, **kwargs):
        """

        :param message:
        :param kwargs:      camera_identity = kwargs["camera_identity"]
        :return:
        """
        if not message:
            return

        title = message.get("title", "")
        text = message.get("text", "")
        informative_text = message.get("informative_text", "")
        detailed_text = message.get("detailed_text", "")

        now = Messenger.get_time()

        content = "{text}\t{informative_text}\t{detailed_text}".format(
            text=text,
            informative_text=informative_text,
            detailed_text=detailed_text
        )

        prefix = "[{now}]\t[{title}]".format(now=now, title=title)

        if "camera_identity" in kwargs:
            camera_identity = kwargs["camera_identity"]
            identity = Messenger.get_camera_identity(camera_identity)
            output = "{prefix}\t[{identity}]\t{content}".format(
                prefix=prefix,
                identity=identity,
                content=content
            )
        else:
            output = "{prefix}\t{content}".format(
                prefix=prefix,
                content=content
            )

        # print(output)
        # 发送的字符串 带有 \r\n 转义字符
        sys.stdout.write("{}\n".format(output))
        # 刷新缓冲区，用于立即发送
        sys.stdout.flush()

    @staticmethod
    def show_message_box(widget: Optional[QWidget], message: dict, **kwargs):
        """
        输出消息
        :param widget:
        :param message:
        :param kwargs:      buttons = kwargs.get("buttons")
                            init = kwargs.get("init")
                            camera_identity = kwargs["camera_identity"]
        :return:
        """
        if not message:
            return

        level = message.get("level")
        title = message.get("title", "")
        text = message.get("text", "")
        informative_text = message.get("informative_text", "")
        detailed_text = message.get("detailed_text", "")

        # 实例化消息框
        if widget is None and kwargs.get("init"):
            QApplication(sys.argv)
            message_box = QMessageBox()
        elif widget is not None:
            message_box = QMessageBox(widget)
        else:
            message_box = QMessageBox()

        # 设置图标
        if level.upper() == "CRITICAL" or level.upper() == "ERROR":
            icon = QMessageBox.Critical
        elif level.upper() == "WARNING":
            icon = QMessageBox.Warning
        elif level.upper() == "INFO":
            icon = QMessageBox.Information
        elif level.upper() == "QUESTION":
            icon = QMessageBox.Question
        else:
            icon = QMessageBox.NoIcon
        message_box.setIcon(icon)

        # 设置标题
        if title.strip() != "":
            message_box.setWindowTitle(title)

        # 设置文本
        if text.strip() != "":
            message_box.setText(text)

        # 设置 消息文本
        if informative_text.strip() != "":
            message_box.setInformativeText(informative_text)

        # 设置 详细文本
        now = Messenger.get_time()
        detailed = "[{}]".format(now)
        if "camera_identity" in kwargs:
            camera_identity = kwargs["camera_identity"]
            identity = Messenger.get_camera_identity(camera_identity)
            detailed += "\n[{}]".format(identity)
        detailed += "\n{}".format(detailed_text)
        message_box.setDetailedText(detailed)

        # # 用于更改消息框尺寸
        # QLabelMinWidth = kwargs.get("QLabelMinWidth")
        # QLabelMinHeight = kwargs.get("QLabelMinHeight")
        #
        # style = "QLabel{"
        # if QLabelMinWidth is not None:
        #     style += "min-width:%dpx; " % QLabelMinWidth
        # if QLabelMinHeight is not None:
        #     style += "min-height:%dpx; " % QLabelMinHeight
        #
        # style += "}"
        # message_box.setStyleSheet(style)

        buttons = kwargs.get("buttons")
        # 如没有buttons，那界面中只有OK，返回值1024
        # role  {"OK": QMessageBox.AcceptRole}
        # AcceptRole = 0
        # ActionRole = 3
        # ApplyRole = 8
        # DestructiveRole = 2
        # HelpRole = 4
        # InvalidRole = -1
        # NoRole = 6
        # RejectRole = 1
        # ResetRole = 7
        # YesRole = 5

        if isinstance(buttons, dict):
            for i, (key, val) in enumerate(buttons.items()):
                button = message_box.addButton(key, val)
                # 设置默认按钮
                if i == 0:
                    message_box.setDefaultButton(button)

        # 以窗口级别的模态对话框弹出
        ret = message_box.exec_()

        # # 设置窗口图标
        # msgBox.setWindowIcon()
        # # 设置按钮
        # msgBox.setStandardButtons()

        return ret

    @staticmethod
    def output_log(message: dict, **kwargs):
        """
        输出日志
        :param message:
        :param kwargs:  camera_identity = kwargs["camera_identity"]
        :return:
        """
        level = message.get("level")
        level = "DEBUG" if level.upper() == "QUESTION" else level
        # title = message.get("title", "")
        text = message.get("text", "")
        informative_text = message.get("informative_text", "")
        detailed_text = message.get("detailed_text", "")

        output = "{text}\t{informative_text}\t{detailed_text}".format(
            text=text,
            informative_text=informative_text,
            detailed_text=detailed_text
        )
        if "camera_identity" in kwargs:
            camera_identity = kwargs["camera_identity"]
            identity = Messenger.get_camera_identity(camera_identity)
            output = "[{identity}]\t{output}".format(
                identity=identity,
                output=output
            )
        Messenger.logging(level=level, message=output)

    @staticmethod
    def get_camera_identity(camera_identity) -> str:
        """
        获取相机身份
        :param camera_identity:
        :return:
        """
        address = camera_identity.address
        identity = address
        return identity

    @staticmethod
    def get_time(accurate: bool = False) -> str:
        if accurate:
            fmt = '%G-%m-%d %H:%M:%S:%f'
        else:
            fmt = '%G-%m-%d %H:%M:%S'
        now = datetime.now().strftime(fmt)
        return now
