import os
import glob
import cv2
from tqdm import tqdm       # 进度条
import argparse
from typing import Optional

# 将视频转换为MVS 虚拟相机


def extractor(src_file: str, dst_dim: Optional[tuple] = None,
              start_frame: Optional[int] = None, end_frame: Optional[int] = None, step_frame: Optional[int] = None,
              is_gray: bool = True, flip: Optional[int] = None, show_ratio: float = 0.5,
              dst_postfix: Optional[str] = None, image_prefix: Optional[str] = None):
    """
    抽取视频帧，并保存为 .bmp 文件
    :param src_file:        源视频文件
    :param dst_dim:         相机分辨率
    :param start_frame:     起始帧
    :param end_frame:       结束帧
    :param step_frame:      步距
    :param is_gray:         是否为灰度相机
    :param flip:            反转      >0 -> y轴翻转; ==0 -> x轴翻转; <0 -> xy轴翻转
    :param show_ratio:      显示比例
    :param dst_postfix:     保存路径后缀
    :param image_prefix:
    :return:
    """

    # 验证源视频路径
    assert os.path.exists(src_file), Exception("Video file {} does not exist !".format(src_file))

    # 打开视频
    cap = cv2.VideoCapture(src_file)
    # 验证视频是否成功打开
    assert cap.isOpened(), Exception("Unable to open video {} !".format(src_file))

    # 获取视频名称
    video_name = src_file.split('\\')[-1]
    video_dir = src_file[-len(src_file): -len(video_name) - 1]
    abs_video_name = video_name.split('.')[0]
    print("===================================================")
    print("[video info]\tname [%s] has been opened" % (video_name,))

    # 宽度
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    # 高度
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    # 帧率
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    # 帧数
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print("===================================================")
    print("[video info]\twidth [%d]\theight [%d]\tfps [%d]\tframe count [%d]" % (width, height, fps, frame_count))

    # 设置 起始帧 结束帧 步距
    if start_frame is None:
        start = 0
    else:
        if start_frame < 0:
            start = 0
        elif 0 <= start_frame < frame_count:
            start = start_frame
        else:
            start = frame_count - 1

    if end_frame is None:
        end = frame_count - 1
    else:
        if end_frame < start:
            end = start
        elif start <= end_frame < frame_count:
            end = end_frame
        else:
            end = frame_count - 1

    if step_frame is None:
        step = 1
    else:
        if step_frame > 0:
            step = step_frame
        else:
            step = 1
    print("===================================================")
    print("[video info]\tstart_frame [%d]\tend_frame [%d]\tstep_frame [%d]" % (start, end, step))

    # 目标路径
    folder_name = "%s_%d_%d_%d_%.2f" % (abs_video_name, start, end, step, fps/step)
    if is_gray:
        folder_name += "_GRAY"
    else:
        folder_name += "_RGB"

    if flip is not None:
        if flip > 0:
            folder_name += "_Y"
        elif flip < 0:
            folder_name += "_XY"
        else:
            folder_name += "_X"

    if dst_postfix is not None or (isinstance(dst_postfix, str) and dst_postfix != ""):
        folder_name += "_{}".format(dst_postfix)

    dst_dir = os.path.join(video_dir, folder_name)
    if not os.path.exists(dst_dir):
        os.mkdir(dst_dir)
        print("[video info]\tcreate destination folder [{}]".format(dst_dir))
    else:
        for file in glob.glob("%s/*" % dst_dir):
            os.remove(file)
        print("[video info]\tclear destination folder [{}]".format(dst_dir))

    # 设置视频读取的起始帧
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)

    # 初始化显示窗口
    window_name = "video [%s]" % (abs_video_name,)
    set_window_info(name=window_name, width=int(width * show_ratio), height=int(height * show_ratio))

    # 位数，用于补零
    figures = len(str(frame_count))

    i = start
    c = 0
    cc = 0
    for i in tqdm(range(start, end + 1)):

        if not cap.isOpened():
            print("===================================================")
            print("[video info]\terror\tvideo closed")
            break

        res, frame = cap.read()
        if not res:
            print("===================================================")
            print("[video info]\terror\tvideo read error")
            break

        c += 1
        if step > 1 and c % step != 1:
            continue

        if is_gray:
            # 灰度图
            frame = cv2.cvtColor(src=frame, code=cv2.COLOR_BGR2GRAY)
        else:
            # RGB
            frame = cv2.cvtColor(src=frame, code=cv2.COLOR_BGR2RGB)

        # resize
        if dst_dim is not None:
            # resize
            # frame = cv2.resize(frame, dst_dim)

            # 向四周填充黑边
            # 定义边界颜色
            if is_gray:
                pad = 0
            else:
                pad = [0, 0, 0]
            # 定义边界尺寸
            h, w = frame.shape[:2]
            dst_w, dst_h = dst_dim
            top = int((dst_h - h) / 2)
            bottom = dst_h - h - top
            left = int((dst_w - w) / 2)
            right = dst_w - w - left
            # border
            frame = cv2.copyMakeBorder(frame, top, bottom, left, right, cv2.BORDER_CONSTANT, value=pad)

        # 镜像
        if flip is not None:
            frame = cv2.flip(frame, flipCode=flip)

        # 保存bmp
        # 补零
        image_name = "%s.bmp" % str(i).zfill(figures)
        if image_prefix is not None or (isinstance(image_prefix, str) and image_prefix != ""):
            image_name = "{}_{}".format(image_prefix, image_name)

        dst_path = os.path.join(dst_dir, image_name)
        cv2.imwrite(dst_path, frame)

        # 显示图像
        cv2.imshow(window_name, frame)

        cc += 1

        # 按键监测
        # [esc] & [q] & 点击窗口关闭按键 -> 关闭视频
        key = cv2.waitKey(10) & 0xFF
        if key == 27 or key == ord('q') or int(cv2.getWindowProperty(window_name, 0)) == -1:
            break

    cap.release()
    cv2.destroyAllWindows()

    print("===================================================")
    print("[video info]\tprogram done\textract %d frames [%d,%d,%d]" % (cc, start, i, step))
    print("===================================================")


