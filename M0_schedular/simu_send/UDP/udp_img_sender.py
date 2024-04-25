import sys
import socket
# import struct
import os
import time
import logging

# Add the parent directory to the sys.path list
from utils.image_utils import pack_udp_packet, LOGGER,IP_ADDRESS

SEND_PORT = 8090
CHUNK_SIZE = 1024           # 图片分片长度


def send_image(filename, server_ip, server_port, chunk_size):
    # 创建UDP套接字
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 读取图像文件
    with open(filename, 'rb') as file:
        image_data = file.read()
    
    # 获取图像文件大小和分片数量
    image_size = os.path.getsize(filename)
    chunk_sum = (image_size + chunk_size - 1) // chunk_size

    # 获取时间戳
    timestamp = time.time()
    time_s = int(timestamp)
    time_ms = int((timestamp - time_s) * 1000)

    # 发送图像分片
    sent_chunks = 0
    for i in range(chunk_sum):
        # 获取图片分片
        start = i * chunk_size
        end = min((i + 1) * chunk_size, image_size)
        image_chunk = image_data[start:end]
        
        # 发送UDP帧
        udp_packet = pack_udp_packet(
            time_s, 
            time_ms, 
            chunk_sum, 
            i, 
            image_chunk
        )
        sock.sendto(udp_packet, (server_ip, server_port))
        sent_chunks += 1
    
    # 输出发送图片结束时的日志：分片数量，文件大小
    LOGGER.info("已发送分片数: " + str(sent_chunks))
        
    #关闭文件
    file.close()

    # 关闭套接字
    sock.close()

# 图像文件路径
img_512 = './test_images/512.bmp' # 512 * 512
img_1024 = './test_images/1024.bmp' # 1024 * 1024
img_2048 = './test_images/2048.bmp' # 2048 * 2048
img_tiff = './camera/1.tiff' 
        
def send_4_images(img_file):
    count = [1,2,3,4]
    for i in count:
        LOGGER.info(f"准备发送第{i}张图" )
        send_image(img_file, IP_ADDRESS, SEND_PORT, CHUNK_SIZE)
        time.sleep(0.2)

def send_1024():
    send_4_images(img_1024)

def main():
    counter = 0
    while counter < 100:
        # send_1024()
        send_image(img_2048, IP_ADDRESS, SEND_PORT, CHUNK_SIZE)
        counter += 1
        time.sleep(0.2)

if __name__ == '__main__':
    main()