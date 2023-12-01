import redis
import base64
import cv2
import numpy as np

# config
conn = redis.Redis(host='127.0.0.1', port=6379)
sub = conn.pubsub()
sub.subscribe("topic.img")

# receive and process images
for message in sub.listen():
    if message['type'] == 'message':
        message_data = message['data']
        message_dict = eval(message_data)  # Convert the string message back to a dictionary

        img_name = message_dict['name']
        encoded_img = message_dict['data']
        img_data = base64.b64decode(encoded_img)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, 0)    # 0 represents grayscale

        # Process the received image (img) here
        # For example, you can display the image using OpenCV
        print("image_name: ", img_name)
        cv2.imshow('Received Image'.format(img_name), img)
        cv2.waitKey(1)