import redis
import json
from enum import Enum
import re
import time
import os

import sys
# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)
from utils.constants import TOPIC_ANGLE, TOPIC_IMAGE_STATUS
# REDIS

REDIS = redis.Redis(host='127.0.0.1', port=6379)

"""
    靶标类别枚举值
"""
class Target(Enum):
    NONE = 0xFF     # 无效
    SINGLE = 0x00   # L形，单翼
    BALL = 0x01     # 球形 
    DOUBLE = 0x02   # 双翼     

"""
    部件识别结果类别枚举值
"""
class RESULT(Enum):
    NONE = 0xFF     # 无效
    GOOD = 0x55     # 正常

# 当部件识别结果为无效的时候，返回默认值
DEFAULT_RESULTS = [0xFF,0xFF,0xFF,0xFF]

def format_angle(angle_result):
    """
        Redis中的数值转化为遥测数据类型
        例如：
        Redis: [2.0, -2.140959675024313, 1.79414481327961, 0.8620831370353699]
        return: [0x01, -2.140, 1.794, 86]
    """
    format_result = [
        int(angle_result[0]), # 类别(0默认 1主体 2帆板); 
        # 俯仰角; 偏航角; 置信度
        round(angle_result[1], 3),
        round(angle_result[2], 3),
        int(angle_result[3] * 100)
    ]
    return format_result

def image_detect_result(data):
    """
        根据REDIS-2中的内容，解析出图片中识别到的部件类别和数值信息
        REDIS-2定义的类别：
        0:L
        1:Ball
        2:D_cabin
        3:D_panel

        本函数应固定返回4个数值：
        1. target 靶标类别(0-L型，1-球形，2-双翼)
        2. cabin 主体识别结果(是否有效；俯仰角; 方位角; 置信度)
        3. panel_1 左帆板识别结果(是否有效；俯仰角; 方位角; 置信度)
        4. panel_2 右帆板识别结果(是否有效；俯仰角; 方位角; 置信度)
    """
    # 定义默认值
    empty_result = \
            Target.NONE.value, DEFAULT_RESULTS, DEFAULT_RESULTS, DEFAULT_RESULTS
    # 解析第一个识别结果的内容,如果置信度为0，说明本次没有有效识别到任何物体
    target, _, _, conf = format_angle(data['angle1'])
    target2, _, _, conf2 = format_angle(data['angle2'])
    target3, _, _, conf3 = format_angle(data['angle3'])
    if conf == 0 and conf2==0 and conf3==0: 
        return empty_result
    
    # 由第一个结果的类别数值，可以判断当前BB的类别
    if target == Target.SINGLE.value:     # L形，只返回左帆板
        panel_1 = format_angle(data['angle1'])
        panel_1[0] = RESULT.GOOD.value
        cabin = DEFAULT_RESULTS
        panel_2 = DEFAULT_RESULTS

    elif target == Target.BALL.value:     # 球形，只返回主体
        cabin = format_angle(data['angle1'])
        cabin[0] = RESULT.GOOD.value
        panel_1 = DEFAULT_RESULTS
        panel_2 = DEFAULT_RESULTS

    # 增加只有一个双翼帆板的时候也返回目标类型的逻辑，有点丑陋，宇航老师再重构一下
    elif target == Target.DOUBLE.value or conf2!=0 or conf3!=0:   # 双翼，返回主体和两个帆板
        target = Target.DOUBLE.value
        cabin = format_angle(data['angle1'])
        # TODO(wangyuhang):如果双翼主体的置信度为0，则上面应该已经被返回empty result了，当前分支进不来
        if cabin[3] == 0:
            cabin = DEFAULT_RESULTS
        else:
            cabin[0] = RESULT.GOOD.value
        
        # 如果左帆板置信度为0，说明左帆板识别结果无效，返回默认值；否则按算法输入值返回
        panel_1 = format_angle(data['angle2'])
        if panel_1[3] == 0:
            panel_1 = DEFAULT_RESULTS
        else:
            panel_1[0] = RESULT.GOOD.value

        # 如果右帆板置信度为0，说明左帆板识别结果无效，返回默认值；否则按算法输入值返回
        panel_2 = format_angle(data['angle3'])
        if panel_2[3] == 0:
            panel_2 = DEFAULT_RESULTS
        else:
            panel_2[0] = RESULT.GOOD.value
    else:
        print(f"当前BB类型为无效值{target}")
        return empty_result

    return target, cabin, panel_1, panel_2
    
