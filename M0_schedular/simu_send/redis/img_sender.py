import redis
from redis.exceptions import ConnectionError, TimeoutError
import os
import time
import base64
import cv2
import numpy as np

# 用发送时间命名图片
def get_timestamps():
    current_time = time.time()
    time_s = int(current_time)
    time_ms = int((current_time - time_s) * 1000)
    return time_s, time_ms

# 获取待发送图片列表
img_dir = os.path.dirname(os.path.abspath(__file__)) + '/images/'
img_list = sorted(os.listdir(img_dir))

# 开窗大小
windows = {
    0x00: (2048, 2048),
    0x01: (640, 640),
    0x02: (1024, 1024)
}

# 连接redis
REDIS = redis.Redis(host='127.0.0.1', port=6379)
try:
    # 尝试执行Redis操作
    for img_name in img_list:
        filename = os.path.join(img_dir, img_name)
        img = cv2.imread(filename, cv2.IMREAD_UNCHANGED)
        encoded_img = base64.b64encode(img).decode('utf-8')    # serialize
        ts, tms = get_timestamps()
        image_id = f"{ts}_{tms}"

        message = {
            'name': image_id,
            'win_size': windows[0x00],   # 0x00默认不开窗
            'window': [0, 0],
            'data': encoded_img
        }

        REDIS.publish("topic.img", str(message))    # send

        print("Image:", img_name)
        time.sleep(1)

except ConnectionError as ce:
    print("无法连接到Redis服务器:" + str(ce))

except TimeoutError:
    print("Redis操作超时")

finally:
    REDIS.close()