def set_window_info(name: str, width: int, height: int):
    """
    设置显示窗口信息
    :param name:    窗口名称
    :param width:   窗口宽度
    :param height:  窗口豪赌
    :return:
    """
    cv2.namedWindow(name, cv2.WINDOW_KEEPRATIO)
    # cv2.resizeWindow(name, width, height)


if __name__ == "__main__":
    # src -> 不可以有中文字符
    # dim -> 2448,2048
    ap = argparse.ArgumentParser()
    ap.add_argument("-s", "--src", required=False)
    ap.add_argument("-d", "--dim", required=False)
    ap.add_argument("-t", "--step", required=False)
    ap.add_argument("-f", "--flip", required=False)
    ap.add_argument("-p", "--postfix", required=False)
    ap.add_argument("-r", "--prefix", required=False)
    args = vars(ap.parse_args())

    src = args["src"]
    if src is None:
        src = r"D:\02_Creativity\02_Projects\ScrapsMonitor\VirtualCameras\new\5-200-OP30\30-1-1 (DA0537474)\Video_20240426092958301.avi"

    dim_str = args["dim"]
    if dim_str is None:
        dim = (2448, 2048)
        # dim = None
    else:
        dim = dim_str.split(',')

    s = args["step"]
    if s is None:
        s = None

    f = args["flip"]
    if f is None:
        f = None

    postfix = args["postfix"]
    if postfix is None:
        postfix = 'MVCA05010GM'
        # postfix = 'MVCA06011GM'
        # postfix = '1280x1024'

    prefix = args["prefix"]
    if prefix is None:
        prefix = 'OP30_3'

    extractor(src_file=src, dst_dim=dim, start_frame=None, end_frame=99, step_frame=s, is_gray=True, flip=f, show_ratio=0.3, dst_postfix=postfix, image_prefix=prefix)
