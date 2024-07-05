import redis

# 连接redis
REDIS = redis.Redis(host='127.0.0.1', port=6379)
CHANNEL = 'channel.query'

def handle_message(channel, message):
    response_channel = f"{channel}:response"  # 创建用于发送响应的队列
    response = process_message(message)  # 处理接收到的消息
    REDIS.rpush(response_channel, response)  # 将响应推送到响应队列

def process_message(message):
    # 在这里查找文件并返回列表
    response = {
        'file_path': 'path_to_files',
        'file_list':[
            '1.jpg',
            '2.jpg',
            '3.jpg'
        ]
    }
    return f"Processed: {response}"

def receive_message(channel):
    while True:
        message = REDIS.blpop(channel)[1]  # 阻塞等待接收消息
        handle_message(channel, message.decode('utf-8'))

# 示例用法


receive_message(CHANNEL)