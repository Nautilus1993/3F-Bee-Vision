import cv2
import os
import struct
import time
import numpy as np
import redis
import base64
import logging
from PIL import Image
import imageio.v3 as iio
from io import BytesIO

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
FILE_IMAGE = 0x00 # TODO:图片文件
FILE_LOG = 0xaa   # TODO:日志文件


# 数据分片大小
CHUNK_SIZE = 93
HEADER_SIZE = 11 # TODO：暂时只加包序号调通代码



from message_config.udp_format import FILE_DOWN_FORMAT

# from utils.share import get_timestamps

# 封装图像UDP包
def pack_udp_packet(file_type, chunk_sum, chunk_seq, file_chunk):
    # 补全数据域为CHUNK_SIZE Byte定长
    byte_array = bytearray(b'0' * CHUNK_SIZE)
    byte_array[:len(file_chunk)] = file_chunk
    udp_packet = struct.pack(
        FILE_DOWN_FORMAT,        # 0. UDP包格式
        file_type,               # 1. 文件类型
        len(file_chunk),         # 2. 有效数据长度
        chunk_sum,               # 3. 分片数量
        chunk_seq,               # 4. 包序号
        bytes(byte_array)        # 5. 数据域
    )
    return udp_packet

# 解析文件UDP包
def unpack_udp_packet(udp_packet):
    file_type, \
    effect_len, \
    chunk_sum, \
    chunk_seq, \
    file_chunk \
    = struct.unpack(FILE_DOWN_FORMAT, udp_packet)
    return file_type, effect_len, chunk_sum, chunk_seq, file_chunk

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

# 解析FILE_DOWN首帧数据
def unpack_file_down_header(file_down_header):
    if len(file_down_header) != 11:
        LOGGER.warning("file_down帧头数据长度有误！")
    file_type, _, _, _, _ = struct.unpack(FILE_DOWN_FORMAT, file_down_header)
    return 


from utils.share import format_udp_packet
# 打印图像UDP数据包
def format_file_udp_packet(udp_packet):
    config_file = 'file_down_config.json'
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

def process_file_to_bin(image_data):
    file_name = f"raw_{time_s}_{time_ms}.bmp"
    with open(file_name, 'wb') as file:
        formated_bytes = format_bytes_stream(image_data)
        file.write(image_data)

# 将收到的图片存储为文件
def process_image_to_file(image_data):
    # image_name = f"image_{time_s}_{time_ms}_{exposure}.bmp"
    image_name = "output.bmp"
    LOGGER.info(f"图片{image_name} 长度 {len(image_data)} bytes写入文件")
    image = jpeg2000_decode(image_data)
    iio.imwrite(image_name, image)

    # 转为Numpy bytes
    # image_array = np.frombuffer(image_data, dtype=np.uint8)
    # cv2.imwrite(os.path.join(IMAGE_DIR, image_name), image_array)
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


def jpeg2000_encode(image_data):
    # 读取图像并压缩为JPEG2000格式
    image = iio.imread('./test_images/xingmin.bmp')
    image_np = np.array(image)
    buffer = BytesIO()
    iio.imwrite(buffer ,image, format='jpeg')
    compressed_data = buffer.getvalue()
    # with open(compressed_image_path, 'rb') as f:
    #     compressed_data = f.read()
    return compressed_data



# jpeg2000解码
def jpeg2000_decode(compressed_data):
    # 读取压缩文件并解码为图像
    # compressed_image_path = 'compressed.jp2'
    # with open(compressed_image_path, 'wb') as f:
    #     f.write(compressed_data)
    # image = iio.imread(compressed_image_path)
    image = iio.imread(compressed_data)
    return image