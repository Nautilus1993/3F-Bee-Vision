import logging
import json

# 日志输出到控制台
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)

# TODO:本机IP，需要按实际情况修改
IP_ADDRESS = '192.168.29.201'

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