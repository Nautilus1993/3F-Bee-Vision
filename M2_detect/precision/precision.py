# 计算yolov5预测结果中主体的中心点精度随着距离变化


import os
import math
import matplotlib.pyplot as plt

# 真实中心点坐标
true_center = (256, 256)
# 图像大小
image_size = 512

# 目标检测结果文件夹路径
result_folder = "tools/exp14-labels"

def calculate_rmse(predictions):
    num_predictions = len(predictions)

    for prediction in predictions:
        # 提取类别和中心点坐标
        category, center_x, center_y, width, height = prediction

        if category == 1:
            # 计算中心点相对于图像大小的像素值
            pred_center = (center_x * image_size, center_y * image_size)
            # 计算均方根误差
            squared_error = (pred_center[0] - true_center[0]) ** 2 + (pred_center[1] - true_center[1]) ** 2
            return squared_error

def read_predictions(file_path):
    predictions = []
    with open(file_path, "r") as file:
        for line in file:
            # 解析每一行的预测结果
            prediction = [float(value) for value in line.strip().split()]
            predictions.append(prediction)
    return predictions

# 存储距离和像素误差的列表
distances = []
pixel_errors = []

# 遍历目标检测结果文件夹中的文件
for file_name in os.listdir(result_folder):
    if file_name.endswith(".txt"):
        # 提取文件名中的距离信息
        distance = int(file_name[:6])  # 假设文件名格式为"000030.txt"
        # if distance > 250:
        #     break
        distances.append(distance)
        file_path = os.path.join(result_folder, file_name)
        
        # 读取目标检测结果
        predictions = read_predictions(file_path)

        # 计算像素精度
        rmse = calculate_rmse(predictions)
        pixel_errors.append(rmse)
print("平均值：", sum(pixel_errors)/len(pixel_errors))
# 绘制距离与像素误差图表
plt.plot(distances, pixel_errors, 'b.')
plt.xlabel("Distance (m)")
plt.ylabel("Pixel Error")
plt.title("Pixel Error vs Distance")
plt.grid(True)
plt.savefig("exp14-labels.png", dpi=300)
