import struct
import redis
import os
import json
from enum import Enum
from typing import List

import sys
# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)

# 加载docker client用于控制docker compose 服务
from utils.docker_status import DockerComposeManager
from utils.share import LOGGER, get_timestamps, serialize_msg, deserialize_msg
from download.file_down_utils import check_and_zip_files, \
    DownloadState, update_download_status
from utils.constants import TOPIC_INSTRUCTION, TOPIC_TIME, TOPIC_QUERY, \
    REDIS_QUEUE_MAX_LENGTH, DOWNLOAD_SERVICE_NAME, COMPOSE_FILE

# 加载遥测数据格式配置文件,生成UDP包格式
from message_config.udp_format import INDIRECT_INS_UDP_FORMAT, \
    TIME_INS_FORMAT, INJECT_DATA_IMAGE_FORMAT

# REDIS
REDIS = redis.Redis(host='127.0.0.1', port=6379)

LENGTH = 9  
SENDER_ID  = 0x55
RECEIVER_ID = 0xAA

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
    DOWNLOAD_IMAGE = 0xF3   # 图像下行指令
    UPDATE_PARAMS = 0xF4    # 常量修改指令

class DownloadStrategy(Enum):
    """
        下载策略枚举值
    """
    TOP_N = 0x55            # 择优下载N张图片
    BY_TIME = 0x77          # 按时间戳下行

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
    elif instruction_code == Instruction.STOP_DOWNLOAD.value:
        control_services(['file_download'], turn_on=False)
        update_download_status(DownloadState.STOPPED.value, 0)
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
    json_str = json.dumps(timestamp)
    REDIS.lpush(TOPIC_TIME, json_str)
    # 修剪队列长度
    REDIS.ltrim(TOPIC_TIME, 0, REDIS_QUEUE_MAX_LENGTH - 1)

