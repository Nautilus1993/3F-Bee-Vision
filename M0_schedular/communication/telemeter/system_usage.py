import psutil
import shutil
import time

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
    """获取实时功率
    注意:这需要额外的硬件支持,如果没有相关硬件,则无法获取此数据
    """
    # 使用第三方库获取实时功率数据
    try:
        from jtop import jtop
        with jtop() as jetson:
            return jetson.stats.power  # 返回功率信息
    except ImportError:
        print("请先安装 jtop 库: pip install jtop")
        return 0

def get_system_status():
    # start_time = time.time()
    # cpu_usage = int(get_cpu_usage())
    # elapsed_time = time.time() - start_time
    # print(elapsed_time)
    disk_usage = int(get_disk_usage())
    # disk_usage = 0
    cpu_usage = 0
    memory_usage = int(get_memory_usage())
    sys_status = [cpu_usage, disk_usage, memory_usage]
    if len(sys_status) != 3:
        print("系统状态返回值长度异常")
        sys_status = [0, 0, 0]
    return sys_status

def main():
    # 使用示例
    print("CPU 占用率: {:.2f}%".format(get_cpu_usage()))
    print("磁盘占用率: {:.2f}%".format(get_disk_usage()))
    print("内存占用率: {:.2f}%".format(get_memory_usage()))
    print("实时功率: {:.2f}W".format(get_power_usage()))

if __name__=="__main__":
    main()