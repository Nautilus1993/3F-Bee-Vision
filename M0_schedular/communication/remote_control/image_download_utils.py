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

from utils.share import LOGGER, serialize_msg, deserialize_msg
from utils.constants import TOPIC_QUERY, DOWNLOAD_SERVICE_NAME
from download.file_down_utils import check_and_zip_files, \
    DownloadState, update_download_status
from message_config.udp_format import INJECT_DATA_IMAGE_FORMAT 
from remote_control_utils import REDIS, Instruction, is_service_running, control_services

class DownloadStrategy(Enum):
    """
        下载策略枚举值
    """
    TOP_N = 0x55            # 择优下载N张图片
    BY_TIME = 0x77          # 按时间戳下行

    
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
        0,                  # 1. 有效数据长度
        0,                  # 2. 数据发送方
        0,                  # 3. 数据接收方
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

def query_best_images(download_image_num):
    """
        查询M3: 按照默认规则，获取历史中最好的N张图片
    """
    LOGGER.info(f"择优下载{download_image_num}张图片，正在查询...")
    redis_query = {
        'count': download_image_num,         # 返回指定数量的图片文件列表
        'time_start': 0,    # 图片时间戳区间，预留支持查找某段时间内的最好图片的接口
        'time_end': 0,   
        'sort': 0,          # 排序规则：默认按置信度排序，保留扩展排序规则的接口
        'source': 0,        # 载荷编号：保留扩展到多个载荷的接口 
        'timestamps':[]     # 时间戳参数
    }
    return redis_query

def query_images_by_time(download_image_num, timestamps):
    """
        查询M3: 按照时间戳查询图片
    """
    LOGGER.info(f"按时间戳下载{download_image_num}张图片，正在查询...")
    redis_query = {
        'count': download_image_num,         # 返回指定数量的图片文件列表
        'time_start': 0,    # 图片时间戳区间，预留支持查找某段时间内的最好图片的接口
        'time_end': 0,   
        'sort': 2,          # 排序规则：默认按置信度排序，保留扩展排序规则的接口
        'source': 0,        # 载荷编号：保留扩展到多个载荷的接口 
        'timestamps':timestamps     # 时间戳参数
    }
    return redis_query

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
    timestamps = timestamps[0:download_image_num]

    # 判断是否有下载任务正在运行，如果正在运行则忽略当前指令
    if is_downloading():
        LOGGER.info("文件下载任务正在运行中……可发指令停止当前服务")
        return 
    
    # 1. 查询需要下载的文件列表(redis-6)
    if download_strategy == DownloadStrategy.TOP_N.value:
        redis_query = query_best_images(download_image_num)
    elif download_strategy == DownloadStrategy.BY_TIME.value:
        redis_query = query_images_by_time(download_image_num, timestamps)
    else:
        LOGGER.error(f"图片下载策略数值有误{download_strategy}")
        return
    json_string = serialize_msg(redis_query)
    # print(json_string)
    # return # debug
    # 清空
    response_channel = f"{TOPIC_QUERY}:response"  # 用于接收响应的队列
    REDIS.ltrim(response_channel, 1, 0)  # 将响应队列修剪为空
    REDIS.rpush(TOPIC_QUERY, json_string)  # 将消息推送到指定的队列
    
    # 2. 解析查询结果
    LOGGER.info("已发送查询请求，等待相应...")
    response = REDIS.blpop(response_channel, timeout=10)[1]  # 阻塞等待接收响应消息
    response = deserialize_msg(response)
    LOGGER.info(f"收到查询结果: {response}")
    # 增加判断查询结果状态码的判断, 如果数据库查询异常，则返回对应状态值;注意读取字典的异常处理
    query_status = response['status']
    if query_status == 0:
        file_path = response['file_path']
        file_list = response['file_list']
    else:
        update_download_status(query_status, 0)
        return

        # 3. 确认图片文件存在并copy到临时存储区，并生成.zip文件,然后开启下载服务
    if check_and_zip_files(file_path, file_list):
        start_download_service()