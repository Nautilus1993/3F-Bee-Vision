import struct
import redis
import time
import json
import os


import sys
# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)

from utils.share import format_udp_packet
from yolov5_result import get_result_from_redis
from system_usage import get_system_status

# 遥测帧UDP格式
from message_config.udp_format import TELEMETER_UDP_FORMAT

# 发送端的IP地址和端口号
SERVER_PORT = 18089
SEND_IP = '192.168.0.103'

# 获取系统状态
def get_device_status():
    # TODO(wangyuhang):增加判断数据合法性的逻辑
    device_status = get_system_status()
    return device_status
    

def get_yolov5_result():
    # TODO(wangyuhang):增加判断数据合法性的逻辑
    target, \
    angle_1, \
    angle_2, \
    angle_3, \
    image_time_s, \
    image_time_ms = get_result_from_redis()
    return target, angle_1, angle_2, angle_3, image_time_s, image_time_ms
    

def fake_result_from_redis():
    # 目标1: 类别(0默认 1主体 2帆板); 俯仰角; 偏航角; 置信度
    target_1 = [0x01, 0.0, 30.0, 90]
    # 目标2
    target_2 = [0x02, -30.0, 30.0, 90]  
    # 目标3
    target_3 = [0x02, 30.0, 30.0, 90]  
    return "fake_image.png", target_1, target_2, target_3

"""
    生成给定长度的随机bytes
"""
def generate_random_bytes(length):
    return os.urandom(length)

def generate_incrementing_bytes(length):
    """
    生成一个从 0 开始循环递增的 bytes 对象，长度为指定的 length。

    参数:
    length (int): 生成的 bytes 对象的长度。

    返回:
    bytes: 包含从 0 开始循环递增值的 bytes 对象。
    """
    return bytes([i % 256 for i in range(length)])

# fake_string_11_26 = generate_incrementing_bytes(30)
fake_string_40_50 = generate_incrementing_bytes(20)

"""
    UDP 解析和组包 
"""
def pack_telemeter_packet(c1, c2, ins_code, \
        time_s, time_ms, \
        target, cabin, panel_1, panel_2, sys_status, \
        image_time_s, image_time_ms, exposure, win_w, win_h, win_x, win_y):
    udp_packet = struct.pack(TELEMETER_UDP_FORMAT, 
        time_s,             # 1. 组包时间秒
        time_ms,            # 2. 组包时间毫秒
        c1,                 # 3. 输出计数器
        c2,                 # 4. 指令接收计数器
        ins_code,           # 5. 指令接收状态码
        0x00,               # 6. AI计算机设备状态码(TODO)
        sys_status[0],      # 7. CPU占用率
        sys_status[1],      # 8. 磁盘占用率
        sys_status[2],      # 9. 内存占用率
        0x00,               # 10. AI计算机功率(TODO)
        0x00,               # 11. 软件基础模块运行状态
        0x00,               # 12. 算法模块运行状态
        0x00,               # 13. 图像接收状态码
        0,                  # 14. 图像1接收时延
        0,                  # 15. 图像2接收时延
        0,                  # 16. 图像3接收时延
        0,                  # 17. 图像4接收时延
        0,                  # 18. 筛选图像总数
        0,                  # 19. 当前识别图像质量指标（亮度）
        image_time_s,       # 20. 当前识别图像时间戳秒
        image_time_ms,      # 21. 当前识别图像时间戳毫秒
        exposure,           # 22. 当前识别图像曝光时长
        win_w,              # 23. 当前识别图像开窗宽度w
        win_h,              # 24. 当前识别图像开窗高度h
        win_x,              # 25. 当前识别图像开窗位置x
        win_y,              # 26. 当前识别图像开窗位置y
        target,             # 27. BB类别
        cabin[0],           # 28. 主体 识别结果
        cabin[1],           # 29. 主体 方位角
        cabin[2],           # 30. 主体 俯仰角
        cabin[3],           # 31. 主体 置信度
        panel_1[0],         # 32. 左帆板 识别结果
        panel_1[1],         # 33. 左帆板 方位角
        panel_1[2],         # 34. 左帆板 俯仰角
        panel_1[3],         # 35. 左帆板 置信度
        panel_2[0],         # 36. 右帆板 识别结果
        panel_2[1],         # 37. 右帆板 方位角
        panel_2[2],         # 38. 右帆板 俯仰角
        panel_2[3],         # 39. 右帆板 置信度
        fake_string_40_50   # 40-50:共20bytes保留字段
    )
    return udp_packet

def unpack_telemeter_packet(udp_packet):
    time_s, time_ms, \
    counter_telemeter, counter_instruction, instruction_code, _, \
    cpu_usage, disk_usage, memory_usage, _, \
    fake_str1, \
    target, \
    t1_class, t1_horizon, t1_vertical, t1_conf, \
    t2_class, t2_horizon, t2_vertical, t2_conf, \
    t3_class, t3_horizon, t3_vertical, t3_conf, \
    fake_str2 \
        = struct.unpack(TELEMETER_UDP_FORMAT, udp_packet)
    return counter_telemeter, time_s, time_ms

def format_telemeter(udp_packet):
    config_file = 'telemeter_config.json'
    config_file_path = parent_dir + "/message_config/" + config_file
    format_udp_packet(udp_packet, config_file_path)

# TODO(wangyuhang):统一到pack_telemeter函数中
def pack_udp_packet(telemeter_data):
    """
        根据遥测数据计算校验和并附在遥测数据后面
        输入：遥测数据(96 bytes)
        输出：数据类型和长度 + 遥测数据 + 校验和 (101bytes)
    """
    UDP_FORMAT = "!HB96s"
    data_length = 96
    data_type = 0x12
    udp_packet = struct.pack(UDP_FORMAT, 
        data_length, 
        data_type, 
        telemeter_data)
    checksum = single_byte_checksum(udp_packet)
    udp_packet_with_checksum = struct.pack("!99sH",
        udp_packet,
        checksum)
    return udp_packet_with_checksum

def single_byte_checksum(data):
    """
    计算单字节校验和。

    参数:
    data (bytes): 需要计算校验和的字节数据。

    返回:
    int: 单字节校验和(0-65535)
    """
    checksum = sum(data) % 65536
    print(f"数据长度 {len(data)} 校验和: {checksum}")
    return checksum

def sync_time():
    """
        同步系统时间，让遥测数据整秒发送
    """
    current_time = time.time()
    next_second = current_time + 1 - (current_time % 1)
    time.sleep(next_second - current_time)

# def main():
#     result = get_result_from_redis()
#     print(result)

# if __name__=="__main__":
#     main()