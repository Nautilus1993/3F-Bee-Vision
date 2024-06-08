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
from remote_control_utils import pack_udp_packet
    

def send_remote_control_data(instruction):
    # 发送UDP包
    udp_packet = pack_udp_packet(instruction)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(udp_packet, (IP_ADDRESS, SERVER_PORT))
    # 关闭套接字
    sock.close()

def main():
    instruction = Instruction.APP_STOP.value
    send_remote_control_data(instruction)

if __name__=="__main__":
    main()