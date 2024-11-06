import sys
import socket
import os
import time
import logging
import cv2
import struct
import json
import asyncio
script_dir = os.path.dirname(os.path.abspath(__file__))
# from utlis.share import LOGGER, IP_ADDRESS
# from utlis.image_utils import pack_udp_packet

IP_ADDRESS = '127.0.0.1'

cameralink_json = '''
{
    "schema": "Image",
    "fields": [
        {
            "name": "frame_header", 
            "id": 1,
            "type": "uint16",
            "description": "帧头"
        },
        {
            "name": "data_length", 
            "id": 2,
            "type": "uint16",
            "description": "数据长度"
        },
        {
            "name": "frame_type",
            "id": 3, 
            "type": "uint8",
            "description": "帧类型"
        },
        {
            "name": "telemeter_type", 
            "id": 4,
            "type": "uint8",
            "description": "遥测数据类型"
        },
        {
            "name": "telemeter_num", 
            "id": 5,
            "type": "uint8",
            "description": "遥测数据分类号"
        },
        {
            "name": "image_counter", 
            "id": 6,
            "type": "uint8",
            "description": "图像计数"
        },
        {
            "name": "exposure",
            "id": 7,
            "type": "uint16",
            "description": "曝光时间"
        },
        {
            "name": "exposure_delay",
            "id": 8,
            "type": "uint8",
            "description": "曝光间隔"
        },
        {
            "name": "time_s",
            "id": 9,
            "type": "uint32",
            "description": "图像拍摄时间戳秒"
        },
        {
            "name": "time_ms",
            "id": 10,
            "type": "uint16",
            "description": "图像拍摄时间戳毫秒"
        },
        {
            "name": "window_x", 
            "id": 11,
            "type": "uint16",
            "description": "开窗左上坐标x"
        },
        {
            "name": "window_y", 
            "id": 12,
            "type": "uint16",
            "description": "开窗左上坐标y"
        },
        {
            "name": "window_width", 
            "id": 13,
            "type": "uint16",
            "description": "开窗宽度"
        },
        {
            "name": "window_height", 
            "id": 14,
            "type": "uint16",
            "description": "开窗高度"
        },
        {
            "name": "checksum", 
            "id": 15,
            "type": "uint16",
            "description": "校验和"
        },
        {
            "name": "frame_end", 
            "id": 16,
            "type": "uint16",
            "description": "帧尾"
        }
    ]
}
'''


image_json = '''
{
    "schema": "Image",
    "fields": [
        {
            "name": "effect_length", 
            "id": 1,
            "type": "uint16",
            "description": "有效数据长度"
        },
        {
            "name": "sender_id", 
            "id": 2,
            "type": "uint8",
            "description": "数据发送方"
        },
        {
            "name": "receiver_id",
            "id": 3, 
            "type": "uint8",
            "description": "数据接收方"
        },
        {
            "name": "time_s", 
            "id": 4,
            "type": "uint32",
            "description": "图像拍摄时间戳秒"
        },
        {
            "name": "time_ms",
            "id": 5,
            "type": "uint16",
            "description": "图像拍摄时间戳毫秒"
        },
        {
            "name": "exposure", 
            "id": 6,
            "type": "uint16",
            "description": "曝光时长"
        },
        {
            "name": "chunk_sum", 
            "id": 7,
            "type": "uint32",
            "description": "图像数据UDP包总数"
        },
        {
            "name": "chunk_seq", 
            "id": 8,
            "type": "uint32",
            "description": "包序号"
        },
        {
            "name": "window_width", 
            "id": 9,
            "type": "uint16",
            "description": "开窗宽度"
        },
        {
            "name": "window_height", 
            "id": 10,
            "type": "uint16",
            "description": "开窗高度"
        },
        {
            "name": "window_x", 
            "id": 11,
            "type": "uint16",
            "description": "开窗左下坐标x"
        },
        {
            "name": "window_y", 
            "id": 12,
            "type": "uint16",
            "description": "开窗左下坐标y"
        },
        {
            "name": "image_chunk",
            "id": 13,
            "type": "string",
            "length": 1024,
            "description": "图像包数据域"
        }
    ]
}
'''

SEND_PORT = 18089
CHUNK_SIZE = 1024           # 图片分片长度
SENDER_DEVICE = 0x00        # TODO:转发板设备ID
RECV_DEVICE = 0x01          # TODO: AI计算机设备ID

