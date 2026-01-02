import cv2
import os
 
# 图片目录
image_folder = r'C:\Users\yy\Desktop\0 - 2024-07-08 09-26-35-260\cap'
# 视频输出路径
video_output = 'output_video.avi'
video_path = os.path.join(image_folder, video_output)

# 图片尺寸
frame_width = 3072
frame_height = 1728
rate = 30.0
 
# 图片文件列表
images = [img for img in os.listdir(image_folder) if img.endswith(".png")]
# 图片按数字排序
# images.sort(key=lambda f: int(f.split('.')[0][-3:]))
 

# 视频编码器和输出视频的创建
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter(video_path, fourcc, rate, (frame_width, frame_height))

cv2.namedWindow("video", cv2.WINDOW_KEEPRATIO)

for image in images:
    # 读取图片
    img_path = os.path.join(image_folder, image)
    frame = cv2.imread(img_path)
    
    # 如果图片尺寸与视频不符，则需要调整尺寸
    if frame.shape[:2] != (frame_width, frame_height):
        frame = cv2.resize(frame, (frame_width, frame_height), interpolation=cv2.INTER_AREA)
    
    cv2.imshow("video", frame)
    cv2.waitKey(10)

    # 将帧写入视频
    out.write(frame)

cv2.destroyAllWindows()
# 释放VideoWriter对象
out.release()
