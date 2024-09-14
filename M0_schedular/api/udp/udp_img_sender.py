import sys
import socket
import os
import time
import cv2

# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取M0模块目录路径
parent_dir = os.path.dirname(os.path.dirname(script_dir))
sys.path.append(parent_dir)

# Add the parent directory to the sys.path list
from communication.utils.share import LOGGER, IP_ADDRESS
from communication.utils.constants import IP_ADDRESS, PORT_IMAGE_RECEIVE
from communication.image.image_utils import \
    pack_udp_packet, pack_fake_cameralink_header

CHUNK_SIZE = 1024           # 图片分片长度

class InvalidWindowError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

# 模拟星上时每次发送的时间戳, 默认每秒发送4张图
def time_generator(freq=4):
    time_s = 0
    time_ms = 0
    delta = int(1000 / freq)
    while True:
        yield time_s, time_ms
        time_ms += delta
        if time_ms >= 1000:
            time_ms = 0
            time_s += 1

def fake_cameralink_header(time_gen, exposure, window):
    """ 
        用于模拟生成camerlink header
        输入：
            time_gen(generator): 用于生成星上时时间戳
            exposure(int):曝光时间
            window([int]):窗口信息，长度为4 [w h x y]
    """
    # 生成星上时时间戳
    time_s, time_ms = next(time_gen)
    # 判断窗口大小的合法性
    if len(window) != 4:
        raise InvalidWindowError(f"开窗信息长度有误！{window}")
    cameralink_header = pack_fake_cameralink_header(
        time_s,
        time_ms,
        exposure,
        window[0],
        window[1],
        window[2],
        window[3],
    )
    return cameralink_header

def send_image_data(image_data):
    """
        发送UDP图片分片
        输入(bytes): 固定长度的字节串，头部为cameralink帧头
    """
    # 创建UDP套接字
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 获取图像文件大小和分片数量
    image_size = len(image_data)
    chunk_sum = (image_size + CHUNK_SIZE - 1) // CHUNK_SIZE

    # 发送图像分片
    sent_chunks = 0
    for i in range(chunk_sum):
        # 获取图片分片
        start = i * CHUNK_SIZE
        end = min((i + 1) * CHUNK_SIZE, image_size)
        image_chunk = image_data[start:end]
        # 发送UDP帧
        udp_packet = pack_udp_packet(
            0, 
            0, 
            chunk_sum, 
            i, 
            image_chunk
        )
        sock.sendto(udp_packet, (IP_ADDRESS, PORT_IMAGE_RECEIVE))
        sent_chunks += 1
    
    # 输出发送图片结束时的日志：分片数量，文件大小
    LOGGER.info(f"分片数:{sent_chunks})")

    # 关闭套接字
    sock.close()

# 图像文件路径
image_path = script_dir + '/test_images/xingmin.bmp' # 2048 * 2048
gen = time_generator(4)

def send_scroll_images():
    """
        模拟滚动曝光，不开窗
    """
    # 从图像文件中读取图片
    with open(image_path, 'rb') as file:
        raw_image = file.read()
    for _ in range(1000):
        header = fake_cameralink_header(gen, 100, [2048, 2048, 0, 0])
        image_data = header + raw_image
        send_image_data(image_data)
        time.sleep(0.16)

def sync_time():
    """
        模拟1s发送一组图片
    """
    current_time = time.time()
    next_second = current_time + 1 - (current_time % 1)
    time.sleep(next_second - current_time)


def main():
    send_scroll_images()

if __name__ == '__main__':
    main()