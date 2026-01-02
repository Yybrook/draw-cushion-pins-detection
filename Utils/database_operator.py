from abc import ABC, abstractmethod
from typing import Optional, Union
import pymssql
import sqlite3
#  windows
import pyodbc
from Utils.messenger import Messenger, show_message_static

from User.config_static import TB_CAMERAS_IDENTITY, TB_PROCESS_PARAMETERS, TB_PARTS_PINSMAP, TB_DETECTION_RECORDS, TB_SOCKET_CONFIG

INJECTION_FLAG_MSSQL = "%s"
INJECTION_FLAG_ODBC = "?"
INJECTION_FLAG_SQLITE = "?"

DATABASE_SYMBOL_MSSQL = 'MSSQL'
DATABASE_SYMBOL_ODBC = 'ODBC'
DATABASE_SYMBOL_SQLITE = 'SQLITE'


def with_try(func):
    """
    try 装饰器
    :param func:
    :return:
    """
    def _decorator(self, *args, **kwargs):
        try:
            obj = func(self, *args, **kwargs)
            successful_callback = kwargs.get('successful_callback')
            if successful_callback is not None:
                successful_callback()
            if obj is None:
                return True
            else:
                return obj
        except Exception as err:
            failed_callback = kwargs.get('failed_callback')
            if failed_callback is not None:
                self.show_failure(error=err, func_name=func.__name__, message_callback=failed_callback)
            return False
    return _decorator


def with_rollback(func):
    """
    rollback 装饰器
    :param func:
    :return:
    """
    def _decorator(self, *args, **kwargs):
        try:
            obj = func(self, *args, **kwargs)
            successful_callback = kwargs.get('successful_callback')
            if successful_callback is not None:
                successful_callback()
            if obj is None:
                return True
            else:
                return obj
        except Exception as err:
            # 获取连接
            connection = self.__dict__.get("connection")
            # 回滚
            if connection is not None:
                connection.rollback()

            failed_callback = kwargs.get('failed_callback')
            if failed_callback is not None:
                self.show_failure(error=err, func_name=func.__name__, message_callback=failed_callback)
            return False
    return _decorator


class DbConnector(ABC):

    def __init__(self):
        super().__init__()

    @abstractmethod
    def create_conn(self, **kwargs):
        """
        创建连接
        :param kwargs:
        :return:
        """
        pass

    def __call__(self, **kwargs):
        return self.create_conn(**kwargs)


class MssqlConnector(DbConnector):
    def __init__(self):
        super().__init__()
        self.symbol = DATABASE_SYMBOL_MSSQL
        self.injection_flag = INJECTION_FLAG_MSSQL

    def create_conn(self, server: str, user, password: str, database: str, port: str, timeout: int = 3, **kwargs):
        """
        创建连接
        :param server:
        :param user:
        :param password:
        :param database:
        :param port:
        :param timeout:
        :param kwargs:      successful_callback = kwargs.get('successful_callback')
                            failed_callback = kwargs.get('failed_callback')
        :return:
        """
        conn = pymssql.connect(
            server=server,
            user=user,
            password=password,
            database=database,
            port=port,
            charset='utf8',
            tds_version='7.0',
            timeout=timeout,
        )
        return conn


# windows
class OdbcConnector(DbConnector):
    def __init__(self):
        super().__init__()
        self.symbol = DATABASE_SYMBOL_ODBC
        self.injection_flag = INJECTION_FLAG_ODBC

    def create_conn(self, path: str, **kwargs):
        """
        创建连接
        :param path:
        :param kwargs:      successful_callback = kwargs.get('successful_callback')
                            failed_callback = kwargs.get('failed_callback')
        :return:
        """
        conn = pyodbc.connect('Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s' % (path,))
        return conn


