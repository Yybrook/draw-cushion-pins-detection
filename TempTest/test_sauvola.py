import numpy as np
import cv2
from skimage.filters import threshold_sauvola


def sauvola_binarization_1(image, window_size=15, k=0.2, r=128):
    """
    Apply Sauvola binarization to an image.

    Parameters:
        image (ndarray): Grayscale image to be binarized.
        window_size (int): Size of the local region (should be odd).
        k (float): Hyperparameter, typically in range [0.2, 0.5].
        r (float): Dynamic range of standard deviation (default: 128 for 8-bit images).

    Returns:
        binary_image (ndarray): Binarized image.
    """
    # Calculate the mean and standard deviation within the window
    # mean = cv2.blur(image, (window_size, window_size))
    mean = cv2.boxFilter(image, ddepth=-1, ksize=(window_size, window_size))
    # mean_sq = cv2.blur(image ** 2, (window_size, window_size))
    mean_sq = cv2.boxFilter(image ** 2, ddepth=-1, ksize=(window_size, window_size))
    stddev = np.sqrt(mean_sq - mean ** 2)

    # Compute the threshold using Sauvola formula
    threshold = mean * (1 + k * ((stddev / r) - 1))

    # Apply the threshold to get the binary image
    binary_image = (image > threshold).astype(np.uint8) * 255

    return binary_image


def sauvola_binarization_2(image, window_size=15, k=0.2, r=128):

    # 应用阈值进行二值化
    sauvola = threshold_sauvola(image, window_size, k, r)
    binary_image = (image > sauvola).astype(np.uint8) * 255

    return binary_image


if __name__ == '__main__':
    path = r"C:\Users\yy\Documents\MyProject\PinsErrorProof\pins-error-proof\Software\Pins-Ctrl\PinsCtrlData\Temp\Teach\test.jpg"

    # 读取图像
    img = cv2.imread(path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 使用Sauvola快速算法进行阈值化
    bina1 = sauvola_binarization_1(img)
    bina2 = sauvola_binarization_2(img)


    cv2.namedWindow('Original Image', cv2.WINDOW_KEEPRATIO)
    cv2.namedWindow('sauvola1 Image', cv2.WINDOW_KEEPRATIO)
    cv2.namedWindow('sauvola2 Image', cv2.WINDOW_KEEPRATIO)
    # 显示结果
    cv2.imshow('Original Image', img)
    cv2.imshow('sauvola1 Image', bina1)
    cv2.imshow('sauvola2 Image', bina2)


    cv2.waitKey(0)
    cv2.destroyAllWindows()
