import socket
import serial
import os
import json
import sys
import time

# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)

from utils.share import LOGGER, IP_ADDRESS, get_timestamps
from remote_control.remote_control_utils import read_instruction_from_redis
from telemeter_utils import SERVER_PORT, SEND_IP
from telemeter_utils import get_result_from_redis, get_device_status, \
    get_image_status, \
    pack_telemeter_packet, format_telemeter, pack_udp_packet, sync_time

# TODO(wangyuhang):后面把串口的逻辑拆出这个模块
SERIAL_PORT = '/dev/ttyXRUSB1'
BRATE = 115200    

def packup_telemetering_data(counter):
    
    # 1. 组包时间
    time_s, time_ms = get_timestamps()

    # 2. 指令状态
    json_string = read_instruction_from_redis()
    try:
        last_instruction = json.loads(json_string)
        ins_counter = last_instruction['counter']
        # 指令转为16进制数
        ins_code = int(last_instruction['instruction_code'], 16)
    except TypeError:
        ins_counter = 0
        ins_code = 0x00
    
    # 3. 获取设备状态[cpu, disk, memory]
    sys_status = get_device_status() 
    
    
    # 4. yolo识别结果与时间戳
    target, cabin, panel_1, panel_2, image_time_s, image_time_ms, \
    exposure, win_w, win_h, win_x, win_y \
        = get_result_from_redis()
    
    # 5. 图片接收状态
    image_status, image_sum, image_delays, image_score \
        = get_image_status()
    
    # 组装遥测帧
    telemeter_data = pack_telemeter_packet(
        counter,
        ins_counter,
        ins_code,
        time_s,             
        time_ms, 
        target,         
        cabin, 
        panel_1, 
        panel_2,
        sys_status,
        image_status, 
        image_sum, 
        image_delays, 
        image_score,
        image_time_s,
        image_time_ms,
        exposure, 
        win_w, 
        win_h, 
        win_x, 
        win_y  
    )
    # 打印遥测帧
    format_telemeter(telemeter_data)
    udp_packet = pack_udp_packet(telemeter_data)    
    return udp_packet


def send_udp(counter, interval):
    data = packup_telemetering_data(counter)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    LOGGER.info(f"向IP {SEND_IP} Port {SERVER_PORT} 发送数据")
    sock.sendto(data, (SEND_IP, SERVER_PORT))
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
        send_udp(counter, 1)
        counter += 1
        sync_time()

if __name__=="__main__":
    main()