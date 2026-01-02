from PyQt5.QtCore import QThread, pyqtSignal

from Utils.messenger import Messenger


class ImageBufferListener(QThread):

    # 信号
    showImageBufferSignal = pyqtSignal(dict)

    def __init__(self, conn):
        super().__init__()

        # parent_pipe
        self.conn = conn

        # 线程退出标志
        self.to_exit = False

    def run(self):
        self.listen()

    def listen(self):
        """
        循环查询
        :return:
        """
        while True:

            self.usleep(10)

            if self.to_exit:
                break

            try:
                # 判断管道中是否有数据
                if not self.conn.poll():
                    continue
                # 接收数据
                data = self.conn.recv()
                # 解析数据
                if isinstance(data, dict):
                    if "SerialNumber" in data and "FrameData" in data:
                        self.showImageBufferSignal.emit(data)

            except Exception as err:
                level = 'ERROR'
                title = '错误'
                text = '子管道意外关闭！'
                informative_text = str(err)
                detailed_text = ''
                Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)

        level = 'INFO'
        title = '信息'
        text = '进程结束！'
        informative_text = ''
        detailed_text = ''
        Messenger.print(widget=None, level=level, title=title, text=text, informative_text=informative_text, detailed_text=detailed_text)
