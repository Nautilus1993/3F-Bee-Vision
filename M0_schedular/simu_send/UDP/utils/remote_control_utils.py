import struct
import redis
import os
import json
from enum import Enum
from .share import generate_udp_format, get_timestamps
from .docker_status import DockerComposeManager

# 接收端的IP地址和端口号
SERVER_PORT = 10090

# REDIS
REDIS = redis.Redis(host='127.0.0.1', port=6379)
TOPIC_INSTRUCTION = 'topic.remote_control'
BUFFER_SIZE = 10 # redis中最多缓存的指令数量

# 加载遥测数据格式配置文件,生成UDP包格式
config_file = "remote_control_config.json"
config_file_path = os.path.dirname(os.path.abspath(__file__)) + "/" + config_file
REMOTE_CONTROL_UDP_FORMAT = generate_udp_format(config_file_path)
LENGTH = 11
SENDER_ID  = 0x55
RECEIVER_ID = 0xAA


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
    指令码枚举值
"""
class Instruction(Enum):
    APP_RESTART = 0xFED1
    APP_STOP = 0xFED2
    STOP_DOWNLOAD = 0xFED3

"""
    UDP 解析和组包 
"""
def pack_udp_packet(instruction):
    time_s, time_ms = get_timestamps()
    udp_packet = struct.pack(REMOTE_CONTROL_UDP_FORMAT, 
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
        = struct.unpack(REMOTE_CONTROL_UDP_FORMAT, udp_packet)
    return ins_type, instruction

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

def execute(instruction):
    print(hex(instruction))
    print(Instruction.APP_START.value)
    if instruction == Instruction.APP_START.value:
        service_list = ['image_receiver', 'yolov5','quality']
        control_services(service_list, turn_on=True)
    elif instruction == Instruction.APP_STOP.value:
        service_list = ['image_receiver', 'yolov5','quality']
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