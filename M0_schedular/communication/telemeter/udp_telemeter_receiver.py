from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
import sys
import os

# 获取当前脚本文件所在的目录路径
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录路径
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)
sys.path.append(script_dir)
from utils.share import LOGGER
from telemeter_utils import SERVER_PORT
from telemeter_utils import unpack_telemeter_packet

class UDPTelemeterProtocol(DatagramProtocol):
    def datagramReceived(self, data, addr):
        counter, time_s, time_ms \
            = unpack_telemeter_packet(data)
        LOGGER.info(f" 遥测帧计数{counter} 时间戳 {time_s}.{time_ms}")
        # self.transport.write(data, addr)

def main():
    # 启动一个事件循环
    reactor.listenUDP(SERVER_PORT, UDPTelemeterProtocol())
    print('server start')
    reactor.run()

if __name__ == '__main__':
    main()