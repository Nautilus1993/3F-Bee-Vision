import struct
import redis
import time
import os
from .share import generate_udp_format, get_timestamps, LOGGER, format_udp_packet

# 发送端的IP地址和端口号
SERVER_PORT = 8090

# REDIS
REDIS = redis.Redis(host='127.0.0.1', port=6379)
TOPIC_RESULT = 'sat_bbox_det'
TOPIC_ANGLE = 'sat_angle_det'

# 加载遥测数据格式配置文件,生成UDP包格式
config_file = "telemeter_config.json"
config_file_path = os.path.dirname(__file__) + "/" + config_file
TELEMETER_UDP_FORMAT = generate_udp_format(config_file_path)

"""
    软件状态码: 
    1. 上一条指令值 (初始值0xFF)
    2. AI计算机设备状态 (默认值 0x00)
    3. 图像接收状态 (默认值 0x00)
"""
# TODO: 返回上一条执行的指令，增加状态监控逻辑
def fake_states():
    return 0xFF, 0x00, 0x00

def fake_timestamps():
    time_s, time_ms = get_timestamps()
    return time_s, time_ms, time_s, time_ms, time_s, time_ms

"""
    从redis中的读取识别结果，最多返回三个目标，不足三个结果用0补全
"""
# TODO: 把bbox换为角度
def get_result_from_redis():
    if REDIS.lrange(TOPIC_RESULT, 0, -1):
        data = REDIS.lrange(TOPIC_RESULT, 0, -1)
        bbox = [float(value.decode()) for value in data[0:-1]]
        image_name = data[-1].decode()
        return image_name, bbox
    return "No Image Received", [0, 0, 0, 0, 0, 0]

def fake_result_from_redis():
    # 目标1: 类别(0默认 1主体 2帆板); 俯仰角; 偏航角; 置信度
    target_1 = [0x01, 30, 30, 0.90]
    # 目标2
    target_2 = [0x02, 30, 30, 0.90]  
    # 目标3
    target_3 = [0x02, 30, 30, 0.90]  
    return "fake_image.png", target_1, target_2, target_3


"""
    UDP 解析和组包 
"""
def pack_udp_packet(c1, c2, ins_code, time_s, time_ms, t1, sys_status):
    states = fake_states()
    udp_packet = struct.pack(TELEMETER_UDP_FORMAT, 
        c1,                 # 3. 输出计数器
        c2,                 # 4. 指令接收计数器
        ins_code,           # 5. 指令接收状态码
        states[1],          # 6. AI计算机设备状态码
        states[2],          # 7. 图像接收状态码
        time_s,             # 8. 组包时间秒
        time_ms,            # 9. 组包时间毫秒
        t1[0],              # 15. 目标1 识别结果
        t1[1],              # 16. 目标1 方位角
        t1[2],              # 17. 目标1 俯仰角
        t1[3],              # 18. 目标1 置信度
        sys_status[0],      # 35. CPU占用率
        sys_status[1],      # 36. 磁盘占用率
        sys_status[2]       # 37. 内存占用率
    )
    return udp_packet

def unpack_udp_packet(udp_packet):
    counter_telemeter, counter_instruction, \
    state_instruction, state_computer, state_image, \
    time_s, time_ms, \
    t1_class, t1_vertical, t1_horizon, t1_conf, \
    cpu_usage, disk_usage, memory_usage \
        = struct.unpack(TELEMETER_UDP_FORMAT, udp_packet)
    return counter_telemeter, time_s, time_ms, \
        [t1_class, t1_vertical, t1_horizon, t1_conf]

def format_telemeter(udp_packet):
    format_udp_packet(udp_packet, config_file_path)