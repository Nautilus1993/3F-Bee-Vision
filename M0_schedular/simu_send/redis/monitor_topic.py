import argparse
import redis
import json
from pprint import pprint

def truncate_string(string, max_length):
    if len(string) <= max_length:
        return string
    else:
        return string[:max_length] + "..." + str(len(string))

def truncate_dict_fields(data_dict, max_length):
    truncated_dict = {}
    for key, value in data_dict.items():
        if isinstance(value, str):
            truncated_dict[key] = truncate_string(value, max_length)
        else:
            truncated_dict[key] = value
    return truncated_dict

def message_handler(topic, message):
    # print(f"Topic: {topic}, Message: {message['data'].decode()}")  # 处理接收到的消息
    data_dict = eval(message['data'].decode())
    # 处理字段长度过长的情况
    max_field_length = 20  # 最大字段长度设置为 20
    truncated_dict = truncate_dict_fields(data_dict, max_field_length)
    print(f"Topic: {topic}, Message:")
    pprint(truncated_dict)

def monitor_redis_topic(redis_host, redis_port, topic):
    r = redis.Redis(host=redis_host, port=redis_port)
    pubsub = r.pubsub()
    # 订阅指定频道
    pubsub.subscribe(topic)
    

    # 启动监听循环
    for message in pubsub.listen():
        if message['type'] == 'message':
            message_handler(topic, message)

# 解析命令行参数
parser = argparse.ArgumentParser()
parser.add_argument("--topic", help="Redis topic to monitor")
args = parser.parse_args()

# 示例使用
redis_host = '127.0.0.1'  # Redis 主机名或 IP 地址
redis_port = 6379  # Redis 端口号
topic = args.topic  # 从命令行参数获取要监听的 Redis topic
print(topic)

monitor_redis_topic(redis_host, redis_port, topic)