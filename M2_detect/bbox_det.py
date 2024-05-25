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

# 000

def inference(img_grey):
    """输入灰度图，输出相机的俯仰角和方位角
    Args:
        img_grey:灰度图矩阵
    Returns:
        sat_bbox: [class, angle_pitch, angle_azimuth, probability, name]
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
            best_bbox = pred[i]     # 640*640下的坐标
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

        sat_bbox.append(best_bbox[0] / result_w * img_w)    # left  投影回开窗原尺寸的坐标
        sat_bbox.append(best_bbox[1] / result_h * img_h)    # top
        sat_bbox.append(best_bbox[2] / result_w * img_w)    # right
        sat_bbox.append(best_bbox[3] / result_h * img_h)    # down
        sat_bbox.append(best_bbox[4])    # probability
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

        # 输出成x,y,w,h,p,c格式     问题：这里的x，y是左上角的坐标还是中心坐标？
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
    key = 'sat_angle_det'
    sat_bbox.append(img_name)    # category, angle_pitch, angle_azimuth, p, name
    values = sat_bbox
    print(values)
    print('Successfully published the result to the Redis server')
    # Set the key with the list value
    conn.delete(key)  # Optional: Delete the key if it already exists
    conn.rpush(key, *values)

# config
weights = os.path.dirname(os.path.realpath(__file__)) + "/pt/02bv5.pt"
fl = 4648.540   # camera focal length
camera_center = [1024, 1024]    # 原图大小：2048*2048
img_size = 2048
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

        """message info:
        message = {
            'name': image_name,
            'win_size': (2048, 2048),
            'window': [win_x, win_y],
            'data': encoded_img
        }
        """
        img_name = message_dict['name']
        # win_size = message_dict['win_size'][0]    # message_dict好像没有win_size这个属性，因此下面用了定值
        win_size = 2048
        [win_x, win_y] = message_dict['window']   # 开窗坐标系以左下角为原点
        encoded_img = message_dict['data']
        img_data = base64.b64decode(encoded_img)
        nparr = np.frombuffer(img_data, np.uint8)
        img = np.resize(nparr,(img_size, img_size))

        # 根据窗口大小裁剪图像
        win_img = img[win_x - win_size + 1 : win_x, win_y : win_y + win_size]
        # left_up_corner = [img_size + win_x - win_size, win_y]   # 开窗的左上角在原图中的坐标
        left_up_corner = [img_size + win_y - win_size, win_x]   # 开窗的左上角在原图中的坐标
        win_img = img[left_up_corner[0] : left_up_corner[0] + win_size, left_up_corner[1] : left_up_corner[1] + win_size]

        # img = cv2.imdecode(nparr, 0)  # 0 represents grayscale      
        # 得到检测边界框
        sat_bbox = inference(win_img)    # x,y,w,h,p,c

        # 得到检测框中心在窗口中的坐标
        sat_bbox_center = [sat_bbox[1]+sat_bbox[3]/2, sat_bbox[0]+sat_bbox[2]/2] 

        # 计算检测框中心坐标在全图中的坐标
        sat_bbox_center[0] = sat_bbox_center[0] + left_up_corner[0]
        sat_bbox_center[1] = sat_bbox_center[1] + left_up_corner[1]

        # 计算相机中心与检测框中心的偏移角度
        dh = camera_center[0] - sat_bbox_center[0]  # h方向偏移量，大于0仰视
        dw = sat_bbox_center[1] - camera_center[1]  # w方向偏移量，大于0右侧

        angle_pitch = np.arctan(dh/fl) * 180 / np.pi    # 俯仰角，俯视为负， -90~90
        angle_azimuth = np.arctan(dw/fl) * 180 / np.pi  # 方位角，左侧为负， -180~180


        # 输出结果发送
        print(img_name)

        prob = sat_bbox[4]
        catagory = sat_bbox[5]
        pub_result([catagory, angle_pitch, angle_azimuth, prob], img_name)    # pub by redis key category, angle_pitch, angle_azimuth, p, name
        
        
        # 日志记录检测框和耗时
        logger.info("sat_bbox: {}".format(sat_bbox))
        logger.info("time_consuming: {:.4f} s".format(time.time()-start_time))
