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

# 数据分片大小
CHUNK_SIZE = 1024
HEADER_SIZE = 10 # TODO：暂时只加包序号调通代码
IP_ADDRESS = '192.168.29.201'

# 日志
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

# 输出到控制台
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)

"""
Header: 暂时只加包序号调通代码
Byte[0:1]   有效数据长度,最后一包分片有效长度与图片大小有关 
Byte[2:5]   包总数
Byte[6:9]   包序号
Byte[10:N]  数据域固定1024bytes
"""
# 图像UDP包格式
UDP_FORMAT = "!HII1024s"

# 封装图像UDP包
def pack_udp_packet(chunk_sum, chunk_seq, image_chunk):
    # 补全数据域为1024定长
    byte_array = bytearray(b'0' * 1024)
    byte_array[:len(image_chunk)] = image_chunk
    udp_packet = struct.pack(UDP_FORMAT, len(image_chunk), chunk_sum, chunk_seq, bytes(byte_array))
    return udp_packet

# 解析图像UDP包
def unpack_udp_packet(udp_packet):
    effect_len, \
    chunk_sum, \
    chunk_seq, \
    image_chunk \
    = struct.unpack(UDP_FORMAT, udp_packet)
    return chunk_sum, chunk_seq, image_chunk[:effect_len]

# 用当前时间命名图像数据
def generate_image_name():
    current_time = datetime.datetime.now()
    time_string = current_time.strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"file_{time_string}.png"
    return file_name

# UDP收包测试函数，返回counter计数器
def check_image_receiving_status(counter, chunk_sum, chunk_seq):
    # 如果是第一包，判断当前计数器是否为0
    if chunk_seq == 0 and counter != 0:
        LOGGER.info(f"丢包:!收到第一帧数据，计数器非空 counter = {counter}")
        counter = 0

    counter += 1

    # 如果是最后一帧，判断目前是否收到所有的包
    if chunk_seq == (chunk_sum - 1):
        if counter == chunk_sum:
            LOGGER.info("已接收到所有分片共 " + str(counter) + " 个")
            # Concatenate the packets in the correct order
        else:
            LOGGER.info(f"还未收全，应收到 {chunk_sum}, 已收到 {counter}")
        counter = 0
    return counter

# 将收到的图片发给redis并存储为文件
def process_image(image_data, redis_conn, filename):
    # TODO: 文件名改为从UDP包中读取
    image_name = generate_image_name()
    # 转为Numpy bytes
    image_array = np.frombuffer(image_data, dtype=np.uint8) 
    encoded_img = base64.b64encode(image_array).decode('utf-8')    # serialize
    # 发送Redis
    message = {
        'name': image_name,
        'data': encoded_img
    }
    redis_conn.publish("topic.img", str(message))   
    # 存储到文件 
    with open(filename, 'wb') as file:
        file.write(image_data)