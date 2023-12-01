import redis

# Connect to Redis
conn = redis.Redis(host='127.0.0.1', port=6379)

# Read the value of the key
key = 'sat_bbox_det'
data = conn.lrange(key, 0, -1)

bbox = [float(value.decode()) for value in data[0:-1]]
image_name = data[-1].decode()

# Print the value
print('bbox: ', bbox)
print('image_name: ', image_name)
