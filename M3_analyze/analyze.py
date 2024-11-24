from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
import redis
import time
import base64
import numpy as np
import logging
from logging import handlers
import cv2
import os
import json
import queue
from queue import PriorityQueue  
import threading
from multiprocessing import Process
from database import DataStorage
import pdb

# 初始化log
logger = logging.getLogger("analyze-log")
logger.setLevel(logging.DEBUG)
log_file = "analyze.log"
# 设置日志文件大小在3M时截断
# 最多保留1个日志备份
fh = handlers.RotatingFileHandler(filename=log_file, maxBytes=3000000, backupCount=1)
formatter = logging.Formatter('%(asctime)s %(message)s')
# 输出到文件
fh.setFormatter(formatter)
logger.addHandler(fh)
# 输出到屏幕
ch = logging.StreamHandler()
logger.addHandler(ch)


# 初始化redis
conn = redis.Redis(host='127.0.0.1', port=6379)
sub = conn.pubsub()
sub.subscribe("topic.img")
logger.info("Receiving...")

# 初始化数据库
db = DataStorage('./data/m3.db')

# query redis
query = redis.Redis(host='127.0.0.1', port=6379)
query_sub = query.pubsub()
query_sub.subscribe("channel.query")
logger.info('query ready...')


# 初始化tsne降维工具
tsne = TSNE(n_components=3)


# evluation of the result
def eval_result(bbox1, bbox2, bbox3, angle1, angle2, angle3):
    # evaluation
    mean_conf = 0.0
    if bbox1[5] == 2:
        mean_conf = (bbox1[4] + bbox2[4] + bbox3[4]) / 3
    else:
        mean_conf = bbox1[4]
    
    if mean_conf == 0:
        mean_conf = 0.0001
        
    return 1.0/ mean_conf


def tsne_transform(data):
    return tsne.fit_transform(data)


image_dict = {} 
result_queue = queue.Queue()
rank_q = PriorityQueue()
time_dict = {}

image_mutex = threading.Lock()
result_mutex = threading.Lock()
rank_mutex = threading.Lock()
time_mutex = threading.Lock()
db_mutex = threading.Lock()


def producer_img():
    while True:
        item = sub.get_message()
        if item and item['type'] == 'message':
            message_data = item['data']
            message_dict = eval(message_data)
            img_name = message_dict['name']
            win_width, win_height = message_dict['win_size'] 
            encoded_img = message_dict['data']
            img_data = base64.b64decode(encoded_img)
            nparr = np.frombuffer(img_data, np.uint8)

            img = np.resize(nparr,(win_height, win_width)) # real send 
            # img = cv2.imdecode(nparr, 0) # simu send

            image_mutex.acquire()
            image_dict[img_name] = img
            image_mutex.release()

        time.sleep(0.1)


def producer_result():
    while True:
        res_json = conn.get('sat_bbox_angle_det')
        if res_json is not None:
            # conn.delete('sat_bbox_angle_det')
            res = json.loads(res_json)
            bbox1, bbox2, bbox3 = res['bbox1'], res['bbox2'], res['bbox3']
            angle1, angle2, angle3 = res['angle1'], res['angle2'], res['angle3']
            img_name = res['name']

            result_mutex.acquire()
            result_queue.put((img_name, bbox1, bbox2, bbox3, angle1, angle2, angle3))
            result_mutex.release()

        time.sleep(0.1)


