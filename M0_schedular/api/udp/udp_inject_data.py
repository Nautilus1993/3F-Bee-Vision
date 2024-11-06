import sys
import socket
import os
import time

# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取M0模块目录路径
parent_dir = os.path.dirname(os.path.dirname(script_dir))
sys.path.append(parent_dir)

from communication.utils.constants import IP_ADDRESS, PORT_REMOTE_CONTROL
from communication.remote_control.remote_control_utils \
    import Instruction, pack_inject_data_image_packet, \
    pack_indirect_instruction_packet

def send_remote_control_data(instruction):
    # 发送UDP包
    udp_packet = pack_indirect_instruction_packet(instruction)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(udp_packet, (IP_ADDRESS, PORT_REMOTE_CONTROL))
    # 关闭套接字
    sock.close()

def send_inject_data_image(download_num):
    download_image_num = download_num
    download_strategy = 0x55
    timestamps = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # 模拟10个假时间戳
    udp_packet = pack_inject_data_image_packet(
        download_image_num,
        download_strategy,
        timestamps
    )
    print(f"发送图片下传指令到{IP_ADDRESS}:{PORT_REMOTE_CONTROL}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(udp_packet, (IP_ADDRESS, PORT_REMOTE_CONTROL))
    # 关闭套接字
    sock.close()

def main():
    # 发送重启或关闭算法模块的指令Try
    # instruction = Instruction.APP_START.value
    # send_remote_control_data(instruction)

    # 发送下传三张最好图片的指令
    send_inject_data_image(3)


if __name__=="__main__":
    main()