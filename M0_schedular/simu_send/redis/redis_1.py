import redis
import os
import time
from datetime import datetime, timedelta
import base64
import cv2
from PIL import Image, ImageEnhance
import json

# config
image_folder = '/home/ywang/Documents/3F-Bee-Vision/M0_schedular/simu_send/redis/camera_image/'
REDIS = redis.Redis(host='127.0.0.1', port=6379)
REDIS_1_TOPIC = "topic.raw_img"

# 定义亮度增强因子（0.0为完全黑暗，1.0为原始亮度，大于1.0为增加亮度）
brightness_factors = [0.3, 0.5, 0.7, 0.9]

# 输入一张图片的文件路径，输出生成四种亮度的图片
def scroll_images(input_image, result_folder, time_s, time_ms):
    for factor in brightness_factors:
        # 创建亮度增强对象
        enhancer = ImageEnhance.Brightness(input_image)      
        # 增强亮度
        output_image = enhancer.enhance(factor)
        # 保存输出图片
        output_image.save(f"{result_folder}/{time_s}_{time_ms}_{int(factor * 100)}.bmp")

# 生成星上时格式的时间戳
def get_timestamps():
    current_time = time.time()
    time_s = int(current_time)
    time_ms = int((current_time - time_s) * 1000)
    return time_s, time_ms

def generate_images(image_file, timestamps):
    # 创建处理结果存储路径
    if not os.path.exists(image_file):
        print("文件不存在！")
        return
    # 获取待处理文件列表
    format_time = time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime(time.time()))
    scroll_folder = image_folder + f"image_{format_time}/"
    os.makedirs(scroll_folder)

    # 根据星上时时间戳，生成对应的图像文件
    input_image_path = os.path.join(scroll_folder, image_file)
    input_image = Image.open(input_image_path)
    # TODO：暂时使用当前时间戳，后面可以改为从redis中获取星上时时间戳
    # time_s, time_ms = get_timestamps()
    for timestamp in timestamps:
        ts, tms = timestamp
        scroll_images(input_image, scroll_folder, ts, tms)
    return scroll_folder

def time_sync(interval, start_time=None):
    """
    计算需要 sleep 的时间，以确保在指定的时间间隔后精准执行任务。
    
    参数:
    interval (float): 时间间隔，以毫秒为单位。
    start_time (datetime, optional): 开始时刻
    
    返回:
    float: 需要 sleep 的时间，以秒为单位。
    """
    if start_time is None:
        start_time = datetime.now()
    # 计算下一次执行任务的时间点
    next_time = (start_time + timedelta(milliseconds=interval))
    # 计算从当前时间到下一次执行任务的时间差
    current_time = datetime.now()
    sleep_time = (next_time - current_time).total_seconds()
    time.sleep(sleep_time)
    return sleep_time


def send_image_to_redis(scroll_folder):
    
    image_list = sorted(os.listdir(scroll_folder))
    try:
        # 尝试执行Redis操作
        for image_name in image_list:
            start_time = datetime.now()
            file_path = os.path.join(scroll_folder, image_name)
            img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
            encoded_img = base64.b64encode(img).decode('utf-8')    # serialize
            message = {
                'name': image_name,
                'win_size': (2048, 2048),   # 不开窗
                'window': [0, 0],
                'data': encoded_img
            }
            json_str = json.dumps(message)
            REDIS.publish(REDIS_1_TOPIC, json_str)    # send
            print("Image:", image_name)
            time_sync(0.25 * 1000, start_time)

    except ConnectionError as ce:
        print("无法连接到Redis服务器:" + str(ce))

    except TimeoutError:
        print("Redis操作超时")

    finally:
        REDIS.close()

timestamps = [
    (10, 0),
    (20, 0),
    (30, 0),
    (40, 0)
]

def main():
    image_file = "/home/ywang/Documents/3F-Bee-Vision/M0_schedular/simu_send/redis/camera_image/xingmin.bmp"
    # scroll_folder = generate_images(image_file, timestamps)
    # print(scroll_folder)
    scroll_folder = "/home/ywang/Documents/3F-Bee-Vision/M0_schedular/simu_send/redis/camera_image/image_2024-07-05-09:48:39"
    while True:
        send_image_to_redis(scroll_folder)

if __name__=="__main__":
    main()

