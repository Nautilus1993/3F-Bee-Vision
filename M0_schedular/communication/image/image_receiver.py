import socket
import sys
import os
import signal

# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)

from utils.share import LOGGER, IP_ADDRESS
from image_utils import unpack_udp_packet, unpack_cameralink_header 
from image_utils import process_image_to_file, process_image_to_redis, process_image_to_bin
from image_utils import CHUNK_SIZE, HEADER_SIZE, RECV_PORT
from image_utils import format_image_udp_packet, format_cameralink_header

def receive_image(buffer_size):
    # UDP包缓存：以包序号为key存储UDP包中的有效数据
    received_packets = {}

    while True:
        udp_packet, addr = sock.recvfrom(buffer_size)
        # 判断当前包长度是否是图像包
        if len(udp_packet) != HEADER_SIZE + CHUNK_SIZE:
            LOGGER.warning(f"收到的图像UDP包长度有误！{len(udp_packet)}")
            continue
        
        # 长度正确则调用UDP解析函数
        _, \
        _, \
        _, \
        _, \
        _, \
        _, \
        chunk_sum, \
        chunk_seq, \
        image_chunk = unpack_udp_packet(udp_packet)

        # Case1: 首帧
        if chunk_seq == 0:
            # 打印UDP首帧
            # format_image_udp_packet(udp_packet)
            
            # 打印cameralink帧头内容
            cameralink_header = image_chunk[:29]
            # format_cameralink_header(cameralink_header)
            time_s, time_ms, exposure, win_w, win_h, win_x, win_y \
                = unpack_cameralink_header(cameralink_header)
            # 若缓存非空，说明上一张图片未收全
            if(len(received_packets) != 0):
                LOGGER.error("收到第一帧数据，缓存非空，上一张图片未收全!")
            # 清空缓存开始接收当前图片
            received_packets = {}

        # Case2:中间帧
        if chunk_seq not in received_packets:
            received_packets[chunk_seq] = image_chunk
        else:
            LOGGER.error(f"包序号为{chunk_seq}的包已在缓存中，UDP包乱序发送")

        # Case3: 尾帧
        if chunk_seq == (chunk_sum - 1):
            # 如果已收到所有的包，组包存储到文件或redis
            if len(received_packets) == chunk_sum:
                # 按照chunk_seq组合有效数据部分
                sorted_packets = [received_packets[i] for i in range(chunk_sum)]
                image_data = b''.join(sorted_packets)
                length = win_h * win_w
                if(length <= len(image_data)):
                    image_data = image_data[:length]
                else:
                    LOGGER.error("window size is too big!")
                # 将图像名，图像时间戳，开窗位置返回给redis或写入文件
                LOGGER.info(f"共接收{len(received_packets)}个分片")
                # process_image_to_bin(image_data)
                # process_image_to_file(image_data, time_s, time_ms, exposure, win_w, win_h, win_x, win_y)
                process_image_to_redis(image_data, time_s, time_ms, win_w, win_h, win_x, win_y)
            # 如果未收到所有的包，则报丢包错误
            else:
                LOGGER.error(f"还未收全，应收到 {chunk_sum}, 已收到 {len(received_packets)}")
            # 清空UDP包缓存
            received_packets = {} 

# 创建UDP套接字
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    
# 绑定IP地址和端口号
sock.bind((IP_ADDRESS, RECV_PORT))

# 增加退出docker的逻辑
def signal_handler(sig, frame):
    LOGGER.info("接收到Ctrl-C信号，关闭socket链接")
    sock.close()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

while(True):
    LOGGER.info(IP_ADDRESS + " : " + str(RECV_PORT) + "  开始接收图片...")
    try:
        # buffer_size: UDP包的大小，每次接收定长的UDP包
        buffer_size = HEADER_SIZE + CHUNK_SIZE
        receive_image(buffer_size)

    except socket.error as e:
        # 没有数据可读，错误码为 EWOULDBLOCK 或 EAGAIN
        if e.errno == socket.errno.EWOULDBLOCK or e.errno == socket.errno.EAGAIN:
            LOGGER.exception('socket没有数据')
        else:
            # 其他错误，需要处理
            LOGGER.exception('Error:', e)
            break