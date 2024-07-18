import redis

# 初始化redis
conn = redis.Redis(host='192.168.8.20', port=6379)  # wifi local ip
sub = conn.pubsub()
sub.subscribe("topic.img")

# 处理后转发的频道
publish_channel = "topic.img_save"

def main():
    while True:
        try:
            # 通过redis收图做预测
            print('waiting for image...')
            for item in sub.listen():
                if item['type'] == 'message':
                    # 直接转发消息
                    conn.publish(publish_channel, item['data'])
                    # send log
                    message_data = item['data']
                    message_dict = eval(message_data)
                    img_name = message_dict['name']
                    print("send image: ", img_name)
        except Exception as e:
            print(e)

if __name__ == "__main__":
    main()