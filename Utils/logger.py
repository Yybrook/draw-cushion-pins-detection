import logging
from typing import Optional, Union


class Logger:
    # DEBUG < INFO < WARNING < ERROR < CRITICAL

    def __int__(self, name: str, fh_level: Union[int, str, None], ch_level: Union[int, str, None], filename: Optional[str], formatter: Optional[logging.Formatter]):
        """

        :param name:
        :param fh_level:
        :param ch_level:
        :param filename:
        :param formatter:
        :return:
        """
        # 创建 logger
        self.logger = logging.getLogger(name)

        # 输出到控制台等级
        if ch_level is not None:
            self.ch_level = ch_level
        else:
            self.ch_level = logging.DEBUG

        # 写入日志文件等级
        if fh_level is not None:
            self.fh_level = fh_level
        else:
            self.fh_level = logging.DEBUG

        # 日志文件路径
        self.filename = filename

        # formatter
        if formatter is not None:
            self.formatter = formatter
        else:
            self.formatter = logging.Formatter('[%(asctime)s]\t[%(name)s]\t[%(levelname)s]\t[### %(message)s ***]\t[%(filename)s -> %(funcName)s]\t'
                                               '[Process: (%(process)d / %(processName)s)]\t[Thread: (%(thread)d / %(threadName)s)]',
                                               datefmt="%Y-%m-%d %H:%M:%S")

        # 初始化 logger
        self.init_logger()

    def init_logger(self):
        """
        初始化 logger
        :return:
        """
        # 设置 logger 级别
        # logger.setLevel(logging.DEBUG)

        # 创建 handler，用于输出到控制台
        ch = logging.StreamHandler()
        # 设置 handler 级别
        ch.setLevel(self.ch_level)
        # 给 handler 添加 formatter
        ch.setFormatter(self.formatter)
        # 给 logger 添加 handler
        self.logger.addHandler(ch)

        if isinstance(self.filename, str) and self.filename != "":
            # 创建 handler，用于写入日志文件
            fh = logging.FileHandler(self.filename, encoding='utf-8')
            # 设置 handler 级别
            fh.setLevel(self.fh_level)
            # 给 handler 添加 formatter
            fh.setFormatter(self.formatter)
            # 给 logger 添加 handler
            self.logger.addHandler(fh)

    def output(self, level: str, message: str):
        """
        输出 log
        :param level:
        :param message:
        :return:
        """
        if level.upper() == "CRITICAL":
            self.logger.critical(message)
        elif level.upper() == "ERROR":
            self.logger.error(message)
        elif level.upper() == "WARNING":
            self.logger.warning(message)
        elif level.upper() == "INFO":
            self.logger.info(message)
        elif level.upper() == "DEBUG":
            self.logger.debug(message)
        else:
            pass
