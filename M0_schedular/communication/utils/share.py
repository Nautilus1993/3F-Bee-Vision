import logging
import json
import time
import struct

# 日志输出到控制台
logging.basicConfig(filename="M0-log.txt", filemode='a')
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)

# TODO:本机IP，需要按实际情况修改
IP_ADDRESS = '127.0.0.1'
# IP_ADDRESS = '192.168.0.101'

# 根据配置文件生成UDP打包格式
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

# 生成星上时格式的时间戳
def get_timestamps():
    current_time = time.time()
    time_s = int(current_time)
    time_ms = int((current_time - time_s) * 1000)
    return time_s, time_ms

# 根据json配置文件，显示udp包里面每个字段的内容
def format_udp_packet(packet, config_file):
    format_string = generate_udp_format(config_file)
    try:
        # 使用 struct.unpack() 函数解包数据
        field_values = struct.unpack(format_string, packet)
    except struct.error as e:
        LOGGER.error(f"UDP包解析错误，包内容与格式不符：{ format_string }")
        return
    # 加载config文件
    with open(config_file, "r") as config_file:
        config = json.load(config_file)
    field_configs = config['fields'] # 返回一个list
    # 判断字段个数和config文件一致
    if len(field_values) != len(field_configs):
        LOGGER.error("UDP包字段个数与config文件不符")
        return
    
    format_string = ""
    for i in range(len(field_configs)):
        value = field_values[i]
        field = field_configs[i]
        field_type = field['type']
        field_info = field['description']
        if field_type == 'uint8':
            format_string += f"{field_info}:\t{value:d}\n"
        elif field_type == 'uint16':
            format_string += f"{field_info}:\t{value:d}\n"
        elif field_type == 'uint32':
            format_string += f"{field_info}:\t{value:d}\n"
        elif field_type == 'float':
            format_string += f"{field_info}:\t{value:.2f}\n"
        elif field_type == 'string':
            length = field['length']
            if length <= 20:
                format_string += f"{field_info}:\t{value}\n"
            else:
                format_string += f"{field_info}:\t{value[:20]} ...总长度 {len(value)}\n"
    print(format_string)