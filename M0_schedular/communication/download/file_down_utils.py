
import os
import struct
import redis
from enum import Enum
import zipfile

import sys
# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)
from utils.share import LOGGER, serialize_msg, set_redis_key
from utils.constants import KEY_DOWNLOAD_STATUS

# 接收端的IP地址和端口号
RECV_PORT = 18089

# 存储
REDIS = redis.Redis(host='127.0.0.1', port=6379)
IMAGE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/received_images/"

# 后面按需替换
FILE_IMAGE = 0x00 # TODO:图片文件
FILE_LOG = 0xaa   # TODO:日志文件

# 数据分片大小
CHUNK_SIZE = 93
HEADER_SIZE = 11

# TODO(wangyuhang): 文件压缩包大小上限应改为200KB
ZIPFILE_MAXSIZE = 1000 * 1024

class DownloadState(Enum):
    """
        下载任务状态值枚举类
    """
    NONE = 0x00             # 默认值，此时无下载任务 
    RUNNING = 0x55          # 文件正在下载
    STOPPED = 0x77          # 文件下载任务中断/取消
    FILE_ERROR = 0xAA       # 文件不存在/损坏
    FILE_OVERFLOW = 0xEE    # 文件体积超过上限值

from message_config.udp_format import FILE_DOWN_FORMAT

# 封装文件UDP包
def pack_udp_packet(file_type, chunk_sum, chunk_seq, file_chunk):
    # 补全数据域为CHUNK_SIZE Byte定长
    byte_array = bytearray(b'0' * CHUNK_SIZE)
    byte_array[:len(file_chunk)] = file_chunk
    udp_packet = struct.pack(
        FILE_DOWN_FORMAT,        # 0. UDP包格式
        file_type,               # 1. 文件类型
        len(file_chunk),         # 2. 有效数据长度
        chunk_sum,               # 3. 分片数量
        chunk_seq,               # 4. 包序号
        bytes(byte_array)        # 5. 数据域
    )
    return udp_packet

# 解析文件UDP包
def unpack_udp_packet(udp_packet):
    file_type, \
    effect_len, \
    chunk_sum, \
    chunk_seq, \
    file_chunk \
    = struct.unpack(FILE_DOWN_FORMAT, udp_packet)
    return file_type, effect_len, chunk_sum, chunk_seq, file_chunk

def update_download_status(state, progress):
    """
    将文件下载进度更新到redis
    """
    message = {
        'state': state,              # 文件下载状态
        'progress': progress        # 文件下载状态
    }
    json_string = serialize_msg(message)
    set_redis_key(key=KEY_DOWNLOAD_STATUS, value=json_string)

def check_and_zip_files(file_dir, file_names):
    """
        确认文件存在性，并压缩成.zip放在指定目录下
    """
     # 检查文件是否存在,若不存在则更新文件错误状态到redis
    LOGGER.info(f"开始检查文件， 文件路径{file_dir} 文件列表{file_names}")
    missing_files = [file for file in file_names if not os.path.isfile(os.path.join(file_dir, file))]
    if missing_files:
        LOGGER.error(f"文件夹{file_dir}下不存在：{missing_files}")
        update_download_status(DownloadState.FILE_ERROR.value, 0)
        return False
    # 若文件存在，则开始压缩为.zip
    LOGGER.info("文件列表检查完毕，开始压缩...")
    # 确保 tmp 文件夹存在，清空tmp下面的.zip文件
    tmp_dir = os.path.join('/usr/src/data/', 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    # 如果tmp文件存在，则清空下面的.zip文件
    for f in os.listdir(tmp_dir):
        if f.endswith('.zip'):
            file_path = os.path.join(tmp_dir, f)
            os.remove(file_path)
            print(f"删除已存在的.zip文件{file_path}")

    # TODO(wangyuhang): 目前没有压缩，只是叠加写入了一个.zip文件而已
    zip_file_path = os.path.join(tmp_dir, 'output.zip')
    with zipfile.ZipFile(zip_file_path, 'w') as zipf:
        for file in file_names:
            file_path = os.path.join(file_dir, file)
            zipf.write(file_path, arcname=file)
    LOGGER.info(f"文件压缩完毕：{zip_file_path}")

    # TODO(wangyuhang): 判断压缩后文件大小，如果超过上限值，则更新错误状态到redis
    if os.path.getsize(zip_file_path) > ZIPFILE_MAXSIZE:
        LOGGER.error("压缩后的文件大小超过上限值！")
        update_download_status(DownloadState.FILE_OVERFLOW.value, 0)
        return False
    return True

# 解析FILE_DOWN首帧数据
def unpack_file_down_header(file_down_header):
    if len(file_down_header) != 11:
        LOGGER.warning("file_down帧头数据长度有误！")
    file_type, _, _, _, _ = struct.unpack(FILE_DOWN_FORMAT, file_down_header)
    return 

from utils.share import format_udp_packet
# 打印图像UDP数据包
def format_file_udp_packet(udp_packet):
    config_file = 'file_down_config.json'
    config_file_path = parent_dir + "/message_config/" + config_file
    format_udp_packet(udp_packet, config_file_path)