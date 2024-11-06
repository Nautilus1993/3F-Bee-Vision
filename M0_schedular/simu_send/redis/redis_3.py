import redis
import time

# 连接redis
REDIS = redis.Redis(host='127.0.0.1', port=6379)
TOPIC_TIME = 'queue.time' 
MAX_LENGTH = 10


# 生成星上时格式的时间戳
def get_timestamps():
    current_time = time.time()
    time_s = int(current_time)
    time_ms = int((current_time - time_s) * 1000)
    return time_s, time_ms

# 用于时间同步
def sync_time():
    current_time = time.time()
    next_second = current_time + 1 - (current_time % 1)
    time.sleep(next_second - current_time)

# 模拟星上时发送。从0s开始，每秒发送一次时间戳
def send_timestamp():
    counter = 0
    while True:
        time_s = counter
        time_ms = 0
        sys_time_s, sys_time_ms = get_timestamps()
        # 星上时时间戳，系统时间，两者差值
        timestamp = {
            'time_s': time_s,
            'time_ms': time_ms,
            'sys_time_s': sys_time_s,
            'sys_time_ms': sys_time_ms,
            'delta_s': sys_time_s - time_s,
            'delta_ms': sys_time_ms - time_ms
        }
        # 将消息推送到队列
        REDIS.lpush(TOPIC_TIME, str(timestamp))
        # 修剪队列长度
        REDIS.ltrim(TOPIC_TIME, 0, MAX_LENGTH - 1)
        counter += 1
        sync_time()

def main():
    send_timestamp()

if __name__=="__main__":
    main()