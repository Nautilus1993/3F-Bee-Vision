import redis
import time
import base64
import json
from threading import Thread, Lock
import numpy as np


REDIS = redis.Redis(host='127.0.0.1' , port=6379)
REDIS_1_TOPIC = "topic.raw_img"
REDIS_2_TOPIC = "topic.img"
BUFFER = []

class RawImage:
    def __init__(self, name, time_s, time_ms, data, value, score):
        self.name = name
        self.time_s = time_s
        self.time_ms = time_ms
        self.data = data
        self.value = value
        self.score = score
    
    def __lt__(self, other):
        return self.score > other.score

def thresh_mean(image_data):
    """统计大于自适应阈值的亮度均值
    :param image_data: 传入图像 base64.b64decode(encoded_img)后的内容
    """
    nparr = np.frombuffer(image_data, np.uint8)
    # 定义采样点数
    num_samples = 256 * 256

    # 计算采样间隔
    step = len(nparr) // num_samples

    # 从数组中均匀采样
    small_nparr = nparr[::step][:num_samples]
    threshold = np.mean(small_nparr)
    img_thresh = np.where(small_nparr <= threshold, 0, small_nparr)
    # 统计大于阈值像素的亮度均值
    pix_nums = np.sum(img_thresh > 0)
    print(pix_nums)
    value = float(np.sum(img_thresh) / pix_nums)
    score = abs(value - 90)
    return value, score

def add_buffer(image_name, image_data, time_s, time_ms, score=thresh_mean):
    decoded_image_data = base64.b64decode(image_data)
    value, score = score(decoded_image_data)
    raw_image_obj = RawImage(image_name, time_s, time_ms, image_data, value, score)
    print(f"加入缓存：{image_name} 亮度值：{value}")
    BUFFER.append(raw_image_obj)

def process_buffer():
    print("开始排序")
    BUFFER.sort()
    best_raw_image = BUFFER[-1]
    BUFFER.clear()
    print("清空缓存")
    return best_raw_image

def is_buffer_ready(time_s):
    """
        根据buffer中image的时间戳和当前收到图片的时间戳，判别是否收齐一次滚动曝光的图片
        
        输入：
            time_s: int 最近收到图片的时间戳秒
        
        返回：
            buffer_is_ready: bool可以进行排序并输出组好结果；False接续接收原始图片
    """
    if(len(BUFFER) != 0):
        buffer_time = BUFFER[0].time_s
        if(time_s != buffer_time):
            return True
    return False

def extract_timestamp(filename):
    """
        用于从文件名中提取时间戳信息
        
        输入：
            filename (string): 文件名字符串
        输出：
            time_s, time_ms (tuple): 当前图片的拍摄时间戳
    """
    try:
        split_strings = filename.split("_")
        time_s = int(split_strings[0])
        time_ms = int(split_strings[1])
        return time_s, time_ms
    except ValueError:
        print(f"无法解析文件名：{filename}")

def image_handler(message):
    """
        收到一张图像，解析图片时间戳，并计算质量评价结果
    """
    try:
        
        if message['type'] == 'message':
            data = message['data'].decode('utf-8')
        data_dict = json.loads(data)
        image_name = data_dict['name']
        image_data = data_dict['data']
        #image_data = base64.b64decode(data_dict['data'])
        win_w, win_h = data_dict['win_size']
        [win_x, win_y] = data_dict['window']
        time_s, time_ms = extract_timestamp(image_name)
        
        if(is_buffer_ready(time_s)):
            best_image = process_buffer()
            print(f"最好图像为 {best_image.name} 亮度{best_image.value}")
            send_redis_2(best_image)

        add_buffer(image_name, image_data, time_s, time_ms)
        

    except Exception as e:
        print(f"Error: {e}")
        return None

def receive_redis_1(topic="topic.raw_img"):
    """
        订阅到redis_1，收到的图片放入队列
    """
    pubsub = REDIS.pubsub()
    # 订阅指定频道
    pubsub.subscribe(topic)
    # 启动监听循环
    for message in pubsub.listen():
        if message['type'] == 'message':
            start_time = time.time()
            image_handler(message)
            # 记录程序结束时间
            end_time = time.time()
            # 计算程序运行时长
            duration = end_time - start_time
            print(f"图片处理时长：{duration:.2f} 秒 ")

# 筛选后的图片发送到redis_2接口
def send_redis_2(raw_image):
    message = {
            'name': raw_image.name,
            'win_size': (2048, 2048),   # 不开窗
            'window': [0, 0],
            'data': raw_image.data
        }
    
    json_str = json.dumps(message)
    REDIS.publish(REDIS_2_TOPIC, json_str)    # send
    pass

def main():
    receive_redis_1()

if __name__=="__main__":
    main()