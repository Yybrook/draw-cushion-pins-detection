from pyodbc import connect
from typing import Optional
from User.config_static import CF_DATABASE_PATH, TB_CAMERAS_IDENTITY, TB_PROCESS_PARAMETERS, TB_PARTS_PINSMAP, TB_DETECTION_RECORDS, TB_SOCKET_CONFIG


class DatabaseOperator:
    def __init__(self, database_path: str = CF_DATABASE_PATH):
        # 链接数据库
        self.conn = connect('Driver={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=%s' % database_path)
        # 创建游标
        self.cursor = self.conn.cursor()

    def create_cursor(self):
        # 创建游标
        self.cursor = self.conn.cursor()

    def close(self, obj: Optional[str] = None):
        if obj is None or obj.lower() == "all":
            # 关闭游标
            self.cursor.close()
            # 关闭链接
            self.conn.close()
        elif obj.lower() == "cursor":
            # 关闭游标
            self.cursor.close()
        elif obj.lower() == "conn":
            # 关闭链接
            self.conn.close()

    @staticmethod
    def assign_where(filter_dict: Optional[dict] = None):
        assignment = ''
        params = list()
        if filter_dict is not None:
            for key, val in filter_dict.items():
                if isinstance(val, str):
                    if val.strip().upper() == "ALL" or val.strip() == "":
                        continue
                    else:
                        if val.strip().upper() == "FALSE":
                            val = False
                        elif val.strip().upper() == "TRUE":
                            val = True

                assignment += '%s=? and ' % key
                params.append(val)
        return assignment[:-5], params

    def get_table_rows(self, table_name: str, filter_dict: Optional[dict] = None) -> int:
        assignment, params = self.assign_where(filter_dict=filter_dict)
        if params:
            sql = 'select count(ID) from %s where %s' % (table_name, assignment)
            self.cursor.execute(sql, params)
        else:
            sql = 'select count(ID) from %s' % (table_name,)
            self.cursor.execute(sql)

        data = self.cursor.fetchall()
        rows = data[0][0]
        return rows

    def get_table_pages(self, table_name: str, page_rows: int, filter_dict: Optional[dict] = None):
        rows = self.get_table_rows(table_name=table_name, filter_dict=filter_dict)
        full_pages, residue_rows = divmod(rows, page_rows)
        pages = full_pages + bool(residue_rows)
        return pages, full_pages, residue_rows

    def select_from_table(self, table_name: str, demand_list: list, filter_dict: Optional[dict] = None, is_fetchall: bool = True,
                          page: int = 0, page_rows: int = -1,
                          order_by: Optional[str] = None, is_desc: bool = True):
        """

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
        if page_rows > 0:
            is_fetchall = True
            if order_by is None:
                order_by = demand_list[0]

        # 排序
        order = ''
        order_temp = ''
        if order_by is not None:
            if order_by not in demand_list:
                demand_list.append(order_by)
            if is_desc:
                order = ' order by %s desc' % (order_by,)
                order_temp = ' order by %s' % (order_by,)
            else:
                order = ' order by %s' % (order_by,)
                order_temp = ' order by %s desc' % (order_by,)

        # 需求
        demand = ""
        for k in demand_list:
            demand += "%s, " % k
        demand = demand[-len(demand): -2]

        # where
        where, where_params = self.assign_where(filter_dict=filter_dict)

        # 不分页
        if page_rows <= 0:
            # 无筛选
            if not where_params:
                sql = 'select %s from %s%s' % (demand, table_name, order)
                self.cursor.execute(sql)
            # 有筛选
            else:
                sql = 'select %s from %s where %s%s' % (demand, table_name, where, order)
                self.cursor.execute(sql, where_params)
        # 分页
        else:
            # 获取页数
            pages, full_pages, residue_rows = self.get_table_pages(table_name=table_name, page_rows=page_rows, filter_dict=filter_dict)
            if pages == 0:
                return list()
            if 0 <= page < full_pages:
                required_rows = page_rows
            elif page == full_pages:
                required_rows = residue_rows
            else:
                return list()

            temp_rows = (page + 1) * page_rows

            # 无筛选
            if not where_params:
                sql = ('select top %d %s from (select top %d %s from %s%s)%s' % (required_rows, demand, temp_rows, demand, table_name, order_temp, order))
                self.cursor.execute(sql)
            # 有筛选
            else:
                sql = ('select top %d %s from (select top %d %s from %s where %s%s)%s' % (required_rows, demand, temp_rows, demand, table_name, where, order_temp, order))
                self.cursor.execute(sql, where_params)

        if is_fetchall:
            data = self.cursor.fetchall()
            res = list()
            for row in data:
                res.append(dict(zip(demand_list, row)))
            return res
        else:
            data = self.cursor.fetchone()
            if data:
                res = dict(zip(demand_list, data))
            else:
                res = dict()
            return res

    def update_table(self, table_name: str, demand_dict: dict, filter_dict: Optional[dict] = None):
        # 需求
        demand = ""
        for k in demand_dict.keys():
            demand += "%s=?, " % k
        demand = demand[-len(demand): -2]
        demand_params = list(demand_dict.values())

        # where
        where, where_params = self.assign_where(filter_dict=filter_dict)

        sql = 'update %s set %s where %s' % (table_name, demand, where)
        params = demand_params + where_params

        self.cursor.execute(sql, params)
        self.conn.commit()

    def insert_to_table(self, table_name: str, demand_dict: dict):
        # 需求
        demand = ""
        demand_interrogation = ""
        for k in demand_dict.keys():
            demand += "%s, " % k
            demand_interrogation += "?, "
        demand = demand[-len(demand): -2]
        demand_interrogation = demand_interrogation[-len(demand_interrogation): -2]
        params = list(demand_dict.values())

        sql = 'insert into %s (%s) values (%s)' % (table_name, demand, demand_interrogation)
        self.cursor.execute(sql, params)
        self.conn.commit()

    def delete_from_table(self, table_name: str, filter_dict: dict):
        # where
        where, where_params = self.assign_where(filter_dict=filter_dict)

        sql = 'delete from %s where %s' % (table_name, where)

        self.cursor.execute(sql, where_params)
        self.conn.commit()

    def verify_camera_existence(self, table_name: str, serial_number: str) -> bool:
        sql = 'select SerialNumber from %s where SerialNumber=?' % (table_name,)
        self.cursor.execute(sql, serial_number)
        data = self.cursor.fetchone()
        if data:
            return True
        else:
            return False

    def verify_part_existence(self, table_name: str, part: str, line: str) -> bool:
        sql = 'select Part from %s where Part=? and Line=?' % (table_name,)
        self.cursor.execute(sql, part, line)
        data = self.cursor.fetchone()
        if data:
            return True
        else:
            return False

    def get_camera_identity(self, demand_list: list, filter_dict: dict):
        return self.select_from_table(table_name=TB_CAMERAS_IDENTITY, demand_list=demand_list, filter_dict=filter_dict, is_fetchall=False)

    def set_camera_identity(self, demand_dict: dict, filter_dict: dict):
        res = self.verify_camera_existence(table_name=TB_CAMERAS_IDENTITY, serial_number=filter_dict['SerialNumber'])
        # 改
        if res:
            self.update_table(table_name=TB_CAMERAS_IDENTITY, demand_dict=demand_dict, filter_dict=filter_dict)
        # 增
        else:
            demand_dict.update(filter_dict)
            self.insert_to_table(table_name=TB_CAMERAS_IDENTITY, demand_dict=demand_dict)

    def delete_camera_identity(self, filter_dict: dict):
        # res = self.verify_camera_existence(table_name=TB_CAMERAS_IDENTITY, serial_number=filter_dict['SerialNumber'])
        # if res:
        self.delete_from_table(table_name=TB_CAMERAS_IDENTITY, filter_dict=filter_dict)

    def set_process_parameters(self, demand_dict: dict, filter_dict: dict):
        res = self.verify_camera_existence(table_name=TB_PROCESS_PARAMETERS, serial_number=filter_dict['SerialNumber'])
        # update
        if res:
            self.update_table(table_name=TB_PROCESS_PARAMETERS, demand_dict=demand_dict, filter_dict=filter_dict)
        # insert
        else:
            demand_dict.update(filter_dict)
            self.insert_to_table(table_name=TB_PROCESS_PARAMETERS, demand_dict=demand_dict)

    def get_process_parameters(self, demand_list: list, filter_dict: dict) -> dict:
        return self.select_from_table(table_name=TB_PROCESS_PARAMETERS, demand_list=demand_list, filter_dict=filter_dict, is_fetchall=False)

    def get_all_process_parameters(self, filter_dict: dict) -> dict:
        demand_list = [
            "P1X", "P1Y", "P2X", "P2Y", "P3X", "P3Y", "P4X", "P4Y",
            "XNumber", "XMini", "XMaxi", "YNumber", "YMini", "YMaxi",
            "ScaleAlpha", "ScaleBeta", "ScaleEnable",
            "GammaConstant", "GammaPower", "GammaEnable",
            "LogConstant", "LogEnable",
            "Thresh", "AutoThresh",
            "EliminatedSpan", "ReservedInterval",
            "ErodeShape", "ErodeKsize", "ErodeIterations",
            "DilateShape", "DilateKsize", "DilateIterations",
            "StripeEnable", "ErodeEnable", "DilateEnable",
            "MinArea", "MaxArea", "MaxRoundness", "MaxDistance"
        ]
        return self.get_process_parameters(demand_list=demand_list, filter_dict=filter_dict)

    def get_parts_pins_map(self, demand_list: list, filter_dict: dict) -> dict:
        return self.select_from_table(table_name=TB_PARTS_PINSMAP, demand_list=demand_list, filter_dict=filter_dict, is_fetchall=False)

    def set_parts_pins_map(self, demand_dict: dict, filter_dict: dict):
        res = self.verify_part_existence(table_name=TB_PARTS_PINSMAP, part=filter_dict['Part'], line=filter_dict['Line'])
        # update
        if res:
            self.update_table(table_name=TB_PARTS_PINSMAP, demand_dict=demand_dict, filter_dict=filter_dict)
        # insert
        else:
            demand_dict.update(filter_dict)
            self.insert_to_table(table_name=TB_PARTS_PINSMAP, demand_dict=demand_dict)

    def delete_parts_pins_map(self, filter_dict: dict):
        # res = self.verify_part_existence(table_name=TB_PARTS_PINSMAP, part=filter_dict['Part'], line=filter_dict['Line'])
        # if res:
        self.delete_from_table(table_name=TB_PARTS_PINSMAP, filter_dict=filter_dict)

    def get_lines(self) -> dict:
        sql = 'select Line, count(*) from %s group by Line order by Line' % (TB_PARTS_PINSMAP,)
        self.cursor.execute(sql)
        data = self.cursor.fetchall()
        lines = dict()
        for d in data:
            lines[d[0]] = d[1]
        return lines

    def get_parts(self, line: str) -> list:
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

    def set_detection_records(self, demand_dict: dict):
        self.insert_to_table(table_name=TB_DETECTION_RECORDS, demand_dict=demand_dict)

    def get_detection_records(self, demand_list: list, filter_dict: dict) -> dict:
        return self.select_from_table(table_name=TB_DETECTION_RECORDS, demand_list=demand_list, filter_dict=filter_dict, is_fetchall=False)

    def delete_detection_records(self, filter_dict: dict):
        self.delete_from_table(table_name=TB_DETECTION_RECORDS, filter_dict=filter_dict)

    def get_all_parts_pins_map(self, demand_list: list, page: int = 0, page_rows: int = -1, filter_dict: Optional[dict] = None) -> list:
        return self.select_from_table(table_name=TB_PARTS_PINSMAP, demand_list=demand_list, filter_dict=filter_dict, page=page, page_rows=page_rows, order_by="ID")

    def get_parts_pins_map_pages(self, page_rows: int, filter_dict: Optional[dict] = None):
        return self.get_table_pages(table_name=TB_PARTS_PINSMAP, page_rows=page_rows, filter_dict=filter_dict)

    def get_all_detection_records(self, demand_list: list, page: int = 0, page_rows: int = -1, filter_dict: Optional[dict] = None) -> list:
        return self.select_from_table(table_name=TB_DETECTION_RECORDS, demand_list=demand_list, filter_dict=filter_dict, page=page, page_rows=page_rows,
                                      order_by="ID", is_desc=False)

    def get_detection_records_pages(self, page_rows: int, filter_dict: Optional[dict] = None):
        return self.get_table_pages(table_name=TB_DETECTION_RECORDS, page_rows=page_rows, filter_dict=filter_dict)

    def get_latest_detection_records(self, demand_list: list, filter_dict: Optional[dict] = None):
        # 降序
        return self.select_from_table(table_name=TB_DETECTION_RECORDS, demand_list=demand_list, filter_dict=filter_dict, is_fetchall=False, order_by="ID", is_desc=True)

    def get_socket_config(self, ip: str):
        return self.select_from_table(table_name=TB_SOCKET_CONFIG, demand_list=["Port", "Auto"], filter_dict={"IP": ip}, is_fetchall=False)

    def set_socket_config(self, ip: str, port: Optional[int], auto: Optional[bool]):
        table_name = TB_SOCKET_CONFIG

        demand_dict = dict()
        if port is not None:
            demand_dict["Port"] = port
        if auto is not None:
            demand_dict["Auto"] = auto

        # 查询ip存在
        sql = 'select IP from %s where IP=?' % (table_name,)
        self.cursor.execute(sql, ip)
        data = self.cursor.fetchone()
        # 改
        if data:
            self.update_table(table_name=table_name, demand_dict=demand_dict, filter_dict={"IP": ip})
        # 增
        else:
            demand_dict["IP"] = ip
            self.insert_to_table(table_name=table_name, demand_dict=demand_dict)


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


if __name__ == "__main__":
    operator = DatabaseOperator(database_path=r"..\PinsCtrlData\Database\pins_ctrl_database.accdb")

    operator.close()
