import redis
import os
import time
import base64
import cv2

# config
img_dir = 'images/'
conn = redis.Redis(host='127.0.0.1', port=6379)

# get image name
img_list = sorted(os.listdir(img_dir))

# send
for img_name in img_list:
    filename = os.path.join(img_dir, img_name)
    img = cv2.imread(filename)

    _, img_data = cv2.imencode('.png', img)    # convert np matrix to bytes
    encoded_img = base64.b64encode(img_data).decode('utf-8')    # serialize

    message = {
        'name': img_name,
        'win_size': (1024, 1024),
        'window': [512, 512],
        'data': encoded_img
    }

    conn.publish("topic.img", str(message))    # send

    print("Image:", img_name)
    time.sleep(1)
