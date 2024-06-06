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
import json


def trans_bbox_format(single_bbox, result_w, result_h, img_w, img_h):
    """input single predict bbox list, output single bbox list by x,y,w,h,p,c
    """
    sat_bbox = []
    sat_bbox.append(single_bbox[0] / result_w * img_w)    # left
    sat_bbox.append(single_bbox[1] / result_h * img_h)    # top
    sat_bbox.append(single_bbox[2] / result_w * img_w)    # right
    sat_bbox.append(single_bbox[3] / result_h * img_h)    # down
    sat_bbox.append(single_bbox[4])    # p
    sat_bbox.append(single_bbox[5])    # category

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
    return sat_bbox

def inference(img_grey):
    """输入灰度图，输出检测结果
    Args:
        img_grey:灰度图矩阵
    Returns:
        result_bbox = [[],[],[]]
    """
    img_h = img_grey.shape[0]
    img_w = img_grey.shape[1]
    img0 = cv2.cvtColor(img_grey, cv2.COLOR_GRAY2BGR)

    # Padded resize
    img = letterbox(img0, 640, stride=32, auto=True)[0]
    if img_w >= img_h:
        rate_hw = float(img_w) / img_h
        result_w = 640
        result_h = result_w / rate_hw
    else:
        rate_hw = float(img_h) / img_w
        result_h = 640
        result_w = result_h / rate_hw
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

    # 取 3 bboxs
    # classes = ['L', 'Ball', 'D_cabin', 'D_panel']
    # 0:L
    # 1:Ball
    # 2:D_cabin
    # 3:D_panel
    result_bbox = [[],[],[]]

    if len(pred) > 0:
        all_bbox = []
        D_cabin_L_Ball = []
        D_panel = []
        for i in pred:
            single_bbox = trans_bbox_format(i, result_w, result_h, img_w, img_h)
            all_bbox.append(single_bbox)
            if single_bbox[-1] in [0, 1, 2]:
                D_cabin_L_Ball.append(single_bbox)
            else:
                D_panel.append(single_bbox)
        # Sort the list based on the last element of each sublist
        sorted_D_cabin_L_Ball = sorted(D_cabin_L_Ball, key=lambda x: x[-2])[::-1]
        sorted_D_panel = sorted(D_panel, key=lambda x: x[-2])[::-1]

        if len(sorted_D_cabin_L_Ball) > 0:
            result_bbox[0] = sorted_D_cabin_L_Ball[0]
            if result_bbox[0][-1] in [0,1]:
                result_bbox[1] = [0, 0, 0, 0, 0, 0]
                result_bbox[2] = [0, 0, 0, 0, 0, 0]
            elif result_bbox[0][-1] == 2:
                if len(sorted_D_panel) >= 2:
                    result_bbox[1] = sorted_D_panel[0]
                    result_bbox[2] = sorted_D_panel[1]
                elif len(sorted_D_panel) == 1:
                    result_bbox[1] = sorted_D_panel[0]
                    result_bbox[2] = [0, 0, 0, 0, 0, 0]
                elif len(sorted_D_panel) == 0:
                    result_bbox[1] = [0, 0, 0, 0, 0, 0]
                    result_bbox[2] = [0, 0, 0, 0, 0, 0]
        else:
            result_bbox[0] = [0, 0, 0, 0, 0, 0]
            if len(sorted_D_panel) >= 2:
                result_bbox[1] = sorted_D_panel[0]
                result_bbox[2] = sorted_D_panel[1]
            elif len(sorted_D_panel) == 1:
                result_bbox[1] = sorted_D_panel[0]
                result_bbox[2] = [0, 0, 0, 0, 0, 0]
            elif len(sorted_D_panel) == 0:
                result_bbox[1] = [0, 0, 0, 0, 0, 0]
                result_bbox[2] = [0, 0, 0, 0, 0, 0]
    else:
        result_bbox[0] = [0, 0, 0, 0, 0, 0]    # 没有检测结果
        result_bbox[1] = [0, 0, 0, 0, 0, 0]
        result_bbox[2] = [0, 0, 0, 0, 0, 0]
    return result_bbox