CAMERALINK_FRAME_HEADER = 0xeb90




# 日志输出到控制台
# logging.basicConfig(filename="M0-log.txt", filemode='a')
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
LOGGER.addHandler(ch)

exposure_img_names = []
exposures = [1.0, 0.5, 2.0, 4.0]
exposure_time = [100, 200, 400, 800]
first_frame_time = time.time()








def generate_udp_format(json_str):
    # with open(config_file, mode="r", encoding="utf-8") as config_file:
    #     config = json.load(config_file)
    config = json.loads(json_str)
    format_string = '!'  
    for field in config['fields']:
        field_type = field['type']
        if field_type == 'uint8':
            format_string += 'B'
        elif field_type == 'uint16':
            format_string += 'H'
        elif field_type == 'uint32':
            format_string += 'I'
        elif field_type == 'float':
            format_string += 'f'
        elif field_type == 'string':
            length = field['length']
            format_string += str(length) + 's'
    return format_string

IMAGE_UDP_FORMAT = generate_udp_format(image_json)
CAMERALINK_UDP_FORMAT = generate_udp_format(cameralink_json)


def pack_udp_packet(time_s, time_ms, chunk_sum, chunk_seq, image_chunk, exposure_time, window_x, window_y, pos_x, pos_y):
    """
        封装图像UDP包
    """
    # 补全数据域为1024定长
    byte_array = bytearray(b'0' * 1024)
    byte_array[:len(image_chunk)] = image_chunk
    
    udp_packet = struct.pack(
        IMAGE_UDP_FORMAT,             
        len(image_chunk),       # 1. 有效数据长度(固定值，数值不影响图片解析程序)
        SENDER_DEVICE,          # 2. 发送方(固定值)
        RECV_DEVICE,            # 3. 接收方(固定值)
        time_s,                 # 4. 时间戳秒
        time_ms,                # 5. 时间戳毫秒
        exposure_time,          # 6. 曝光参数(从cameralink中解析)
        chunk_sum,              # 7. 分片数量
        chunk_seq,              # 8. 包序号
        window_x,               # 9. 开窗宽度w(从cameralink中解析)
        window_y,               # 10. 开窗高度h(从cameralink中解析)
        pos_x,                  # 11. 开窗左下坐标x(从cameralink中解析)
        pos_y,                  # 12. 开窗左下坐标y(从cameralink中解析)
        bytes(byte_array)       # 13. 数据域
    )
    #format_udp_packet(udp_packet, IMAGE_UDP_FORMAT , image_json)
    return udp_packet


def pack_cameralink_packet(filename, expo_time, time_s, time_ms, window_x, window_y, pos_x, pos_y):
    """
    	pack cameralink udp bag
    """
    img = cv2.imread(filename, 0)
    byte_array = img.tobytes()
    
    """
    with open(filename, 'rb') as file:
        image_data = file.read()
        file.close()
    byte_array = bytearray(b'0' * len(image_data))
    byte_array[:len(image_data)] = image_data
    """
    udp_packet = struct.pack(
    	CAMERALINK_UDP_FORMAT + str(len(byte_array)) + 's',
    	CAMERALINK_FRAME_HEADER,	#1.frame header: 0xeb90
    	0,		#2.有效数据长度	
    	0,				#3.帧类型
    	0,				#4.遥测数据类型
    	0,				#5.遥测数据分类号
    	0,				#6.图像计数
    	expo_time,			#7.曝光时间
    	0,				#8.曝光间隔
    	time_s,			#9.图像拍摄时间戳秒
    	time_ms,			#10.图像拍摄时间戳毫秒
    	pos_x,				#11.开窗左上坐标x
    	pos_y,				#12.开窗左上坐标y
    	window_x,			#13.开窗宽度
    	window_y,			#14.开窗高度
    	0,				#15.校验和
    	0,				#16.帧尾
    	bytes(byte_array) #17.数据域
    )
    #format_udp_packet(udp_packet, CAMERALINK_UDP_FORMAT + str(len(image_data)) + 's', cameralink_json)
    return udp_packet
    	


