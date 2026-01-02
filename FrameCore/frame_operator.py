from typing import Optional, Union
import numpy as np
import cv2
import math
from numba import jit
from json import dumps
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from scipy.signal import savgol_filter, argrelextrema
from scipy.interpolate import make_interp_spline
from findpeaks import findpeaks
from pandas import DataFrame

from User.config_static import (CF_COLOR_PINSMAP_PIN, CF_COLOR_PINSMAP_NULL, CF_TEACH_REFERENCE_SIDE,
                                CF_COLOR_KEYSTONE_POINT, CF_COLOR_KEYSTONE_LINE, CF_COLOR_DIVISION_VERTICAL_LINE, CF_COLOR_DIVISION_HORIZONTAL_LINE,
                                CF_COLOR_CONTOURS_CIRCLE, CF_COLOR_ERROR_PINS, CF_COLOR_ERROR_NULL,
                                CF_COLOR_COLOR_REGION_LINE)
from Utils.serializer import MySerializer

MORPH_RECT = 0
MORPH_CROSS = 1
MORPH_ELLIPSE = 2


class FrameOperator:

    @staticmethod
    def sort_vertexes(vertexes: Union[np.ndarray, list]) -> Optional[np.ndarray]:
        """
        对矩形的四个顶点位置进行排序，左上->右上->右下->左下
        :param vertexes:
        :return:
        """
        if isinstance(vertexes, list):
            vertexes = np.array(vertexes, np.float32)
        else:
            vertexes = vertexes.astype(np.float32)

        # 非矩形顶点
        if vertexes.shape != (4, 2):
            return None

        # # 方法一
        # x_sum_y = rect_contour.sum(axis=1)
        # lt = rect_contour[np.argmin(x_sum_y)]  # 左上 -> 0
        # rb = rect_contour[np.argmax(x_sum_y)]  # 右下 -> 2
        #
        # y_diff_x = np.diff(rect_contour, axis=1)
        # rt = rect_contour[np.argmin(y_diff_x)]  # 右上 -> 1
        # lb = rect_contour[np.argmax(y_diff_x)]  # 左下 -> 3

        # # 方法二
        # y方向上排序
        sorted_in_y = np.argsort(vertexes[:, 1:2], axis=0)
        # x方向上比较
        if vertexes[sorted_in_y[2][0]][0] < vertexes[sorted_in_y[3][0]][0]:
            lb = sorted_in_y[2][0]
            rb = sorted_in_y[3][0]
        else:
            rb = sorted_in_y[2][0]
            lb = sorted_in_y[3][0]
        if vertexes[sorted_in_y[0][0]][0] < vertexes[sorted_in_y[1][0]][0]:
            lt = sorted_in_y[0][0]
            rt = sorted_in_y[1][0]
        else:
            rt = sorted_in_y[0][0]
            lt = sorted_in_y[1][0]

        sorted_vertexes = vertexes[[lt, rt, rb, lb], :]

        return sorted_vertexes

    @staticmethod
    def perspective_transform(frame: np.ndarray, vertexes: Union[np.ndarray, list]) -> np.ndarray:
        """
        透视变换
        :param frame
        :param vertexes:
        :return:    图片，（宽，高）
        """
        # 对矩形的四个顶点进行排序
        sorted_vertexes = FrameOperator.sort_vertexes(vertexes=vertexes)
        if sorted_vertexes is None:
            return frame

        # 定义目标画布尺寸
        # 获得x方向和y方向的差值，并取绝对值
        # sub = np.absolute(np.diff(sorted_vertexes, axis=0, prepend=sorted_vertexes[-1:, :]))
        sub = np.diff(sorted_vertexes, axis=0, prepend=sorted_vertexes[-1:, :])
        # 计算距离
        dis = np.hypot(sub[:, 0], sub[:, 1])
        # 计算平均宽度、高度
        target_width = int((dis[1] + dis[3]) / 2)
        target_height = int((dis[0] + dis[2]) / 2)
        # 目标画布尺寸
        target_vertexes = np.array([[0, 0],
                                    [target_width - 1, 0],
                                    [target_width - 1, target_height - 1],
                                    [0, target_height - 1]],
                                   np.float32)

        # 计算转换矩阵
        # 第一个参数是校正前的四个角点坐标，第二个参数是校正后的四个角点坐标
        perspective_matrix = cv2.getPerspectiveTransform(sorted_vertexes, target_vertexes)
        # 完成透视变换
        perspective_frame = cv2.warpPerspective(frame, perspective_matrix, (target_width, target_height))

        return perspective_frame

    @staticmethod
    def draw_point(frame: np.ndarray, point: tuple, radius: int, text,
                   color: tuple = CF_COLOR_KEYSTONE_POINT, thickness: int = 2,
                   font=cv2.FONT_HERSHEY_SIMPLEX, font_scale: int = 2,
                   draw_line: bool = True, draw_text: bool = True) -> np.ndarray:
        """
        画点
        :param frame:
        :param point:
        :param radius:
        :param text:
        :param color:
        :param thickness:
        :param font:
        :param font_scale:
        :param draw_line:
        :param draw_text:
        :return:
        """
        # 复制
        copy = frame.copy()
        # 画圈
        cv2.circle(copy, point, radius=radius, color=color, thickness=-1, lineType=cv2.LINE_AA)
        x, y = point
        # 画线
        if draw_line:
            span = radius * 2
            pt1 = (x - span, y - span)
            pt2 = (x + span, y - span)
            pt3 = (x + span, y + span)
            pt4 = (x - span, y + span)
            cv2.line(copy, pt1, pt3, color=color, thickness=thickness, lineType=cv2.LINE_AA)
            cv2.line(copy, pt2, pt4, color=color, thickness=thickness, lineType=cv2.LINE_AA)
        if draw_text:
            gap = radius * 3
            pt = (x + gap, y - gap)
            text = "P%d" % (text + 1,)
            cv2.putText(copy, text, pt, fontFace=font, fontScale=font_scale, color=color, thickness=thickness, lineType=cv2.LINE_AA)
        return copy

    @staticmethod
    def draw_vertexes(frame: np.ndarray, vertexes: Union[np.ndarray, list],
                      color: tuple = CF_COLOR_KEYSTONE_LINE, thickness: int = 2, radius: int = 6) -> np.ndarray:
        """
        画四边形顶点
        :param frame:
        :param vertexes:
        :param color:
        :param thickness:
        :param radius:
        :return:
        """
        if isinstance(vertexes, list):
            vertexes = np.array(vertexes, np.int32)
        # 非矩形顶点
        if vertexes.shape != (4, 2):
            return frame

        # 复制
        if frame.ndim == 2:
            copy = cv2.cvtColor(src=frame, code=cv2.COLOR_GRAY2BGR)
        else:
            copy = frame.copy()

        # 画多边形
        cv2.polylines(copy, [vertexes], isClosed=True, color=color, thickness=thickness, lineType=cv2.LINE_AA)
        # 画点
        for i, pt in enumerate(vertexes.tolist()):
            copy = FrameOperator.draw_point(copy, tuple(pt), radius=radius, text=i)
        return copy

    @staticmethod
    def binarization_transform(frame: np.ndarray, scale_alpha: float, scale_beta: float, gamma_c: float, gamma_power: float, log_c: float, thresh: int,
                               scale_enable: bool = True, gamma_enable: bool = False, log_enable: bool = False, auto_thresh: bool = False):

        copy = frame.copy()

        # 滤波
        # copy = cv2.blur(copy, (5, 5))
        copy = cv2.GaussianBlur(copy, (5, 5), 1)
        # copy = cv2.medianBlur(copy, 5)

        # 线性变换
        if scale_enable:
            copy = cv2.convertScaleAbs(copy, alpha=scale_alpha, beta=scale_beta)

        # 伽马变换
        if gamma_enable:
            copy = FrameOperator.convert_gamma(copy, c=gamma_c, gamma=gamma_power)

        # 对数变换
        if log_enable:
            copy = FrameOperator.convert_log(copy, c=log_c)
        # 灰度图
        gray = copy

        # 根据灰度图自动获取thresh
        if auto_thresh:
            # 计算直方图
            x, hist = FrameOperator.calculate_hist(gray)
            # 平滑曲线
            smooth_x, smooth_hist = FrameOperator.smooth_hist(x=x, hist=hist)
            # 找波谷
            valleys_x, _, _, _ = FrameOperator.find_valleys_and_peaks(x=smooth_x, hist=smooth_hist, whitelist=['valley'])
            # 找参考值
            ref_thresh = FrameOperator.calculate_reference_thresh(valleys_x, _, _, _)

            if ref_thresh is not None:
                thresh = ref_thresh

        # 二值化
        _, binarization = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
        return binarization, gray

    @staticmethod
    def convert_gamma(frame: np.ndarray, c: float, gamma: float):
        """
        伽马变换
        :param frame:
        :param c:
        :param gamma:
        :return:
        """
        # 归一化，注意255.0得采用浮点数
        norm = frame / 255.0
        # 伽马变换原理：power(x, y) 函数，计算每个像素点的值x 的 γ 次方，0<γ<1为变亮，γ＞1为变暗
        frame = c * np.power(norm, gamma) * 255.0
        # 设定数据类型
        frame = frame.astype(np.uint8)
        return frame

    @staticmethod
    def convert_log(frame: np.ndarray, c: float):
        """
        对数变换
        :param frame:
        :param c:
        :return:
        """
        frame = c * np.log1p(frame)
        frame = frame.astype(np.uint8)
        frame = cv2.normalize(frame, None, 0, 255, cv2.NORM_MINMAX)
        return frame

    @staticmethod
    def denoise_transform(frame: np.ndarray, eliminated_span: int, reserved_interval: int,
                          erode_shape: Union[int, str], erode_ksize: int, erode_iterations: int,
                          dilate_shape: Union[int, str], dilate_ksize: int, dilate_iterations: int,
                          stripe_enable: bool = True, erode_enable: bool = True, dilate_enable: bool = True):
        """
        消除噪音
        :param frame:
        :param eliminated_span:
        :param reserved_interval:
        :param erode_shape:
        :param erode_ksize:
        :param erode_iterations:
        :param dilate_shape:
        :param dilate_ksize:
        :param dilate_iterations:
        :param stripe_enable:
        :param erode_enable:
        :param dilate_enable:
        :return:
        """
        if stripe_enable:
            # 消除黑色条纹状噪声
            frame = FrameOperator.stripe_denoise(frame=frame, eliminated_span=eliminated_span, reserved_interval=reserved_interval)
        if erode_enable or dilate_enable:
            # 取反
            frame = cv2.bitwise_not(frame, frame)
            if erode_enable:
                # 腐蚀
                erode_kernel = FrameOperator.set_kernel(shape_flag=erode_shape, ksize=erode_ksize)
                frame = cv2.erode(frame, kernel=erode_kernel, iterations=erode_iterations)
            if dilate_enable:
                # 膨胀
                dilate_kernel = FrameOperator.set_kernel(shape_flag=dilate_shape, ksize=dilate_ksize)
                frame = cv2.dilate(frame, kernel=dilate_kernel, iterations=dilate_iterations)
            # 取反
            frame = cv2.bitwise_not(frame, frame)
        return frame

    @staticmethod
    @jit(nopython=True)
    def stripe_denoise(frame: np.ndarray,
                       eliminated_span: int, reserved_interval: int,
                       eliminated_pixel: int = 0, replaced_pixel: int = 255):
        """
        去噪 消除黑色/白色条纹状噪声
        :param frame:
        :param eliminated_span:      要消除像素的跨度
        :param reserved_interval:    两段要消除像素之间的最大间隔像素数量
        :param eliminated_pixel:     要消除像素值,黑色为0,白色为255
        :param replaced_pixel:       想替换像素值,黑色为0,白色为255
        :return:
        """
        eliminated_count: int = 0
        reserved_count: int = 0
        total_reserved_count: int = 0

        # 转2维图片
        if frame.ndim != 2:
            copy = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            copy = frame.copy()

        # 获取图片尺寸
        height, width = copy.shape

        # 遍历图片
        for h in range(height):
            for w in range(width):
                if copy[h, w] <= eliminated_pixel:
                    eliminated_count += 1
                    if reserved_count != 0:
                        total_reserved_count += reserved_count
                        reserved_count = 0
                else:
                    if eliminated_count != 0:
                        reserved_count += 1
                        if reserved_count >= reserved_interval:
                            if eliminated_count >= eliminated_span:
                                total_reserved_count += reserved_count
                                for p in range(w - eliminated_count - total_reserved_count + 1,
                                               w - reserved_count + 1):
                                    copy[h, p] = replaced_pixel
                            eliminated_count = 0
                            reserved_count = 0
                            total_reserved_count = 0
            # 每行最后
            if eliminated_count >= eliminated_span:
                total_reserved_count += reserved_count
                for p in range(width - eliminated_count - total_reserved_count,
                               width - reserved_count):
                    copy[h, p] = replaced_pixel
            eliminated_count = 0
            reserved_count = 0
            total_reserved_count = 0
        return copy

    @staticmethod
    def set_kernel(shape_flag: Union[int, str], ksize: int):
        """
        返回指定形状和尺寸的结构元素
        :param shape_flag:   0 -> 矩形：MORPH_RECT, 1 -> 交叉形：MORPH_CROSS, 2 -> 椭圆形：MORPH_ELLIPSE
        :param ksize:
        :return:
        """
        """
        矩形：MORPH_RECT
        交叉形：MORPH_CROSS
        椭圆形：MORPH_ELLIPSE
        """
        if shape_flag == MORPH_RECT or (isinstance(shape_flag, str) and shape_flag.upper() == "MORPH_RECT"):
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))
        elif shape_flag == MORPH_CROSS or (isinstance(shape_flag, str) and shape_flag.upper() == "MORPH_CROSS"):
            kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (ksize, ksize))
        elif shape_flag == MORPH_ELLIPSE or (isinstance(shape_flag, str) and shape_flag.upper() == "MORPH_ELLIPSE"):
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
        else:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ksize, ksize))
        return kernel

    @staticmethod
    def draw_division(frame: np.ndarray,
                      x_number: int, x_mini: int, x_maxi: int,
                      y_number: int, y_mini: int, y_maxi: int,
                      vertical_color: tuple = CF_COLOR_DIVISION_VERTICAL_LINE,
                      horizontal_color: tuple = CF_COLOR_DIVISION_HORIZONTAL_LINE,
                      thickness: int = 2):
        """
        画分区
        :param frame:
        :param x_number:
        :param x_mini:
        :param x_maxi:
        :param y_number:
        :param y_mini:
        :param y_maxi:
        :param vertical_color:
        :param horizontal_color:
        :param thickness:
        :return:
        """
        x_division, _, _ = FrameOperator.get_sorted_division(number=x_number, mini=x_mini, maxi=x_maxi)
        y_division, _, _ = FrameOperator.get_sorted_division(number=y_number, mini=y_mini, maxi=y_maxi)

        # 复制
        if frame.ndim == 2:
            copy = cv2.cvtColor(src=frame, code=cv2.COLOR_GRAY2BGR)
        else:
            copy = frame.copy()

        height, width = copy.shape[:2]

        # 垂直线
        for x in x_division:
            pt1 = (x, 0)
            pt2 = (x, height - 1)
            cv2.line(copy, pt1, pt2, color=vertical_color, thickness=thickness, lineType=cv2.LINE_AA)

        # 水平线
        for y in y_division:
            pt1 = (0, y)
            pt2 = (width - 1, y)
            cv2.line(copy, pt1, pt2, color=horizontal_color, thickness=thickness, lineType=cv2.LINE_AA)

        return copy

    @staticmethod
    def calculate_contour_roundness(contour: np.ndarray, center: tuple, radius: float):
        """
        计算轮廓基于最小包围圆的平均圆度差
        :param contour:     轮廓
        :param center:      圆心坐标元组
        :param radius:      最小包围圆半径
        :return:
        """
        x, y = center
        # 将轮廓的所有点转化为二维
        contour = contour.reshape(-1, 2).astype(np.float32)
        # 计算x方向和y方向的差值
        sub = contour - np.array([x, y], dtype=np.float32)
        # 计算轮廓点到圆心的距离
        dis = np.hypot(sub[:, 0], sub[:, 1])
        # 计算与半径的差值
        diff = np.absolute(dis - np.array([radius], dtype=np.float32))
        # 求平均值
        roundness = np.mean(diff)
        return roundness

    @staticmethod
    def find_matched_contours(frame: np.ndarray,
                              min_area: int, max_area: int,
                              max_roundness: float,
                              max_distance: int,
                              x_number: int, x_mini: int, x_maxi: int,
                              y_number: int, y_mini: int, y_maxi: int,
                              ) -> dict:
        """
        寻找匹配的轮廓
        :param frame:
        :param min_area:
        :param max_area:
        :param max_roundness:
        :param max_distance:
        :param x_number:
        :param x_mini:
        :param x_maxi:
        :param y_number:
        :param y_mini:
        :param y_maxi:
        :return:
        """

        '''
        mode ->
            CV_RETR_EXTERNAL：只有最外层轮廓
            CV_RETR_LIST  ： 检测所有的轮廓，但是轮廓之间都是单独的，没有父子关系
            CV_RETR_CCOMP ： 检测所有的轮廓，但所有轮廓只建立两个等级关系；如果超过两个等级关系的，从顶层开始每两层分解成一个轮廓
            CV_RETR_TREE ： 检测所有轮廓，所有轮廓按照真实的情况建立等级关系，层数不限；
        method ->
            CHAIN_APPROX_NONE ：算出来的轮廓不经过处理，算出来是啥就是啥
            CHAIN_APPROX_SIMPLE：压缩轮廓，把横竖撇捺都压缩得只剩下顶点
            CHAIN_APPROX_TC89_L1：用Teh-Chin chain approximation algorithm的一种算法压缩轮廓
            CHAIN_APPROX_TC89_KCOS：用Teh-Chin chain approximation algorithm的另一种算法压缩轮廓；
        '''
        _, contours, _ = cv2.findContours(image=frame, mode=cv2.RETR_LIST, method=cv2.CHAIN_APPROX_NONE)

        contours_collection = dict()

        min_area, max_area = FrameOperator.sort_range(mini=min_area, maxi=max_area)

        # 获取间隔
        x_division, _, _ = FrameOperator.get_sorted_division(number=x_number, mini=x_mini, maxi=x_maxi)
        y_division, _, _ = FrameOperator.get_sorted_division(number=y_number, mini=y_mini, maxi=y_maxi)

        # 获取中间值  float32
        x_center = (x_division[1:] + x_division[:-1]) / 2
        y_center = (y_division[1:] + y_division[:-1]) / 2

        # 轮询所有轮廓
        for contour in contours:
            # 计算圆的面积
            area = cv2.contourArea(contour)
            # 按圆面积进行筛选
            if area < min_area or area > max_area:
                continue
            # 最小包围圆 返回 -> (圆心x坐标，圆心y坐标)，圆半径
            (x, y), radius = cv2.minEnclosingCircle(contour)
            if x < x_division[0] or x > x_division[-1] or y < y_division[0] or y > y_division[-1]:
                continue
            # 计算平均圆度
            roundness = FrameOperator.calculate_contour_roundness(contour, (x, y), radius)
            # 按平均圆度差进行筛选
            if roundness > max_roundness:
                continue
            # 计算中心距
            # 获取圆心所在位置
            x_sub = np.abs(x_division - x)
            x_index = (np.argsort(x_sub)[:2].sum() - 1) // 2
            y_sub = np.abs(y_division - y)
            y_index = (np.argsort(y_sub)[:2].sum() - 1) // 2
            x_diff = x_center[x_index] - x
            y_diff = y_center[y_index] - y
            square_dis = math.pow(x_diff, 2) + math.pow(y_diff, 2)
            # 按中心距进行筛选
            if square_dis > math.pow(max_distance, 2):
                continue
            # 将最小包围圆信息加入集合
            cur_circular = (contour, (x, y), radius, roundness, square_dis)
            key = (x_index, y_index)
            per_circular = contours_collection.get(key)
            if per_circular is None:
                contours_collection[key] = cur_circular
            else:
                # 得分说明：square_dis 越小越好，roundness 越小越好
                # roundness, square_dis
                per = np.array(per_circular[3:])
                cur = np.array(cur_circular[3:])
                weight = np.array([1, 1])
                diff = ((cur - per) * weight) <= 0
                score = np.sum(diff)
                if score:
                    contours_collection[key] = (contour, (x, y), radius, roundness, square_dis)
        return contours_collection

    @staticmethod
    def draw_matched_contours(frame: np.ndarray, contours_collection: dict,
                              color: tuple = CF_COLOR_CONTOURS_CIRCLE, thickness: int = 2) -> np.ndarray:

        # 复制
        if frame.ndim == 2:
            copy = cv2.cvtColor(src=frame, code=cv2.COLOR_GRAY2BGR)
        else:
            copy = frame.copy()
        # 绘制
        for value in contours_collection.values():
            contour = value[0]
            cv2.drawContours(copy, [contour], contourIdx=-1, color=color, thickness=thickness, lineType=cv2.LINE_AA)
        return copy

    @staticmethod
    def calculate_ref_value(x_number: int, x_mini: int, x_maxi: int, y_number: int, y_mini: int, y_maxi: int):

        x_division, _, _ = FrameOperator.get_sorted_division(number=x_number, mini=x_mini, maxi=x_maxi)
        y_division, _, _ = FrameOperator.get_sorted_division(number=y_number, mini=y_mini, maxi=y_maxi)

        x_gap = np.mean(np.diff(x_division))
        y_gap = np.mean(np.diff(y_division))
        # 椭圆面积
        area_ref = x_gap * y_gap * 3.1415926 * 0.25
        # 轮廓面积
        min_area_ref = round(area_ref * 0.0225)  # 0.15 * 0.15
        max_area_ref = round(area_ref * 0.64)  # 0.8 * 0.8
        area_max = round(x_gap * y_gap)
        # 中心距
        distance_max = round(math.sqrt(math.pow(x_gap, 2) + math.pow(x_gap, 2)) * 0.5)
        # distance_max = round(max(x_gap, y_gap) * 0.5)
        distance_ref = round(distance_max * 0.25)  # 0.25
        return min_area_ref, max_area_ref, area_max, distance_ref, distance_max

    @staticmethod
    def sort_range(mini, maxi) -> tuple:
        if mini > maxi:
            temp = maxi
            maxi = mini
            mini = temp
        return mini, maxi

    @staticmethod
    def get_sorted_division(number: int, mini: int, maxi: int) -> tuple:
        mini, maxi = FrameOperator.sort_range(mini=mini, maxi=maxi)
        division = np.linspace(mini, maxi, number + 1, endpoint=True, dtype=np.int32)
        return division, mini, maxi

    @staticmethod
    def convert_contours_collection_to_array(contours_collection: dict, x_number: int, y_number: int,
                                             pin_color: tuple = CF_COLOR_PINSMAP_PIN, null_color: tuple = CF_COLOR_PINSMAP_NULL):
        pins_map = np.zeros((y_number, x_number, 3), np.uint8)
        pins_map = pin_color - pins_map

        for key in contours_collection.keys():
            x_index, y_index = key
            pins_map[y_index, x_index] = np.array(null_color, np.uint8)

        return pins_map

    @staticmethod
    def calculate_hist(frame: np.ndarray, bins: int = 64):
        """
        计算直方图
        :param frame:
        :param bins:
        :return:
        """
        # 计算直方图  shape (bins, 1)
        hist = cv2.calcHist([frame], [0], None, [bins], [0, 256])
        # reshape    shape (bins,)
        hist = hist.reshape(-1)
        # 转换为百分比
        hist = hist / np.sum(hist)
        # x轴坐标
        x = np.linspace(0, 256, bins, endpoint=True, dtype=np.int32)
        return x, hist

    @staticmethod
    def smooth_hist(x: np.ndarray, hist: np.ndarray, method: str = "convolve", **kwargs):
        """
        平滑直方图曲线
        :param x:
        :param hist:
        :param method:
        :return:
        """
        # Savitzky-Golay 滤波器
        if method.lower() == "savgol":
            window_length = kwargs.get("window_length", 9)  # window_length即窗口长度 取值为奇数且不能超过len(x) 它越大，则平滑效果越明显 越小，则更贴近原始曲线
            polyorder = kwargs.get("polyorder", 3)  # polyorder为多项式拟合的阶数 它越小，则平滑效果越明显 越大，则更贴近原始曲线
            hist_savgol = savgol_filter(hist, window_length, polyorder, mode='nearest')
            return x, hist_savgol
        # 滑动平均滤波
        elif method.lower() == "convolve":
            window_size = kwargs.get("window_size", 4)
            window = np.ones(int(window_size)) / float(window_size)
            hist_convolve = np.convolve(hist, window, 'same')
            return x, hist_convolve
        # 插值
        elif method.lower() == "interp":
            number = kwargs.get("number", 4)
            x_interp = np.linspace(0, 256, number)
            hist_interp = make_interp_spline(x, hist)(x_interp)
            return x_interp, hist_interp
        else:
            return x, hist

    @staticmethod
    def find_valleys_and_peaks(x: np.ndarray, hist: np.ndarray, method: str = "argrelextrema", whitelist: list = ('peak', 'valley'), **kwargs):
        """
        寻找波谷
        :param x:
        :param hist:
        :param method:
        :param whitelist:
        :param kwargs:
        :return:
        """
        # TODO 需要更多匹配条件,自动寻找图片直方图的波峰和波谷，以适应更多条件
        # findpeaks 方法比 argrelextrema 方法多首尾两个点
        if method.lower() == "findpeaks" and "findpeaks" in kwargs:
            '''
            fp = findpeaks(
                method='peakdetect',    # 检测方式：一维数组【】二维数据【】
                whitelist=['peak', 'valley'],   # 检测目标【峰peak,谷valley,峰谷['peak','valley']】
                lookahead=1,            # 前瞻性优化算法【数据量越少，此数字越小，比如50个数据，最好选择1或者2】
                )
            '''
            fp: findpeaks = kwargs["findpeaks"]
            fit = fp.fit(hist)
            df: DataFrame = fit['df']

            if 'valley' in whitelist:
                # 波谷
                valleys: DataFrame = df[df['valley']]
                # 波谷索引
                valleys_index = np.asarray(valleys["x"])
                # x
                valleys_x = x[valleys_index]
                # hist
                valleys_hist = hist[valleys_index]
            else:
                valleys_x = np.empty(0)
                valleys_hist = np.empty(0)

            if 'peak' in whitelist:
                # 波峰
                peaks: DataFrame = df[df['peak']]
                # 波谷索引
                peaks_index = np.asarray(peaks["x"])
                # x
                peaks_x = x[peaks_index]
                # hist
                peaks_hist = hist[peaks_index]
            else:
                peaks_x = np.empty(0)
                peaks_hist = np.empty(0)

            return valleys_x, valleys_hist, peaks_x, peaks_hist
        elif method.lower() == "argrelextrema":
            if 'valley' in whitelist:
                # 波谷索引
                valleys_index = argrelextrema(hist, np.less)
                # x
                valleys_x = x[valleys_index]
                # hist
                valleys_hist = hist[valleys_index]
            else:
                valleys_x = np.empty(0)
                valleys_hist = np.empty(0)

            if 'peak' in whitelist:
                # 波峰索引
                peaks_index = argrelextrema(hist, np.greater)
                # x
                peaks_x = x[peaks_index]
                # hist
                peaks_hist = hist[peaks_index]
            else:
                peaks_x = np.empty(0)
                peaks_hist = np.empty(0)

            return valleys_x, valleys_hist, peaks_x, peaks_hist
        else:
            null = np.empty(0)
            return null, null, null, null

    @staticmethod
    def calculate_reference_thresh(valleys_x: np.ndarray, valleys_hist: np.ndarray, peaks_x: np.ndarray, peaks_hist: np.ndarray, **kwargs):
        """
        计算二值化阈值参考点
        :param valleys_x:
        :param valleys_hist:
        :param peaks_x:
        :param peaks_hist:
        :param kwargs:
        :return:
        """
        # 最简单的规律，选择第一个波谷
        if valleys_x.shape[0] > 0:
            thresh = valleys_x[0]
            return int(thresh)
        else:
            return None

    @staticmethod
    def draw_hist(canvas: FigureCanvas, x: np.ndarray, hist: np.ndarray, **kwargs):
        # 清除画布
        plt.clf()

        # 画图
        plt.plot(x, hist, "g-")
        if "smooth_x" in kwargs and "smooth_hist" in kwargs:
            plt.plot(kwargs["smooth_x"], kwargs["smooth_hist"], "b--")

            plt.legend(['原始', '拟合'])

        if "valleys_x" in kwargs and "valleys_hist" in kwargs:
            plt.scatter(kwargs["valleys_x"], kwargs["valleys_hist"], c='r', alpha=0.8)

        # x轴范围
        plt.xlim(-10, 266)
        # x轴刻度
        ticks = np.arange(0, 270, 20)
        plt.xticks(ticks)
        # 标题
        plt.title('灰度直方图')
        # 网格线
        plt.grid(True)

        # 刷新
        canvas.draw()

    @staticmethod
    def online_process_algorithm(frame: np.ndarray, algorithm_parameters: dict):
        vertexes = [[algorithm_parameters["P1X"], algorithm_parameters["P1Y"]],
                    [algorithm_parameters["P2X"], algorithm_parameters["P2Y"]],
                    [algorithm_parameters["P3X"], algorithm_parameters["P3Y"]],
                    [algorithm_parameters["P4X"], algorithm_parameters["P4Y"]]]

        region_direction = algorithm_parameters["MaskRegionDirection"]
        region_ratio = algorithm_parameters["MaskRegionRatio"]
        super_green_region = algorithm_parameters["SuperGreenMaskRegion"]

        filter_d = algorithm_parameters["BilateralFilterD"]
        filter_sigma_color = algorithm_parameters["BilateralFilterSigmaColor"]
        filter_sigma_space = algorithm_parameters["BilateralFilterSigmaSpace"]

        h_lower_1 = algorithm_parameters["HLower"]
        h_upper_1 = algorithm_parameters["HUpper"]
        s_lower_1 = algorithm_parameters["SLower"]
        s_upper_1 = algorithm_parameters["SUpper"]
        v_lower_1 = algorithm_parameters["VLower"]
        v_upper_1 = algorithm_parameters["VUpper"]

        open_ksize_1 = algorithm_parameters["OpenKernelSize"]
        open_iterations_1 = algorithm_parameters["OpenIterations"]

        h_lower_2 = algorithm_parameters["HLower_2"]
        h_upper_2 = algorithm_parameters["HUpper_2"]
        s_lower_2 = algorithm_parameters["SLower_2"]
        s_upper_2 = algorithm_parameters["SUpper_2"]
        v_lower_2 = algorithm_parameters["VLower_2"]
        v_upper_2 = algorithm_parameters["VUpper_2"]

        open_ksize_2 = algorithm_parameters["OpenKernelSize_2"]
        open_iterations_2 = algorithm_parameters["OpenIterations_2"]

        x_number = algorithm_parameters["XNumber"]
        x_mini = algorithm_parameters["XMini"]
        x_maxi = algorithm_parameters["XMaxi"]
        y_number = algorithm_parameters["YNumber"]
        y_mini = algorithm_parameters["YMini"]
        y_maxi = algorithm_parameters["YMaxi"]

        shift = algorithm_parameters["SectionShift"]
        mean_threshold = algorithm_parameters["SectionMeanThreshold"]

        # 梯形变换
        perspective = FrameOperator.perspective_transform(frame, vertexes)
        # 获取颜色mask
        green_mask = FrameOperator.get_color_mask_for_green(
            frame=perspective,
            region_direction=region_direction, region_ratio=region_ratio, super_green_region=super_green_region,
            hsv_lower_2=[h_lower_1, s_lower_1, v_lower_1], hsv_upper_2=[h_upper_1, s_upper_1, v_upper_1],
            ksize_2=open_ksize_1, iterations_2=open_iterations_1,
            hsv_lower_1=[h_lower_2, s_lower_2, v_lower_2], hsv_upper_1=[h_upper_2, s_upper_2, v_upper_2],
            ksize_1=open_ksize_2, iterations_1=open_iterations_2,
        )

        # 获取区域划分
        x_division, _, _ = FrameOperator.get_sorted_division(x_number, x_mini, x_maxi)
        y_division, _, _ = FrameOperator.get_sorted_division(y_number, y_mini, y_maxi)

        # 计算pins_map
        pins_map = FrameOperator.aaa(
            frame=green_mask,
            x_number=x_number, x_mini=x_mini, x_maxi=x_maxi,
            y_number=y_number, y_mini=y_mini, y_maxi=y_maxi,
            x_division=x_division, y_division=y_division,
            shift=shift, threshold=mean_threshold,
        )

        draw = FrameOperator.draw_color_extract(
            frame=perspective, extract_mask=green_mask,
            region_direction=region_direction, region_ratio=region_ratio,
            draw_region_line=False
        )

        draw = FrameOperator.draw_mean_threshold(
            frame=draw, pins_map=pins_map,
            x_division=x_division, y_division=y_division,
            shift=shift
        )

        return draw

    # @staticmethod
    # def online_process_algorithm(frame: np.ndarray, algorithm_parameters: dict):
    #     vertexes = [[algorithm_parameters["P1X"], algorithm_parameters["P1Y"]],
    #                 [algorithm_parameters["P2X"], algorithm_parameters["P2Y"]],
    #                 [algorithm_parameters["P3X"], algorithm_parameters["P3Y"]],
    #                 [algorithm_parameters["P4X"], algorithm_parameters["P4Y"]]]
    #     scale_alpha = algorithm_parameters["ScaleAlpha"]
    #     scale_beta = algorithm_parameters["ScaleBeta"]
    #     scale_enable = algorithm_parameters["ScaleEnable"]
    #     gamma_c = algorithm_parameters["GammaConstant"]
    #     gamma_power = algorithm_parameters["GammaPower"]
    #     gamma_enable = algorithm_parameters["GammaEnable"]
    #     log_c = algorithm_parameters["LogConstant"]
    #     log_enable = algorithm_parameters["LogEnable"]
    #     thresh = algorithm_parameters["Thresh"]
    #     auto_thresh = algorithm_parameters["AutoThresh"]
    #     eliminated_span = algorithm_parameters["EliminatedSpan"]
    #     reserved_interval = algorithm_parameters["ReservedInterval"]
    #     erode_shape = algorithm_parameters["ErodeShape"]
    #     erode_ksize = algorithm_parameters["ErodeKsize"]
    #     erode_iterations = algorithm_parameters["ErodeIterations"]
    #     dilate_shape = algorithm_parameters["DilateShape"]
    #     dilate_ksize = algorithm_parameters["DilateKsize"]
    #     dilate_iterations = algorithm_parameters["DilateIterations"]
    #     stripe_enable = algorithm_parameters["StripeEnable"]
    #     erode_enable = algorithm_parameters["ErodeEnable"]
    #     dilate_enable = algorithm_parameters["DilateEnable"]
    #     x_number = algorithm_parameters["XNumber"]
    #     x_mini = algorithm_parameters["XMini"]
    #     x_maxi = algorithm_parameters["XMaxi"]
    #     y_number = algorithm_parameters["YNumber"]
    #     y_mini = algorithm_parameters["YMini"]
    #     y_maxi = algorithm_parameters["YMaxi"]
    #     min_area = algorithm_parameters["MinArea"]
    #     max_area = algorithm_parameters["MaxArea"]
    #     max_roundness = algorithm_parameters["MaxRoundness"]
    #     max_distance = algorithm_parameters["MaxDistance"]
    #
    #     # 梯形变换
    #     perspective = FrameOperator.perspective_transform(frame, vertexes)
    #     # 二值化
    #     binarization, _ = FrameOperator.binarization_transform(perspective, scale_alpha, scale_beta, gamma_c, gamma_power, log_c, thresh,
    #                                                            scale_enable, gamma_enable, log_enable, auto_thresh)
    #     # 去噪
    #     denoise = FrameOperator.denoise_transform(binarization, eliminated_span, reserved_interval,
    #                                               erode_shape, erode_ksize, erode_iterations,
    #                                               dilate_shape, dilate_ksize, dilate_iterations,
    #                                               stripe_enable, erode_enable, dilate_enable)
    #     # 轮廓集
    #     contours_collection = FrameOperator.find_matched_contours(denoise, min_area, max_area, max_roundness, max_distance,
    #                                                               x_number, x_mini, x_maxi, y_number, y_mini, y_maxi)
    #
    #     draw = FrameOperator.draw_matched_contours(perspective, contours_collection)
    #
    #     return draw

    @staticmethod
    def offline_process_algorithm(frame: np.ndarray, message: dict,
                                  show_detection_callback=None, record_detection_callback=None,
                                  err_pins_color: tuple = CF_COLOR_ERROR_PINS, err_null_color: tuple = CF_COLOR_ERROR_NULL):
        """

        :param frame:
        :param message:
        :param show_detection_callback:
        :param record_detection_callback:
        :param err_pins_color:
        :param err_null_color:
        :return:
        """
        vertexes = [[message["P1X"], message["P1Y"]],
                    [message["P2X"], message["P2Y"]],
                    [message["P3X"], message["P3Y"]],
                    [message["P4X"], message["P4Y"]]]

        region_direction = message["MaskRegionDirection"]
        region_ratio = message["MaskRegionRatio"]
        super_green_region = message["SuperGreenMaskRegion"]

        filter_d = message["BilateralFilterD"]
        filter_sigma_color = message["BilateralFilterSigmaColor"]
        filter_sigma_space = message["BilateralFilterSigmaSpace"]

        h_lower_1 = message["HLower"]
        h_upper_1 = message["HUpper"]
        s_lower_1 = message["SLower"]
        s_upper_1 = message["SUpper"]
        v_lower_1 = message["VLower"]
        v_upper_1 = message["VUpper"]

        open_ksize_1 = message["OpenKernelSize"]
        open_iterations_1 = message["OpenIterations"]

        h_lower_2 = message["HLower_2"]
        h_upper_2 = message["HUpper_2"]
        s_lower_2 = message["SLower_2"]
        s_upper_2 = message["SUpper_2"]
        v_lower_2 = message["VLower_2"]
        v_upper_2 = message["VUpper_2"]

        open_ksize_2 = message["OpenKernelSize_2"]
        open_iterations_2 = message["OpenIterations_2"]

        x_number = message["XNumber"]
        x_mini = message["XMini"]
        x_maxi = message["XMaxi"]
        y_number = message["YNumber"]
        y_mini = message["YMini"]
        y_maxi = message["YMaxi"]

        shift = message["SectionShift"]
        mean_threshold = message["SectionMeanThreshold"]

        ref_pins_map = message["PinsMap"]

        location = message["Location"]
        side = message["Side"]
        line = message["Line"]

        # 梯形变换
        perspective = FrameOperator.perspective_transform(frame, vertexes)

        # 获取颜色mask
        green_mask = FrameOperator.get_color_mask_for_green(
            frame=perspective,
            region_direction=region_direction, region_ratio=region_ratio, super_green_region=super_green_region,
            hsv_lower_2=[h_lower_1, s_lower_1, v_lower_1], hsv_upper_2=[h_upper_1, s_upper_1, v_upper_1],
            ksize_2=open_ksize_1, iterations_2=open_iterations_1,
            hsv_lower_1=[h_lower_2, s_lower_2, v_lower_2], hsv_upper_1=[h_upper_2, s_upper_2, v_upper_2],
            ksize_1=open_ksize_2, iterations_1=open_iterations_2,
        )

        # 获取区域划分
        x_division, _, _ = FrameOperator.get_sorted_division(x_number, x_mini, x_maxi)
        y_division, _, _ = FrameOperator.get_sorted_division(y_number, y_mini, y_maxi)

        # 计算pins_map
        pins_map = FrameOperator.aaa(
            frame=green_mask,
            x_number=x_number, x_mini=x_mini, x_maxi=x_maxi,
            y_number=y_number, y_mini=y_mini, y_maxi=y_maxi,
            x_division=x_division, y_division=y_division,
            shift=shift, threshold=mean_threshold,
        )

        # 计算实际 ref_pins_map
        if side != CF_TEACH_REFERENCE_SIDE:
            ref_pins_map = cv2.flip(ref_pins_map, flipCode=0)  # 水平翻转

        # pins_map 与 ref_pins_map 对比
        err_pins_location, err_null_location = FrameOperator.match_pins_map(pins_map, ref_pins_map)

        # 检测结果
        # detection_res = not bool(err_pins_location.any() or err_null_location.any())
        if err_pins_location.shape == (0, 2) and err_null_location.shape == (0, 2):
            detection_res = True
        else:
            detection_res = False

        # 显示 颜色提取
        # draw = FrameOperator.draw_color_extract(
        #     frame=perspective, extract_mask=green_mask,
        #     region_direction=region_direction, region_ratio=region_ratio,
        #     draw_region_line=False
        # )
        draw = perspective
        # 画错误位置
        if not detection_res:
            draw = FrameOperator.draw_err_location(draw, x_division, y_division, err_pins_location, color=err_pins_color, shift=0.2)
            draw = FrameOperator.draw_err_location(draw, x_division, y_division, err_null_location, color=err_null_color, shift=0.2)

        # 保存记录回调函数
        if record_detection_callback is not None:
            record_message = dict()

            record_message["Part"] = message["Part"]
            record_message["Line"] = line
            record_message["Location"] = location
            record_message["Result"] = detection_res

            if not detection_res:
                # 序列化
                str_err_pins_location = MySerializer.serialize(err_pins_location)
                str_err_null_location = MySerializer.serialize(err_null_location)
                err = {"ErrorPinsLocation": str_err_pins_location,
                       "ErrorNullLocation": str_err_null_location}
                # json序列化
                record_message["Error"] = dumps(err)

            if "User" in message:
                record_message["User"] = message.get("User", "")

            record_detection_callback(record_message=record_message, origin_frame=frame, detection_frame=draw)

        # 显示检测结果回调函数
        if show_detection_callback is not None:
            show_detection_callback(result=detection_res, frame=draw)

    # @staticmethod
    # def offline_process_algorithm(frame: np.ndarray, message: dict,
    #                               show_detection_callback=None, record_detection_callback=None,
    #                               err_pins_color: tuple = CF_COLOR_ERROR_PINS, err_null_color: tuple = CF_COLOR_ERROR_NULL):
    #     """
    #
    #     :param frame:
    #     :param message:
    #     :param show_detection_callback:
    #     :param record_detection_callback:
    #     :param err_pins_color:
    #     :param err_null_color:
    #     :return:
    #     """
    #     vertexes = [[message["P1X"], message["P1Y"]],
    #                 [message["P2X"], message["P2Y"]],
    #                 [message["P3X"], message["P3Y"]],
    #                 [message["P4X"], message["P4Y"]]]
    #     scale_alpha = message["ScaleAlpha"]
    #     scale_beta = message["ScaleBeta"]
    #     scale_enable = message["ScaleEnable"]
    #     gamma_c = message["GammaConstant"]
    #     gamma_power = message["GammaPower"]
    #     gamma_enable = message["GammaEnable"]
    #     log_c = message["LogConstant"]
    #     log_enable = message["LogEnable"]
    #     thresh = message["Thresh"]
    #     auto_thresh = message["AutoThresh"]
    #     eliminated_span = message["EliminatedSpan"]
    #     reserved_interval = message["ReservedInterval"]
    #     erode_shape = message["ErodeShape"]
    #     erode_ksize = message["ErodeKsize"]
    #     erode_iterations = message["ErodeIterations"]
    #     dilate_shape = message["DilateShape"]
    #     dilate_ksize = message["DilateKsize"]
    #     dilate_iterations = message["DilateIterations"]
    #     stripe_enable = message["StripeEnable"]
    #     erode_enable = message["ErodeEnable"]
    #     dilate_enable = message["DilateEnable"]
    #     x_number = message["XNumber"]
    #     x_mini = message["XMini"]
    #     x_maxi = message["XMaxi"]
    #     y_number = message["YNumber"]
    #     y_mini = message["YMini"]
    #     y_maxi = message["YMaxi"]
    #     min_area = message["MinArea"]
    #     max_area = message["MaxArea"]
    #     max_roundness = message["MaxRoundness"]
    #     max_distance = message["MaxDistance"]
    #
    #     ref_pins_map = message["PinsMap"]
    #
    #     camera_location = message["CameraLocation"]
    #     location = camera_location["Location"]
    #     side = camera_location["Side"]
    #
    #     # 梯形变换
    #     perspective = FrameOperator.perspective_transform(frame, vertexes)
    #     # 二值化
    #     binarization, _ = FrameOperator.binarization_transform(perspective, scale_alpha, scale_beta, gamma_c, gamma_power, log_c, thresh,
    #                                                            scale_enable, gamma_enable, log_enable, auto_thresh)
    #     # 去噪
    #     denoise = FrameOperator.denoise_transform(binarization, eliminated_span, reserved_interval,
    #                                               erode_shape, erode_ksize, erode_iterations,
    #                                               dilate_shape, dilate_ksize, dilate_iterations,
    #                                               stripe_enable, erode_enable, dilate_enable)
    #     # 轮廓集
    #     contours_collection = FrameOperator.find_matched_contours(denoise, min_area, max_area, max_roundness, max_distance,
    #                                                               x_number, x_mini, x_maxi, y_number, y_mini, y_maxi)
    #     # 获取区域划分
    #     x_division, _, _ = FrameOperator.get_sorted_division(x_number, x_mini, x_maxi)
    #     y_division, _, _ = FrameOperator.get_sorted_division(y_number, y_mini, y_maxi)
    #
    #     # 计算pins_map
    #     pins_map = FrameOperator.convert_contours_collection_to_array(contours_collection, x_number, y_number)
    #
    #     # 计算实际 ref_pins_map
    #     if side != CF_TEACH_REFERENCE_SIDE:
    #         ref_pins_map = cv2.flip(ref_pins_map, flipCode=0)  # 水平翻转
    #
    #     # pins_map 与 ref_pins_map 对比
    #     err_pins_location, err_null_location = FrameOperator.match_pins_map(pins_map, ref_pins_map)
    #
    #     # 检测结果
    #     # detection_res = not bool(err_pins_location.any() or err_null_location.any())
    #     if err_pins_location.shape == (0, 2) and err_null_location.shape == (0, 2):
    #         detection_res = True
    #     else:
    #         detection_res = False
    #
    #     # 画轮廓集
    #     draw = FrameOperator.draw_matched_contours(perspective, contours_collection)
    #     # 画错误位置
    #     if not detection_res:
    #         draw = FrameOperator.draw_err_location(draw, x_division, y_division, err_pins_location, color=err_pins_color)
    #         draw = FrameOperator.draw_err_location(draw, x_division, y_division, err_null_location, color=err_null_color)
    #
    #     # 保存记录回调函数
    #     if record_detection_callback is not None:
    #         record_message = dict()
    #
    #         record_message["Part"] = message["Part"]
    #         record_message["Line"] = camera_location["Line"]
    #         record_message["Location"] = location
    #         record_message["Result"] = detection_res
    #
    #         if not detection_res:
    #             # 序列化
    #             str_err_pins_location = MySerializer.serialize(err_pins_location)
    #             str_err_null_location = MySerializer.serialize(err_null_location)
    #             err = {"ErrorPinsLocation": str_err_pins_location,
    #                    "ErrorNullLocation": str_err_null_location}
    #             # json序列化
    #             record_message["Error"] = dumps(err)
    #
    #         if "User" in message:
    #             record_message["User"] = message.get("User", "")
    #
    #         record_detection_callback(record_message=record_message, origin_frame=frame, detection_frame=draw)
    #
    #     # 显示检测结果回调函数
    #     if show_detection_callback is not None:
    #         show_detection_callback(result=detection_res, frame=draw)

    @staticmethod
    def match_pins_map(pins_map: np.ndarray, ref_pins_map: np.ndarray):
        # pins_map 中 是顶棒的位置
        pins = np.where(pins_map == CF_COLOR_PINSMAP_PIN)
        # pins_map 中 是孔的位置
        null = np.where(pins_map == CF_COLOR_PINSMAP_NULL)

        # where 结果拼接为 二维位置坐标
        pins_location = np.stack((pins[1][::3], pins[0][::3]), axis=1)
        null_location = np.stack((null[1][::3], null[0][::3]), axis=1)

        # 将一维数组转为二维
        pins_location_in_ref = ref_pins_map[pins].reshape(-1, 3)
        null_location_in_ref = ref_pins_map[null].reshape(-1, 3)

        # 查找错误位置
        err_pins = np.where(pins_location_in_ref == CF_COLOR_PINSMAP_NULL)
        err_null = np.where(null_location_in_ref == CF_COLOR_PINSMAP_PIN)

        # where 结果转换为index序号信息
        err_pins_index = err_pins[0][::3]
        err_null_index = err_null[0][::3]

        # 转化为err位置坐标
        err_pins_location = pins_location[err_pins_index]
        err_null_location = null_location[err_null_index]

        # print(pins_location[err_pins_index])
        # print(null_location[err_null_index])

        return err_pins_location, err_null_location

    @staticmethod
    def draw_err_location(frame: np.ndarray, x_division: np.ndarray, y_division: np.ndarray, err_location: np.ndarray, color: tuple,
                          shift: float = 0.2, alpha: float = 1, beta: float = 0.5, gamma: int = 0):

        # 复制
        if frame.ndim == 2:
            copy = cv2.cvtColor(src=frame, code=cv2.COLOR_GRAY2BGR)
        else:
            copy = frame.copy()

        # 创建掩膜
        mark = np.zeros_like(copy)

        for location in err_location:
            x, y = location

            x_pad = int(shift * (x_division[x + 1] - x_division[x]))
            y_pad = int(shift * (y_division[y + 1] - y_division[y]))

            x_min = x_division[x] + x_pad
            x_max = x_division[x + 1] - x_pad

            y_min = y_division[y] + y_pad
            y_max = y_division[y + 1] - y_pad

            lt = x_min, y_min
            rb = x_max, y_max

            cv2.rectangle(mark, lt, rb, color=color, thickness=-1, lineType=cv2.LINE_AA)

        # 图像融合 可以调整融合度参数控制透明度
        # 图像相加的公式是 R=a*x1+b*x2+c
        copy = cv2.addWeighted(copy, alpha, mark, beta, gamma)

        return copy

    @staticmethod
    def draw_mean_threshold(frame: np.ndarray, pins_map: np.ndarray,
                            x_division: np.ndarray, y_division: np.ndarray,
                            color: tuple = CF_COLOR_CONTOURS_CIRCLE,
                            shift: float = 0.2, alpha: float = 1, beta: float = 0.5, gamma: int = 0
                            ) -> np.ndarray:

        # 复制
        if frame.ndim == 2:
            copy = cv2.cvtColor(src=frame, code=cv2.COLOR_GRAY2BGR)
        else:
            copy = frame.copy()

        # # 创建掩膜
        # mark = np.zeros_like(copy)
        #
        # # pins_map 中 是孔的位置
        # null = np.where(pins_map == CF_COLOR_PINSMAP_NULL)
        # # where 结果拼接为 二维位置坐标
        # null_location = np.stack((null[1][::3], null[0][::3]), axis=1)
        #
        # for location in null_location:
        #     x, y = location
        #
        #     x_pad = int(shift * (x_division[x + 1] - x_division[x]))
        #     y_pad = int(shift * (y_division[y + 1] - y_division[y]))
        #
        #     x_min = x_division[x] + x_pad
        #     x_max = x_division[x + 1] - x_pad
        #
        #     y_min = y_division[y] + y_pad
        #     y_max = y_division[y + 1] - y_pad
        #
        #     lt = x_min, y_min
        #     rb = x_max, y_max
        #
        #     cv2.rectangle(mark, lt, rb, color=color, thickness=-1, lineType=cv2.LINE_AA)
        #
        # # 图像融合 可以调整融合度参数控制透明度
        # # 图像相加的公式是 R=a*x1+b*x2+c
        # copy = cv2.addWeighted(copy, alpha, mark, beta, gamma)

        # pins_map 中 是孔的位置
        null = np.where(pins_map == CF_COLOR_PINSMAP_NULL)
        # where 结果拼接为 二维位置坐标
        null_location = np.stack((null[1][::3], null[0][::3]), axis=1)

        for location in null_location:
            x, y = location
            x_pad = int(shift * (x_division[x + 1] - x_division[x]))
            y_pad = int(shift * (y_division[y + 1] - y_division[y]))

            x_min = x_division[x] + x_pad
            x_max = x_division[x + 1] - x_pad

            y_min = y_division[y] + y_pad
            y_max = y_division[y + 1] - y_pad

            lt = x_min, y_min
            rb = x_max, y_max

            cv2.rectangle(copy, lt, rb, color=color, thickness=2, lineType=cv2.LINE_AA)

        return copy

    @staticmethod
    def get_super_green_mask(frame: np.ndarray):
        # 浮点 归一
        f_frame = np.array(frame, dtype=np.float32) / 255.0
        # 分割
        b, g, r = cv2.split(f_frame)
        # super green
        gray = 2 * g - b - r
        # gray = (2 * g - b - r) / (g + b + r)

        # 最大值 最小值
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(gray)

        # # 计算直方图
        # hist = cv2.calcHist([gray], [0], None, [256], [min_val, max_val])
        # plt.plot(hist)
        # plt.show()

        # 整形
        gray_u8 = np.array((gray - min_val) / (max_val - min_val) * 255, dtype=np.uint8)

        # otsu 二值化
        # thresh, mask = cv2.threshold(gray_u8, 73, 255, cv2.THRESH_BINARY)
        thresh, mask = cv2.threshold(gray_u8, -1.0, 255, cv2.THRESH_OTSU)

        return mask

    @staticmethod
    def get_color_mask_by_hsv(frame: np.ndarray, hsv_lower: list, hsv_upper: list, ksize: int = 5, iterations: int = 1):
        # 使用 HSV
        # hsv_lower, hsv_upper = [0.27, 0, 0], [0.66, 1, 0.5]
        # hsv_const = [180, 255, 255]

        # 转hsv
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # hsv_lower = (np.array(hsv_lower) * np.array(hsv_const)).astype(np.uint8)
        # hsv_upper = (np.array(hsv_upper) * np.array(hsv_const)).astype(np.uint8)
        hsv_lower = np.array(hsv_lower, dtype=np.uint8)
        hsv_upper = np.array(hsv_upper, dtype=np.uint8)
        # 获得二值化
        mask = cv2.inRange(hsv, hsv_lower, hsv_upper)
        if iterations > 0:
            # 形态学
            kernel = FrameOperator.set_kernel(shape_flag=2, ksize=ksize)
            # bin_img = cv2.erode(bin_img, kernel, iterations=2)
            # bin_img = cv2.dilate(bin_img, kernel, iterations=1)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=iterations)

        return mask

    @staticmethod
    def bilateral_filter(frame: np.ndarray, d: int, sigmaColor: int, sigmaSpace: int):
        # d = 9
        # sigmaColor = 75
        # sigmaSpace = 75
        frame = cv2.bilateralFilter(frame, d, sigmaColor, sigmaSpace)
        return frame

    @staticmethod
    def get_color_mask_for_green(frame: np.ndarray,
                                 region_direction: int, region_ratio: float, super_green_region: int,
                                 hsv_lower_1: list, hsv_upper_1: list, ksize_1: int, iterations_1: int,
                                 hsv_lower_2: list, hsv_upper_2: list, ksize_2: int, iterations_2: int
                                 ) -> np.ndarray:

        mask = np.zeros_like(frame[:, :, 0])
        height, width = frame.shape[:2]

        # 宽度
        if region_direction == 0:
            mask_width = int(width * region_ratio)
            mask[:, mask_width:] = 255
        # 高度
        else:
            mask_height = int(height * region_ratio)
            mask[mask_height:, :] = 255

        # 区域1
        if super_green_region == 0:
            mask_for_super_green = 255 - mask
            mask_for_hsv = mask
        # 区域2
        else:
            mask_for_super_green = mask
            mask_for_hsv = 255 - mask

        # super green
        # green_mask_by_super_green = FrameOperator.get_super_green_mask(frame=frame)
        # green_mask_by_super_green = cv2.bitwise_and(green_mask_by_super_green, green_mask_by_super_green, mask=mask_for_super_green)
        green_mask_by_hsv_1 = FrameOperator.get_color_mask_by_hsv(
            frame=frame,
            hsv_lower=hsv_lower_1, hsv_upper=hsv_upper_1,
            ksize=ksize_1, iterations=iterations_1
        )
        green_mask_by_super_green = cv2.bitwise_and(green_mask_by_hsv_1, green_mask_by_hsv_1, mask=mask_for_super_green)
        # hsv
        green_mask_by_hsv_2 = FrameOperator.get_color_mask_by_hsv(
            frame=frame,
            hsv_lower=hsv_lower_2, hsv_upper=hsv_upper_2,
            ksize=ksize_2, iterations=iterations_2
        )
        green_mask_by_hsv = cv2.bitwise_and(green_mask_by_hsv_2, green_mask_by_hsv_2, mask=mask_for_hsv)

        green_mask = green_mask_by_super_green + green_mask_by_hsv

        return green_mask

    @staticmethod
    def draw_color_extract(frame: np.ndarray, extract_mask: np.ndarray,
                           region_direction: int, region_ratio: float,
                           draw_region_line: bool = True,
                           color: tuple = CF_COLOR_COLOR_REGION_LINE,
                           thickness: int = 4) -> np.ndarray:
        b, g, r = cv2.split(frame)
        frame = cv2.merge([b & extract_mask, g & extract_mask, r & extract_mask])

        if draw_region_line:
            height, width = frame.shape[:2]
            # 宽度
            if region_direction == 0:
                mask_width = int(width * region_ratio)
                pt1 = (mask_width, 0)
                pt2 = (mask_width, height)
            # 高度
            else:
                mask_height = int(height * region_ratio)
                pt1 = (0, mask_height)
                pt2 = (width, mask_height)
            cv2.line(frame, pt1, pt2, color=color, thickness=thickness, lineType=cv2.LINE_AA)

        return frame

    @staticmethod
    def aaa(frame: np.ndarray,
            x_number: int, x_mini: int, x_maxi: int,
            y_number: int, y_mini: int, y_maxi: int,
            x_division: Optional[np.ndarray] = None, y_division: Optional[np.ndarray] = None,
            shift: float = 0.1, threshold: float = 0.01,
            pin_color: tuple = CF_COLOR_PINSMAP_PIN, null_color: tuple = CF_COLOR_PINSMAP_NULL
            ):

        # 顶棒图
        pins_map = np.zeros((y_number, x_number, 3), np.uint8)
        pins_map = pin_color - pins_map

        # 获取间隔
        if x_division is None or y_division is None:
            x_division, _, _ = FrameOperator.get_sorted_division(number=x_number, mini=x_mini, maxi=x_maxi)
            y_division, _, _ = FrameOperator.get_sorted_division(number=y_number, mini=y_mini, maxi=y_maxi)

        for x in range(x_number):
            for y in range(y_number):

                x_1, x_2 = x_division[x], x_division[x + 1]
                y_1, y_2 = y_division[y], y_division[y + 1]
                x_shift, y_shift = int(shift * (x_2 - x_1)), int(shift * (y_2 - y_1))

                section = frame[y_1 + y_shift: y_2 - y_shift, x_1 + x_shift: x_2 - x_shift]
                mask = 255 - np.zeros_like(section)

                r = np.mean(section / mask)

                if r > threshold:
                    pins_map[y, x] = np.array(null_color, np.uint8)

        return pins_map


