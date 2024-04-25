import socket
import struct
import json
import redis
import time
import os
import sys

# Add the parent directory to the sys.path list
from M0_schedular.simu_send.utils.image_utils import LOGGER, IP_ADDRESS

# 发送端的IP地址和端口号
SERVER_PORT = 8090

# 加载遥测数据格式配置文件
config_file = os.path.dirname(os.path.realpath(__file__)) + "/telemeter_data_config.json"

# Generate format string based on the configuration
def generate_udp_format(config_file):
    with open(config_file, "r") as config_file:
        config = json.load(config_file)
    format_string = '!'  
    for field in config['fields']:
        field_type = field['type']
        if field_type == 'uint8':
            format_string += 'B'
        elif field_type == 'uint16':
            format_string += 'H'
        elif field_type == 'uint32':
            format_string += 'I'
        elif field_type == 'float':
            format_string += 'f'
        elif field_type == 'string':
            length = field['length']
            format_string += str(length) + 's'
    return format_string
UDP_FORMAT = generate_udp_format(config_file)

# 收集redis中的yolo识别结果并返回
def get_result_from_redis():
    # Read the value of the key
    key = 'sat_bbox_det'
    if data := conn.lrange(key, 0, -1):
        bbox = [float(value.decode()) for value in data[0:-1]]
        image_name = data[-1].decode()
        return image_name, bbox
    return "No Image Received", [0, 0, 0, 0, 0, 0]

def pack_udp_packet(time_s, time_ms, target_class, x, y):
    udp_packet = struct.pack(UDP_FORMAT, time_s, time_ms, target_class, x, y)
    return udp_packet

def send_telemetering_data(server_ip, server_port):
    # 1. 组包时间
    current_time = time.time()
    time_s = int(current_time)
    time_ms = int((current_time - time_s) * 1000)
    
    # 2. yolo识别结果
    image_name, bbox = get_result_from_redis()
    bbox_x = round(bbox[0])
    bbox_y = round(bbox[1])
    bbox_w = round(bbox[2])
    bbox_h = round(bbox[3])
    bbox_conf = round(bbox[4])
    bbox_class = round(bbox[5])
    LOGGER.info("From redis get result of image: " + image_name)

    # 发送UDP包
    udp_packet = pack_udp_packet(time_s, time_ms, bbox_class, bbox_x, bbox_y)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(udp_packet, (server_ip, server_port))
    # 关闭套接字
    sock.close()

# 模拟1s发一个遥测包
conn = redis.Redis(host='127.0.0.1', port=6379)
def main():
    while True:
        send_telemetering_data(IP_ADDRESS, SERVER_PORT)
        time.sleep(1)

if __name__=="__main__":
    main()