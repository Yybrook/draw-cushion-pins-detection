import xlrd
import numpy as np
import cv2
from User.config_static import (CF_PART_NUMBER_IGNORE_SYMBOLS, CF_TEACH_REFERENCE_SIDE,
                                CF_COLOR_PINSMAP_PIN, CF_COLOR_PINSMAP_NULL, CF_COLOR_PINSMAP_FREE, CF_COLOR_PINSMAP_DOWEL)


class ExcelReader:
    def __init__(self, rows: int, columns: int, decode_codes: dict):

        self.rows = rows
        self.columns = columns
        self.decode_codes = decode_codes

        self.workbook = None  # excel文件对象
        self.table_index = -1  # OP20文件的索引号
        self.table = None  # OP20工艺卡表格对象

        self.data = dict()  # 获得的数据 其中line为列表

        # 单元格坐标
        # row, column
        self.process_item = (2, 51)  # 工序号
        self.part_item = (2, 8)  # 零件号
        self.line_item = (1, 51)  # 生产线
        self.pins_map_start_item = (17, 7)  # pins_map 中心点

        # # 用于查找rows columns
        # self.pins_map_center_item = (23, 20)     # pins_map 中心点

    def open_file(self, file_path):
        try:
            workbook = xlrd.open_workbook(file_path)
            tables_name = workbook.sheet_names()
            for index, table_name in enumerate(tables_name):
                if table_name.upper().find('OP20') != -1:
                    self.table_index = index
                    self.workbook = workbook
                    self.table = self.workbook.sheet_by_index(self.table_index)
                    self.data = dict()
                    return True, None

            err = "工艺卡不存在含'OP20'的表单"
            return False, err

        except Exception as err:
            err = "打开工艺卡错误，详细[%s]" % err
            return False, err

    def get_part_info(self):
        # 工序
        process = str(self.table.cell_value(rowx=self.process_item[0], colx=self.process_item[1])).upper()
        if process.find('OP20') == -1:
            err = "工序号不等于'OP20'，参考单元格[%d,%d]" % (self.process_item[0] + 1, self.process_item[1] + 1)
            return False, err

        # 零件
        part = str(self.table.cell_value(rowx=self.part_item[0], colx=self.part_item[1])).strip().upper()
        for s in CF_PART_NUMBER_IGNORE_SYMBOLS:
            part = part.replace(s, "")
        if part == '':
            err = "零件号为空，参考单元格[%d,%d]" % (self.part_item[0] + 1, self.part_item[1] + 1)
            return False, err

        # 生产线
        line = str(self.table.cell_value(rowx=self.line_item[0], colx=self.line_item[1])).strip().upper()
        if line == '':
            err = "生产线为空，参考单元格[%d,%d]" % (self.line_item[0] + 1, self.line_item[1] + 1)
            return False, err

        # if decode_lines_callback is not None:
        #     lines = decode_lines_callback(lines_str=line)
        # else:
        #     lines = [line]

        self.data = {"Part": part, "Line": line}
        return True, None

    # @staticmethod
    # def decode_lines(lines_str: str, split_symbol: str = '/') -> list:
    #     if lines_str.find(split_symbol) != -1:
    #         temp = lines_str.split(split_symbol)
    #         lines = [temp[0]]
    #         suffix_list = temp[1:]
    #         prefix = lines_str.split('-')[0]
    #         for suffix in suffix_list:
    #             line = "%s-%s" % (prefix, suffix)
    #             lines.append(line)
    #         return lines
    #     else:
    #         return [lines_str]
    #
    # def get_pins_map_rows_columns(self, row_bias: int = 2, column_bias: int = 2):
    #     """
    #     查找rows columns
    #     实际的rows, columns 需要与excel中的rows, columns 对调
    #     :param row_bias:
    #     :param column_bias:
    #     :return:
    #     """
    #     rows = -1
    #     columns = -1
    #     center_row, center_col = self.pins_map_center_item
    #
    #     for r in reversed(range(center_row)):
    #         symmetry = 2 * center_row - r
    #         if (self.table.cell_value(rowx=r, colx=center_col) == 0 and
    #                 self.table.cell_value(rowx=symmetry, colx=center_col) == 0):
    #             rows = (center_row - r - row_bias) * 2 + 1
    #             break
    #
    #     for c in reversed(range(center_col)):
    #         symmetry = 2 * center_col - c
    #         if (self.table.cell_value(rowx=center_row, colx=c) == 0 and
    #                 self.table.cell_value(rowx=center_row, colx=symmetry) == 0):
    #             columns = (center_col - c - column_bias) * 2 + 1
    #             break
    #
    #     if rows == -1 or columns == -1:
    #         return False
    #     else:
    #         # 对调
    #         self.rows = columns
    #         self.columns = rows
    #         return True

    def get_pins_map(self, pin_color: tuple = CF_COLOR_PINSMAP_PIN, null_color: tuple = CF_COLOR_PINSMAP_NULL,
                     free_color: tuple = CF_COLOR_PINSMAP_FREE, dowel_color: tuple = CF_COLOR_PINSMAP_DOWEL):
        """
        '●' 顶棒
        '○' 孔(可以是孔或顶棒)
        '◎' 定位销
        '×' 禁止放顶棒(必须是孔)
        :return:
        """
        rows = self.columns
        columns = self.rows

        pin_code = self.decode_codes["Pin"]
        null_code = self.decode_codes["Null"]
        dowel_code = self.decode_codes["Dowel"]
        free_code = self.decode_codes.get("Free")

        # 生成numpy数组
        pins_map = np.zeros((rows, columns, 3), np.uint8)

        # 循环表格
        start_row, start_col = self.pins_map_start_item
        end_row, end_col = start_row + rows - 1, start_col + columns - 1

        for y, r in enumerate(range(start_row, end_row + 1)):
            for x, c in enumerate(range(start_col, end_col + 1)):
                v = self.table.cell_value(rowx=r, colx=c)
                # 必须项
                if v == pin_code:
                    pins_map[y, x] = np.array(pin_color, np.uint8)
                elif v == null_code:
                    pins_map[y, x] = np.array(null_color, np.uint8)
                elif v == dowel_code:
                    pins_map[y, x] = np.array(dowel_color, np.uint8)
                # 可选项
                else:
                    if free_color is not None and v == free_code:
                        pins_map[y, x] = np.array(free_color, np.uint8)
                    else:
                        err = "编码超出设定，单元格[{},{}] = '{}'".format(r + 1, c + 1, v)
                        return False, err

        # 旋转numpy
        if CF_TEACH_REFERENCE_SIDE == "RIGHT":
            # 顺时针 90度
            pins_map = cv2.rotate(pins_map, cv2.ROTATE_90_CLOCKWISE)
        else:
            # 逆时针 90度
            pins_map = cv2.rotate(pins_map, cv2.ROTATE_90_COUNTERCLOCKWISE)

        self.data["PinsMap"] = pins_map
        self.data["Rows"] = self.rows
        self.data["Columns"] = self.columns
        return True, None

    def decode_file(self, file_path: str):
        # 打开文件
        result, err = self.open_file(file_path=file_path)
        if not result:
            return False, err

        # 获取 零件号 生产线
        result, err = self.get_part_info()
        if not result:
            return False, err

        # 获取 pins_map
        result, err = self.get_pins_map()
        if not result:
            return False, err

        return True, self.data


if __name__ == '__main__':

    codes = {'Pin': '●', 'Null': '×', 'Free': '○', 'Dowel': '◎'}

    read = ExcelReader(rows=27, columns=13, decode_codes=codes)

    res, data = read.decode_file("../PinsCtrlData/Temp/Cards/11A 809 605 V1.10.xlsx")

    print(res, data)
