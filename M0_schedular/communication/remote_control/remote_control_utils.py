import struct
import redis
import os
import json
from enum import Enum

import sys
# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)

# 加载docker client用于控制docker compose 服务
from utils.docker_status import DockerComposeManager
from utils.share import get_timestamps

# 加载遥测数据格式配置文件,生成UDP包格式
from message_config.udp_format import INDIRECT_INS_UDP_FORMAT, \
    TIME_INS_FORMAT, INJECT_DATA_IMAGE_FORMAT

# 接收端的IP地址和端口号
SERVER_PORT = 17777

# REDIS
REDIS = redis.Redis(host='127.0.0.1', port=6379)
TOPIC_INSTRUCTION = 'topic.remote_control'
BUFFER_SIZE = 10 # redis中最多缓存的指令数量

LENGTH = 9  
SENDER_ID  = 0x55
RECEIVER_ID = 0xAA

TOPIC_TIME = 'queue.time' 
MAX_LENGTH = 10 

# =========  指令类型、指令码枚举类定义 =========

class InstructionType(Enum):
    """
        指令类型枚举值
    """
    TELEMETER = 0x11        # 遥测
    TIMER = 0x31            # 星上时
    ASYNC_PKG = 0x15        # 异步包请求
    INDIRECT_INS = 0x21     # 间接指令
    INJECT_DATA = 0x29      # 注入数据

class Instruction(Enum):
    """
        指令码枚举值
    """
    APP_START = 0xFED1      # 启动收图和算法模块
    APP_STOP = 0xFED2       # 关闭收图和算法模块
    STOP_DOWNLOAD = 0xFED3  # 关闭文件下载程序
    DOWNLOAD_LOG = 0xF2     # 日志下行指令 
    DOWNLOAD_IMAGE = 0xF3     # 图像下行指令
    UPDATE_PARAMS = 0xF4    # 常量修改指令

# =========  间接指令相关函数 =========

def pack_indirect_instruction_packet(instruction):
    """
        间接指令UDP组包 
    """
    udp_packet = struct.pack(INDIRECT_INS_UDP_FORMAT, 
        LENGTH,             # 1. 有效数据长度
        SENDER_ID,          # 2. 数据发送方
        RECEIVER_ID,        # 3. 数据接收方
        0x21,               # 4. 数据类型(目前填固定值间接指令)
        0,                  # 5. 指令时间码(目前全部置0)
        instruction,        # 6. 指令类型码
    )
    return udp_packet

def unpack_indirect_instruction_packet(udp_packet):
    """
        间接指令UDP解包 
    """
    _, _, _, ins_type, _, instruction \
        = struct.unpack(INDIRECT_INS_UDP_FORMAT, udp_packet)
    return ins_type, instruction


def execute_indirect_ins(instruction_code):
    """
        执行间接指令，根据指令码决定启动或关闭指定服务。
    """
    if instruction_code == Instruction.APP_START.value:
        service_list = ['image_receiver', 'quality', 'yolov5']
        control_services(service_list, turn_on=True)
    elif instruction_code == Instruction.APP_STOP.value:
        service_list = ['image_receiver', 'quality', 'yolov5']
        control_services(service_list, turn_on=False)
    else:
        print(f"执行间接指令{instruction_code}, 逻辑待实现...")

# =========  星上时相关函数 =========
def pack_time_ins_packet(time_s, time_ms):
    """
        星上时UDP组包 
    """
    udp_packet = struct.pack(TIME_INS_FORMAT, 
        LENGTH,             # 1. 有效数据长度
        SENDER_ID,          # 2. 数据发送方
        RECEIVER_ID,        # 3. 数据接收方
        0x31,               # 4. 星上时数据类型
        time_s,             # 5. 星上时时间戳秒
        time_ms,            # 6. 星上时时间戳毫秒
    )
    return udp_packet

def unpack_time_ins_packet(udp_packet):
    """
        星上时UDP解析 
    """
    _, _, _, ins_type, time_s, time_ms \
        = struct.unpack(TIME_INS_FORMAT, udp_packet)
    return ins_type, time_s, time_ms

def write_time_to_redis(time_s, time_ms):
    """
        星上时写redis: 星上时时间戳，系统时间，两者差值 
    """
    sys_time_s, sys_time_ms = get_timestamps()
    timestamp = {
        'time_s': time_s,
        'time_ms': time_ms,
        'sys_time_s': sys_time_s,
        'sys_time_ms': sys_time_ms,
        'delta_s': sys_time_s - time_s,
        'delta_ms': sys_time_ms - time_ms
    }
    # 将消息推送到队列
    REDIS.lpush(TOPIC_TIME, str(timestamp))
    # 修剪队列长度
    REDIS.ltrim(TOPIC_TIME, 0, MAX_LENGTH - 1)

