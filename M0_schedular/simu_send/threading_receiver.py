import socket
import threading
import queue

from M0_schedular.simu_send.UDP.utils.image_utils import unpack_udp_packet, check_image_receiving_status
from M0_schedular.simu_send.UDP.utils.image_utils import LOGGER, CHUNK_SIZE, HEADER_SIZE, IP_ADDRESS

BUFFER_SIZE = HEADER_SIZE + CHUNK_SIZE

def receive_datagrams(sock, data_queue):
    while True:
        try:
            data, addr = sock.recvfrom(BUFFER_SIZE)  # Receive UDP datagram
            data_queue.put((data, addr))  # Put received data and address into the queue
        except BlockingIOError:
            # LOGGER.info("no data from socket")
            pass


def process_datagrams(data_queue):
    counter = 0
    while True:    
        while not data_queue.empty():
            data, addr = data_queue.get() 
            chunk_sum, chunk_seq, image_chunk = unpack_udp_packet(data)  
            counter = check_image_receiving_status(counter, chunk_sum, chunk_seq)
            # 根据当前处理数据包的信息，更新计数器并打印接收进度
            # counter = check_image_receiving_status(counter, chunk_sum, chunk_seq)

def main():
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    sock.bind((IP_ADDRESS, 8089))

    # Create a queue to store received datagrams
    data_queue = queue.Queue()  

    # Create a thread for receiving datagrams
    receive_thread = threading.Thread(target=receive_datagrams, args=(sock, data_queue))
    receive_thread.start()

    # Create a thread for processing datagrams
    process_thread = threading.Thread(target=process_datagrams, args=(data_queue,))
    process_thread.start()

    # Wait for the receive thread to finish
    # receive_thread.join()

if __name__=="__main__":
    main()