class SqliteConnector(DbConnector):
    def __init__(self):
        super().__init__()
        self.symbol = DATABASE_SYMBOL_SQLITE
        self.injection_flag = INJECTION_FLAG_SQLITE

    def create_conn(self, path: str, **kwargs):
        """
        创建连接
        :param path:
        :param kwargs:      successful_callback = kwargs.get('successful_callback')
                            failed_callback = kwargs.get('failed_callback')
        :return:
        """
        # 打开 或 创建数据库文件
        conn = sqlite3.connect(database=path)
        return conn


class DbOperator:
    def __init__(self, symbol: str):
        # 创建数据库连接器
        if symbol == DATABASE_SYMBOL_MSSQL:
            self.connector = MssqlConnector()
        elif symbol == DATABASE_SYMBOL_ODBC:
            self.connector = OdbcConnector()
        elif symbol == DATABASE_SYMBOL_SQLITE:
            self.connector = SqliteConnector()
        else:
            raise Exception('illegal database symbol')

        # 数据库标志
        self.symbol = self.connector.symbol
        # 注入标志
        self.injection_flag = self.connector.injection_flag
        # 连接
        self.connection = None
        # 游标
        self.cursor = None

    def connect(self, **kwargs) -> bool:
        """
        连接数据库
        :param kwargs: mssql ->  server: str, user, password: str, database: str, port: str, timeout: int = 3
                       odbc ->   path: str
                       sqlite -> path: str
                                 successful_callback = kwargs.get('successful_callback')
                                 failed_callback = kwargs.get('failed_callback')
        :return:
        """
        # 创建连接
        try:
            self.connection = self.connector(**kwargs)
        except Exception as err:
            self.connection = None
            failed_callback = kwargs.get('failed_callback')
            if failed_callback is not None:
                failed_callback(error=err)
            return False

        # 创建游标
        try:
            self.cursor = self.connection.cursor()
        except Exception as err:
            # 关闭游标
            self.connection.close()
            self.connection = None
            self.cursor = None
            failed_callback = kwargs.get('failed_callback')
            if failed_callback is not None:
                failed_callback(error=err)
            return False

        successful_callback = kwargs.get('successful_callback')
        if successful_callback is not None:
            successful_callback()
        return True

    def close(self) -> bool:
        """
        断开数据库连接
        :return:
        """
        try:
            self.cursor.close()  # 关闭游标
            self.connection.close()  # 关闭连接
            return True
        except:
            return False
        finally:
            self.connection = None
            self.cursor = None

    def is_exited(self):
        """
        数据库 连接 和 游标 是否存在
        :return:
        """
        return False if (self.connection is None or self.cursor is None) else True

    def assign_where(self, filter_dict: Optional[dict] = None) -> tuple:
        """
        定义 sql 语句中的 where
        :param filter_dict:
        :return:
        """
        assignment = ''
        params = list()
        if filter_dict:
            for key, val in filter_dict.items():
                if isinstance(val, str):
                    # val = val.strip().upper()
                    if val.strip().upper() == "ALL" or val.strip().upper() == "":
                        continue
                    else:
                        if val.strip().upper() == "FALSE":
                            val = False
                        elif val.strip().upper() == "TRUE":
                            val = True
                assignment += '{}={} and '.format(key, self.injection_flag)
                params.append(val)
            assignment = assignment[:-5]
        return assignment, tuple(params)

    def assign_demand(self, demand_dict: dict) -> tuple:
        """
        组织 insert 需求
        :param demand_dict:
        :return:
        """
        # 需求
        demand_key = ""
        demand_interrogation = ""

        for k in demand_dict.keys():
            demand_key += "{}, ".format(k)
            demand_interrogation += "{}, ".format(self.injection_flag)
        demand_key = demand_key[-len(demand_key): -2]
        demand_interrogation = demand_interrogation[-len(demand_interrogation): -2]
        params = tuple(demand_dict.values())

        return demand_key, demand_interrogation, params

    def get_table_rows(self, table_name: str, filter_dict: Optional[dict] = None) -> int:
        """
        获取表格行数
        :param table_name:
        :param filter_dict:
        :return:
        """
        if filter_dict:
            assignment, params = self.assign_where(filter_dict=filter_dict)
            sql = 'select count(ID) from {} where {}'.format(table_name, assignment)
            self.cursor.execute(sql, params)
        else:
            sql = 'select count(ID) from {}'.format(table_name, )
            self.cursor.execute(sql)

        data = self.cursor.fetchall()
        rows = data[0][0]
        return rows

    def get_table_pages(self, table_name: str, page_rows: int, filter_dict: Optional[dict] = None) -> tuple:
        """
        按 rows 获取 页数
        :param table_name:
        :param page_rows:
        :param filter_dict:
        :return:                页数，整页，零散行数
        """
        rows = self.get_table_rows(table_name=table_name, filter_dict=filter_dict)
        full_pages, residue_rows = divmod(rows, page_rows)  # 除
        pages = full_pages + bool(residue_rows)
        return pages, full_pages, residue_rows

    def get_table_columns_name(self, table_name: str) -> list:
        """
        获得表格所有列名
        :param table_name:
        :return:
        """
        if self.symbol == DATABASE_SYMBOL_MSSQL:
            sql = 'SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = {}'.format(self.injection_flag)
            self.cursor.execute(sql, table_name)
            data = self.cursor.fetchall()
            columns = [d[0] for d in data]
            return columns
        elif self.symbol == DATABASE_SYMBOL_ODBC:
            sql = 'SELECT TOP 1 * FROM {}'.format(table_name)
            data = self.cursor.execute(sql)
            data = data.description
            columns = [d[0] for d in data]
            return columns
        elif self.symbol == DATABASE_SYMBOL_SQLITE:
            sql = "SELECT name FROM pragma_table_info('{}')".format(table_name)
            self.cursor.execute(sql)
            data = self.cursor.fetchall()
            columns = [d[0] for d in data]
            return columns
        else:
            raise Exception('illegal database symbol')

    def select_from_table(self, table_name: str, demand_list: Optional[list], filter_dict: Optional[dict] = None,
                          is_fetchall: bool = True,
                          page: int = 0, page_rows: int = -1,
                          order_by: Optional[str] = None, is_desc: bool = True) -> Union[list, dict]:
        """
        从表格中筛选
        :param table_name:
        :param demand_list:
        :param filter_dict:
        :param is_fetchall:
        :param page:
        :param page_rows:
        :param order_by:    排序
        :param is_desc:     降序
        :return:
        """
        # 需求
        if demand_list:
            demand = ""
            for k in demand_list:
                demand += "{}, ".format(k)
            demand = demand[-len(demand): -2]
        else:
            demand = "*"
            demand_list = self.get_table_columns_name(table_name)

        # 分页
        required_rows = 0  # 需求页数
        temp_rows = 0  # 当前页前（包含当前页）的总行数
        if page_rows > 0:
            # 获取总页数
            pages, full_pages, residue_rows = self.get_table_pages(
                table_name=table_name,
                page_rows=page_rows,
                filter_dict=filter_dict
            )
            if pages == 0:
                return list()
            # 计算需求页数
            if 0 <= page < full_pages:
                required_rows = page_rows
            elif page == full_pages:
                required_rows = residue_rows
            else:
                return list()
            # 计算当前页前（包含当前页）的总行数
            temp_rows = (page + 1) * page_rows
            # 查找所有
            is_fetchall = True
            # 排序
            if not order_by:
                order_by = demand_list[0]

        # 排序
        order = ''
        order_temp = ''
        if order_by:
            if order_by not in demand_list:
                demand_list.append(order_by)
            if is_desc:
                order = ' order by {} desc'.format(order_by)
                order_temp = ' order by {}'.format(order_by)
            else:
                order = ' order by {}'.format(order_by)
                order_temp = ' order by {} desc'.format(order_by)

        # 不分页,无筛选
        if page_rows <= 0 and not filter_dict:
            sql = 'select {} from {}{}'.format(demand, table_name, order)
            self.cursor.execute(sql)
        # 不分页,有筛选
        elif page_rows <= 0 and filter_dict:
            where, where_params = self.assign_where(filter_dict=filter_dict)
            sql = 'select {} from {} where {}{}'.format(demand, table_name, where, order)
            self.cursor.execute(sql, where_params)
        # 分页,无筛选
        elif page_rows > 0 and not filter_dict:
            sql = ('select top {} {} from (select top {} {} from {}{}){}'.format(required_rows, demand, temp_rows, demand, table_name, order_temp, order))
            self.cursor.execute(sql)
        # 分页,有筛选
        else:
            where, where_params = self.assign_where(filter_dict=filter_dict)
            sql = ('select top {} {} from (select top {} {} from {} where {}{}){}'.format(required_rows, demand, temp_rows, demand, table_name, where, order_temp, order))
            self.cursor.execute(sql, where_params)

        # 查找所有
        if is_fetchall:
            data = self.cursor.fetchall()
            res = list()
            for row in data:
                res.append(dict(zip(demand_list, row)))
            return res
        # 查找第一条
        else:
            data = self.cursor.fetchone()
            if data:
                res = dict(zip(demand_list, data))
            else:
                res = dict()
            return res

    def update_table(self, table_name: str, demand_dict: dict, filter_dict: dict):
        """
        更新表格
        :param table_name:
        :param demand_dict:
        :param filter_dict:
        :return:
        """
        # 需求
        demand = ""
        for k in demand_dict.keys():
            demand += "{}={}, ".format(k, self.injection_flag)
        demand = demand[-len(demand): -2]
        demand_params = tuple(demand_dict.values())

        # where
        where, where_params = self.assign_where(filter_dict=filter_dict)

        sql = 'update {} set {} where {}'.format(table_name, demand, where)
        params = demand_params + where_params

        self.cursor.execute(sql, params)
        self.connection.commit()

    def insert_to_table(self, table_name: str, demand: Union[dict, list, tuple]):
        """
        向表格中插入
        :param table_name:
        :param demand:
        :return:
        """
        # 字典
        if isinstance(demand, dict):
            demand_key, demand_interrogation, params = self.assign_demand(demand)
            sql = 'insert into {} ({}) values ({})'.format(table_name, demand_key, demand_interrogation)
            self.cursor.execute(sql, params)
        # 列表
        else:
            demand_key, demand_interrogation, p = self.assign_demand(demand[0])
            params = [p]
            for d in demand[1:]:
                p = tuple(d.values())
                params.append(p)

            sql = 'insert into {} ({}) values ({})'.format(table_name, demand_key, demand_interrogation)
            self.cursor.executemany(sql, params)
        self.connection.commit()

    def delete_from_table(self, table_name: str, filter_dict: Optional[dict]):
        """
        从表格中删除
        :param table_name:
        :param filter_dict:
        :return:
        """
        if filter_dict:
            where, where_params = self.assign_where(filter_dict=filter_dict)
            sql = 'delete from {} where {}'.format(table_name, where)
            self.cursor.execute(sql, where_params)
        # 删除所有
        else:
            sql = 'delete from {}'.format(table_name)
            self.cursor.execute(sql)
        self.connection.commit()

    def insert_or_update(self, table_name: str, demand_dict: dict, filter_dict: dict):
        # 查找是否存在
        res = self.select_from_table(
            table_name=table_name,
            demand_list=list(filter_dict.keys()),
            filter_dict=filter_dict,
            is_fetchall=False
        )
        # 改
        if res:
            self.update_table(
                table_name=table_name,
                demand_dict=demand_dict,
                filter_dict=filter_dict
            )
        # 增
        else:
            demand_dict.update(filter_dict)
            self.insert_to_table(
                table_name=table_name,
                demand=demand_dict
            )