# if __name__ == '__main__':
#
#     image = cv2.imread(r'C:\Users\yy\Desktop\MyProcessPicture_1921680030042528_XXX_5-100_20240623111914573442.jpg')
#
#     x_number = 27
#     x_mini = 74
#     x_maxi = 1103
#     y_number = 13
#     y_mini = 61
#     y_maxi = 658
#
#     shift = 0.2
#
#     x_division, _, _ = FrameOperator.get_sorted_division(number=x_number, mini=x_mini, maxi=x_maxi)
#     y_division, _, _ = FrameOperator.get_sorted_division(number=y_number, mini=y_mini, maxi=y_maxi)
#
#     pins_map = FrameOperator.aaa(
#         frame=image,
#         x_division=x_division, y_division=y_division,
#         x_number=x_number, x_mini=x_mini, x_maxi=x_maxi,
#         y_number=y_number, y_mini=y_mini, y_maxi=y_maxi,
#         shift=shift, threshold=0.01,
#     )
#
#     draw = FrameOperator.draw_mean_threshold(
#         frame=image, pins_map=pins_map,
#         x_division=x_division, y_division=y_division,
#         shift=shift)
#
#     cv2.imshow('frame', draw)
#     cv2.waitKey(0)
#     cv2.destroyAllWindows()
