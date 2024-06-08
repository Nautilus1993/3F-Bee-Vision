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
telemeter_config_file = script_dir + "/telemeter_config.json"
TELEMETER_UDP_FORMAT = generate_udp_format(telemeter_config_file)

# 加载图像包格式配置文件,生成UDP包格式
image_config_file = script_dir + "/image_config.json"
IMAGE_UDP_FORMAT = generate_udp_format(image_config_file)

# 加载间接指令配置文件,生成UDP包格式
indirect_ins_config_file = script_dir + "/indirect_ins_config.json"
INDIRECT_INS_UDP_FORMAT = generate_udp_format(indirect_ins_config_file)
