import redis
import time
import base64
import json
import numpy as np


REDIS = redis.Redis(host='127.0.0.1' , port=6379)
REDIS_1_TOPIC = "topic.raw_img"
REDIS_2_TOPIC = "topic.img"
REDIS_8_TOPIC = "topic.image_status"
BUFFER = []
DELAYS = []

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
    # print('nparr size:', nparr.size)
    if nparr.size >= 256 * 256:
        num_samples = 256 * 256
        # 计算采样间隔
        step = len(nparr) // num_samples
        # 从数组中均匀采样
        small_nparr = nparr[::step][:num_samples]
    else:
        small_nparr = nparr
    threshold = np.mean(small_nparr)
    img_thresh = np.where(small_nparr <= threshold, 0, small_nparr)
    # 统计大于阈值像素的亮度均值
    pix_nums = np.sum(img_thresh > 0)
    value = float(np.sum(img_thresh) / pix_nums)
    score = abs(value - 130)  # human best exposure
    return value, score

def add_buffer(image_name, image_data, time_s, time_ms, score=thresh_mean, delay=0):
    decoded_image_data = base64.b64decode(image_data)
    value, score = score(decoded_image_data)
    raw_image_obj = RawImage(image_name, time_s, time_ms, image_data, value, score)
    # print(f"加入缓存：{image_name} 亮度值：{value}")
    BUFFER.append(raw_image_obj)
    DELAYS.append(delay)

def process_buffer():
    # print("开始排序")
    BUFFER.sort()
    best_raw_image = BUFFER[-1]
    BUFFER.clear()
    # print("清空缓存")
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
        time_s = int(split_strings[1])
        time_ms = int(split_strings[2])
        return time_s, time_ms
    except ValueError:
        print(f"无法解析文件名：{filename}")

def get_delays_from_buffer():
    """
        当buffer中接收到一组滚动保管的图片时，取出每一张图片的接收时延
        返回[int]: 返回数值为int型的数组
    """
    image_delays = DELAYS.copy()
    DELAYS.clear()
    return image_delays

def send_images_status_to_redis(image_delays, image_score, image_sum):
    """
        将一组滚动曝光的图片接收和排序情况发给Redis
        输入：
        image_delays(list): 接收到的N张图片的时延(N<=4)
        image_score(int): 筛选出的图片亮度值/其他评价指标
        image_sum(int): 接收到的图片总数
    """
    # 如果image_delays不足四个，则用0补全
    while len(image_delays) < 4:
        image_delays.append(0)
    message = {
            'image_status': 0,
            'image_sum': image_sum, 
            'image_delays': image_delays,
            'image_score': int(image_score),
            'timestamp': time.time()
        }
    json_str = json.dumps(message)
    # 先清空队列，再推送消息
    REDIS.ltrim(REDIS_8_TOPIC, 1, 0)
    REDIS.lpush(REDIS_8_TOPIC, json_str)

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
        delay = data_dict['delay']
        time_s, time_ms = extract_timestamp(image_name)
        
        if(is_buffer_ready(time_s)):
            # 获取本组滚动曝光图片的接收时延
            image_delays = get_delays_from_buffer()
            image_sum = len(BUFFER)
            # 筛选一组滚动曝光中最好的图片，筛选后清空缓存
            best_image = process_buffer()
            print(f"最好图像为 {best_image.name} 亮度{best_image.value}")
            # 将筛选后的图片发送给Redis
            send_redis_2(best_image, win_w, win_h, win_x, win_y)
            # 将图片接收和筛选情况发送给redis
            send_images_status_to_redis(image_delays, best_image.value, image_sum)

        add_buffer(image_name, image_data, time_s, time_ms, delay=delay)

    except Exception as e:
        print(f"抛出异常: {e}")
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
def send_redis_2(raw_image, win_w, win_h, win_x, win_y):
    message = {
            'name': raw_image.name,
            'win_size': (win_w, win_h), 
            'window': [win_x, win_y],
            'data': raw_image.data
        }
    
    json_str = json.dumps(message)
    REDIS.publish(REDIS_2_TOPIC, json_str)    # send

def main():
    receive_redis_1()

if __name__=="__main__":
    main()