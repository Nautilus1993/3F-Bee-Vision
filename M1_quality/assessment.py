import cv2
from utils import hist, img_mean, thresh_mean, orb, brenner
import redis
import base64
import numpy as np
import os

# 初始化redis
conn = redis.Redis(host='127.0.0.1', port=6379)
sub = conn.pubsub()
sub.subscribe("topic.img")

print("Receiving...")

# 通过redis收图做预测
for item in sub.listen():
    if item['type'] == 'message':
        print(".-- .- -.. .-.. --- ...- . .-- ..-. -.--")
        # 收到图像数据解析
        message_data = item['data']
        message_dict = eval(message_data)  # Convert the string message back to a dictionary
        img_name = message_dict['name']
        encoded_img = message_dict['data']
        img_data = base64.b64decode(encoded_img)
        # nparr = np.frombuffer(img_data, np.uint8)
        # img = cv2.imdecode(nparr, 0)  # 0 represents grayscale
        nparr = np.frombuffer(img_data, np.uint8)
        img = np.resize(nparr,(2048, 2048))

        # 图像评估
        img_mean_value = img_mean(img)
        thresh_mean_value = thresh_mean(img)
        orb_value = orb(img)
        brenner_value = brenner(img)

        print("图像名称为: ", img_name)
        print("图像平均亮度为: {:.6f}".format(img_mean_value))
        print("图像自适应阈值亮度为: {:.6f}".format(thresh_mean_value))
        print("图像orb特征点数量为: {:.6f}".format(orb_value))
        print("图像brenner清晰度为: {:.6f}".format(brenner_value))

        # 定义文件路径
        file_path = '/usr/src/app/result/result.txt'
        # 检查文件大小
        max_file_size = 100 * 1024 * 1024  # 100MB
        file_size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
        # 决定写入模式
        write_mode = 'w' if file_size >= max_file_size else 'a'

        # 写入文件
        with open(file_path, write_mode) as file:
            file.write(".-- .- -.. .-.. --- ...- . .-- ..-. -.--")
            file.write("图像名称为: " + img_name + "\n")
            file.write("图像平均亮度为: {:.6f}\n".format(img_mean_value))
            file.write("图像自适应阈值亮度为: {:.6f}\n".format(thresh_mean_value))
            file.write("图像orb特征点数量为: {:.6f}\n".format(orb_value))
            file.write("图像brenner清晰度为: {:.6f}\n".format(brenner_value))