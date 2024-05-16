import struct
import redis
import os
from enum import Enum
from .share import generate_udp_format, get_timestamps

# 接收端的IP地址和端口号
SERVER_PORT = 10090

# REDIS
REDIS = redis.Redis(host='127.0.0.1', port=6379)

# 加载遥测数据格式配置文件,生成UDP包格式
config_file = "remote_control_config.json"
config_file_path = os.path.dirname(os.path.abspath(__file__)) + "/" + config_file
REMOTE_CONTROL_UDP_FORMAT = generate_udp_format(config_file_path)
LENGTH = 29
SENDER_ID  = 0x00
RECEIVER_ID = 0x11

"""
    指令码枚举值
"""
class Instruction(Enum):
    DEVICE_STATE = 0x00
    DEVICE_RESET = 0x01
    APP_STATE = 0x10
    APP_RESET = 0x11
    DOWNLOAD_IMG = 0x20
    DOWNLOAD_LOG = 0x21


"""
    UDP 解析和组包 
"""
def pack_udp_packet(instruction, file_info, algorithm_info):
    time_s, time_ms = get_timestamps()
    # TODO:后面加入校验和逻辑
    checksum = 0
    udp_packet = struct.pack(REMOTE_CONTROL_UDP_FORMAT, 
        LENGTH,             # 1. 有效数据长度
        SENDER_ID,          # 2. 数据接收方
        RECEIVER_ID,        # 3. 数据发送方
        time_s,             # 4. 组包时间秒
        time_ms,            # 5. 组包时间毫秒
        instruction,        # 6. 指令码
        file_info,          # 7. 下行文件元信息
        algorithm_info,     # 8. 算法遥控数据
        checksum            # 9. 校验和
    )
    return udp_packet

def unpack_udp_packet(udp_packet):
    _, _, _, \
    time_s, time_ms, instruction, \
    _, _, _ = struct.unpack(REMOTE_CONTROL_UDP_FORMAT, udp_packet)
    return time_s, time_ms, instruction