from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
import struct

from utils.share import LOGGER
from utils.telemeter_utils import SERVER_PORT
from utils.telemeter_utils import unpack_udp_packet

class UDPTelemeterProtocol(DatagramProtocol):
    def datagramReceived(self, data, addr):
        counter, time_s, time_ms \
            = unpack_udp_packet(data)
        LOGGER.info(f" 遥测帧计数{counter} 时间戳 {time_s}.{time_ms}")
        # self.transport.write(data, addr)

def main():
    # 启动一个事件循环
    reactor.listenUDP(SERVER_PORT, UDPTelemeterProtocol())
    print('server start')
    reactor.run()

if __name__ == '__main__':
    main()