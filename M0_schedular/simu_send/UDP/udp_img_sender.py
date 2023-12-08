import cv2
import socket
import struct
import os
import time
import logging

"""
Header: 暂时只加包序号调通代码
Byte[0:1]   有效数据长度,最后一包分片有效长度与图片大小有关 
Byte[2:5]   包总数
Byte[6:9]   包序号
Byte[10:N]  数据域固定1024bytes
"""

# 发送端的IP地址和端口号
# TODO:改为配置文件
SEND_IP = '192.168.31.17'
SEND_PORT = 8089
IMAGE_SIZE = 6621914        # 图片大小 6M.png
CHUNK_SIZE = 1024           # 图片分片长度
UDP_FORMAT = "!HII1024s"    # UDP包格式

# 在图片数据帧头包裹一层header
def pack_udp_packet(chunk_sum, chunk_seq, image_chunk):
    # 补全数据域为1024定长
    byte_array = bytearray(b'0' * 1024)
    byte_array[:len(image_chunk)] = image_chunk
    udp_packet = struct.pack(UDP_FORMAT, len(image_chunk), chunk_sum, chunk_seq, bytes(byte_array))
    return udp_packet

def send_image(filename, server_ip, server_port, chunk_size):
    # 创建UDP套接字
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 读取图像文件
    with open(filename, 'rb') as file:
        image_data = file.read()
    
    # 获取图像文件大小和分片数量
    image_size = os.path.getsize(filename)
    chunk_sum = (image_size + chunk_size - 1) // chunk_size

    # 发送图像分片
    sent_chunks = 0
    for i in range(chunk_sum):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, image_size)
        image_chunk = image_data[start:end]
        
        # 发送UDP帧
        udp_packet = pack_udp_packet(chunk_sum, i, image_chunk)
        sock.sendto(udp_packet, (server_ip, server_port))
        # print(f"发送第 {i} / {chunk_sum} 个分片，分片大小 {len(image_chunk)} bytes")
        sent_chunks += 1
    
    # 输出发送图片结束时的日志：分片数量，文件大小
    print("已发送分片数: " + str(sent_chunks))
        
    #关闭文件
    file.close()

    # 关闭套接字
    sock.close()

# 图像文件路径
img_file = './6M.png'

# 模拟1s发一张图
while(True):
    # img_list = sorted(os.listdir(img_dir))
    # for img_name in img_list:
    send_image(img_file, SEND_IP, SEND_PORT, CHUNK_SIZE)
    time.sleep(3)