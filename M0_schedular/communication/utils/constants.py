"""
    用于存放常量，后续改为config文件，支持变更
"""
# 网络
IP_ADDRESS = '127.0.0.1'        # 本机测试用
# IP_ADDRESS = '192.168.0.101'  # 本机正式环境用
SEND_IP =  '192.168.0.103'      # 转发板IP

PORT_IMAGE_RECEIVE = 18089      # 原始图片接收端口(本机)
PORT_TELEMETER = 18089          # 遥测数据发送端口(转发板)
PORT_IMAGE_DOWNLOAD = 18089     # 文件异步包下行发送端口(转发板)
PORT_REMOTE_CONTROL = 17777     # 间接指令、星上时、注入数据和异步包请求接收端口(本机)

# Redis
TOPIC_IMG_RAW = "topic.raw_img"             # redis-1
TOPIC_IMG = "topic.img"                     # redis-2
TOPIC_ANGLE = 'sat_bbox_angle_det'          # redis-3
TOPIC_INSTRUCTION = 'topic.remote_control'  # redis-4
TOPIC_TIME = "queue.time"                   # redis-5
TOPIC_QUERY = 'channel.query'               # redis-6
TOPIC_IMAGE_STATUS = "topic.image_status"   # redis-8
KEY_DEVICE_STATUS = 'orin_nano_stats'       # redis-9
KEY_DOWNLOAD_STATUS = 'file_download_status'# redis-10

# docker服务名
DOWNLOAD_SERVICE_NAME = 'file_download'
# 所有服务名称和编号
SERVICE_NAMES = ['M0_redis',            # bit-0
                 'M0_remote_control',   # bit-1
                 'M0_telemeter',        # bit-2
                 'M0_image_receiver',   # bit-3
                 'M1_quality',          # bit-4
                 'M2_detect',           # bit-5
                 'M3_analyze',          # bit-6
                 'file_download'        # bit-7
                 ]
SERVICE_IDS = {name: idx for idx, name in enumerate(SERVICE_NAMES)}

# 共享目录
COMPOSE_FILE = "/usr/src/deploy/docker-compose.yaml" # docker-compose.yaml在容器中的映射路径
DOWNLOAD_PATH = "/usr/src/data/tmp/" # 模块间共享数据在容器中的映射路径
DOWNLOAD_FILE = "/usr/src/data/tmp/output.zip" # 下载文件和日志时的读取路径

# 阈值常量
ZIPFILE_MAXSIZE = 1000 * 1024    # 下载文件.zip的最大上限，改为200KB
REDIS_QUEUE_MAX_LENGTH = 10      # redis队列最大长度