def read_time_from_redis():
    """
        从redis中读取星上时信息，用于计算图片延迟。
    """
    default_time = 0, 0, 0, 0, 0, 0
    tf_time = REDIS.lrange(TOPIC_TIME,0, 0)
    if not tf_time:
        LOGGER.error("Redis中没有时间转换信息！")
        return default_time
    try:
        tf_time = json.loads(tf_time[0])
    except Exception as e:
        LOGGER.exception(f"星上时json反序列化异常 {e}")
        return default_time
    # print(tf_time)
    time_s = tf_time['time_s']
    time_ms = tf_time['time_ms']
    sys_time_s = tf_time['sys_time_s']
    sys_time_ms = tf_time['sys_time_ms']
    delta_s = tf_time['delta_s']
    delta_ms = tf_time['delta_ms']
    return time_s, time_ms, sys_time_s, sys_time_ms, delta_s, delta_ms

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
def pack_inject_data_image_packet(
        download_image_num: int,
        download_strategy: int,
        timestamps:List[int]):
    """
        注入数据-图片下行指令UDP组包(仅用于测试)
        输入: 
        下传图片数量: 1-10最多下载十张图片
        下传策略: 0x55按最优策略下行，0xAA按时间戳
        时间戳: 星上时戳秒，用于寻找该时刻拍摄的图片,长度固定10
    """
    if len(timestamps) != 10:
        print(f"时间戳长度{len(timestamps)}有误")
        return
    udp_packet = struct.pack(INJECT_DATA_IMAGE_FORMAT, 
        LENGTH,             # 1. 有效数据长度
        SENDER_ID,          # 2. 数据发送方
        RECEIVER_ID,        # 3. 数据接收方
        0x29,               # 4. 数据类型
        0,                  # 5. 指令时间码
        Instruction.DOWNLOAD_IMAGE.value, # 6. 指令类型码
        download_image_num, # 7. 下行图片数量
        download_strategy,  # 8. 图片下载策略
        timestamps[0],      # 9. 时间戳1
        timestamps[1],      # 10. 时间戳2
        timestamps[2],      # 11. 时间戳3
        timestamps[3],      # 12. 时间戳4
        timestamps[4],      # 13. 时间戳5
        timestamps[5],      # 14. 时间戳6
        timestamps[6],      # 15. 时间戳7
        timestamps[7],      # 16. 时间戳8
        timestamps[8],      # 17. 时间戳9
        timestamps[9],      # 18. 时间戳10
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
    t1, t2, t3, t4, t5, t6, t7, t8, t9, t10, \
    chunksum, frameend = struct.unpack(INJECT_DATA_IMAGE_FORMAT, udp_packet)
    timestamp = [t1, t2, t3, t4, t5, t6, t7, t8, t9, t10]
    return download_image_num, download_strategy, timestamp

def execute_inject_data_image_download(
        download_image_num,
        download_strategy,
        timestamps
):
    """
        执行注入数据指令，根据指令码决定启动或关闭指定服务。
    """
    print(f"收到指令下载图片数量{download_image_num}下载策略{download_strategy}")
    # 判断数据合法性
    if download_image_num <= 0 or download_image_num > 10:
        LOGGER.error(f"文件下载数量{download_image_num}超出范围！")
    if len(timestamps) != 10:
        LOGGER.error(f"时间戳个数{len(timestamps)}有误!") 
    # 截取时间戳有效参数部分
    timestamps = timestamps[0:download_image_num-1]

    # 判断是否有下载任务正在运行，如果正在运行则忽略当前指令
    if is_downloading():
        LOGGER.info("文件下载任务正在运行中……可发指令停止当前服务")
        return 
    
    # 1. 查询需要下载的文件列表(redis-6)
    if download_strategy == DownloadStrategy.TOP_N.value:
        image_dir, image_names = query_best_images(download_image_num)
    elif download_strategy == DownloadStrategy.BY_TIME.value:
        image_dir, image_names = query_images_by_time(download_image_num, timestamps)
    else:
        LOGGER.error(f"图片下载策略数值有误{download_strategy}")
        return
    
    # 2. 确认图片文件存在并copy到临时存储区，并生成.zip文件,然后开启下载服务
    if check_and_zip_files(image_dir, image_names):
        start_download_service()

def query_best_images(download_image_num):
    """
        按照默认规则，获取历史中最好的N张图片
    """
    LOGGER.info(f"择优下载{download_image_num}张图片，正在查询...")
    message = {
        'count': download_image_num,         # 返回指定数量的图片文件列表
        'time_start': 0,    # 图片时间戳区间，预留支持查找某段时间内的最好图片的接口
        'time_end': 0,   
        'sort': 0,          # 排序规则：默认按置信度排序，保留扩展排序规则的接口
        'source': 0,        # 载荷编号：保留扩展到多个载荷的接口 
    }
    json_string = serialize_msg(message)
    REDIS.rpush(TOPIC_QUERY, json_string)  # 将消息推送到指定的队列
    response_channel = f"{TOPIC_QUERY}:response"  # 创建用于接收响应的队列
    response = REDIS.blpop(response_channel)[1]  # 阻塞等待接收响应消息
    response = deserialize_msg(response)
    file_path = response['file_path']
    file_list = response['file_list']
    return file_path, file_list

def query_images_by_time(download_image_num, timestamps):
    """
        按照时间戳查询图片
    """
    LOGGER.info(f"按时间戳下载{download_image_num}张图片，正在查询...")
    # TODO(wangyuhang)查询redis-6接口，获取图片路径和图片名称
    return "", []

def is_downloading():
    """
        查看是否有下载服务正在运行
    """
    return is_service_running(DOWNLOAD_SERVICE_NAME)

def start_download_service():
    """
        调起docker 服务，下传.zip文件，并同步进度到redis.
    """
    control_services([DOWNLOAD_SERVICE_NAME], turn_on=True)
    LOGGER.info("启动文件下载任务")

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
    if REDIS.llen(TOPIC_INSTRUCTION) > REDIS_QUEUE_MAX_LENGTH:
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

# =========  docker compose 相关函数 =========
manager = DockerComposeManager(COMPOSE_FILE)

def is_service_running(service_name):
    service_list_names = [container.name for container in manager.get_running_services()]
    return service_name in service_list_names

def control_services(service_list, turn_on):
    """
        调用相应的docker compose服务(收到关闭、重启、下行文件等)
    """
    if turn_on:
        manager.start_services(service_list)
    else:
        manager.stop_services(service_list)