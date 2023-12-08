import cv2
import socket
import struct
import os
import time
import logging

"""
Header 
Byte[0:1]   data length
Byte[2]     data receiver
Byte[3]     data sender
Byte[4:7]   timestamp of image in second
Byte[8:11]  timestamp of image in millisecond
Byte[12]    chunk number
Byte[13]    package sequence number
Byte[14:14 + 1024] data
"""

# 发送端的IP地址和端口号
SEND_IP = '192.168.31.17'
SEND_PORT = 8089
IMAGE_SIZE = 2207156 # 6621914 6M.png
CHUNK_SIZE = 1024    # 图片分片长度
HEADER_SIZE = 8 # TODO：暂时只加报序号调通代码

# 在图片数据帧头包裹一层header
def pack_udp_frame(chunk_sum, chunk_seq, image_chunk):
    packet_format = "!HII1024s"
    print(f"Pack UDP packet {chunk_seq}/{chunk_sum}, image_chunk length is {len(image_chunk)}")
    udp_frame = struct.pack(packet_format, len(image_chunk), chunk_sum, chunk_seq, image_chunk)
    return udp_frame



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
    send_chunks = 0
    for i in range(chunk_sum):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, image_size)
        image_chunk = image_data[start:end]
        
        # 发送UDP帧
        udp_frame = pack_udp_frame(chunk_sum, i, image_chunk)
        # print(f"Sent packet {i}/{chunk_sum}: {len(image_chunk)} bytes")
        sock.sendto(udp_frame, (server_ip, server_port))
        send_chunks += 1
    
    # 输出发送图片结束时的日志：分片数量，文件大小
    print("已发送分片数 " + str(send_chunks))
        
    #关闭文件
    file.close()

    # 关闭套接字
    sock.close()

# 图像文件路径
img_file = './new.png'

# 模拟1s发一张图
while(True):
    # img_list = sorted(os.listdir(img_dir))
    # for img_name in img_list:
    send_image(img_file, SEND_IP, SEND_PORT, CHUNK_SIZE)
    time.sleep(3)
# send_image(img_file, SEND_IP, SEND_PORT, CHUNK_SIZE)

