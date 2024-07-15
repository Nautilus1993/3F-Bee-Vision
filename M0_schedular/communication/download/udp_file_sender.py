import sys
import socket
import os
import time
from PIL import Image
import numpy as np

# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)

# Add the parent directory to the sys.path list
from utils.share import LOGGER, IP_ADDRESS
from file_down_utils import RECV_PORT, pack_udp_packet, crop_image
from file_down_utils import jpeg2000_encode

CHUNK_SIZE = 93           # 图片分片长度



# test
IP_ADDRESS = '127.0.0.1'







def send_file_data(file_type, file_data):
    # 创建UDP套接字
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 获取文件大小和分片数量
    file_size = len(file_data)
    # print(file_size)
    chunk_sum = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    # print(chunk_sum)


    # 发送文件分片
    sent_chunks = 0
    for i in range(chunk_sum):
        # 获取文件分片
        start = i * CHUNK_SIZE
        end = min((i + 1) * CHUNK_SIZE, file_size)
        file_chunk = file_data[start:end]
        # 发送UDP帧
        udp_packet = pack_udp_packet(
            file_type,
            chunk_sum,
            i,
            file_chunk
        )
        sock.sendto(udp_packet, (IP_ADDRESS, RECV_PORT))
        sent_chunks += 1
    
    # 输出发送图片结束时的日志：分片数量，文件大小
    LOGGER.info(f"文件类型:{file_type}，已发送分片数:{sent_chunks}，总分片数:{chunk_sum} ，文件大小:{file_size} Byte")

    # 关闭套接字
    sock.close()



#################################################TEST#################################################


# 图像文件路径
image_name = script_dir + '/test_images/xingmin.bmp' # 2048 * 2048
test_cases = [
    [2048, 2048, 0, 0],  
    [1024, 1024, 300, 400], 
    [1024, 1024, 500, 500]
]

# 给定窗口大小和图片文件，发送框定部分的图片数据
def send_window(window, image_file):
    w, h, x, y = window
    image_array = crop_image(w, h, x, y, image_file)
    # image_bytes = image_array.tobytes()
    image_bytes = jpeg2000_encode(image_array)
    print(len(image_bytes))
    send_file_data(0x00, image_bytes)

def main():
    for window in test_cases:
        send_window(window, image_name)
        time.sleep(3)

if __name__ == '__main__':
    main()