def image_meta_info(redis_message):
    """
        从REDIS-2中获取文件名和开窗信息，解析出相应的图片元信息
        例如输入：image_1000_300_2050.bmp, 开窗[2048,2000,0,10]
        应返回：
            image_time_s(int) : 1000
            image_time_ms(int): 300
            exposure(int): 2050
            win_w(int): 2048
            win_h(int): 2000
            win_x(int): 0
            win_y(int): 10
    """
    default_meta_info = 0, 0, 0, 0, 0, 0, 0
    image_name = redis_message['name']
    # 用.或_分割一个字符串["image", "1000", "300", "2050", "bmp"]
    image_infos = re.split(r'[._]', image_name)
    if len(image_infos) != 5:
        print("文件名解析有误！")
        return default_meta_info
    image_time_s = int(image_infos[1])
    image_time_ms = int(image_infos[2])
    exposure = int(image_infos[3])

    # 开窗信息
    window_infos = redis_message['window_info']
    if len(window_infos) != 4:
        print("开窗信息有误！")
        return default_meta_info
    win_w = int(window_infos[0])
    win_h = int(window_infos[1])
    win_x = int(window_infos[2])
    win_y = int(window_infos[3])

    return image_time_s, image_time_ms, exposure, win_w, win_h, win_x, win_y

def get_result_from_redis():   
    empty_result = \
        Target.NONE.value, DEFAULT_RESULTS, DEFAULT_RESULTS, DEFAULT_RESULTS, \
            0, 0, 0, 0, 0, 0, 0
    
    # 如果redis-2消息为空或加载失败，返回empty_result
    serialized_data = REDIS.get(TOPIC_ANGLE)
    if serialized_data == None:
        return empty_result
    try:
        # 反序列化redis-2消息
        data = json.loads(serialized_data)
    except json.JSONDecodeError as e:
        print("REDIS-2: 识别结果json解析异常", e)
        return empty_result
    
    # 如果json加载成功，解析文件的元信息
    target, cabin, panel_1, panel_2 = image_detect_result(data)
    image_time_s, image_time_ms, exposure, win_w, win_h, win_x, win_y = image_meta_info(data)
    return target, cabin, panel_1, panel_2, image_time_s, image_time_ms, \
            exposure, win_w, win_h, win_x, win_y      

def get_image_statistic(ttl_seconds=5):
    """
        从redis中获取一组滚动曝光的图片接收延迟、总数以及筛选出图像的分数。
        设置消息时限为5s,如果超过5s依然消息依然没有更新，则说明收图程序有问题，返回默认值
    """
    # 读取后立刻清空消息队列
    message = REDIS.lrange(TOPIC_IMAGE_STATUS, 0, 0)
    
    # 如果还未接收到图片，返回图片未收到状态值，并返回统计信息默认值
    default_statistic = 0xFF, 0, [0, 0, 0, 0], 0
    if not message:
        # print("Error: Redis中没有图片接收统计信息！")
        return default_statistic
    try:
        message = json.loads(message[0])
        image_status = message['image_status']
        image_sum = message['image_sum']
        image_delays = message['image_delays']
        image_score = message['image_score']
        timestamp = message['timestamp']
        if time.time() - timestamp > ttl_seconds:
            print("Redis中图片接收统计信息已过期！")
            REDIS.ltrim(TOPIC_IMAGE_STATUS, 1, 0)
            return default_statistic
        return image_status, image_sum, image_delays, image_score
    except KeyError:
        print("Redis键值有误！")
    return default_statistic

def main():
    pass

if __name__=="__main__":
    main()