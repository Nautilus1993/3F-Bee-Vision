import socket
import sys
import os
import threading 

# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)
from utils.share import LOGGER
from utils.constants import IP_ADDRESS, PORT_REMOTE_CONTROL
from remote_control_utils import Instruction, InstructionType, \
    unpack_indirect_instruction_packet, write_instruction_to_redis, execute_indirect_ins, \
    unpack_time_ins_packet, write_time_to_redis, \
    unpack_inject_data_image_packet, execute_inject_data_image_download


def receive_instruction(buffer_size):
    counter = 0
    while True:
        udp_packet, addr = sock.recvfrom(buffer_size)
        # 4类需要处理的指令，数据类型都是Byte5
        if len(udp_packet) >= 5:
            ins_type = udp_packet[4]

        # 1: 遥测请求(不作处理)
        if len(udp_packet) == 7:
            pass

        # 2. TODO(wangyuhang):异步包请求
        elif ins_type == InstructionType.ASYNC_PKG.value and len(udp_packet) == 6:
                pass

        # 3. 星上时指令
        elif ins_type == InstructionType.TIMER.value and len(udp_packet) == 11:
            ins_type, time_s, time_ms = unpack_time_ins_packet(udp_packet)
            LOGGER.info(f"收到星上时: time_s = {time_s} time_ms = {time_ms}")
            write_time_to_redis(time_s, time_ms)

        # 4. 间接指令
        elif ins_type == InstructionType.INDIRECT_INS.value and len(udp_packet) == 11:
            ins_type, instruction_code = unpack_indirect_instruction_packet(udp_packet)
            counter += 1
            LOGGER.info(f"收到间接指令： 指令码 {instruction_code} 计数器：{counter}")
            write_instruction_to_redis(instruction_code, counter)
            execute_indirect_ins(instruction_code)
        
        # 5. 注入数据
        elif ins_type == InstructionType.INJECT_DATA.value:
            # 注入数据的指令码是Byte10
            inject_data_code = udp_packet[9]
            # 将收到的注入数据写入redis
            counter += 1
            LOGGER.info(f"收到注入数据指令： 指令码 {inject_data_code} 计数器：{counter}")
            write_instruction_to_redis(inject_data_code, counter)
            # 下载图片文件
            if inject_data_code == Instruction.DOWNLOAD_IMAGE.value:
                download_image_num, download_strategy, timestamps = \
                    unpack_inject_data_image_packet(udp_packet)
                t = threading.Thread(
                    target=execute_inject_data_image_download,
                    args=(download_image_num, download_strategy, timestamps))
                t.start()
            # 下载日志文件
            elif inject_data_code == Instruction.DOWNLOAD_LOG.value:
                print("下载日志文件(待实现)...")
            # 更新常量
            elif inject_data_code == Instruction.UPDATE_PARAMS.value:
                print("常值更改(待实现)...")
            else:
                LOGGER.error(f"注入数据指令码有误{inject_data_code}")   
        # 指令解析错误
        else:
            LOGGER.error("收到无法解析的指令")
        # 计数器清零
        if counter >= 255:
            counter = 0
            

# 创建UDP套接字
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)    
# 绑定IP地址和端口号
sock.bind((IP_ADDRESS, PORT_REMOTE_CONTROL))
LOGGER.info(IP_ADDRESS + " : " + str(PORT_REMOTE_CONTROL) + "  开始接收遥控指令...")
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