def sync_to_satellite_time():
    """
    将当前系统时间转换到星上时体系下
    """
    timestamp = REDIS.lrange(TOPIC_TIME,0, 0)
    if not timestamp:
        print("No time in redis")
    sys_time_s, sys_time_ms = get_timestamps()
    delta_s = timestamp['delta_s']
    delta_ms = timestamp['delta_ms']
    time_s = sys_time_s - delta_s
    time_ms = sys_time_ms - delta_ms
    return time_s, time_ms

# =========  注入数据相关函数 =========
# (TODO:wangyuhang) 增加时间戳相关操作
def pack_inject_data_image_packet(download_image_num):
    """
        注入数据-图片下行指令UDP组包

        输入：download_image_num(int) 
    """
    download_strategy = 0x55
    fake_time_s = 0
    udp_packet = struct.pack(INJECT_DATA_IMAGE_FORMAT, 
        LENGTH,             # 1. 有效数据长度
        SENDER_ID,          # 2. 数据发送方
        RECEIVER_ID,        # 3. 数据接收方
        0x29,               # 4. 数据类型
        0,                  # 5. 指令时间码
        0xF3,               # 6. 指令类型码
        download_image_num, # 7. 下行图片数量
        download_strategy,  # 8. 图片下载策略，0x55按最优策略下行，0xAA按时间戳
        fake_time_s,        # 9. 假时间戳
        fake_time_s,        # 10. 假时间戳
        fake_time_s,        # 11. 假时间戳
        fake_time_s,        # 12. 假时间戳
        fake_time_s,        # 13. 假时间戳
        fake_time_s,        # 14. 假时间戳
        fake_time_s,        # 15. 假时间戳
        fake_time_s,        # 16. 假时间戳
        fake_time_s,        # 17. 假时间戳
        fake_time_s,        # 18. 假时间戳
        0,                  # 19. 校验和
        0                   # 20. 帧尾
    )
    return udp_packet

def unpack_inject_data_image_packet(udp_packet):
    """
        注入数据-图片下行指令UDP解包
    """
    _, _, _, _, _, \
    inject_data_code, download_image_num, download_strategy, \
    _, _, _, _, _, _, _, _, _, _, \
    chunksum, frameend = struct.unpack(INJECT_DATA_IMAGE_FORMAT, udp_packet)
    return download_image_num, download_strategy

def execute_inject_data(instruction_code):
    """
        执行注入数据指令，根据指令码决定启动或关闭指定服务。
    """
    if instruction_code == Instruction.DOWNLOAD_IMAGE.value:
        print(f"执行注入数据指令 图片文件下传 , 逻辑待实现...")
    else:
        print(f"执行注入数据指令{instruction_code}, 逻辑待实现...")


# =========  指令相关通用函数 =========
def write_instruction_to_redis(instruction, counter):
    """
        收到的间接指令写入redis
    """ 
    
    time_s, time_ms = get_timestamps()
    message = {
        'instruction_code': hex(instruction),
        'instruction_name': Instruction(instruction).name,
        'time_s': time_s,
        'time_ms': time_ms,
        'counter': counter
    }
    print("write to redis" + str(message))
    REDIS.rpush(TOPIC_INSTRUCTION, json.dumps(message))
    # 判断是否已经达到指令缓存数量上限
    if REDIS.llen(TOPIC_INSTRUCTION) > BUFFER_SIZE:
        REDIS.lpop(TOPIC_INSTRUCTION)


def read_instruction_from_redis():
    """
    遥测调用，从redis中获取上一条指令执行的内容
    """
    last_element = REDIS.lindex(TOPIC_INSTRUCTION, -1)
    if last_element is not None:
        return last_element.decode()
    else:
        return None

def control_services(service_list, turn_on):
    """
        调用相应的docker compose服务(收到关闭、重启、下行文件等)
    """
    # docker container中的docker-compose.yaml文件路径
    compose_file_path = "/usr/src/deploy/docker-compose.yaml"
    manager = DockerComposeManager(compose_file_path)
    if turn_on:
        manager.start_services(service_list)
    else:
        manager.stop_services(service_list)