def pos2angle(bbox, left_up_corner, camera_center):
    """
    Args:
        bbox = [[], [], []]
        left_up_corner
        camera_center
    Output: angles = [[pitch, yaw], [], []]
    """
    sat_angle_boxes = []
    for sat_bbox in bbox:
        # 得到检测框中心在窗口中的坐标
        sat_bbox_center = [sat_bbox[1]+sat_bbox[3]/2, sat_bbox[0]+sat_bbox[2]/2] 

        # 计算检测框中心坐标在全图中的坐标
        sat_bbox_center[0] = sat_bbox_center[0] + left_up_corner[0]
        sat_bbox_center[1] = sat_bbox_center[1] + left_up_corner[1]

        # 计算相机中心与检测框中心的偏移角度
        dh = camera_center[0] - sat_bbox_center[0]  # h方向偏移量，大于0仰视
        dw = sat_bbox_center[1] - camera_center[1]  # w方向偏移量，大于0右侧

        angle_pitch = np.arctan(dh/fl) * 180 / np.pi    # 俯仰角，俯视为负， -90~90
        angle_yaw = np.arctan(dw/fl) * 180 / np.pi  # 方位角，左侧为负， -180~180

        prob = sat_bbox[4]
        category = sat_bbox[5]

        sat_angle_boxes.append([category, angle_pitch, angle_yaw, prob])
    return sat_angle_boxes

def draw_boxes(image, boxes, output_size=None):
    # 定义类别，用于显示
    classes = ['L', 'Ball', 'D_cabin', 'D_panel']
    for bbox in boxes:
        x1,y1,x2,y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]+bbox[0]), int(bbox[3]+bbox[1])

        confidence = bbox[4]
        # label = str(bbox[5])
        label = classes[int(bbox[5])]
        color = (255, 0, 0)  # Red color for box
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        cv2.putText(image, f'{label} {confidence:.2f}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        if output_size is not None:
            image = cv2.resize(image, output_size, interpolation=cv2.INTER_LINEAR)
    return image

def pub_result(sat_bboxes, sat_angle_boxes, img_name):
    # Define the key and list of values
    """
    sat_bbox = {'bbox1':0,
            'angle1':0,
            'bbox2':0,
            'angle2':0,
            'bbox3':0,
            'angle3':0,
            'name':0}
    """
    key = 'sat_bbox_angle_det'
    result = {'bbox1':sat_bboxes[0],
        'angle1':sat_angle_boxes[0],
        'bbox2':sat_bboxes[1],
        'angle2':sat_angle_boxes[1],
        'bbox3':sat_bboxes[2],
        'angle3':sat_angle_boxes[2],
        'name':img_name}
    serialized_result = json.dumps(result)
    
    # Set the key with the list value
    conn.delete(key)  # Optional: Delete the key if it already exists
    # conn.rpush(key, *values)

    conn.set(key, serialized_result)

# config
weights = os.path.dirname(os.path.realpath(__file__)) + "/pt/best.pt"
fl = 4648.540   # camera focal length
camera_center = [1024, 1024]    # 原图大小：2048*2048
img_size = 2048
visualization = 1    # 0不可视化，1可视化
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
        win_width, win_height = message_dict['win_size']    # message_dict好像没有win_size这个属性，因此下面用了定值
        [win_x, win_y] = message_dict['window']   # 开窗坐标系以左下角为原点
        encoded_img = message_dict['data']
        img_data = base64.b64decode(encoded_img)
        nparr = np.frombuffer(img_data, np.uint8)
        # img = np.resize(nparr,(img_size, img_size))
        img = cv2.imdecode(nparr, 0) 

        # 根据窗口大小裁剪图像
        win_img = img[img_size - win_y - win_height: img_size - win_y, win_x: win_x + win_width]
        left_up_corner = [img_size - win_y - win_height, win_x]   # 开窗的左上角在原图中的坐标
          
        # 得到检测边界框数组
        sat_bboxes = inference(win_img)    # [[x,y,w,h,p,c], [x,y,w,h,p,c], [x,y,w,h,p,c]]
        sat_angle_boxes = pos2angle(sat_bboxes, left_up_corner, camera_center)

        # visualization
        if visualization:
            boxed_img = draw_boxes(img, sat_bboxes)
            # cv2.imshow('image with boxes', boxed_img)
            # cv2.waitKey(1)

            cv2.imwrite('output.jpg', boxed_img)
        
        pub_result(sat_bboxes, sat_angle_boxes, img_name)    # pub by redis key sat_angle_det, category, angle_pitch, angle_azimuth, p, name
        
        # 日志记录检测框和耗时
        
        logger.info('angle_bbox: {}'.format(sat_angle_boxes))
        logger.info("sat_bbox: {}".format(sat_bboxes))
        logger.info("time_consuming: {:.4f} s".format(time.time()-start_time))
