import redis
from redis.exceptions import ConnectionError, TimeoutError
import os
import time
import base64
import cv2
import numpy as np
import json

# 连接redis
REDIS = redis.Redis(host='127.0.0.1', port=6379)
CHANNEL = 'channel.query'

"""
    Redis-6查询字段含义：
    count: 查询图片张数，取值0~10
    time_start & time_end: 查询图片的时间戳秒范围(目前无此功能)
    sort: 排序策略
        0-置信度排序,1-时间戳范围, 2-时间戳直接查
    source: 数据来源(目前无此功能)
"""

# 按最优策略查询3张图片
q1 = {
    'count': 3,
    'time_start': 0,
    'time_end': 0,   
    'sort': 0,
    'source': 0,
    'timestamps':[]
}
# 按照时间戳查询3张图片
q2 = {
    'count': 3,
    'time_start': 0,
    'time_end': 0,   
    'sort': 2,
    'source': 0,
    'timestamps':[700, 555, 98] # 三个时间戳均能查找到
}

# 按照最优策略查询50张图片，此处50是一个不合法的查询数值
q3 = {
    'count': 50,
    'time_start': 0,
    'time_end': 0,   
    'sort': 0,
    'source': 0,
    'timestamps':[]
}

# 查询策略参数不合法
q4 = {
    'count': 3,
    'time_start': 0,
    'time_end': 0,   
    'sort': 6,
    'source': 0,
    'timestamps':[]
}

# 按照时间戳查找，时间戳个数和count不一致
q5 = {
    'count': 7,
    'time_start': 0,
    'time_end': 0,   
    'sort': 2,
    'source': 0,
    'timestamps':[700, 555, 3000]
}

# redis消息缺少key=count
q6 = {
    'time_start': 0,
    'time_end': 0,   
    'sort': 2,
    'source': 0,
    'timestamps':[700, 555, 3000]
}

# 重复的时间戳
q7 = {
    'count': 3,
    'time_start': 0,
    'time_end': 0,   
    'sort': 2,
    'source': 0,
    'timestamps':[700, 700, 20]
}

# 超出文件最大查询个数的时间戳
q8 = {
    'count': 0,
    'time_start': 0,
    'time_end': 0,   
    'sort': 2,
    'source': 0,
    'timestamps':[1,2,3,4,5,6,7,8,9,10,11,12,13]
}

def send_message(channel, message):
    REDIS.rpush(channel, message)  # 将消息推送到指定的队列
    response_channel = f"{channel}:response"  # 创建用于接收响应的队列
    response = REDIS.blpop(response_channel)[1]  # 阻塞等待接收响应消息
    print(f"Received response: {response.decode('utf-8')}")

try:
    # 尝试执行Redis操作
    message = {
        'count': 3,         # 返回指定数量的图片文件列表
        'time_start': 0,    # 图片时间戳区间，预留支持查找某段时间内的最好图片的接口
        'time_end': 0,   
        'sort': 0,          # 排序规则：默认按置信度排序，保留扩展排序规则的接口
        'source': 0,        # 载荷编号：保留扩展到多个载荷的接口 
    }
    json_msg = json.dumps(message)
    send_message(CHANNEL, json_msg)   # send

except ConnectionError as ce:
    print("无法连接到Redis服务器:" + str(ce))

except TimeoutError:
    print("Redis操作超时")

finally:
    REDIS.close()