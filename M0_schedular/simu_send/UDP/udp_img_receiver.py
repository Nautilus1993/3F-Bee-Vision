import cv2
import os
import socket
import struct
import time
import datetime
import numpy as np
import redis
import base64
import sys

# Add the parent directory to the sys.path list
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
from utils.image_utils import unpack_udp_packet, LOGGER, CHUNK_SIZE, HEADER_SIZE, IP_ADDRESS

# 接收端的IP地址和端口号
RECV_PORT = 8089

# UDP_FORMAT = "!HII1024s"    # UDP包格式

# 图像大小(按实际情况调整)
IMAGE_SIZE = 263222 # 图片大小 000030.bmp

# 收到图片存放位置(和程序在同一路径下)
img_dir = os.path.dirname(os.path.abspath(__file__)) + "/received_images/"

# 用当前时间命名图像数据
def generate_image_name():
    current_time = datetime.datetime.now()
    time_string = current_time.strftime("%Y-%m-%d_%H-%M-%S")
    file_name = f"file_{time_string}.png"
    return file_name

# 将图片数据存入文件
def process_image(image_data):
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
    conn.publish("topic.img", str(message))   
    # 存储到文件 
    filename = os.path.join(img_dir, image_name)
    with open(filename, 'wb') as file:
        file.write(image_data)

def receive_image(buffer_size):
    # 以包序号为key存储UDP包中的有效数据
    received_packets = {}
    received_chunks = 0

    while True:
        udp_packet, addr = sock.recvfrom(buffer_size)
        # TODO:完善解析UDP的逻辑
        chunk_sum, chunk_seq, image_chunk = unpack_udp_packet(udp_packet)
        # print(f"接收到编号 {chunk_seq} 的分片，分片大小 {len(image_chunk)} bytes")

        # 如果收到第一帧时字典和计数器非空，说明上一张图片有丢包
        if chunk_seq == 0:
            if(len(received_packets) != 0):
                print("丢包:!收到第一帧数据，字典非空，清空received_packet重新接收")
            received_packets = {}
            received_chunks = 0

        # 将当前Packet加入
        if chunk_seq not in received_packets:
            received_packets[chunk_seq] = image_chunk
            received_chunks += 1

        # 如果是最后一帧，判断目前是否收到所有的包；若完整收到一幅图，组包存储为图片文件
        if chunk_seq == (chunk_sum - 1):
            if len(received_packets) == chunk_sum:
                print("已接收到所有分片共 " + str(len(received_packets)) + " 个")
                # Concatenate the packets in the correct order
                sorted_packets = [received_packets[i] for i in range(chunk_sum)]
                image_data = b''.join(sorted_packets)
                received_packets = {}
                process_image(image_data)
            else:
                print(f"还未收全，应收到 {chunk_sum}, 已收到 {len(received_packets)}")
                return 

    # 关闭套接字
    # sock.close()

# 创建UDP套接字
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    
# 绑定IP地址和端口号
sock.bind((IP_ADDRESS, RECV_PORT))
conn = redis.Redis(host='127.0.0.1', port=6379)

while(True):
    print("start server")
    try:
        # buffer_size: UDP包的大小，每次接收定长的UDP包
        buffer_size = HEADER_SIZE + CHUNK_SIZE
        receive_image(buffer_size)

    except socket.error as e:
        # 没有数据可读，错误码为 EWOULDBLOCK 或 EAGAIN
        if e.errno == socket.errno.EWOULDBLOCK or e.errno == socket.errno.EAGAIN:
            print('No data received')
        else:
            # 其他错误，需要处理
            print('Error:', e)
            break