class DatabaseOperator(DbOperator):
    def __init__(self, symbol: str):
        super().__init__(symbol=symbol)

    @staticmethod
    @show_message_static
    def show_failure(error: str, func_name: str, **kwargs):
        """
        显示失败信息
        :param error:
        :param func_name:
        :param kwargs:
        :return:
        """
        message = {
            "level": 'ERROR',
            "title": '错误',
            "text": '操作数据库失败！',
            "informative_text": '函数[{}]'.format(func_name),
            "detailed_text": error
        }
        return message

    def verify_camera_existence(self, table_name: str, serial_number: str) -> bool:
        data = self.select_from_table(
            table_name=table_name,
            demand_list=["SerialNumber",],
            filter_dict={"SerialNumber": serial_number},
            is_fetchall=False,
        )
        return bool(data)

    def verify_part_existence(self, table_name: str, part: str, line: str) -> bool:
        data = self.select_from_table(
            table_name=table_name,
            demand_list=["Part", ],
            filter_dict={"Part": part, "Line": line},
            is_fetchall=False,
        )
        return bool(data)

    @with_try
    def get_camera_identity(self, demand_list: list, filter_dict: dict, is_fetchall: bool = False, **kwargs) -> Union[dict, list]:
        """
        获取 camera identity
        :param demand_list:
        :param filter_dict:
        :param is_fetchall:
        :param kwargs:
        :return:
        """
        return self.select_from_table(
            table_name=TB_CAMERAS_IDENTITY,
            demand_list=demand_list,
            filter_dict=filter_dict,
            is_fetchall=is_fetchall
        )

    @with_rollback
    def set_camera_identity(self, demand_dict: dict, filter_dict: dict, **kwargs):
        """
        设置 camera identity
        :param demand_dict:
        :param filter_dict:
        :param kwargs:
        :return:
        """
        self.insert_or_update(
            table_name=TB_CAMERAS_IDENTITY,
            demand_dict=demand_dict,
            filter_dict=filter_dict,
        )

    @staticmethod
    def map_camera_identity_to_database(station: str, sequence: str, amount: int) -> int:
        pass

    @with_rollback
    def delete_camera_identity(self, filter_dict: dict, **kwargs):
        """
        删除 camera_identity
        :param filter_dict:
        :param kwargs:
        :return:
        """
        self.delete_from_table(
            table_name=TB_CAMERAS_IDENTITY,
            filter_dict=filter_dict
        )

    @with_rollback
    def set_process_parameters(self, demand_dict: dict, filter_dict: dict, **kwargs):
        """
        设置处理参数
        :param demand_dict:
        :param filter_dict:
        :return:
        """
        self.insert_or_update(
            table_name=TB_PROCESS_PARAMETERS,
            demand_dict=demand_dict,
            filter_dict=filter_dict,
        )

    @with_try
    def get_process_parameters(self, demand_list: list, filter_dict: dict, **kwargs) -> dict:
        """
        获取处理参数
        :param demand_list:
        :param filter_dict:
        :param kwargs:
        :return:
        """
        return self.select_from_table(
            table_name=TB_PROCESS_PARAMETERS,
            demand_list=demand_list,
            filter_dict=filter_dict,
            is_fetchall=False
        )

    @with_try
    def get_all_process_parameters(self, filter_dict: dict, **kwargs) -> dict:
        """
        获取所有处理参数
        :param filter_dict:
        :param kwargs:
        :return:
        """
        # demand_list = [
        #     "P1X", "P1Y", "P2X", "P2Y", "P3X", "P3Y", "P4X", "P4Y",
        #     "XNumber", "XMini", "XMaxi", "YNumber", "YMini", "YMaxi",
        #     "ScaleAlpha", "ScaleBeta", "ScaleEnable",
        #     "GammaConstant", "GammaPower", "GammaEnable",
        #     "LogConstant", "LogEnable",
        #     "Thresh", "AutoThresh",
        #     "EliminatedSpan", "ReservedInterval",
        #     "ErodeShape", "ErodeKsize", "ErodeIterations",
        #     "DilateShape", "DilateKsize", "DilateIterations",
        #     "StripeEnable", "ErodeEnable", "DilateEnable",
        #     "MinArea", "MaxArea", "MaxRoundness", "MaxDistance"
        # ]
        demand_list = [
            "P1X", "P1Y", "P2X", "P2Y", "P3X", "P3Y", "P4X", "P4Y",
            "HLower", "HUpper", "SLower", "SUpper", "VLower", "VUpper",
            "OpenKernelSize", "OpenIterations",
            "HLower_2", "HUpper_2", "SLower_2", "SUpper_2", "VLower_2", "VUpper_2",
            "OpenKernelSize_2", "OpenIterations_2",
            "BilateralFilterD", "BilateralFilterSigmaColor", "BilateralFilterSigmaSpace",
            "MaskRegionDirection", "MaskRegionRatio", "SuperGreenMaskRegion",
            "XNumber", "XMini", "XMaxi", "YNumber", "YMini", "YMaxi",
            "SectionShift", "SectionMeanThreshold",
            # "ScaleAlpha", "ScaleBeta", "ScaleEnable",
            # "GammaConstant", "GammaPower", "GammaEnable",
            # "LogConstant", "LogEnable",
            # "Thresh", "AutoThresh",
            # "EliminatedSpan", "ReservedInterval",
            # "ErodeShape", "ErodeKsize", "ErodeIterations",
            # "DilateShape", "DilateKsize", "DilateIterations",
            # "StripeEnable", "ErodeEnable", "DilateEnable",
            # "MinArea", "MaxArea", "MaxRoundness", "MaxDistance"
        ]
        return self.get_process_parameters(
            demand_list=demand_list,
            filter_dict=filter_dict,
            **kwargs
        )

    @with_try
    def get_parts_pins_map(self, demand_list: list, filter_dict: dict, **kwargs) -> dict:
        """
        获取 parts_pins_map
        :param demand_list:
        :param filter_dict:
        :return:
        """
        return self.select_from_table(
            table_name=TB_PARTS_PINSMAP,
            demand_list=demand_list,
            filter_dict=filter_dict,
            is_fetchall=False,
        )

    @with_rollback
    def set_parts_pins_map(self, demand_dict: dict, filter_dict: dict, **kwargs):
        """
        设置 parts_pins_map
        :param demand_dict:
        :param filter_dict:
        :param kwargs:
        :return:
        """
        self.insert_or_update(
            table_name=TB_PARTS_PINSMAP,
            demand_dict=demand_dict,
            filter_dict=filter_dict,
        )

    @with_rollback
    def delete_parts_pins_map(self, filter_dict: dict, **kwargs):
        """
        删除 parts_pins_map
        :param filter_dict:
        :param kwargs:
        :return:
        """
        self.delete_from_table(table_name=TB_PARTS_PINSMAP, filter_dict=filter_dict)

    @with_try
    def get_lines(self, **kwargs) -> dict:
        """
        获取所有生产线
        :return:
        """
        sql = 'select Line, count(*) from %s group by Line order by Line' % (TB_PARTS_PINSMAP,)
        self.cursor.execute(sql)
        data = self.cursor.fetchall()
        lines = dict()
        for d in data:
            lines[d[0]] = d[1]
        return lines

    @with_try
    def get_parts(self, line: str, **kwargs) -> list:
        """
        获取零件号
        :param line:
        :return:
        """
        if line == "ALL" or line == "" or line == " ":
            sql = 'select distinct Part from %s order by Part' % (TB_PARTS_PINSMAP,)
            self.cursor.execute(sql)
        else:
            sql = 'select distinct Part from %s where Line=? order by Part' % (TB_PARTS_PINSMAP,)
            self.cursor.execute(sql, line)
        data = self.cursor.fetchall()
        parts = list()
        for d in data:
            parts.append(d[0])
        return parts

    @with_rollback
    def set_detection_records(self, demand_dict: dict, **kwargs):
        """
        设置 检测记录
        :param demand_dict:
        :return:
        """
        self.insert_to_table(table_name=TB_DETECTION_RECORDS, demand=demand_dict)

    @with_try
    def get_detection_records(self, demand_list: list, filter_dict: dict, **kwargs) -> dict:
        return self.select_from_table(
            table_name=TB_DETECTION_RECORDS,
            demand_list=demand_list,
            filter_dict=filter_dict,
            is_fetchall=False
        )

    @with_rollback
    def delete_detection_records(self, filter_dict: dict, **kwargs):
        self.delete_from_table(table_name=TB_DETECTION_RECORDS, filter_dict=filter_dict)

    @with_try
    def get_all_parts_pins_map(self, demand_list: list, page: int = 0, page_rows: int = -1, filter_dict: Optional[dict] = None, **kwargs) -> list:
        return self.select_from_table(
            table_name=TB_PARTS_PINSMAP,
            demand_list=demand_list,
            filter_dict=filter_dict,
            page=page,
            page_rows=page_rows,
            order_by="ID"
        )

    @with_try
    def get_parts_pins_map_pages(self, page_rows: int, filter_dict: Optional[dict] = None, **kwargs):
        return self.get_table_pages(
            table_name=TB_PARTS_PINSMAP,
            page_rows=page_rows,
            filter_dict=filter_dict
        )

    @with_try
    def get_all_detection_records(self, demand_list: list, page: int = 0, page_rows: int = -1, filter_dict: Optional[dict] = None, **kwargs) -> list:
        return self.select_from_table(
            table_name=TB_DETECTION_RECORDS,
            demand_list=demand_list,
            filter_dict=filter_dict,
            page=page,
            page_rows=page_rows,
            order_by="ID",
            is_desc=False
        )

    @with_try
    def get_detection_records_pages(self, page_rows: int, filter_dict: Optional[dict] = None, **kwargs):
        return self.get_table_pages(table_name=TB_DETECTION_RECORDS, page_rows=page_rows, filter_dict=filter_dict)

    @with_try
    def get_latest_detection_records(self, demand_list: list, filter_dict: Optional[dict] = None, **kwargs):
        # 降序
        return self.select_from_table(
            table_name=TB_DETECTION_RECORDS,
            demand_list=demand_list,
            filter_dict=filter_dict,
            is_fetchall=False,
            order_by="ID",
            is_desc=True
        )

    @with_try
    def get_socket_config(self, ip: str, **kwargs):
        return self.select_from_table(
            table_name=TB_SOCKET_CONFIG,
            demand_list=["Port", "Auto"],
            filter_dict={"IP": ip},
            is_fetchall=False
        )

    @with_rollback
    def set_socket_config(self, ip: str, port: Optional[int], auto: Optional[bool], **kwargs):
        table_name = TB_SOCKET_CONFIG

        demand_dict = dict()
        if port is not None:
            demand_dict["Port"] = port
        if auto is not None:
            demand_dict["Auto"] = auto

        self.insert_or_update(
            table_name=TB_PARTS_PINSMAP,
            demand_dict=demand_dict,
            filter_dict={"IP": ip},
        )


def get_lines_with_all(db_operator: DatabaseOperator) -> list:
    lines = db_operator.get_lines()
    lines = sorted(list(lines.keys()))
    lines.insert(0, "ALL")
    return lines


def get_parts_with_all(db_operator: DatabaseOperator, line: str) -> list:
    parts = db_operator.get_parts(line=line)
    parts = sorted(parts)
    parts.insert(0, "ALL")
    return parts


if __name__ == '__main__':

    db_odbc = DatabaseOperator(symbol=DATABASE_SYMBOL_ODBC)

    print(db_odbc.connect(
        path=r"D:\02_Creativity\02_Projects\PinsErrorProof\pins-error-proof\Software\Pins-Ctrl-RGB\PinsCtrlData\Database\pins_ctrl_database.accdb",
    ))

    print(db_odbc.get_camera_identity(
        demand_list=list(),
        filter_dict=dict(),
        is_fetchall=True,
        failed_callback=Messenger.print
    ))

    db_odbc.close()
