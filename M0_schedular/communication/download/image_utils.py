import cv2
import os
import struct
import time
import numpy as np
import redis
import base64
import logging
from PIL import Image

import sys
# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)
from utils.share import LOGGER

# 接收端的IP地址和端口号
RECV_PORT = 18089

# 存储
REDIS = redis.Redis(host='127.0.0.1', port=6379)
IMAGE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/received_images/"
TOPIC_IMG_RAW = "topic.img_raw"
TOPIC_IMG = "topic.img"

# 后面按需替换
SENDER_DEVICE = 0x00 # TODO:转发板设备ID
RECV_DEVICE = 0x01   # TODO: AI计算机设备ID
EXPOSE = 0x03 
WINDOW_SIZE = 0   # TODO 后面需要根据收包内容更改

# 数据分片大小
CHUNK_SIZE = 1024
HEADER_SIZE = 28 # TODO：暂时只加包序号调通代码
IMAGE_SIZE = 4195382 # 图片大小 2048.bmp

# 图像UDP包格式
# https://docs.python.org/3/library/struct.html#format-characters
from message_config.udp_format import IMAGE_UDP_FORMAT, CAMERALINK_HEADER_FORMAT

from utils.share import get_timestamps

# 封装图像UDP包
def pack_udp_packet(time_s, time_ms, window, chunk_sum, chunk_seq, image_chunk):
    # 补全数据域为1024定长
    byte_array = bytearray(b'0' * 1024)
    byte_array[:len(image_chunk)] = image_chunk
    
    udp_packet = struct.pack(
        IMAGE_UDP_FORMAT,             
        len(image_chunk),       # 1. 有效数据长度
        SENDER_DEVICE,          # 2. 发送方
        RECV_DEVICE,            # 3. 接收方
        time_s,                 # 4. 时间戳秒
        time_ms,                # 5. 时间戳毫秒
        EXPOSE,                 # 6. 曝光参数
        chunk_sum,              # 7. 分片数量
        chunk_seq,              # 8. 包序号
        window[0],              # 9. 开窗宽度w
        window[1],              # 10. 开窗高度h
        window[2],              # 11. 开窗左下坐标x
        window[3],              # 12. 开窗左下坐标y
        bytes(byte_array)       # 13. 数据域
    )
    return udp_packet

# 解析图像UDP包
def unpack_udp_packet(udp_packet):
    effect_len, _, _, \
    time_s, time_ms, _, \
    chunk_sum, chunk_seq, \
    win_w, win_h, win_x, win_y, \
    image_chunk \
    = struct.unpack(IMAGE_UDP_FORMAT, udp_packet)
    # return time_s, time_ms, win_w, win_h, win_x, win_y, chunk_sum, chunk_seq, image_chunk[:effect_len]
    return time_s, time_ms, win_w, win_h, win_x, win_y, chunk_sum, chunk_seq, image_chunk

# 解析cameralink首帧数据
def unpack_cameralink_header(cameralink_header):
    if len(cameralink_header) != 29:
        LOGGER.warning("cameralink帧头数据长度有误！")
    frame_header, _, _, _, \
    _, _, exposure, _, \
    time_s, time_ms, win_x, win_y, \
    win_w, win_h, _, _ \
     = struct.unpack(CAMERALINK_HEADER_FORMAT, cameralink_header)
    return time_s, time_ms, exposure, win_w, win_h, win_x, win_y
    

from utils.share import format_udp_packet
# 打印图像UDP数据包
def format_image_udp_packet(udp_packet):
    config_file = 'image_config.json'
    config_file_path = parent_dir + "/message_config/" + config_file
    format_udp_packet(udp_packet, config_file_path)

# 打印星敏帧头数据包
def format_cameralink_header(cameralink_header):
    config_file = 'cameralink_config.json'
    config_file_path = parent_dir + "/message_config/" + config_file
    format_udp_packet(cameralink_header, config_file_path)

