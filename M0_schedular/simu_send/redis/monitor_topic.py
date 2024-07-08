import argparse
import redis
import json
from pprint import pprint
import time

# 长字符压缩显示长度
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

# 消息内容打印函数
def message_handler(topic, message):
    # print(f"Topic: {topic}, Message: {message['data'].decode()}")  # 处理接收到的消息
    data_dict = eval(message['data'].decode())
    # 处理字段长度过长的情况
    max_field_length = 20  # 最大字段长度设置为 20
    truncated_dict = truncate_dict_fields(data_dict, max_field_length)
    print(f"Topic: {topic}, Message:")
    pprint(truncated_dict)

# 订阅到某一个topic，实时输出发布的message
def monitor_redis_topic(redis_host, redis_port, topic):
    r = redis.Redis(host=redis_host, port=redis_port)
    pubsub = r.pubsub()
    # 订阅指定频道
    pubsub.subscribe(topic)
    # 启动监听循环
    for message in pubsub.listen():
        if message['type'] == 'message':
            message_handler(topic, message)

# 每隔0.5s轮询某一个queue，输出最新的元素
def listen_to_queue(redis_host, redis_port, queue):
    r = redis.Redis(host=redis_host, port=redis_port)
    TEMP_QUEUE = 'temp_queue'
    while True:
         # 使用 BRPOPLPUSH 命令阻塞地监听队列
        message = r.lrange(queue, 0, 0)
        if message:
            print(f'Received: {message[0].decode("utf-8")}')
        time.sleep(0.5)

# 解析命令行参数
parser = argparse.ArgumentParser()
parser.add_argument("--topic", help="Redis topic to monitor")
parser.add_argument("--queue", help="Redis queue to monitor")
args = parser.parse_args()

# 示例使用
redis_host = '127.0.0.1'  # Redis 主机名或 IP 地址
redis_port = 6379  # Redis 端口号

"""
    redis-3 星上时： --queue queue.time
"""
if args.topic:
    topic = args.topic
    print(f"订阅主题 {topic} ...")
    monitor_redis_topic(redis_host, redis_port, topic)
elif args.queue:
    queue = args.queue
    print(f"监听队列 {queue} ...")
    listen_to_queue(redis_host, redis_port, queue)
else:
    print("参数有误")