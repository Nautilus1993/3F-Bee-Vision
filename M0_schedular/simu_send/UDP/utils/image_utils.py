import cv2
import os
import socket
import struct
import time
import datetime
import numpy as np
import redis
import base64
import logging

# 日志输出到控制台
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)

# 接收端的IP地址和端口号
RECV_PORT = 8090
IP_ADDRESS = '192.168.29.201'

# 存储
REDIS = redis.Redis(host='127.0.0.1', port=6379)
IMAGE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/received_images/"


# 后面按需替换
SENDER_DEVICE = 0x00 # TODO:转发板设备ID
RECV_DEVICE = 0x01   # TODO: AI计算机设备ID
EXPOSE = 0x03 
WINDOW_SIZE = 0   # TODO 后面需要根据收包内容更改
win_x = 0
win_y = 0

# 数据分片大小
CHUNK_SIZE = 1024
HEADER_SIZE = 25 # TODO：暂时只加包序号调通代码
IMAGE_SIZE = 4195382 # 图片大小 2048.bmp

# 图像UDP包格式
# https://docs.python.org/3/library/struct.html#format-characters
UDP_FORMAT = "!HBB" + "IHH" + "IIB" + "HH1024s"

# 封装图像UDP包
def pack_udp_packet(time_s, time_ms, chunk_sum, chunk_seq, image_chunk):
    # 补全数据域为1024定长
    byte_array = bytearray(b'0' * 1024)
    byte_array[:len(image_chunk)] = image_chunk
    
    udp_packet = struct.pack(
        UDP_FORMAT,             
        len(image_chunk),       # 1. 有效数据长度
        SENDER_DEVICE,          # 2. 发送方
        RECV_DEVICE,            # 3. 接收方
        time_s,                 # 4. 时间戳秒
        time_ms,                # 5. 时间戳毫秒
        EXPOSE,                 # 6. 曝光参数
        chunk_sum,              # 7. 分片数量
        chunk_seq,              # 8. 包序号
        WINDOW_SIZE,            # 9. 开窗大小(2048或640)
        win_x,                  # 10. 开窗x
        win_y,                  # 11. 开窗y
        bytes(byte_array)       # 12. 数据域
    )
    return udp_packet

# 解析图像UDP包
def unpack_udp_packet(udp_packet):
    effect_len, _, _, \
    time_s, time_ms, _, \
    _, win_x, win_y, \
    chunk_sum, chunk_seq, image_chunk \
    = struct.unpack(UDP_FORMAT, udp_packet)
    return time_s, time_ms, win_x, win_y, chunk_sum, chunk_seq, image_chunk[:effect_len]

# 将收到的图片发给redis并存储为文件
def process_image(image_data, time_s, time_ms, win_x, win_y):
    image_name = f"image_{time_s}_{time_ms}.png"
    # 转为Numpy bytes
    image_array = np.frombuffer(image_data, dtype=np.uint8) 
    encoded_img = base64.b64encode(image_array).decode('utf-8')    # serialize
    # 发送Redis
    message = {
        'name': image_name,
        'window': [win_x, win_y],
        'data': encoded_img
    }
    REDIS.publish("topic.img", str(message))   
    # 存储到文件 
    # with open(os.path.join(IMAGE_DIR, image_name), 'wb') as file:
    #     file.write(image_data)