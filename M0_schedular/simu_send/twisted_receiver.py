from twisted.internet import reactor, defer
from twisted.internet.protocol import DatagramProtocol
from twisted.internet.task import LoopingCall
import queue
import os
import sys

# Add the parent directory to the sys.path list
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
from M0_schedular.simu_send.UDP.utils.image_utils import unpack_udp_packet, check_image_receiving_status
from M0_schedular.simu_send.UDP.utils.image_utils import LOGGER, CHUNK_SIZE, HEADER_SIZE, IP_ADDRESS


class UDPImageProtocol(DatagramProtocol):
    def __init__(self):
        self.counter = 0
        self.data_queue = queue.Queue()

    def datagramReceived(self, data, addr):
        # Put the received datagram into the queue
        # print("receive data")
        self.data_queue.put((data, addr))
    
    def processData(self):
        # print("process data")
        data, addr = self.data_queue.get()
        # Process the received datagram here
        chunk_sum, chunk_seq, image_chunk = unpack_udp_packet(data)
        self.counter = check_image_receiving_status(self.counter, chunk_sum, chunk_seq)

    @defer.inlineCallbacks
    def processDatagrams(self):
        # print("process data queue")
        while not self.data_queue.empty():
            yield self.processData()
      
            

def main():
    # 启动一个事件循环
    imageProtocal = UDPImageProtocol()
    reactor.listenUDP(8089, imageProtocal)
    print('sever start')

    # Create a LoopingCall task to process the datagrams in the queue
    processing_task = LoopingCall(imageProtocal.processDatagrams)
    processing_task.start(0.1)  # Adjust the interval as needed

    reactor.run()

if __name__ == '__main__':
    main()