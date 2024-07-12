import socket
import os
import sys
# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)
from utils.share import LOGGER, IP_ADDRESS
from remote_control_utils import SERVER_PORT, Instruction
from remote_control_utils import pack_indirect_instruction_packet, \
pack_inject_data_image_packet
    

def send_remote_control_data(instruction):
    # 发送UDP包
    udp_packet = pack_indirect_instruction_packet(instruction)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(udp_packet, (IP_ADDRESS, SERVER_PORT))
    # 关闭套接字
    sock.close()

def send_inject_data_image(download_num):
    udp_packet = pack_inject_data_image_packet(3)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(udp_packet, (IP_ADDRESS, SERVER_PORT))
    # 关闭套接字
    sock.close()

def main():
    # 发送重启或关闭算法模块的指令
    # instruction = Instruction.APP_START.value
    # send_remote_control_data(instruction)

    # 发送下传三张最好图片的指令
    send_inject_data_image(3)


if __name__=="__main__":
    main()