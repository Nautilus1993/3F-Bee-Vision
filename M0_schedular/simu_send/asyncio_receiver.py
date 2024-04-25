import asyncio
import socket

from M0_schedular.simu_send.UDP.utils.image_utils import unpack_udp_packet, check_image_receiving_status
from M0_schedular.simu_send.UDP.utils.image_utils import LOGGER, CHUNK_SIZE, HEADER_SIZE, IP_ADDRESS

BUFFER_SIZE = HEADER_SIZE + CHUNK_SIZE

received_chunks = {}

async def process_datagram(data):
    chunk_sum, chunk_seq, image_chunk = unpack_udp_packet(data)
    if chunk_seq == 0:
        if len(received_chunks) > 0:
            print(f"丢包:!收到第一帧数据，队列非空 长度 = {len(received_chunks) > 0}")
            received_chunks = {}

    if chunk_seq not in received_chunks:
            received_chunks[chunk_seq] = image_chunk
    else:
        print(f"重复收到编号{chunk_seq}的分片")

    if chunk_seq == chunk_sum:
        if len(received_chunks) == chunk_sum:
            print("已经收到了完整的图片")   
        else:
            print(f"收到最后一帧但还未收完整，队列长度 = {len(received_chunks) > 0}")

async def receive_datagrams(sock, loop) -> None:
    while True:
        try:
            while data := await loop.sock_recv(sock, BUFFER_SIZE):
                asyncio.create_task(process_datagram(data))             
        except Exception as ex:
            LOGGER.exception(ex)
        finally:
            sock.close()

async def main():
    # 包计数器
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = (IP_ADDRESS, 8089)
    server_socket.setblocking(False)
    server_socket.bind(server_address)
    await receive_datagrams(server_socket, loop)

# 使用自定义的loop
loop = asyncio.new_event_loop() # E
loop.set_debug(True)

try:
    loop.run_until_complete(main())
finally:
    loop.close()