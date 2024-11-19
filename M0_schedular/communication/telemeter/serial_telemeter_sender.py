import socket
import serial
import struct
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

from utils.share import LOGGER, get_timestamps, generate_udp_format, \
    format_udp_packet

# 根据实际情况调整
CONFIG_FILE = "/home/ywang/Documents/3F-Bee-Vision/M0_schedular/communication/message_config/xmf_config.json"
TELEMETER_SERIAL_FORMAT = generate_udp_format(CONFIG_FILE)
SERIAL_PORT = '/dev/ttyXRUSB1'
BRATE = 115200   
FAKE_RESULT = bytes([i % 256 for i in range(31)])

print(TELEMETER_SERIAL_FORMAT)
def pack_telemeter(counter, sys_time_s, sys_time_ms):
    telemeter_data = struct.pack(TELEMETER_SERIAL_FORMAT, 
        0xA57E,             # 1. 帧头
        39,                 # 2. 数据长度
        0x21,               # 3. 数据类型
        sys_time_s,         # 4. 组包时间戳秒
        sys_time_ms,        # 5. 组包时间戳毫秒
        counter,            # 6. 输出计数器
        FAKE_RESULT,        # 7. (TODO)预留字段填充字符共31bytes
        0,                  # 23. 校验和(后续填充)
        0x09D7,             # 24. 帧尾
    )
    # 数据域单字节累加和
    checksum = sum(telemeter_data[4:-4]) % 65536
    checked_telemeter_data = telemeter_data[:-4] + \
                             checksum.to_bytes(2, "little") +\
                             telemeter_data[-2:]
    return checked_telemeter_data

def format_telemeter(packet):
    config_file = 'telemeter_config.json'
    format_udp_packet(packet, CONFIG_FILE)

def packup_telemetering_data(counter):
    # 1. 组包时间
    sys_time_s, sys_time_ms = get_timestamps()

    # 组装遥测帧
    telemeter_data = pack_telemeter(
        counter,
        sys_time_s,             
        sys_time_ms,
    )
    return telemeter_data

def send_serial(counter):
    data = packup_telemetering_data(counter)
    # format_telemeter(data)
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
        send_serial(counter)
        counter += 1
        time.sleep(0.5)

if __name__=="__main__":
    main()