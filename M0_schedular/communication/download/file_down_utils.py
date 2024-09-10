import cv2
import os
import struct
import time
import numpy as np
import redis
import base64
import logging
from PIL import Image
# import imageio.v3 as iio
from io import BytesIO
from enum import Enum

import sys
# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)
from utils.share import LOGGER, serialize_msg, set_redis_key
from utils.constants import KEY_DOWNLOAD_STATUS

# 接收端的IP地址和端口号
RECV_PORT = 18089

# 存储
REDIS = redis.Redis(host='127.0.0.1', port=6379)
IMAGE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/received_images/"

# 后面按需替换
FILE_IMAGE = 0x00 # TODO:图片文件
FILE_LOG = 0xaa   # TODO:日志文件

# 数据分片大小
CHUNK_SIZE = 93
HEADER_SIZE = 11

class DownloadState(Enum):
    """
        下载任务状态值枚举类
    """
    NONE = 0x00             # 默认值，此时无下载任务 
    RUNNING = 0x55          # 文件正在下载
    STOPPED = 0x77          # 文件下载任务中断/取消
    FILE_ERROR = 0xAA       # 文件不存在/损坏

from message_config.udp_format import FILE_DOWN_FORMAT

# 封装文件UDP包
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

def update_download_status(state, progress):
    """
    将文件下载进度更新到redis
    """
    message = {
        'state': state,              # 文件下载状态
        'progress': progress        # 文件下载状态
    }
    json_string = serialize_msg(message)
    set_redis_key(key=KEY_DOWNLOAD_STATUS, value=json_string)

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

# 将收到的图片存储为文件
def process_image_to_file(image_data):
    # image_name = f"image_{time_s}_{time_ms}_{exposure}.bmp"
    image_name = "output.bmp"
    LOGGER.info(f"图片{image_name} 长度 {len(image_data)} bytes写入文件")
    # image = jpeg2000_decode(image_data)
    # iio.imwrite(image_name, image)

    # 转为Numpy bytes
    # image_array = np.frombuffer(image_data, dtype=np.uint8)
    # cv2.imwrite(os.path.join(IMAGE_DIR, image_name), image_array)
    # LOGGER.info(f"图片{image_name}写入文件, winsize = ({win_w}, {win_h}), window = ({win_x}, {win_y})")


# def jpeg2000_encode(image_data):
#     # 读取图像并压缩为JPEG2000格式
#     image = iio.imread('./test_images/xingmin.bmp')
#     image_np = np.array(image)
#     buffer = BytesIO()
#     iio.imwrite(buffer ,image, format='jpeg')
#     compressed_data = buffer.getvalue()
#     # with open(compressed_image_path, 'rb') as f:
#     #     compressed_data = f.read()
#     return compressed_data

# jpeg2000解码
# def jpeg2000_decode(compressed_data):
#     # 读取压缩文件并解码为图像
#     # compressed_image_path = 'compressed.jp2'
#     # with open(compressed_image_path, 'wb') as f:
#     #     f.write(compressed_data)
#     # image = iio.imread(compressed_image_path)
#     image = iio.imread(compressed_data)
#     return image