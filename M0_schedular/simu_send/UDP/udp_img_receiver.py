import cv2
import os
import socket
import struct
import time
import datetime
import numpy as np

# 接收端的IP地址和端口号
RECV_IP = '192.168.31.17'
RECV_PORT = 8089
# 数据分片大小
CHUNK_SIZE = 1024
HEADER_SIZE = 10 # TODO：暂时只加包序号调通代码

# timeout设置
TIMEOUT = 10

# 图像大小，应该是固定的大小 2k * 2k
IMAGE_SIZE = 2207156 # 6621914 6M.png

# 收到图片存放位置
img_dir = 'received_images/'

def unpack_udp_packet(udp_packet):
    # Define the packet format
    packet_format = "!HII1024s"
    chunk_length, chunk_sum, chunk_seq, image_chunk = struct.unpack(packet_format, udp_packet)
    # print(f"Unpack UDP packet {chunk_seq}/{chunk_sum}, image_chunk length is {chunk_length}")
    return chunk_sum, chunk_seq, image_chunk[:chunk_length]


def generate_image_name():
    # 获取当前时间
    current_time = datetime.datetime.now()
    # 将当前时间转换为指定格式的字符串
    time_string = current_time.strftime("%Y-%m-%d_%H-%M-%S")
    # 构建文件名
    file_name = f"file_{time_string}.png"
    return file_name

def timer(func):
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter() 
        result = func(*args, **kwargs)
        end_time = time.perf_counter() 
        elapsed_time = end_time - start_time
        print(f"开始时间的毫秒计数：{start_time}")
        print(f"结束时间的毫秒计数：{end_time}")
        print(f"函数 {func.__name__} 的执行时间为：{elapsed_time} 秒")
        return result
    return wrapper

# 将接收到的数据写入文件，发送给redis
def process_image(image_data):
    # TODO: add image meta data like timestamp
    filename = os.path.join(img_dir, generate_image_name())
    with open(filename, 'wb') as file:
        file.write(image_data)

# @timer
def receive_image(image_size, buffer_size):
    # 接收UDP帧
    received_packets = {}

    while True:
        # 接收分片数据
        udp_packet, addr = sock.recvfrom(buffer_size)
        # TODO:加入解析UDP的逻辑
        chunk_sum, chunk_seq, image_chunk = unpack_udp_packet(udp_packet)
        # print(f"Received packet {chunk_seq}/{chunk_sum}: {len(image_chunk)} bytes")

        # 如果是第一帧，则清空buffer 重新累加
        if chunk_seq == 0:
            if(len(received_packets) != 0):
                print("收到第一帧数据，但是当前buffer中还有数据，清空buffer重新接收")
            received_packets = {}

        # 如果是最后一帧，需要判断当前是否已经收齐了所有的数据包
        # if chunk_seq == (chunk_sum - 1):
        #     print(chunk_seq)
        #     if len(received_packets) != chunk_sum:
        #         print(f"已经接收到最后一包，但还未收全，应收到 {chunk_sum}, 已收到 {len(received_packets)}")
        #         return

        # 将当前Packet加入
        if chunk_seq not in received_packets:
            received_packets[chunk_seq] = image_chunk

        # Check if all packets have been received
        if len(received_packets) == chunk_sum:
            # Concatenate the packets in the correct order
            print("   =========   ") 
            print("received_packages = " + str(len(received_packets)))
            sorted_packets = [received_packets[i] for i in range(chunk_sum)]
            image_data = b''.join(sorted_packets)

            # Reset the received packets dictionary
            received_packets = {}

            # Process the complete image data
            process_image(image_data)
    
    # 关闭套接字
    # sock.close()

# 创建UDP套接字
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    
# 绑定IP地址和端口号
sock.bind((RECV_IP, RECV_PORT))
# sock.settimeout(TIMEOUT)

while(True):
    try:
        # 收到图像数据包的第一帧
        # meta_data = sock.recv(CHUNK_SIZE) 
        # print("received meta_data")  
        buffer_size = HEADER_SIZE + CHUNK_SIZE
        receive_image(IMAGE_SIZE, buffer_size)

    except socket.error as e:
        # 没有数据可读，错误码为 EWOULDBLOCK 或 EAGAIN
        if e.errno == socket.errno.EWOULDBLOCK or e.errno == socket.errno.EAGAIN:
            print('No data received')
        else:
            # 其他错误，需要处理
            print('Error:', e)
            break
        
