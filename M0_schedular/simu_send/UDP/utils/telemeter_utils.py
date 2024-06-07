import struct
import redis
import time
import json
import os
from .share import generate_udp_format, get_timestamps, LOGGER, format_udp_packet
from .yolov5_result import get_result_from_redis

# 发送端的IP地址和端口号
SERVER_PORT = 8090

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

def get_yolov5_result():
    # TODO(wangyuhang):增加判断数据合法性的逻辑
    target, angle_1, angle_2, angle_3 = get_result_from_redis()
    return target, angle_1, angle_2, angle_3
    

def fake_result_from_redis():
    # 目标1: 类别(0默认 1主体 2帆板); 俯仰角; 偏航角; 置信度
    target_1 = [0x01, 0.0, 30.0, 90]
    # 目标2
    target_2 = [0x02, -30.0, 30.0, 90]  
    # 目标3
    target_3 = [0x02, 30.0, 30.0, 90]  
    return "fake_image.png", target_1, target_2, target_3

"""
    UDP 解析和组包 
"""
def pack_udp_packet(c1, c2, ins_code, time_s, time_ms, target, t1, t2, t3, sys_status):
    states = fake_states()
    udp_packet = struct.pack(TELEMETER_UDP_FORMAT, 
        time_s,             # 1. 组包时间秒
        time_ms,            # 2. 组包时间毫秒
        c1,                 # 3. 输出计数器
        c2,                 # 4. 指令接收计数器
        ins_code,           # 5. 指令接收状态码
        sys_status[0],      # 7. CPU占用率
        sys_status[1],      # 8. 磁盘占用率
        sys_status[2],      # 9. 内存占用率
        target,             # 27. BB类别
        t1[0],              # 28. 主体 识别结果
        t1[1],              # 29. 主体 方位角
        t1[2],              # 30. 主体 俯仰角
        t1[3],              # 31. 主体 置信度
        t2[0],              # 32. 主体 识别结果
        t2[1],              # 33. 主体 方位角
        t2[2],              # 34. 主体 俯仰角
        t2[3],              # 35. 主体 置信度
        t3[0],              # 36. 主体 识别结果
        t3[1],              # 37. 主体 方位角
        t3[2],              # 38. 主体 俯仰角
        t3[3],              # 39. 主体 置信度
    )
    return udp_packet

def unpack_udp_packet(udp_packet):
    time_s, time_ms, \
    counter_telemeter, counter_instruction, instruction_code, \
    cpu_usage, disk_usage, memory_usage, target, \
    t1_class, t1_horizon, t1_vertical, t1_conf, \
    t2_class, t2_horizon, t2_vertical, t2_conf, \
    t3_class, t3_horizon, t3_vertical, t3_conf \
        = struct.unpack(TELEMETER_UDP_FORMAT, udp_packet)
    return counter_telemeter, time_s, time_ms

def format_telemeter(udp_packet):
    format_udp_packet(udp_packet, config_file_path)

# def main():
#     result = get_result_from_redis()
#     print(result)

# if __name__=="__main__":
#     main()