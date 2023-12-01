import redis

# Connect to Redis
conn = redis.Redis(host='127.0.0.1', port=6379)
image_name = 'a001.png'

# Define the key and list of values
key = 'mylist'
values = [10, 30.1, 40, 600, 0.99, 0, image_name]

# Set the key with the list value
conn.delete(key)  # Optional: Delete the key if it already exists
conn.rpush(key, *values)

# Retrieve the list from Redis
result = conn.lrange(key, 0, -1)
print(result)