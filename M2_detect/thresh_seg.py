"""
自适应阈值分割，输入图像，输出基于平均亮度作为阈值的前后景分割结果
"""
import os
import numpy as np
import cv2
from tqdm import tqdm

def thresh_mean(img):
    """基于全局阈值(图像均值)的简单图像二值化分割
    :param img: 灰度图像
    :return: 前景
    """
    # 自适应阈值，因为室内有背景，需要稍微加点偏置
    threshold = np.mean(img) + 20
    # 基于threshold对图像进行二值分割,大于区域为1,小于区域为0
    result = np.where(img > threshold, 255, 0)
    return result

img_dir = 'images'
output_dir = 'output'

for file_name in tqdm(os.listdir(img_dir)):
    img_path = os.path.join(img_dir, file_name)
    output_path = os.path.join(output_dir, file_name)
    img = cv2.imread(img_path, 0)
    img_seg = thresh_mean(img)
    cv2.imwrite(output_path, img_seg)

