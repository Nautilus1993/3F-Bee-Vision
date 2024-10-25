import cv2
import redis
import time
import base64
import numpy as np
import os
import json

# 初始化参数
n = 3  # 不同曝光图像的数量
interval = 1 / n  # 发送图像之间的时间间隔
win_w, win_h, win_x, win_y = 2048, 2048, 0, 0
time_s = 0 # 初始化发送图像的s值
exposure_value = [1.0, 0.5, 2.0, 4.0]
exposure_time = [100, 50, 200, 400]

# 初始化Redis连接
conn = redis.Redis(host='127.0.0.1', port=6379)

# P图像所在文件夹的路径
folder_path = 'test_image'

# 调整亮度的函数
def adjust_brightness(image, value):
    exposure_img = cv2.convertScaleAbs(img, alpha=value, beta=0)
    return exposure_img

# 处理文件夹中的每张图像
for filename in os.listdir(folder_path):
    print(filename)
    image_path = os.path.join(folder_path, filename)
    img = cv2.imread(image_path, 0)
    time_s += 1
    
    # 生成不同曝光的图像
    for i in range(n):
        adjusted_img = adjust_brightness(img, exposure_value[i])

        # 将图像转换为二进制流
        img_data = adjusted_img.tobytes()

        # 编码
        encoded_img = base64.b64encode(img_data).decode('utf-8')

        # 创建消息
        time_ms = i * (1000 // n)
        image_name = f"{filename.split('.')[0]}_{time_s}_{time_ms}_{exposure_time[i]}.bmp"
        print(image_name)
        # cv2.imwrite(image_name, adjusted_img)
        message = {
            'name': image_name,
            'win_size': (win_w, win_h),
            'window': [win_x, win_y],
            'delay': 0,  # 暂时设置为0
            'data': encoded_img
        }
        json_str = json.dumps(message)
        # 发送消息
        conn.publish("topic.raw_img", json_str)

        # 等待一定时间间隔
        time.sleep(interval)
