import struct
import os
import time
import socket

# TODO:本机IP，需要按实际情况修改
IP_ADDRESS = '127.0.0.1'
PORT = 8089

"""
    UDP 组包 
"""
def pack_udp_packet(length, bytes):
    if length != len(bytes):
        print("长度值和字符串不匹配")
        return None
    format = "!H" + str(length) + "s"
    udp_packet = struct.pack(format, 
        length,             # 1. 有效数据长度
        bytes,               # 2. 有效数据部分
    )
    return udp_packet

"""
    生成给定长度的随机bytes
"""
def generate_random_bytes(length):
    return os.urandom(length)


"""
    format打印的Bytes格式，用于对照每个字节和接收方是否一致
"""
def format_bytes_stream(byte_stream):
    formatted_stream = ""
    for i, byte in enumerate(byte_stream):
        formatted_stream += f"{byte:02X}"
        if (i + 1) % 2 == 0:
            formatted_stream += " "
        if (i + 1) % 16 == 0:
            formatted_stream += "\n"
    return formatted_stream

# 发UDP包
def send_some_shit(length):
    print(f"发送长度为{length}的有效数据")
    bytes = generate_random_bytes(length)
    udp_packet = pack_udp_packet(length, bytes)
    print(format_bytes_stream(udp_packet))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(udp_packet, (IP_ADDRESS, PORT))
    # 关闭套接字
    sock.close()

def main():
    while True:
        send_some_shit(29)
        time.sleep(1)

if __name__=="__main__":
    main()