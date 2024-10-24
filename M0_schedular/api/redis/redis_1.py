import cv2
import redis
import time
import base64
import numpy as np
import os

# 初始化参数
n = 4  # 不同曝光图像的数量
interval = 1 / n  # 发送图像之间的时间间隔
win_w, win_h, win_x, win_y = 2048, 2048, 0, 0
time_s = 0 # 初始化发送图像的s值

# 初始化Redis连接
conn = redis.Redis(host='127.0.0.1', port=6379)

# P图像所在文件夹的路径
folder_path = 'path_to_test_images'

# 调整亮度的函数
def adjust_brightness(image, value):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    v = cv2.add(v, value)
    v = np.clip(v, 0, 255)
    final_hsv = cv2.merge((h, s, v))
    return cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)

# 处理文件夹中的每张图像
for filename in os.listdir(folder_path):
    image_path = os.path.join(folder_path, filename)
    img = cv2.imread(image_path)
    time_s += 1
    
    # 生成不同曝光的图像
    for i in range(n):
        exposure_value = i * (255 // (n - 1))  # 计算曝光值
        adjusted_img = adjust_brightness(img, exposure_value)

        # 将图像转换为二进制流
        _, buffer = cv2.imencode('.bmp', adjusted_img)
        img_data = buffer.tobytes()

        # 编码
        encoded_img = base64.b64encode(img_data).decode('utf-8')

        # 创建消息
        time_ms = i * (1000 // n)
        image_name = f"{filename.split('.')[0]}_{time_s}_{time_ms}_{exposure_value}.bmp"
        message = {
            'name': image_name,
            'win_size': (win_w, win_h),
            'window': [win_x, win_y],
            'delay': 0,  # 暂时设置为0
            'data': encoded_img
        }

        # 发送消息
        conn.publish("topic.img", str(message))

        # 等待一定时间间隔
        time.sleep(interval)