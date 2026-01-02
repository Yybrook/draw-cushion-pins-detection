import logging
from typing import Union


class Logger:
    # DEBUG < INFO < WARNING < ERROR < CRITICAL

    _config = {
        "format": (
            '[%(asctime)s]\t'
            '[%(name)s]\t'  # the name of logger
            '[%(levelname)s]\t'
            '%(message)s\t'
            # '[%(filename)s|%(funcName)s|%(lineno)d]\t'
            # '[Process: (%(process)d / %(processName)s)]\t'
            # '[Thread: (%(thread)d / %(threadName)s)]'
        ),

        "datefmt": "%Y-%m-%d %H:%M:%S",
    }

    @staticmethod
    def init_logger(level: Union[int, str], filename: str):
        """
        初始化 logging
        :param level:
        :param filename:
        :return:
        """
        logging.basicConfig(
            level=level,
            filename=filename,
            format=Logger._config["format"],
            datefmt=Logger._config["datefmt"],
            # stream=sys.stdout
        )

    @staticmethod
    def logging(level: str, message: str):
        """
        输出 log
        :param level:
        :param message:
        :return:
        """
        if level.upper() == "CRITICAL":
            logging.critical(message)
        elif level.upper() == "ERROR":
            logging.error(message)
        elif level.upper() == "WARNING":
            logging.warning(message)
        elif level.upper() == "INFO":
            logging.info(message)
        elif level.upper() == "DEBUG":
            logging.debug(message)
        else:
            raise Exception("illegal logger level")
