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
from file_down_utils import unpack_udp_packet, process_image_to_file, process_image_to_redis, process_file_to_bin
from file_down_utils import CHUNK_SIZE, HEADER_SIZE, RECV_PORT
from file_down_utils import format_file_udp_packet
from file_down_utils import FILE_IMAGE, FILE_LOG
#test
IP_ADDRESS = '127.0.0.1'



def receive_file(buffer_size):
    # UDP包缓存：以包序号为key存储UDP包中的有效数据
    received_packets = {}

    while True:
        udp_packet, addr = sock.recvfrom(buffer_size)
        # 判断当前包长度是否是文件低速下行异步包
        if len(udp_packet) != HEADER_SIZE + CHUNK_SIZE:
            LOGGER.warning(f"收到的文件UDP包长度有误！{len(udp_packet)}")
            continue
        # print(unpack_udp_packet(udp_packet))
        
        # 长度正确则调用UDP解析函数
        file_type, _,\
        chunk_sum, \
        chunk_seq, \
        file_chunk = unpack_udp_packet(udp_packet)
        # Case1: 首帧
        if chunk_seq == 0:
            format_file_udp_packet(udp_packet)
            # 若缓存非空，说明上一个文件未收全
            if(len(received_packets) != 0):
                LOGGER.error("收到第一帧数据，缓存非空，上一个文件未收全!")
                # 仍然拼接文件
                stitching_packets(file_type, received_packets)

                LOGGER.info(f"共接收{len(received_packets)}个分片")
                # 清空缓存开始接收当前图片
                received_packets = {}
            
            received_packets[chunk_seq] = file_chunk

        # Case2: 尾帧
        elif chunk_seq == (chunk_sum - 1):
            received_packets[chunk_seq] = file_chunk
            # 如果已收到所有的包，组包存储到文件或redis
            if len(received_packets) == chunk_sum:
                LOGGER.info(f"共接收{len(received_packets)}个分片")
            # 如果未收到所有的包，则报丢包错误
            else:
                LOGGER.error(f"还未收全，应收到 {chunk_sum}, 已收到 {len(received_packets)}")
            
            # 无论是否丢包，尝试拼接文件
            stitching_packets(file_type, received_packets)
            
            # 清空UDP包缓存
            received_packets = {} 

        # Case3:中间帧
        elif chunk_seq not in received_packets:
            received_packets[chunk_seq] = file_chunk
        else:
            LOGGER.error(f"包序号为{chunk_seq}的包已在缓存中，UDP包乱序发送")
            #丢弃乱序的后来帧

        



def stitching_packets(file_type, received_packets):
    sorted_packets = [received_packets[i] for i in range(len(received_packets)) if i in received_packets]
    file_data = b''.join(sorted_packets)
    if file_type == FILE_IMAGE:
        print('处理图片')
        process_image_to_file(file_data)
    elif file_type == FILE_LOG:
        print('log file')
        # process_log_to_file(file_data)
        #TODO: process_log_to_file
        pass



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
        receive_file(buffer_size)

    except socket.error as e:
        # 没有数据可读，错误码为 EWOULDBLOCK 或 EAGAIN
        if e.errno == socket.errno.EWOULDBLOCK or e.errno == socket.errno.EAGAIN:
            LOGGER.exception('socket没有数据')
        else:
            # 其他错误，需要处理
            LOGGER.exception('Error:', e)
            break