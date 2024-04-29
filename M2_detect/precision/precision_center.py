"""计算三种类别的中心点预测精度，目前仅考虑预测框正确的情况"""

import os
import math
import matplotlib.pyplot as plt
import matplotlib.cm as cm  # 导入色彩映射模块
import numpy as np

def read_predictions(file_path):
    predictions = []
    with open(file_path, "r") as file:
        for line in file:
            # 解析每一行的预测结果
            prediction = [float(value) for value in line.strip().split()]
            predictions.append(prediction)
    return predictions


def calculate_rmse(predictions, truth):
    category_errors = {0: [], 1: [], 2: []}
    for prediction in predictions:
        # 提取类别和中心点坐标
        category, center_x, center_y, width, height = prediction

        if category in [0, 1, 2]:
            # 预测值中心点
            pred_center = (center_x * image_size, center_y * image_size)
            # 真值中心点
            for i in truth:
                if i[0] == category:
                    truth_center = (i[1]* image_size, i[2]* image_size)
                    print('truth_center: ', truth_center)
            # 计算均方根误差
            squared_error = ((pred_center[0]-truth_center[0])**2 + (pred_center[1]-truth_center[1])**2) ** 0.5
            category_errors[category].append(squared_error)
    return category_errors

if __name__ == "__main__":
    # 图像大小
    image_size = 2048
    # 目标检测结果文件夹路径
    pred_folder = "data/bh/40m精度评定/预测值"
    truth_folder = "data/bh/40m精度评定/真值"
    # 存储不同类别的像素误差
    category_errors = {0: [], 1: [], 2: []}

    # 遍历目标检测结果文件夹中的文件
    for file_name in os.listdir(pred_folder):
        if file_name.endswith(".txt"):
            pred_file_path = os.path.join(pred_folder, file_name)
            truth_file_path = os.path.join(truth_folder, file_name)    
            # 读取目标检测结果
            predictions = read_predictions(pred_file_path)
            print('pred: ', predictions)
            # 读取真值检测结果
            truth = read_predictions(truth_file_path)
            print('truth: ', truth)

            # 计算不同类别的像素误差
            file_errors = calculate_rmse(predictions, truth)
            for category, errors in file_errors.items():
                category_errors[category].extend(errors)
    print('各个类别误差：', category_errors)

    # 设置颜色映射
    # 设置颜色映射
    colors = ['#4CAF50', '#FF9800', '#2196F3']
    # 绘制箱线图
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    data = [category_errors[0], category_errors[1], category_errors[2]]
    boxplot = ax.boxplot(data, patch_artist=True, labels=['L', 'Ball', 'D_cabin'])
    # 设置每个箱线图的颜色
    for patch, color in zip(boxplot['boxes'], colors):
        patch.set_facecolor(color)
    # 设置标题
    ax.set_title('Pixel Error Boxplot for Different Categories', fontsize=16)
    ax.set_xlabel('Category', fontsize=14)
    ax.set_ylabel('Pixel Error', fontsize=14)
    ax.grid()
    plt.tight_layout()
    # 保存高清图片
    plt.savefig('pixel_error_boxplot.png', dpi=300, bbox_inches='tight')
    plt.show()