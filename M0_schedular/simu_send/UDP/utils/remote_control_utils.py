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
LENGTH = 29
SENDER_ID  = 0x00
RECEIVER_ID = 0x11

"""
    指令码枚举值
"""
class Instruction(Enum):
    DEVICE_STATE = 0x00
    DEVICE_RESET = 0x01
    APP_STOP = 0x10
    APP_START = 0x11
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