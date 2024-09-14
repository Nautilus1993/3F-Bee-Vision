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

from utils.share import LOGGER, get_timestamps
from utils.constants import SEND_IP, PORT_TELEMETER
from telemeter_utils import get_result_from_redis, \
    get_device_status, get_instruction_status, \
    get_image_status, get_docker_status, \
    get_download_status, pack_telemeter_packet, \
    format_telemeter, pack_udp_packet, sync_time

# TODO(wangyuhang):后面把串口的逻辑拆出这个模块
SERIAL_PORT = '/dev/ttyXRUSB1'
BRATE = 115200    

def packup_telemetering_data(counter):
    
    # 1. 组包时间
    sys_time_s, sys_time_ms = get_timestamps()

    # 2. 指令状态
    ins_code, ins_counter = get_instruction_status()
    
    # 3. 获取设备状态[cpu_temp, cpu_usage, disk_usage, memory_usage, power]
    sys_status = get_device_status() 
    
    # 4. yolo识别结果与时间戳
    target, cabin, panel_1, panel_2, image_time_s, image_time_ms, \
    exposure, win_w, win_h, win_x, win_y \
        = get_result_from_redis()
    
    # 5. 图片接收状态
    image_status, image_sum, image_delays, image_score \
        = get_image_status()
    
    # 6. 获取各docker状态
    docker_status = get_docker_status()

    # 7. 获取文件下载状态
    download_state, download_progress = get_download_status()
    
    # 组装遥测帧
    telemeter_data = pack_telemeter_packet(
        counter,
        ins_counter,
        ins_code,
        sys_time_s,             
        sys_time_ms,
        docker_status,
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
        win_y,
        0,
        download_state, 
        download_progress
    )
    # 打印遥测帧
    format_telemeter(telemeter_data)
    udp_packet = pack_udp_packet(telemeter_data)    
    return udp_packet


def send_udp(counter, interval):
    data = packup_telemetering_data(counter)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    LOGGER.info(f"向IP {SEND_IP} Port {PORT_TELEMETER} 发送数据")
    sock.sendto(data, (SEND_IP, PORT_TELEMETER))
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