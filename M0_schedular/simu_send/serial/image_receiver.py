import cv2
import time
import os
from datetime import datetime
import numpy as np
import redis
import base64

IMAGE_FOLDER = '/root/workspace/3F-Bee-Vision/M0_schedular/simu_send/serial/data'

# 存储
REDIS = redis.Redis(host='127.0.0.1', port=6379)

# 将收到的图片发给redis并存储为文件
def send_image_redis(image_data, image_name):
    message = {
        'name': image_name,
        'window': [0, 0],
        'win_size': [2048,2048],
        'data': image_data
    }
    REDIS.publish("topic.img", str(message))  

# 将图片文件转化为bytes流
def get_image_array(image_name):
    img = cv2.imread(image_name, cv2.IMREAD_UNCHANGED)
    encoded_img = base64.b64encode(img).decode('utf-8')    # serialize
    return encoded_img

# 根据图片文件名解析为星上时时间戳格式
# 文件命名规则为“YYYYMMDD_ HHMMSS_ xx.img”，其中“YYYYMMDD”为日期，“HIHMIMSS”为时间，“xx”为顺序号，从01到10，即每秒钟最多接收10帧。
def parse_time_string(time_string):
    # 解析日期和时间部分
    date_str, time_str, _ = time_string.split('_')

    # 解析日期部分
    date = datetime.strptime(date_str, "%Y%m%d").date()

    # 解析时间部分
    time = datetime.strptime(time_str, "%H%M%S").time()

    # 组合日期和时间
    combined_datetime = datetime.combine(date, time)

    # 计算秒和毫秒
    seconds = int(combined_datetime.timestamp())
    milliseconds = int(combined_datetime.microsecond / 1000)

    return seconds, milliseconds

# 从某个指定路径中获取最新的图片
# TODO(wangyuhang): 增加文件路径不存在的异常判断
def get_latest_image(folder_path):
    # 获取文件夹中的所有文件
    file_list = os.listdir(folder_path)
    # 过滤出图片文件
    
    image_files = [f for f in file_list if f.endswith('.jpg') or f.endswith('.png')]
    images = []
    for f in image_files:
        images.append(folder_path + '/' + f)
    print(images)
    if images:
        # 获取最新的图片文件
        latest_image = max(images, key=os.path.getctime)
        print("最新图片:", latest_image)
        return latest_image.split("/")[-1]
    return None

def receive_image():
    image_name = get_latest_image(IMAGE_FOLDER)
    time_s, time_ms = parse_time_string(image_name)
    image_path = IMAGE_FOLDER + '/' + image_name
    image_data = get_image_array(image_path)
    send_image_redis(image_data, image_name)

def main():
    while(True):
        receive_image()
        time.sleep(3)

if __name__=="__main__":
    main()