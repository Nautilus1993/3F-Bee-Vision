import socket
import serial
import struct
import json
import redis
import time
import os

from utils.share import LOGGER, IP_ADDRESS, get_timestamps
from utils.telemeter_utils import SERVER_PORT
from utils.telemeter_utils import \
    fake_result_from_redis, pack_udp_packet

SERIAL_PORT = '/dev/ttyXRUSB1'
BRATE = 115200    

def packup_telemetering_data(counter):
    # 1. 组包时间
    time_s, time_ms = get_timestamps()
    
    # 2. yolo识别结果
    # TODO(wangyuhang):换成redis中的真实数据
    image_name, t1, t2, t3 = fake_result_from_redis()
    LOGGER.info("From redis get result of image: " + image_name)

    # 组装遥测帧
    telemeter_data = pack_udp_packet(
        counter,
        0,
        time_s,             
        time_ms,            
        t1,         
        t2,             
        t3              
    )
    return telemeter_data


def send_udp(counter):
    data = packup_telemetering_data(counter)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data, (IP_ADDRESS, SERVER_PORT))
    # 关闭套接字
    sock.close()

def send_serial(counter):
    data = packup_telemetering_data(counter)
    print(data)
    with serial.Serial(SERIAL_PORT, BRATE, timeout=None) as ser:
        if(ser.isOpen()):
            ser.write(data)
            LOGGER.info(f"向串口 {SERIAL_PORT} 发送长度为 {len(data)} 的数据")
            ser.close()

def main():
    counter = 0
    while True:
        if counter > 255:
            counter = 0
        # 串口发送
        # send_serial(counter)
        # UDP发送
        send_udp(counter)
        counter += 1
        time.sleep(1)

if __name__=="__main__":
    main()