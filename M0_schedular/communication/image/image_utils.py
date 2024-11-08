import cv2
import os
import struct
import time
import numpy as np
import redis
import base64
import json
from PIL import Image

import sys
# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)
from utils.share import LOGGER
from utils.constants import TOPIC_IMG_RAW

# 存储
REDIS = redis.Redis(host='127.0.0.1', port=6379)
IMAGE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/received_images/"

# 后面按需替换
SENDER_DEVICE = 0x00 # TODO:转发板设备ID
RECV_DEVICE = 0x01   # TODO: AI计算机设备ID

# 数据分片大小
CHUNK_SIZE = 1024
HEADER_SIZE = 28 # TODO：暂时只加包序号调通代码
MAX_UNSIGNED_SHORT = 65535

# 图像UDP包格式
# https://docs.python.org/3/library/struct.html#format-characters
from message_config.udp_format import IMAGE_UDP_FORMAT, CAMERALINK_HEADER_FORMAT
from utils.share import get_timestamps
from remote_control.remote_control_utils import read_time_from_redis

def pack_udp_packet(time_s, time_ms, chunk_sum, chunk_seq, image_chunk):
    """
        封装图像UDP包
    """
    # 补全数据域为1024定长
    byte_array = bytearray(b'0' * 1024)
    byte_array[:len(image_chunk)] = image_chunk
    
    udp_packet = struct.pack(
        IMAGE_UDP_FORMAT,             
        len(image_chunk),       # 1. 有效数据长度(固定值，数值不影响图片解析程序)
        SENDER_DEVICE,          # 2. 发送方(固定值)
        RECV_DEVICE,            # 3. 接收方(固定值)
        time_s,                 # 4. 时间戳秒
        time_ms,                # 5. 时间戳毫秒
        0,                      # 6. 曝光参数(从cameralink中解析)
        chunk_sum,              # 7. 分片数量
        chunk_seq,              # 8. 包序号
        0,                      # 9. 开窗宽度w(从cameralink中解析)
        0,                      # 10. 开窗高度h(从cameralink中解析)
        0,                      # 11. 开窗左下坐标x(从cameralink中解析)
        0,                      # 12. 开窗左下坐标y(从cameralink中解析)
        bytes(byte_array)       # 13. 数据域
    )
    return udp_packet

def unpack_udp_packet(udp_packet):
    """
        解析图像UDP包
    """
    effect_len, _, _, \
    time_s, time_ms, _, \
    chunk_sum, chunk_seq, \
    win_w, win_h, win_x, win_y, \
    image_chunk \
    = struct.unpack(IMAGE_UDP_FORMAT, udp_packet)
    return time_s, time_ms, win_w, win_h, win_x, win_y, chunk_sum, chunk_seq, image_chunk

def pack_fake_cameralink_header(time_s, time_ms, exposure, win_w, win_h, win_x, win_y):
    """
        模拟生成cameralink首帧数据，仅模拟UDP发图时使用
    """
    fake_cameralink_header = struct.pack(
        CAMERALINK_HEADER_FORMAT,             
        0xeb90,                 # 1. 帧头(固定值，数值不影响图片解析程序)
        0,                      # 2. 数据长度(填充值)
        0,                      # 3. 帧类型(填充值)
        0,                      # 4. 遥测数据类型
        0,                      # 5. 遥测数据分类号
        0,                      # 6. 图像计数
        exposure,               # 7. 曝光时间
        0,                      # 8. 曝光间隔
        time_s,                 # 9. 图像拍摄时间戳秒
        time_ms,                # 10. 图像拍摄时间戳毫秒
        win_x,                  # 11. 开窗左下坐标x
        win_y,                  # 12. 开窗左下坐标y
        win_w,                  # 13. 开窗左下坐标w
        win_h,                  # 14. 开窗左下坐标h
        0,                      # 15. 校验和
        0                       # 16. 帧尾
    )
    return fake_cameralink_header

def unpack_cameralink_header(cameralink_header):
    """
        解析cameralink首帧数据
    """
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
def process_image_to_redis(image_data, time_s, time_ms, exposure, win_w, win_h, win_x, win_y):
    image_name = f"image_{time_s}_{time_ms}_{exposure}.bmp"
    # 计算接收时延
    delay = calculate_image_delay(time_s, time_ms)
    # 转为Numpy bytes
    image_array = np.frombuffer(image_data, dtype=np.uint8) 
    encoded_img = base64.b64encode(image_array).decode('utf-8')    # serialize
    # 发送Redis
    message = {
        'name': image_name,
        'win_size': (win_w, win_h),
        'window': [win_x, win_y],
        'delay': delay,
        'data': encoded_img
    }
    json_str = json.dumps(message)
    REDIS.publish(TOPIC_IMG_RAW, json_str)   
    LOGGER.info(f"图片{image_name}写入redis")

def calculate_image_delay(image_time_s, image_time_ms):
    """
        计算接收图片的时延
        输入(int, int)：图片时间戳秒，时间戳毫秒
        返回(unsigned short)：接收到图片时相距图片拍摄时的时延(单位毫秒)
    """
    # 获取当前系统时间
    sys_time_s, sys_time_ms = get_timestamps()
    # 从redis中获取最新一次星上时信息
    time_s, time_ms, _, _, delta_s, delta_ms = read_time_from_redis()
    # 计算时延
    # 图片接收时延 = 当前系统时戳 - (上次授时系统时戳 - 上次授时星上时戳) - 图片接收星上时戳
    delay_time_s = sys_time_s - delta_s - image_time_s
    delay_time_ms = sys_time_ms - delta_ms - image_time_ms
    delay = delay_time_s * 1000 + delay_time_ms
    # 检查时延的数值合法性 0~65,535
    if delay < 0 or delay > MAX_UNSIGNED_SHORT:
        LOGGER.error(f"时延数值超过范围 {delay}")
        return MAX_UNSIGNED_SHORT
    return int(delay)

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