import socket

from utils.share import LOGGER, IP_ADDRESS
from utils.remote_control_utils import SERVER_PORT, Instruction, \
unpack_udp_packet

def receive_instruction(buffer_size):
    while True:
        udp_packet, addr = sock.recvfrom(buffer_size)
        time_s, time_ms, instruction = unpack_udp_packet(udp_packet)
        LOGGER.info(f"收到遥控指令：{Instruction(instruction).name} 指令码 {hex(instruction)}")

# 创建UDP套接字
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    
# 绑定IP地址和端口号
sock.bind((IP_ADDRESS, SERVER_PORT))
LOGGER.info(IP_ADDRESS + " : " + str(SERVER_PORT) + "  开始接收遥控指令...")
try:
    buffer_size = 1024
    receive_instruction(buffer_size)
except socket.error as e:
    # 没有数据可读，错误码为 EWOULDBLOCK 或 EAGAIN
    if e.errno == socket.errno.EWOULDBLOCK or e.errno == socket.errno.EAGAIN:
        LOGGER.exception('socket没有数据')
    else:
        # 其他错误，需要处理
        LOGGER.exception('Error:', e)
except Exception as e:
    LOGGER.exception("其他异常:", str(e))
finally:
    sock.close()