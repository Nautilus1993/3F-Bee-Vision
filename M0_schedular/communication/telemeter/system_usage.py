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
    disk_usage = shutil.disk_usage("/")
    used = disk_usage.used
    total = disk_usage.total
    return (used / total) * 100

def get_memory_usage():
    """获取内存占用率"""
    memory = psutil.virtual_memory()
    used = memory.used
    total = memory.total
    return (used / total) * 100

def get_power_usage():
    """获取实时功率和CPU温度
    注意:这需要额外的硬件支持,如果没有相关硬件,则无法获取此数据
    """
    # 使用第三方库获取实时功率数据
    try:
        from jtop import jtop
        with jtop() as jetson:
            total_power =  int(jetson.stats['Power TOT']) / 100
            temp_cpu = int(jetson.stats['Temp CPU']) % 100
            return int(total_power), int(temp_cpu) 
    except ImportError:
        print("请先安装 jtop 库: pip install jtop")
    except Exception as e:
        print("获取实时功率失败:", e)
    return 0, 0

def collect_system_status():
    disk_usage = int(get_disk_usage())
    cpu_usage = int(get_cpu_usage())
    memory_usage = int(get_memory_usage())
    power_usage, cpu_temp = get_power_usage()
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
