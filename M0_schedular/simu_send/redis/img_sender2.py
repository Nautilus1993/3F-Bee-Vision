import redis
import os
import time
import base64
import cv2
import random

# config
img_dir = 'images/'
conn = redis.Redis(host='127.0.0.1', port=6379)

# get image name
img_list = sorted(os.listdir(img_dir))


def generate_image_filename():
    # 获取当前时间的时间戳
    current_time = time.time()
    
    # 将时间戳分成秒和毫秒
    seconds = int(current_time)
    milliseconds = int((current_time - seconds) * 1000)
    
    # 生成文件名
    filename = f"image_{seconds}_{milliseconds}_{random.randint(1000, 9999)}.bmp"
    return filename


# send
for img_name in img_list:
    filename = os.path.join(img_dir, img_name)
    img = cv2.imread(filename)

    _, img_data = cv2.imencode('.png', img)    # convert np matrix to bytes
    encoded_img = base64.b64encode(img_data).decode('utf-8')    # serialize

    message = {
        'name': generate_image_filename(),
        'win_size': (2048, 2048),
        'window': [0, 0],
        'data': encoded_img
    }

    conn.publish("topic.img", str(message))    # send

    print("Image:", img_name)
    time.sleep(1)
