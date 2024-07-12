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
from message_config.udp_format import INDIRECT_INS_UDP_FORMAT, TIME_INS_FORMAT

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


"""
    指令类型枚举值
"""
class InstructionType(Enum):
    TELEMETER = 0x11        # 遥测
    TIMER = 0x31            # 星上时
    ASYNC_PKG = 0x15        # 异步包请求
    INDIRECT_INS = 0x21     # 间接指令
    INJECT_DATA = 0x29      # 注入数据

"""
    间接指令码枚举值
"""
class Instruction(Enum):
    APP_START = 0xFED1
    APP_STOP = 0xFED2
    STOP_DOWNLOAD = 0xFED3

"""
    间接指令UDP解析和组包 
"""
def pack_udp_packet(instruction):
    udp_packet = struct.pack(INDIRECT_INS_UDP_FORMAT, 
        LENGTH,             # 1. 有效数据长度
        SENDER_ID,          # 2. 数据发送方
        RECEIVER_ID,        # 3. 数据接收方
        0x21,               # 4. 数据类型(目前填固定值间接指令)
        0,                  # 5. 指令时间码(目前全部置0)
        instruction,        # 6. 指令类型码
    )
    return udp_packet

def unpack_udp_packet(udp_packet):
    _, _, _, ins_type, _, instruction \
        = struct.unpack(INDIRECT_INS_UDP_FORMAT, udp_packet)
    return ins_type, instruction

"""
    星上时UDP解析和组包 
"""
def pack_time_ins_packet(time_s, time_ms):
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
    _, _, _, ins_type, time_s, time_ms \
        = struct.unpack(TIME_INS_FORMAT, udp_packet)
    return ins_type, time_s, time_ms

def write_time_to_redis(time_s, time_ms):
    # 星上时时间戳，系统时间，两者差值
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

def sync_to_time():
    """
    read satellite time from redis, transfer current system time to satellite time
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

#收到的指令写入redis 
def write_instruction_to_redis(instruction, time_s, time_ms, counter):
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
    last_element = REDIS.lindex(TOPIC_INSTRUCTION, -1)
    if last_element is not None:
        return last_element.decode()
    else:
        return None

def execute_indirect_ins(instruction):
    print(hex(instruction))
    print(Instruction.APP_START.value)
    if instruction == Instruction.APP_START.value:
        service_list = ['image_receiver', 'yolov5']
        control_services(service_list, turn_on=True)
    elif instruction == Instruction.APP_STOP.value:
        service_list = ['image_receiver', 'yolov5']
        control_services(service_list, turn_on=False)
    else:
        print(f"执行指令{instruction}, 逻辑待实现...")

def control_services(service_list, turn_on):
    if 'DEVOPS_WORKSPACE' in os.environ:
        compose_file_path = os.environ['DEVOPS_WORKSPACE'] + "/docker-compose.yaml"
    else:
        compose_file_path = None
    manager = DockerComposeManager(compose_file_path)
    if turn_on:
        manager.start_services(service_list)
    else:
        manager.stop_services(service_list)