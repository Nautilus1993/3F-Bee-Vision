from udp_telemeter_sender import SERVER_PORT, UDP_FORMAT
from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
import struct

import os
import sys

# Add the parent directory to the sys.path list
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)
from utils.image_utils import LOGGER

def unpack_udp_packet(udp_packet):
    time_s, time_ms, bbox_class, bbox_x, bbox_y \
        = struct.unpack(UDP_FORMAT, udp_packet)
    return time_s, time_ms, bbox_class, bbox_x, bbox_y

class UDPTelemeterProtocol(DatagramProtocol):
    def datagramReceived(self, data, addr):
        time_s, time_ms, bbox_class, bbox_x, bbox_y  \
            = unpack_udp_packet(data)
        LOGGER.info(f" 目标类别 {bbox_class}, 中心点 ({bbox_x},{bbox_y})")
        # self.transport.write(data, addr)

def main():
    # 启动一个事件循环
    reactor.listenUDP(SERVER_PORT, UDPTelemeterProtocol())
    print('server start')
    reactor.run()

if __name__ == '__main__':
    main()