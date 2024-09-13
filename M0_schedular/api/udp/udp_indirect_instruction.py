import sys
import socket
import os
import time

# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取M0模块目录路径
parent_dir = os.path.dirname(os.path.dirname(script_dir))
sys.path.append(parent_dir)

from communication.utils.share import IP_ADDRESS
from communication.remote_control.remote_control_utils \
    import SERVER_PORT, Instruction, pack_indirect_instruction_packet

def send_remote_control_data(instruction):
    # 发送UDP包
    udp_packet = pack_indirect_instruction_packet(instruction)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(udp_packet, (IP_ADDRESS, SERVER_PORT))
    # 关闭套接字
    sock.close()

def main():
    # 发送重启\关闭算法模块,停止下载文件的指令
    # instruction = Instruction.APP_START.value
    instruction = Instruction.STOP_DOWNLOAD.value
    send_remote_control_data(instruction)

if __name__=="__main__":
    main()