def consumer_match():
    while True:
        if not result_queue.empty():

            result_mutex.acquire()
            (name, bbox1, bbox2, bbox3, angle1, angle2, angle3) = result_queue.get()
            result_mutex.release()

            image_mutex.acquire()

            try:
                img = image_dict[name]
                image_dict.pop(name)
            except KeyError:
                # logger.info(f"{name} not found")
                image_mutex.release()
                continue

            image_mutex.release()

            # logger.info(name)
            # logger.info(bbox1)
            # logger.info(bbox2)
            # logger.info(bbox3)
            # logger.info(angle1)
            # logger.info(angle2)
            # logger.info(angle3)

            time_s = name.split('_')[1]
            time_ms = name.split('_')[2]
            exposure = name.split('_')[3]
            score = eval_result(bbox1, bbox2, bbox3, angle1, angle2, angle3)
            
            if score > 1000:
                class_type = 0                  #识别结果无效
            else:
                class_type = 1                  #识别结果有效
            db_mutex.acquire()
            db.insert(time_s, time_ms, img.shape[0], img.shape[1], exposure, class_type, score, img)
            db_mutex.release()
            # logger.info(f"score: {score}")
            logger.info(f"insert {name} into database")

        time.sleep(0.1)



def get_res_by_score(count):
    #选用有检测结果的图片
    db_mutex.acquire()
    files = db.queryIDThumbnailByClass(class_type=1)
    db_mutex.release()
    thumbnails = []
    ids = np.array([])
    if(len(files) == 0):
        db_mutex.acquire()
        files = db.queryIDThumbnailByClass(class_type=0)
        db_mutex.release()
    
    for(file) in files:
        thumbnail = cv2.imdecode(np.frombuffer(file[1], np.uint8), cv2.IMREAD_COLOR)
        thumbnail = cv2.resize(thumbnail, (128, 128)).reshape(-1)
        thumbnails.append(thumbnail)
        ids = np.append(ids, file[0])

    thumbnails = np.array(thumbnails)
    try:
        points = tsne_transform(thumbnails)
        kmeans = KMeans(n_clusters=count, random_state=0, n_init='auto').fit(points)
        labels = kmeans.labels_
        res = []
        for i in range(count):
            query_ids = ids[labels == i]
            db_mutex.acquire()
            info, data = db.queryByIDSortByScoreLimitByCount(query_ids.tolist(), count=1)
            db_mutex.release()
            # res.append(info)
            data = cv2.cvtColor(data, cv2.COLOR_BGR2GRAY)
            data = cv2.resize(data, (1024, 1024))
            compress_param = [cv2.IMWRITE_JPEG_QUALITY, 50]
            cv2.imwrite(f'/usr/src/data/tmp/{i}.jpg', data, compress_param)
            res.append(f'{i}.jpg')
    except:
        pass

    return res


def get_res_by_timestamp(time_stamp_list):
    db_mutex.acquire()
    info, data = db.queryByTimeStamp(time_stamp_list)
    db_mutex.release()

    try:
        res = []
        for i in range(len(info)):
            cv2.imwrite(f'/usr/src/data/tmp/{i}.jpg', data[i])
            res.append(f'{i}.jpg')
    except:
        pass
    
    return res



# define enum of status
class Status:
    NORMAL = 0x00
    COUNT_INVALID = 0x01
    SORT_INVALID = 0x02
    TIMESTAMP_DUPLICATE = 0x03
    TIMESTAMP_COUNT_NOT_MATCH = 0x04
    COUNT_NONEXIST = 0x05
    SORT_NONEXIST = 0x06
    TIMESTAMP_NONEXIST = 0x07
    COUNT_EXCEED = 0x08
    JSON_DECODE_ERROR = 0x09






def get_res_by_timestamp(time_stamp_list):
    db_mutex.acquire()
    info, data = db.queryByTimeStamp(time_stamp_list)
    db_mutex.release()

    try:
        res = []
        for i in range(len(info)):
            cv2.imwrite(f'/usr/src/data/tmp/{i}.jpg', data[i])
            res.append(f'{i}.jpg')
    except:
        pass
    
    return res



# define enum of status
class Status:
    NORMAL = 0x00
    COUNT_INVALID = 0x01
    SORT_INVALID = 0x02
    TIMESTAMP_DUPLICATE = 0x03
    TIMESTAMP_COUNT_NOT_MATCH = 0x04
    COUNT_NONEXIST = 0x05
    SORT_NONEXIST = 0x06
    TIMESTAMP_NONEXIST = 0x07
    COUNT_EXCEED = 0x08
    JSON_DECODE_ERROR = 0x09