# 将收到的图片发给redis
def process_image_to_redis(image_data, time_s, time_ms, win_w, win_h, win_x, win_y):
    image_name = f"image_{time_s}_{time_ms}.bmp"
    # 转为Numpy bytes
    image_array = np.frombuffer(image_data, dtype=np.uint8) 
    encoded_img = base64.b64encode(image_array).decode('utf-8')    # serialize
    # 发送Redis
    message = {
        'name': image_name,
        'win_size': (win_w, win_h),
        'window': [win_x, win_y],
        'data': encoded_img
    }
    REDIS.publish("topic.img", str(message))   
    LOGGER.info(f"图片{image_name}写入redis")

"""
    format打印的Bytes格式，用于对照每个字节和接收方是否一致
"""
def format_bytes_stream(byte_stream):
    formatted_stream = ""
    for i, byte in enumerate(byte_stream):
        formatted_stream += f"{byte:02X}"
        if (i + 1) % 2 == 0:
            formatted_stream += " "
        if (i + 1) % 16 == 0:
            formatted_stream += "\n"
    return formatted_stream

def process_image_to_bin(image_data):
    time_s, time_ms = get_timestamps()
    file_name = f"raw_{time_s}_{time_ms}.bmp"
    with open(file_name, 'wb') as file:
        formated_bytes = format_bytes_stream(image_data)
        file.write(image_data)

# 将收到的图片存储为文件
def process_image_to_file(image_data, time_s, time_ms, exposure, win_w, win_h, win_x, win_y):
    # image_name = f"image_{time_s}_{time_ms}_{exposure}.bmp"
    image_name = "output.bmp"
    LOGGER.info(f"图片{image_name} 长度 {len(image_data)} bytes写入文件, winsize = ({win_w}, {win_h}), window = ({win_x}, {win_y})")

    # 转为Numpy bytes
    image_array = np.frombuffer(image_data, dtype=np.uint8) 
    image_array.resize(win_h, win_w)
    cv2.imwrite(os.path.join(IMAGE_DIR, image_name), image_array)
    # LOGGER.info(f"图片{image_name}写入文件, winsize = ({win_w}, {win_h}), window = ({win_x}, {win_y})")

def write_to_bytes(bytes_string, file_name):
    file_path = os.path.join(IMAGE_DIR, file_name)
    with open(file_path, 'wb') as file:
        file.write(bytes_string)


# 将收到的图片存储为文件
def process_image_test(image_data, time_s, time_ms, win_x, win_y):
    # timestamp
    current_time = time.time()
    time_s = int(current_time)
    time_ms = int((current_time - time_s) * 1000)
    image_name = f"image_{time_s}_{time_ms}.bmp"
    # 转为Numpy bytes
    # image_array = np.frombuffer(image_data, dtype=np.uint8)
    image_array = np.frombuffer(image_data, dtype=np.uint16)
    # encoded_img = base64.b64encode(image_array).decode('utf-8')    # serialize
    image_array.resize(512, 512)
    normed = cv2.normalize(image_array, dst=None, alpha=0, beta=65535, norm_type=cv2.NORM_MINMAX)
    encoded_img = base64.b64encode(normed).decode('utf-8')    # serialize
    # 发送Redis
    message = {
        'name': image_name,
        'win_size': (512, 512),
        'window': [win_x, win_y],
        'data': encoded_img
    }
    REDIS.publish("topic.img", str(message)) 
    # 存储到文件 
    cv2.imwrite(os.path.join(IMAGE_DIR, image_name), normed)
    # txt_name = f"image_{time_s}_{time_ms}.txt"
    # write_to_bytes(image_data, txt_name)

# 输入2048的原图，以左下坐标x,y为起点，剪窗口宽度为w, 高度为h的窗口并存储为文件
def crop_image(w, h, x, y, image_name) -> np.array:
    # 计算右上角x, y坐标
    origin_image = Image.open(image_name)
    x_left = x
    x_right = x + w
    y_top = origin_image.size[1] - (y + h)      
    y_bottom = origin_image.size[1] - y
    if x_right > 2048 or y_bottom > 2048 or x_left < 0 or y_top < 0:
        print("裁剪窗口超出原图尺寸大小！")
        return np.array([])
    cropped_image = origin_image.crop((x_left, y_top, x_right, y_bottom))
    image_array = np.array(cropped_image)
    return image_array