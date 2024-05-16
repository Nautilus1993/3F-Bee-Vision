import socket
import struct
import json
import redis
import time
import os

from utils.share import LOGGER, IP_ADDRESS, get_timestamps
from utils.telemeter_utils import SERVER_PORT
from utils.telemeter_utils import \
    fake_result_from_redis, pack_udp_packet
    

def send_telemetering_data(counter, server_ip, server_port):
    # 1. 组包时间
    time_s, time_ms = get_timestamps()
    
    # 2. yolo识别结果
    image_name, t1, t2, t3 = fake_result_from_redis()
    LOGGER.info("From redis get result of image: " + image_name)

    # 发送UDP包
    udp_packet = pack_udp_packet(
        counter,
        0,
        time_s,             
        time_ms,            
        t1,         
        t2,             
        t3              
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(udp_packet, (server_ip, server_port))
    # 关闭套接字
    sock.close()

def main():
    counter = 0
    while True:
        if counter > 255:
            counter = 0
        send_telemetering_data(counter, IP_ADDRESS, SERVER_PORT)
        counter += 1
        time.sleep(1)

if __name__=="__main__":
    main()