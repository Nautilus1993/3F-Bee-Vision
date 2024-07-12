import socket
import sys
import os
# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)
from utils.share import LOGGER, IP_ADDRESS, get_timestamps
from remote_control_utils import SERVER_PORT, Instruction, InstructionType, \
    unpack_udp_packet, write_instruction_to_redis, execute_indirect_ins, \
    unpack_time_ins_packet, write_time_to_redis

def receive_instruction(buffer_size):
    counter = 0
    while True:
        udp_packet, addr = sock.recvfrom(buffer_size)
        # 4类需要处理的指令，数据类型都是Byte5
        if len(udp_packet) >= 5:
            ins_type = udp_packet[4]

        if len(udp_packet) == 7:
            # 遥测指令不作处理
            pass
        elif len(udp_packet) == 6:
            # TODO(wangyuhang):异步包请求
            if ins_type == InstructionType.ASYNC_PKG.value:
                pass
        elif len(udp_packet) == 11:
            # 星上时指令,写redis后续用于时间同步
            if ins_type == InstructionType.TIMER.value:
                ins_type, time_s, time_ms = unpack_time_ins_packet(udp_packet)
                LOGGER.info(f"收到星上时: time_s = {time_s} time_ms = {time_ms}")
                write_time_to_redis(time_s, time_ms)

            # 间接指令
            elif ins_type == InstructionType.INDIRECT_INS.value:
                ins_type, instruction = unpack_udp_packet(udp_packet)
                counter += 1
                LOGGER.info(f"收到遥控指令： 指令码 {instruction} 计数器：{counter}")
                time_s, time_ms = get_timestamps()
                write_instruction_to_redis(instruction, time_s, time_ms, counter)
                if counter >= 255:
                    LOGGER("计数器清零")
                    counter= 0
                execute_indirect_ins(instruction)
        else:
            print("received some other instruction")

# 创建UDP套接字
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    
# 绑定IP地址和端口号
sock.bind((IP_ADDRESS, SERVER_PORT))
LOGGER.info(IP_ADDRESS + " : " + str(SERVER_PORT) + "  开始接收遥控指令...")
try:
    buffer_size = 1024
    receive_instruction(buffer_size)
except socket.error as e:
    # 没有数据可读，错误码为 EWOULDBLOCK 或 EAGAIN
    if e.errno == socket.errno.EWOULDBLOCK or e.errno == socket.errno.EAGAIN:
        LOGGER.exception('socket没有数据')
    else:
        # 其他错误，需要处理
        LOGGER.exception('Error:', e)
except Exception as e:
    LOGGER.exception("其他异常:", str(e))
finally:
    sock.close()