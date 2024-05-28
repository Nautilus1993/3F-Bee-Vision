import cv2
import socket

from utils.share import LOGGER, IP_ADDRESS
from utils.image_utils import unpack_udp_packet, process_image_test, process_image
from utils.image_utils import CHUNK_SIZE, HEADER_SIZE, RECV_PORT

def receive_image(buffer_size):
    # 以包序号为key存储UDP包中的有效数据
    received_packets = {}
    received_chunks = 0

    while True:
        udp_packet, addr = sock.recvfrom(buffer_size)
        
        time_s, \
        time_ms, \
        win_x, \
        win_y, \
        chunk_sum, \
        chunk_seq, \
        image_chunk = unpack_udp_packet(udp_packet)

        # 收到第一帧
        if chunk_seq == 0:
            # 根据当前收包状态判断上一张图片是否有丢包
            if(len(received_packets) != 0):
                LOGGER.error("丢包:!收到第一帧数据，字典非空，清空received_packet重新接收")
            received_packets = {}
            received_chunks = 0

        # 将当前Packet加入
        if chunk_seq not in received_packets:
            received_packets[chunk_seq] = image_chunk
            received_chunks += 1

        # 如果是最后一帧，判断目前是否收到所有的包；若完整收到一幅图，组包存储为图片文件
        if chunk_seq == (chunk_sum - 1):
            if len(received_packets) == chunk_sum:
                # Concatenate the packets in the correct order
                sorted_packets = [received_packets[i] for i in range(chunk_sum)]
                image_data = b''.join(sorted_packets)
                # 将图像名，图像时间戳，开窗位置返回给redis
                process_image_test(image_data, time_s, time_ms, win_x, win_y)
                LOGGER.info(f"图片file_{time_s}_{time_ms}写入redis, 共接收{len(received_packets)}个分片")
                received_packets = {}
            else:
                LOGGER.error(f"还未收全，应收到 {chunk_sum}, 已收到 {len(received_packets)}")
                return 

    # 关闭套接字
    # sock.close()

# 创建UDP套接字
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    
# 绑定IP地址和端口号
sock.bind((IP_ADDRESS, RECV_PORT))

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