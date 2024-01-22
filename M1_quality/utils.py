import numpy as np
import matplotlib.pyplot as plt
import cv2

# 图像直方图
def hist(img):
    # Calculate the histogram
    histogram = cv2.calcHist([img], [0], None, [256], [0, 256])
    # Plot the histogram
    plt.plot(histogram)
    plt.title('Image Histogram')
    plt.xlabel('Pixel Value')
    plt.ylabel('Frequency')
    # Save the histogram
    plt.savefig('result/histogram.png')

# 测光方案1
def img_mean(img):
    """统计亮度均值
    :param img: 传入图像
    """
    value = float(np.mean(img))
    return value

# 测光方案2
def thresh_mean(img):
    """统计大于自适应阈值的亮度均值
    :param img: 传入图像
    """
    threshold = np.mean(img)
    img_thresh = np.where(img <= threshold, 0, img)
    # 统计大于阈值像素的亮度均值
    pix_nums = np.sum(img_thresh > 0)
    value = float(np.sum(img_thresh) / pix_nums)
    return value

# 测清晰度方案1
def orb(img):
    """
    :param path: 图像
    :return: value: 使用ORB提取出来的特征点个数
    """
    # 初始化ORB
    orb = cv2.ORB_create(100000)  # 参数是特征点的最大数量
    # 寻找关键点
    kp = orb.detect(img)
    # 画出关键点，保存
    # outimg1 = cv2.drawKeypoints(img, keypoints=kp, outImage=None)
    # cv2.imwrite('result/orb_bizhangA.bmp', outimg1)
    value = len(kp)
    return value

# 测清晰度方案2
def brenner(img):
    tmp = img[2:, :].astype(int)
    res = np.square(tmp - img[0:-2, :])
    value = np.mean(res)
    return value

