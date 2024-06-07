import redis
import json
from enum import Enum

# REDIS
REDIS = redis.Redis(host='127.0.0.1', port=6379)
TOPIC_RESULT = 'sat_bbox_det'
TOPIC_ANGLE = 'sat_bbox_angle_det'

"""
    靶标类别枚举值
"""
class Target(Enum):
    NONE = 0xFF     # 无效
    SINGLE = 0x00   # L形，单翼
    BALL = 0x01     # 球形 
    DOUBLE = 0x02   # 双翼     

"""
    部件类别枚举值
"""
class Category(Enum):
    NONE = 0x00     # 无效
    CABIN = 0x01    # 主体
    PANEL = 0x02    # 帆板

"""
    Redis中的数值转化为遥测数据类型
    Redis: [2.0, -2.140959675024313, 1.79414481327961, 0.8620831370353699]
    return: [0x01, -2.140, 1.794, 86]
"""
# [2.0, -2.140959675024313, 1.79414481327961, 0.8620831370353699]
def format_angle(angle_result):
    format_result = [
        int(angle_result[0]), # 类别(0默认 1主体 2帆板); 
        # 俯仰角; 偏航角; 置信度
        round(angle_result[1], 3),
        round(angle_result[2], 3),
        int(angle_result[3] * 100)
    ]
    return format_result

"""
    从redis中的读取识别结果，最多返回三个目标，不足三个结果用0补全
    # classes = ['L', 'Ball', 'D_cabin', 'D_panel']
    # 0:L
    # 1:Ball
    # 2:D_cabin
    # 3:D_panel
"""
def get_result_from_redis():
    # json加载失败或第一个识别结果置信度为0时，返回empty_result
    empty_result = Target.NONE.value, [0,0,0,0], [0,0,0,0], [0,0,0,0]
    serialized_data = REDIS.get(TOPIC_ANGLE)
    try:
        # Deserialize the JSON string to a dictionary
        data = json.loads(serialized_data)
    except json.JSONDecodeError as e:
        print("识别结果json解析异常", e)
        return empty_result

    target, _, _, conf = format_angle(data['angle1'])
    
    # 第一个识别结果置信度为0
    if conf == 0:
        return empty_result 
    
    # 由第一个结果的category数值，可以判断当前BB的类别
    if target == Target.SINGLE.value:     # L形，只返回一个帆板
        panel_1 = format_angle(data['angle1'])
        main_body = [0,0,0,0]
        panel_2 = [0,0,0,0]
    elif target == Target.BALL.value:     # 球形，只返回一个主体
        main_body = format_angle(data['angle1'])
        panel_1 = [0,0,0,0]
        panel_2 = [0,0,0,0]
    elif target == Target.DOUBLE.value:   # 双翼，返回主体和两个结果
        main_body = format_angle(data['angle1'])
        panel_1 = format_angle(data['angle2'])
        panel_2 = format_angle(data['angle3'])
    else:
        print("category value error")
        return empty_result

    return target, main_body, panel_1, panel_2

def main():
    result = get_result_from_redis()
    print(result)

if __name__=="__main__":
    main()