def process_message(message):
    # message format
    #     message = {
    #     'count': 3,         # 返回指定数量的图片文件列表
    #     'time_start': 0,    # 图片时间戳区间，预留支持查找某段时间内的最好图片的接口
    #     'time_end': 0,   
    #     'sort': 0,          # 排序规则：默认按置信度排序，保留扩展排序规则的接口
    #     'source': 0,        # 载荷编号：保留扩展到多个载荷的接口 
    # }

    files = None
    # message = eval(message)
    # 反序列化查询消息
    status = Status.NORMAL

    status = Status.NORMAL

    try:
        message = json.loads(message)
    except json.JSONDecodeError as e:
        status = Status.JSON_DECODE_ERROR
        status = Status.JSON_DECODE_ERROR
        print(f"json反序列化失败: {e}")

    if('count' not in message):                                  #缺少count参数
        logger.info("缺少count参数")
        status = Status.COUNT_NONEXIST
    elif('sort' not in message):                                   #缺少sort参数
        logger.info("缺少sort参数")
        status = Status.SORT_NONEXIST
    elif('timestamps' not in message):                             #缺少timestamps参数
        logger.info("缺少timestamps参数")
        status = Status.TIMESTAMP_NONEXIST
    elif('count' in message and message['count'] > 10):                                   #count参数不合法
        count = message['count']
        logger.info(f'count参数不合法: count={count}')
        status = Status.COUNT_INVALID

    files = None
    if(status == Status.NORMAL):
        if int(message['sort']) == 0:                                #sort = 0 置信度排序
            files = get_res_by_score(message['count'])          
        elif int(message['sort']) == 2:                              #sort = 2 时间戳排序
            if(len(message['timestamps']) != message['count']):       #时间戳个数和count不一致
                logger.info(f'时间戳个数和count不一致: count={message["count"]}, timestamps={message["timestamps"]}')
                status = Status.TIMESTAMP_COUNT_NOT_MATCH
            elif(len(message['timestamps']) != len(set(message['timestamps']))):  #重复的时间戳
                logger.info(f"重复的时间戳: timestamps={message['timestamps']}")
                status = Status.TIMESTAMP_DUPLICATE
            if(status == Status.NORMAL):
                files = get_res_by_timestamp(message['timestamps'])
        else:                                                        #sort参数不合法
            logger.info(f"sort参数不合法: sort={message['sort']}")
            status = Status.SORT_INVALID

    response = {
        'status': status,
        'status': status,
        'file_path': '/usr/src/data/tmp/',
        'file_list': files
    } 
    logger.info(f"发送查询结果: {response}")
    # 序列化查询结果
    try:
        json_string = json.dumps(response)
        return json_string
    except TypeError as e:
        print(f"json序列化失败: {e}")

        print(f"json序列化失败: {e}")

    return None


def handle_message(channel, message):
    response_channel = f"{channel}:response"  # 创建用于发送响应的队列
    response = process_message(message)  # 处理接收到的消息
    query.rpush(response_channel, response)  # 将响应推送到响应队列

def query_listening(channel = 'channel.query'):
    while True:
        message = query.blpop(channel)[1]  # 阻塞等待接收消息
        logger.info(f"收到查询请求: {message}")
        handle_message(channel, message)

def main():
    producer_img_thread = threading.Thread(target=producer_img)
    producer_result_thread = threading.Thread(target=producer_result)
    consumer_match_thread = threading.Thread(target=consumer_match)
    query_listening_thread = threading.Thread(target=query_listening)

    producer_img_thread.start()
    producer_result_thread.start()
    consumer_match_thread.start()
    query_listening_thread.start()

    producer_img_thread.join()
    producer_result_thread.join()
    consumer_match_thread.join()
    query_listening_thread.join()

main()
