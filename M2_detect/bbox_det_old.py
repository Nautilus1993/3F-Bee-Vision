import time
import cv2
import numpy as np
import torch
import os
from models.experimental import attempt_load
from utils.torch_utils import select_device
from utils.augmentations import letterbox
from utils.general import non_max_suppression
import redis
import logging
from logging import handlers
import base64

# (TODO:wangyuhang)仅用作和软件所调试数据接口使用，后期需要删除该文件 


def inference(img_grey):
    """输入灰度图，输出检测结果
    Args:
        img_grey:灰度图矩阵
    Returns:
        sat_bbox:[left， top， weight, height, probability, class]
    """
    img_h = img_grey.shape[0]
    img_w = img_grey.shape[1]
    img0 = cv2.cvtColor(img_grey, cv2.COLOR_GRAY2BGR)

    # Padded resize
    img = letterbox(img0, 640, stride=32, auto=True)[0]
    # Convert
    img = img.transpose((2, 0, 1))[::-1]  # HWC to CHW, BGR to RGB
    img = np.ascontiguousarray(img)
    img = torch.from_numpy(img).to(device)
    img = img / 255.0  # 0 - 255 to 0.0 - 1.0
    img = img[None]  # expand for batch dim

    # inference
    pred = model(img, augment=False, visualize=False)[0]
    pred = non_max_suppression(pred, conf_thres=0.25)
    pred = pred[0].cpu().numpy().tolist()
    max_probability = 0.0

    # 取置信度最高的一个检测框
    for i, p in enumerate(pred):
        if p[4] > max_probability:
            max_probability = p[4]
            best_bbox = pred[i]
    sat_bbox = []
    if len(pred) > 0:
        if img_w >= img_h:
            rate_hw = float(img_w) / img_h
            result_w = 640
            result_h = result_w / rate_hw
        else:
            rate_hw = float(img_h) / img_w
            result_h = 640
            result_w = result_h / rate_hw

        sat_bbox.append(best_bbox[0] / result_w * img_w)    # left
        sat_bbox.append(best_bbox[1] / result_h * img_h)    # top
        sat_bbox.append(best_bbox[2] / result_w * img_w)    # right
        sat_bbox.append(best_bbox[3] / result_h * img_h)    # down
        sat_bbox.append(best_bbox[4])    # p
        sat_bbox.append(best_bbox[5])    # category

        # 边界保护
        if sat_bbox[0] < 0:
            sat_bbox[0] = 0
        if sat_bbox[1] < 0:
            sat_bbox[1] = 0
        if sat_bbox[2] > img_w:
            sat_bbox[2] = img_w
        if sat_bbox[3] > img_h:
            sat_bbox[3] = img_h

        # 输出成x,y,w,h,p,c格式
        bbox_w = sat_bbox[2] - sat_bbox[0]
        bbox_h = sat_bbox[3] - sat_bbox[1]
        sat_bbox[2] = bbox_w
        sat_bbox[3] = bbox_h
    else:
        sat_bbox = [0, 0, 0, 0, 0, 0]    # 没有检测结果

    # save result
    img_grey = np.ascontiguousarray(img_grey)
    cv2.rectangle(img_grey, (int(sat_bbox[0]), int(sat_bbox[1])), (int(sat_bbox[0]+sat_bbox[2]), int(sat_bbox[1]+sat_bbox[3])),
                    color=(255, 255, 200), thickness=6)
    cv2.imwrite(output_dir+img_name, img_grey)
    if visualization:
        cv2.imshow('img', img_grey)
        cv2.waitKey(1)
    return sat_bbox

def pub_result(sat_bbox,img_name):
    # Define the key and list of values
    key = 'sat_bbox_det'
    sat_bbox.append(img_name)    # x,y,w,h,p,c,name
    values = sat_bbox
    # print(values)
    # Set the key with the list value
    conn.delete(key)  # Optional: Delete the key if it already exists
    conn.rpush(key, *values)

# config
weights = os.path.dirname(os.path.realpath(__file__)) + "/pt/02bv5.pt"
visualization = 0    # 0不可视化，1可视化
device = select_device('')
model = attempt_load(weights, device=device)
output_dir = 'output/'

# 初始化log
logger = logging.getLogger("det-log")
logger.setLevel(logging.DEBUG)
log_file = "det.log"
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

# 初始化网络
model(torch.zeros(1, 3, 640, 640).to(device).type_as(next(model.parameters())))
logger.info("yolo init success!")

# 初始化redis
conn = redis.Redis(host='127.0.0.1', port=6379)
sub = conn.pubsub()
sub.subscribe("topic.img")
logger.info("Receiving...")

# 通过redis收图做预测
for item in sub.listen():
    if item['type'] == 'message':
        logger.info(".-- .- -.. .-.. --- ...- . .-- ..-. -.--")
        start_time = time.time()
        # 收到图像数据解析
        message_data = item['data']
        message_dict = eval(message_data)  # Convert the string message back to a dictionary
        img_name = message_dict['name']
        encoded_img = message_dict['data']
        img_data = base64.b64decode(encoded_img)
        nparr = np.frombuffer(img_data, np.uint8)
        img = np.resize(nparr,(2048, 2048))
        # img = cv2.imdecode(nparr, 0)  # 0 represents grayscale      
        # 得到检测边界框
        sat_bbox = inference(img)    # x,y,w,h,p,c
        # 输出结果发送
        print(img_name)
        pub_result(sat_bbox,img_name)    # pub by redis key sat_bbox_det, x,y,w,h,p,c,name
        # 日志记录检测框和耗时
        logger.info("sat_bbox: {}".format(sat_bbox))
        logger.info("time_consuming: {:.4f} s".format(time.time()-start_time))
