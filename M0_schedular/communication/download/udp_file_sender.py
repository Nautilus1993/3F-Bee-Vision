import sys
import socket
import os
import time

# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)

# Add the parent directory to the sys.path list
from utils.share import LOGGER, IP_ADDRESS
from utils.constants import IP_ADDRESS, PORT_IMAGE_DOWNLOAD, DOWNLOAD_FILE
from file_down_utils import DownloadState, \
    pack_udp_packet, update_download_status
CHUNK_SIZE = 93           # 图片分片长度

def send_file_data(file_type, file_data, freq = 5):
    """
        发送文件分片并指定分片发送频率(默认每秒发送十个分片)
        输入：
        1. 文件类型(0x00图片文件 0xAA日志文件)
        2. 文件字节流
        3. 每秒发送分片数量
    """
    # 创建UDP套接字
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 获取文件大小和分片数量
    file_size = len(file_data)
    chunk_sum = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE

    # 发送文件分片
    sent_chunks = 0
    progress = 0  # 分片发送进度，范围0-100
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
        sock.sendto(udp_packet, (IP_ADDRESS, PORT_IMAGE_DOWNLOAD))
        sent_chunks += 1 
        cur_progress = int(i / chunk_sum * 100)
        # 更新下载进度到redis
        if progress != cur_progress:
            progress = cur_progress
            LOGGER.info(f"UDP分片下传进度{progress}%, 已下传分片数{i}/{chunk_sum}")
            update_download_status(DownloadState.RUNNING.value, progress)
        # 发送每个分片间隔的s
        time.sleep(1 / freq) 
    
    # 输出发送图片结束时的日志：分片数量，文件大小
    LOGGER.info(f"文件类型:{file_type}，已发送分片数:{sent_chunks}，总分片数:{chunk_sum} ，文件大小:{file_size} Byte")
    update_download_status(DownloadState.NONE.value, 0)
    # 关闭套接字
    sock.close()

# TODO(wangyuhang):需要增加判断是下载日志还是图片的功能
def send_image_file():
    with open(DOWNLOAD_FILE, 'rb') as file:
        raw_data = file.read()
        print("读取文件成功")
    send_file_data(0x00, raw_data)

def main():
    print("download……")
    send_image_file()
    # file_dir = "/home/ywang/Documents/3F-Bee-Vision/M0_schedular/communication/remote_control/tmp/"
    # file_names = [
    #     "image_200_250_0.jpg",
    #     "image_300_250_0.jpg",
    #     "image_500_250_0.jpg"
    # ]
    # check_and_zip_files(file_dir, file_names)

if __name__ == '__main__':
    main()