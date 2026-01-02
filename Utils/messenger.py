from typing import Optional
from datetime import datetime
from sys import argv
from PyQt5.QtWidgets import QMessageBox, QWidget, QApplication


class Messenger:
    @staticmethod
    def print(*args, **kwargs):

        if "message" in kwargs:
            message = kwargs.get("message")
        else:
            message = kwargs

        if "text" not in message:
            return

        level = message.get("level")
        title = message.get("title")
        text = message.get("text")
        informative_text = message.get("informative_text")
        detailed_text = message.get("detailed_text")

        print("[Level]{}, [title]{}, [text]{}, [informative]{}, [detailed]{}".format(level, title, text, informative_text, detailed_text))

    @staticmethod
    def show_QMessageBox(widget: Optional[QWidget], *args, **kwargs):
        """
        输出消息
        :param widget:
        :param args:
        :param kwargs:
        :return:
        """

        if "message" in kwargs:
            message = kwargs.get("message")
        else:
            message = kwargs

        if "text" not in message:
            return

        level = message.get("level")
        title = message.get("title")
        text = message.get("text")
        informative_text = message.get("informative_text")
        detailed_text = message.get("detailed_text")

        # 实例化消息框
        if widget is None:
            if kwargs.get("init"):
                app = QApplication(argv)
            msgBox = QMessageBox()
        else:
            msgBox = QMessageBox(widget)

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
        msgBox.setIcon(icon)

        # 设置标题
        if title != "" and title is not None:
            msgBox.setWindowTitle(title)

        # 设置文本
        msgBox.setText(text)

        # 设置 消息文本
        if informative_text != "" and informative_text is not None:
            msgBox.setInformativeText(informative_text)

        # 设置 详细文本
        now: str = datetime.now().strftime('%G-%m-%d %H:%M:%S:%f')  # 当前时间
        if detailed_text != "" and detailed_text is not None:
            detailed_text = "[%s]\r\n%s" % (now, detailed_text)
        else:
            detailed_text = "[%s]" % (now,)
        msgBox.setDetailedText(detailed_text)

        # 用于更改消息框尺寸
        QLabelMinWidth = kwargs.get("QLabelMinWidth")
        QLabelMinHeight = kwargs.get("QLabelMinHeight")

        style = "QLabel{"
        if QLabelMinWidth is not None:
            style += "min-width:%dpx; " % QLabelMinWidth
        if QLabelMinHeight is not None:
            style += "min-height:%dpx; " % QLabelMinHeight

        style += "}"
        msgBox.setStyleSheet(style)

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

        if buttons is not None and isinstance(buttons, dict):
            for i, (key, val) in enumerate(buttons.items()):
                button = msgBox.addButton(key, val)
                # 设置默认按钮
                if i == 0:
                    msgBox.setDefaultButton(button)

        # 以窗口级别的模态对话框弹出
        ret = msgBox.exec_()

        # # 设置窗口图标
        # msgBox.setWindowIcon()
        # # 设置按钮
        # msgBox.setStandardButtons()

        # # 使用 addButton() 方法添加自定义按钮
        # button_ok = msgBox.addButton('确认', QMessageBox.AcceptRole)
        # button_quit = msgBox.addButton('退出', QMessageBox.RejectRole)
        # button_ignore = msgBox.addButton("忽略", QMessageBox.DestructiveRole)
        # # 设置默认按钮
        # msgBox.setDefaultButton(button_quit)
        # ret = msgBox.exec_()
        # if ret == QMessageBox.AcceptRole:
        #     pass
        # elif ret == QMessageBox.RejectRole:
        #     pass
        # elif ret == QMessageBox.RejectRole:
        #     pass

        return ret
