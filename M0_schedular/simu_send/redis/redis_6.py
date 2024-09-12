import redis
from redis.exceptions import ConnectionError, TimeoutError
import os
import time
import base64
import cv2
import numpy as np

# 连接redis
REDIS = redis.Redis(host='127.0.0.1', port=6379)
CHANNEL = 'channel.query'

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

    send_message(CHANNEL, str(message))   # send

except ConnectionError as ce:
    print("无法连接到Redis服务器:" + str(ce))

except TimeoutError:
    print("Redis操作超时")

finally:
    REDIS.close()