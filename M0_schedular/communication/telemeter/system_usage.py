import psutil
import shutil
import time
import threading
import redis
import json
import os

import sys
# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)
from utils.constants import KEY_DEVICE_STATUS
from utils.share import serialize_msg, deserialize_msg

# REDIS
REDIS = redis.Redis(host='127.0.0.1', port=6379)
DEFAULT_DEVICE_STATUS = [0, 0, 0, 0, 0]

def get_cpu_usage():
    """获取 CPU 占用率"""
    return psutil.cpu_percent(interval=1)

def get_disk_usage():
    """获取磁盘占用率"""
    statvfs = os.statvfs('/')
    # 总容量（字节） 
    total = statvfs.f_blocks * statvfs.f_frsize
    # 已用容量（字节）
    used = (statvfs.f_blocks - statvfs.f_bfree) * statvfs.f_frsize
    usage = (used / total) * 100
    return usage


def get_memory_usage():
    """获取内存占用率"""
    memory = psutil.virtual_memory()
    used = memory.used
    total = memory.total
    return (used / total) * 100

def get_cpu_temp_from_sysfs():
    temp_file = "/sys/class/thermal/thermal_zone0/temp"
    if os.path.isfile(temp_file):
        with open(temp_file, 'r') as f:
            temp = int(f.read()) / 1000
            return temp
    else:
        return None

def collect_system_status():
    disk_usage = int(get_disk_usage())
    cpu_usage = int(get_cpu_usage())
    memory_usage = int(get_memory_usage())
    power_usage = 0                             # TODO：保留数据占位
    cpu_temp = get_cpu_temp_from_sysfs()
    sys_status = [cpu_temp, cpu_usage, memory_usage, disk_usage, power_usage]
    return sys_status

# 获取系统状态并发送给redis
def send_device_status_to_redis():
    """ 
        每3秒计算一次系统状态并写入redis
    """
    device_status = collect_system_status()
    for statu in device_status:
        if statu < 0 or statu > 255:
            print("系统状态值错误: %s", device_status)
            device_status = DEFAULT_DEVICE_STATUS
    # 写入 Redis
    stats_json = serialize_msg(device_status)
    try: 
        REDIS.set(KEY_DEVICE_STATUS, stats_json)
    except redis.ConnectionError:
        print("Failed to connect to Redis")

# 从redis中获取系统状态
def get_device_status_from_redis():
    device_status = REDIS.get(KEY_DEVICE_STATUS)
    if device_status == None:
        return DEFAULT_DEVICE_STATUS
    device_status = deserialize_msg(device_status)
    return device_status

def start_monitor():
    while True:
        # 获取系统状态并发送给redis，用时约2s.
        send_device_status_to_redis()
        time.sleep(3)

device_status_thread = threading.Thread(target=start_monitor)
device_status_thread.daemon = True
device_status_thread.start()

# def main():
#     # 使用示例
#     start_time = time.time()
#     sys_status = collect_system_status()
#     # print("CPU 占用率: {:.2f}%".format(get_cpu_usage()))
#     # print("磁盘占用率: {:.2f}%".format(get_disk_usage()))
#     # print("内存占用率: {:.2f}%".format(get_memory_usage()))
#     # print("实时功率: {:.2f}W".format(get_power_usage() / 1000))
#     elapsed_time = time.time() - start_time
#     print(elapsed_time)
#     print(sys_status)

# if __name__=="__main__":
#     main()
