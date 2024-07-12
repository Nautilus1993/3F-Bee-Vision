import sys
import socket
import os
import time
from io import BytesIO

# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)

# Add the parent directory to the sys.path list
from utils.share import LOGGER, IP_ADDRESS
from image_utils import RECV_PORT, pack_udp_packet, crop_image

CHUNK_SIZE = 1024           # 图片分片长度


def send_image_data(window, image_data):
    # 创建UDP套接字
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 获取图像文件大小和分片数量
    image_size = len(image_data)
    # print(image_size)
    chunk_sum = (image_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    # print(chunk_sum)

    # 获取时间戳
    timestamp = time.time()
    time_s = int(timestamp)
    time_ms = int((timestamp - time_s) * 1000)

    # 发送图像分片
    sent_chunks = 0
    for i in range(chunk_sum):
        # 获取图片分片
        start = i * CHUNK_SIZE
        end = min((i + 1) * CHUNK_SIZE, image_size)
        image_chunk = image_data[start:end]
        # 发送UDP帧
        udp_packet = pack_udp_packet(
            time_s, 
            time_ms, 
            window,
            chunk_sum, 
            i, 
            image_chunk
        )
        sock.sendto(udp_packet, (IP_ADDRESS, RECV_PORT))
        sent_chunks += 1
    
    # 输出发送图片结束时的日志：分片数量，文件大小
    LOGGER.info(f"已发送分片数:{sent_chunks} 开窗大小({window[0]},{window[1]}) 开窗位置({window[2]},{window[3]})")

    # 关闭套接字
    sock.close()

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
    image_bytes = image_array.tobytes()
    send_image_data(window, image_bytes)

def main():
    for window in test_cases:
        send_window(window, image_name)
        time.sleep(3)

if __name__ == '__main__':
    main()