from udp_telemeter_sender import SERVER_IP, SERVER_PORT, UDP_FORMAT
from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
import struct

def unpack_udp_packet(udp_packet):
    time_s, time_ms, bbox_class, bbox_x, bbox_y \
        = struct.unpack(UDP_FORMAT, udp_packet)
    return time_s, time_ms, bbox_class, bbox_x, bbox_y

class UDPTelemeterProtocol(DatagramProtocol):
    def datagramReceived(self, data, addr):
        time_s, time_ms, bbox_class, bbox_x, bbox_y  \
            = unpack_udp_packet(data)
        print(f"received {time_s} . {time_ms}, \
              target is {bbox_class}, \
              center_point is ({bbox_x},{bbox_y})")
        # self.transport.write(data, addr)

def main():
    # 启动一个事件循环
    reactor.listenUDP(SERVER_PORT, UDPTelemeterProtocol())
    print('sever start')
    reactor.run()

if __name__ == '__main__':
    main()