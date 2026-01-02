import logging


# DEBUG<INFO<WARNING<ERROR<CRITICAL

# 创建一个logger
logger = logging.getLogger('mylogger')
# logger.setLevel(logging.DEBUG)

# 创建一个handler，用于写入日志文件
fh = logging.FileHandler('logTest.log', mode='a', encoding='utf-8')
fh.setLevel(logging.INFO)

# 创建一个handler，用于输出到控制台
# ch = logging.StreamHandler()
# ch.setLevel(logging.ERROR)

# 定义handler的输出格式（formatter）
# formatter = logging.Formatter('%(asctime)s\t%(name)s\t%(levelname)s\t'
#                               '%(filename)s\t%(funcName)s\t%(lineno)d\t%(message)s\t'
#                               '%(extra)s\t'
#                               '%(processName)s\t%(process)d\t%(thread)d\t%(threadName)s',
#                               datefmt="%Y-%m-%d %H:%M:%S")
formatter = logging.Formatter('%(asctime)s\t%(levelname)s[%(message)s]\t'
                              'file[%(filename)s]; func[%(funcName)s]; line[%(lineno)d]\t',

                              # '%(processName)s\t%(process)d\t%(thread)d\t%(threadName)s',
                              datefmt="%Y-%m-%d %H:%M:%S")

# 给handler添加formatter
fh.setFormatter(formatter)
# ch.setFormatter(formatter)

# 给logger添加handler
logger.addHandler(fh)
# logger.addHandler(ch)

# # 额外信息
# extra_info = {"extra": "TempTest"}
#
#
# def outputLog():
#     logger.debug('debug message', extra=extra_info)
#     logger.info('info message', extra=extra_info)
#     logger.warning('warning message', extra=extra_info)
#     logger.error('error message', extra=extra_info)
#     logger.critical('critical message', extra=extra_info)
#
#
# outputLog()

logger.debug('debug message')
logger.info('info message')
logger.warning('warning message')
logger.error('error message')
logger.critical('critical message')
