import redis
import base64
import cv2
import numpy as np
import datetime
import os

# config
conn = redis.Redis(host='127.0.0.1', port=6379)
sub = conn.pubsub()
sub.subscribe("topic.img")

# 收到图片存放位置(和程序在同一路径下)
img_dir = os.path.dirname(os.path.abspath(__file__)) + "/received_images/"

# 用当前时间命名图像数据
def generate_image_name():
    current_time = datetime.datetime.now()
    time_string = current_time.strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"file_{time_string}.png"
    return file_name

# 将图片数据存入文件
def process_image(image_name, image_data):
    # 存储到文件 
    filename = os.path.join(img_dir, image_name)
    with open(filename, 'wb') as file:
        file.write(image_data)

# receive and process images
for message in sub.listen():
    if message['type'] == 'message':
        message_data = message['data']
        message_dict = eval(message_data)  # Convert the string message back to a dictionary

        img_name = message_dict['name']
        encoded_img = message_dict['data']
        img_data = base64.b64decode(encoded_img)
        # nparr = np.frombuffer(img_data, np.uint8)
        # img = cv2.imdecode(nparr, 0)    # 0 represents grayscale
        process_image(img_name, img_data)

        # Process the received image (img) here
        # For example, you can display the image using OpenCV
        print("saved image : ", img_name)
        # cv2.imshow('Received Image'.format(img_name), img)
        # cv2.waitKey(1)