def format_udp_packet(packet, format_string, json_str):
    # format_string = generate_udp_format(json_str)
    try:
        # 使用 struct.unpack() 函数解包数据
        field_values = struct.unpack(format_string, packet)
    except struct.error as e:
        LOGGER.error(f"UDP包解析错误，包内容与格式不符：{ format_string }")
        return
    # 加载config文件
    # with open(config_file, mode="r", encoding="utf-8") as config_file:
    #     config = json.load(config_file)
    config = json.loads(json_str)
    field_configs = config['fields'] # 返回一个list
    # 判断字段个数和config文件一致
    #if len(field_values) != len(field_configs):
    #    LOGGER.error("UDP包字段个数与config文件不符")
     #   return
    
    format_string = ""
    for i in range(len(field_configs)):
        value = field_values[i]
        field = field_configs[i]
        field_type = field['type']
        field_info = field['description']
        if field_type == 'uint8':
            format_string += f"{field_info}:\t{value:d}\n"
        elif field_type == 'uint16':
            format_string += f"{field_info}:\t{value:d}\n"
        elif field_type == 'uint32':
            format_string += f"{field_info}:\t{value:d}\n"
        elif field_type == 'float':
            format_string += f"{field_info}:\t{value:.2f}\n"
        elif field_type == 'string':
            length = field['length']
            if length <= 20:
                format_string += f"{field_info}:\t{value}\n"
            else:
                format_string += f"{field_info}:\t{value[:20]} ...总长度 {len(value)}\n"
    print(format_string)

def send_image(filename, server_ip, server_port, chunk_size, exposure_time, window_x, window_y, pos_x, pos_y):
    # 创建UDP套接字
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 获取时间戳
    timestamp = time.time()
    # if first_frame_time is None:
    #     first_frame_time = timestamp
    timestamp = timestamp - first_frame_time
    time_s = int(timestamp)
    time_ms = int((timestamp - time_s) * 1000)

    cameralink_udp_pack = pack_cameralink_packet(filename, exposure_time, time_s, time_ms, window_x, window_y, pos_x, pos_y)
    
    # 获取图像文件大小和分片数量
    image_size = len(cameralink_udp_pack)
    image_data = cameralink_udp_pack
    chunk_sum = (image_size + chunk_size - 1) // chunk_size

    # 发送图像分片
    sent_chunks = 0
    for i in range(chunk_sum):
        # 获取图片分片
        start = i * chunk_size
        end = min((i + 1) * chunk_size, image_size)
        image_chunk = image_data[start:end]
        # 发送UDP帧
        udp_packet = pack_udp_packet(
            time_s, 
            time_ms, 
            chunk_sum, 
            i, 
            image_chunk,
            exposure_time,
            window_x,
            window_y,
            pos_x,
            pos_y
        )
        sock.sendto(udp_packet, (server_ip, server_port))
        sent_chunks += 1
        time.sleep(0.0000001)
    # 输出发送图片结束时的日志：分片数量，文件大小
    LOGGER.info("已发送分片数: " + str(sent_chunks))

    # 关闭套接字
    sock.close()


def generate_four_exposure_images(filename, window_x, window_y, pos_x, pos_y):
    img = cv2.imread(filename)
    img = crop_image(img, window_x, window_y, pos_x, pos_y)
    for exposure in exposures:
        exposure_img = cv2.convertScaleAbs(img, alpha=exposure, beta=0)
        name = 'exposure_' + str(exposure) + '.bmp'
        exposure_img_names.append(name)
        cv2.imwrite(name, exposure_img)


def crop_image(img, window_x, window_y, pos_x, pos_y):
    return img[pos_y:pos_y + window_y, pos_x:pos_x + window_x]


async def begin_send_images(send_freq, window_width, window_height, pos_x, pos_y):
    idx = 0
    while idx < send_freq:
        
        send_image(exposure_img_names[idx], IP_ADDRESS, SEND_PORT, CHUNK_SIZE, exposure_time[idx], window_width, window_height, pos_x, pos_y)
        #idx = (idx + 1) % len(exposures)
        idx += 1
        await asyncio.sleep(1 / send_freq)


def udp_1(filename='xingmin.jpg', send_freq = 4, window_width=512, window_height=512, pos_x = 50, pos_y = 150):
    generate_four_exposure_images(filename, window_width, window_height, pos_x, pos_y)
    first_frame_time = time.time()
    asyncio.run(begin_send_images(send_freq, window_width, window_height, pos_x, pos_y))


if __name__ == "__main__":
    # P图像所在文件夹的路径
    folder_path = '../redis/test_image'
    for filename in os.listdir(folder_path):
        print(filename)
        image_path = os.path.join(folder_path, filename)
        udp_1(image_path, send_freq = 4, window_width=2048, window_height=2048, pos_x = 0, pos_y = 0) 
