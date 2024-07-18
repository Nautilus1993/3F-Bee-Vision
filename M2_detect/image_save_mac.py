import time
import cv2
import numpy as np
import os
import redis
import base64
import json
import os

output_dir = 'output/'

# 初始化redis
conn = redis.Redis(host='192.168.8.20', port=6379)  # orin_nano wifi ip
sub = conn.pubsub()
sub.subscribe("topic.img_save")

def main():
    while True:
        try:
            # 通过redis收图做预测
            print('waiting for image...')
            for item in sub.listen():
                if item['type'] == 'message':
                    # 收到图像数据解析
                    message_data = item['data']
                    message_dict = eval(message_data)  # Convert the string message back to a dictionary
                    img_name = message_dict['name']
                    win_width, win_height = message_dict['win_size']
                    [win_x, win_y] = message_dict['window']   # 开窗坐标系以左上角为原点，往右为X，往下为Y
                    encoded_img = message_dict['data']
                    img_data = base64.b64decode(encoded_img)
                    nparr = np.frombuffer(img_data, np.uint8)
                    print('img_name:',img_name.split('.')[0]+'.jpg')
                    img = np.resize(nparr,(win_height, win_width))  # received is small img
                    # systime 年月日时分秒毫秒字符串，用一个变量来表示
                    SYS_TIME = time.strftime("%Y%m%d%H%M%S", time.localtime())
                    # Check if the output directory exists, if not, create it
                    if not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    cv2.imwrite(output_dir+SYS_TIME+'_'+img_name.split('.')[0]+'.jpg', img)

        except Exception as e:
            print(e)   
              
if __name__=="__main__":
    main()
