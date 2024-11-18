import socket
import sys
import os
import signal
import threading

# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)

from utils.share import LOGGER
from utils.constants import IP_ADDRESS, PORT_IMAGE_RECEIVE, LOSS_TOLERANCE
from image_utils import unpack_udp_packet, unpack_cameralink_header 
from image_utils import process_image_to_file, process_image_to_redis
from image_utils import CHUNK_SIZE, HEADER_SIZE
from image_utils import format_image_udp_packet, format_cameralink_header

def receive_image(buffer_size):
    # UDP包缓存,收到首帧的时候初始化为长度为chunk_sum的数组
    # 数组下标对应包序号，用于存放对应的image_chunk
    received_packets = []
    # 包计数，收到首帧和尾帧的时候需要清零
    packet_count = 0

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

        # Case1: 首帧情况
        if chunk_seq == 0:
            # 打印UDP首帧
            # format_image_udp_packet(udp_packet)
            
            # 打印cameralink帧头内容
            cameralink_header = image_chunk[:29]
            # format_cameralink_header(cameralink_header)
            time_s, time_ms, exposure, win_w, win_h, win_x, win_y \
                = unpack_cameralink_header(cameralink_header)
            # 若包计数非0，说明上一张图片未收全
            if(packet_count != 0):
                LOGGER.error("收到第一帧数据，包计数未清零，上一张图片未收全!")
                packet_count = 0
            # 清空缓存开始接收当前图片
            received_packets = [b'\x00' * 1024 for _ in range(chunk_sum)]

        # 将当前UDP包中有效数据部分放入buffer对应下标位置
        received_packets[chunk_seq] = image_chunk
        packet_count += 1

        # Case2: 尾帧情况
        if chunk_seq == (chunk_sum - 1):
            # 丢包率在tolerance以内，则进行组包
            if packet_count >= chunk_sum * (1 - LOSS_TOLERANCE):
                # 拼接有效数据部分，并根据图片长度对bytes流进行裁剪(图片长度为win_w * win_h)
                image_data = b''.join(received_packets)
                length = win_h * win_w
                if(length <= len(image_data)):
                    image_data = image_data[:length]
                else:
                    LOGGER.error(f"窗口大小 宽{win_w} * 高{win_h}大于image_data总长度{sys.getsizeof(image_data)}")
                    continue
                # 将图像名，图像时间戳，开窗位置返回给redis或写入文件
                # LOGGER.info(f"共接收{len(received_packets)}个分片")
                # process_image_to_file(image_data, time_s, time_ms, exposure, win_w, win_h, win_x, win_y)
                # process_image_to_redis(image_data, time_s, time_ms, exposure, win_w, win_h, win_x, win_y)
                threading.Thread(
                    target=process_image_to_redis, 
                    args=(image_data, time_s, time_ms, exposure, win_w, win_h, win_x, win_y,)
                    ).start()
            # 如果丢包率过高则直接报错
            else:
                LOGGER.error(f"丢包率超过{LOSS_TOLERANCE}!应收到 {chunk_sum}, 已收到 {packet_count}个数据包")
            # 清空UDP包缓存，包计数
            received_packets = []
            packet_count = 0

# 创建UDP套接字
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    
# 绑定IP地址和端口号
sock.bind((IP_ADDRESS, PORT_IMAGE_RECEIVE))

# 增加退出docker的逻辑
def signal_handler(sig, frame):
    LOGGER.info("接收到Ctrl-C信号，关闭socket链接")
    sock.close()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

while(True):
    LOGGER.info(IP_ADDRESS + " : " + str(PORT_IMAGE_RECEIVE) + "  开始接收图片...")
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