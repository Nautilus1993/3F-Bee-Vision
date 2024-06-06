import socket
import struct
import json
import redis
import time
import os

from utils.share import LOGGER, IP_ADDRESS
from utils.remote_control_utils import SERVER_PORT, Instruction
from utils.remote_control_utils import pack_udp_packet
    

def send_remote_control_data(instruction):

    file_info = bytes([1,2,3,4])
    control_info = bytes([1,2,3,4])
    # 发送UDP包
    udp_packet = pack_udp_packet(
        instruction,
        file_info,
        control_info              
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(udp_packet, (IP_ADDRESS, SERVER_PORT))
    # 关闭套接字
    sock.close()

def main():
    instruction = Instruction.APP_STOP.value
    send_remote_control_data(instruction)

if __name__=="__main__":
    main()