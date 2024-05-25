import sys
import socket
# import struct
import os
import time
import logging

# Add the parent directory to the sys.path list
from utils.share import LOGGER, IP_ADDRESS
from utils.image_utils import pack_udp_packet

SEND_PORT = 18089
CHUNK_SIZE = 1024           # 图片分片长度


def send_image(win_size, chunk_size):
    # 创建UDP套接字
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 获取图像大小和分片数量（16位）
    image_size = int((win_size * win_size * 16) / 8)
    chunk_sum = (image_size + chunk_size - 1) // chunk_size
    image_data = bytes([0xFF] * image_size)

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
        sock.sendto(udp_packet, (IP_ADDRESS, SEND_PORT))
        sent_chunks += 1
    
    # 输出发送图片结束时的日志：分片数量，文件大小
    LOGGER.info("已发送分片数: " + str(sent_chunks))

    # 关闭套接字
    sock.close()

#给定图像窗口大小，生成对应长度的16位比特串
def send_test_bytes(win_size):
    length = (win_size * win_size * 16) / 8
    bytes_string = bytes([0xFF] * length)
    print(f"生成长度为{length}的bytes流")

    
    

def main():
    counter = 0
    while counter < 100:
        send_image(512, CHUNK_SIZE)
        counter += 1
        time.sleep(3)

if __name__ == '__main__':
    main()