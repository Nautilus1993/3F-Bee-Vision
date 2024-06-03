import socket
import serial
import struct
import json
import redis
import time
import os
import concurrent.futures

from utils.share import LOGGER, IP_ADDRESS, get_timestamps
from utils.telemeter_utils import SERVER_PORT
from utils.telemeter_utils import \
    fake_result_from_redis, get_result_from_redis, pack_udp_packet, format_telemeter
from utils.remote_control_utils import read_instruction_from_redis
from utils.system_usage import get_system_status


SERIAL_PORT = '/dev/ttyXRUSB1'
BRATE = 115200    

def packup_telemetering_data(counter):
    # 1. 组包时间
    time_s, time_ms = get_timestamps()
    
    # 2. yolo识别结果
    # TODO(wangyuhang):换成redis中的真实数据
    image_name, t1, t2, t3 = fake_result_from_redis()
    # LOGGER.info("From redis get result of image: " + image_name)

    # 3. 上一条指令
    json_string = read_instruction_from_redis()
    last_instruction = json.loads(json_string)
    ins_counter = last_instruction['counter']
    ins_code = last_instruction['instruction_code']

    # 4. 获取设备状态[cpu, disk, memory]
    sys_status = get_system_status() 
    if len(sys_status) != 3:
        LOGGER.warning("系统状态返回值长度异常")

    # 组装遥测帧
    telemeter_data = pack_udp_packet(
        counter,
        ins_counter,
        time_s,             
        time_ms,            
        t1,
        sys_status          
    )
    format_telemeter(telemeter_data)
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