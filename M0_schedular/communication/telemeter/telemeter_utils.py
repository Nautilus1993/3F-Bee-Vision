import struct
import redis
import time
import json
import os
import threading


import sys
# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)

from utils.share import format_udp_packet, LOGGER, \
    get_redis_key, deserialize_msg
from utils.constants import KEY_DOWNLOAD_STATUS, SERVICE_NAMES, SERVICE_IDS
from remote_control.remote_control_utils import read_instruction_from_redis
from algorithm_result import get_result_from_redis, get_image_statistic
from system_usage import get_device_status_from_redis
from utils.docker_status import DockerComposeManager, get_service_status

# 遥测帧UDP格式
from message_config.udp_format import TELEMETER_UDP_FORMAT

def get_instruction_status():
    """
        从redis中获取指令接收状态
    """
    json_string = read_instruction_from_redis()
    try:
        last_instruction = json.loads(json_string)
        ins_counter = last_instruction['counter']
        # 指令转为16进制数
        ins_code = int(last_instruction['instruction_code'], 16)
    except TypeError:
        ins_counter = 0
        ins_code = 0x00
    return ins_code, ins_counter

def get_docker_status():
    """
        返回Docker-compose.yaml文件中所有启动的服务，如果服务启动，
        则服务对应ID位置的bit置为1. 
        如果仅开启基础服务模块，返回 0000 0111 = 7
        如果所有模块都开启，返回0111 1111 = 127
    """
    # docker container中的docker-compose.yaml文件路径
    compose_file_path = "/usr/src/deploy/docker-compose.yaml"
    manager = DockerComposeManager(compose_file_path)
    docker_status = get_service_status(manager, SERVICE_NAMES, SERVICE_IDS)
    docker_status = int.from_bytes(docker_status, byteorder='big')
    # 目前服务数量为7，数值边界判断如下
    if docker_status >=0 and docker_status < (1 << len(SERVICE_NAMES)):
        return docker_status
    LOGGER.error(f"docker status数值有误{docker_status}")
    return 0

def get_device_status():
    """
        获取设备状态信息
    """
    device_status = get_device_status_from_redis()
    for statu in device_status:
        if statu < 0 or statu > 255:
            LOGGER.error("system status error: %s", device_status)
            return [0, 0, 0, 0]
    return device_status

def get_image_status():
    """
        获取图片接收延迟信息和图片筛选信息
    """
    image_status, image_sum, image_delays, image_score = \
          get_image_statistic()
    return image_status, image_sum, image_delays, int(image_score)

def get_yolov5_result():
    # TODO(wangyuhang):增加判断数据合法性的逻辑
    target, \
    angle_1, \
    angle_2, \
    angle_3, \
    image_time_s, \
    image_time_ms = get_result_from_redis()
    return target, angle_1, angle_2, angle_3, image_time_s, image_time_ms

def get_download_status():
    """
        从redis中获取文件下载的状态
        返回：1. 文件下载状态 2. 文件下载进度
        如果没有文件下载任务时，以上两个数值取0
    """
    json_string = get_redis_key(KEY_DOWNLOAD_STATUS)
    if json_string is None:
        LOGGER.info("文件下载任务不存在")
        return 0, 0
    message = deserialize_msg(json_string)
    try: 
        state = message['state']
        progress = message['progress']
    except KeyError as e:
        LOGGER.info("文件下传状态中不存在Key")
    return state, progress

def generate_incrementing_bytes(length):
    """
    生成一个从 0 开始循环递增的 bytes 对象，长度为指定的 length。

    参数:
    length (int): 生成的 bytes 对象的长度。

    返回:
    bytes: 包含从 0 开始循环递增值的 bytes 对象。
    """
    return bytes([i % 256 for i in range(length)])
fake_string_43_48 = generate_incrementing_bytes(14)

"""
    UDP 解析和组包 
"""
def pack_telemeter_packet(c1, c2, ins_code, \
        sys_time_s, sys_time_ms, \
        docker_status, \
        target, cabin, panel_1, panel_2, sys_status, \
        image_status, image_sum, image_delays, image_score, \
        image_time_s, image_time_ms, exposure, win_w, win_h, win_x, win_y, \
        time_s, download_state, download_progress):
    udp_packet = struct.pack(TELEMETER_UDP_FORMAT, 
        sys_time_s,         # 1. 组包时间秒
        sys_time_ms,        # 2. 组包时间毫秒
        c1,                 # 3. 输出计数器
        c2,                 # 4. 指令接收计数器
        ins_code,           # 5. 指令接收状态码
        0x00,               # 6. CPU温度(TODO)
        sys_status[0],      # 7. CPU占用率
        sys_status[1],      # 8. 磁盘占用率
        sys_status[2],      # 9. 内存占用率
        sys_status[3],      # 10. AI计算机功率
        docker_status,      # 11. 软件基础模块运行状态
        0x00,               # 12. 算法模块运行状态(无效)
        image_status,       # 13. 图像接收状态码
        image_delays[0],    # 14. 图像1接收时延
        image_delays[1],    # 15. 图像2接收时延
        image_delays[2],    # 16. 图像3接收时延
        image_delays[3],    # 17. 图像4接收时延
        image_sum,          # 18. 筛选图像总数
        image_score,        # 19. 当前识别图像质量指标（亮度）
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
        time_s,             # 40. 上一次收到的星上时秒
        download_state,     # 41. 文件下行状态值
        download_progress,  # 42. 文件下行进度值
        fake_string_43_48   # 43-48:共14bytes保留字段
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
    # print(f"数据长度 {len(data)} 校验和: {checksum}")
    return checksum

def sync_time():
    """
        同步系统时间，让遥测数据整秒发送
    """
    current_time = time.time()
    next_second = current_time + 1 - (current_time % 1)
    time.sleep(next_second - current_time)

def main():
    get_download_status()

if __name__=="__main__":
    main()