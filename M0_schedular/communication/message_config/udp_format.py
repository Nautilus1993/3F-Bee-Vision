import os
import sys

""" 
    根据输入的config.json文件，生成对应的UDP format string
"""
# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
from utils.share import generate_udp_format

# 加载遥测数据格式配置文件,生成UDP包格式
TELEMETER_UDP_FORMAT = generate_udp_format(script_dir + "/telemeter_config.json")

# 加载图像包格式配置文件,生成UDP包格式
IMAGE_UDP_FORMAT = generate_udp_format(script_dir + "/image_config.json")
# 加载cameralink包头格式配置文件，生成UDP包格式
CAMERALINK_HEADER_FORMAT = generate_udp_format(script_dir + "/cameralink_config.json")

# 加载间接指令配置文件,生成UDP包格式
INDIRECT_INS_UDP_FORMAT = generate_udp_format(script_dir + "/indirect_ins_config.json")

# 加载星上时配置文件,生成UDP包格式
TIME_INS_FORMAT = generate_udp_format(script_dir + "/time_ins_config.json")

# 生成UDP包格式
INJECT_DATA_IMAGE_FORMAT = generate_udp_format(script_dir + "/inject_data_image.json")

# 加载文件低速下行异步包配置文件,生成UDP包格式
file_down_config_file = script_dir + "/file_down_config.json"
FILE_DOWN_FORMAT = generate_udp_format(file_down_config_file)
