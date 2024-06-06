import redis
import json

# Initialize Redis
REDIS = redis.Redis(host='127.0.0.1', port=6379)
TOPIC_RESULT = 'sat_bbox_angle_det'

def get_result_from_redis():
    # Get the JSON string from Redis
    serialized_data = REDIS.get(TOPIC_RESULT)
    if serialized_data:
        # Deserialize the JSON string to a dictionary
        data = json.loads(serialized_data)
        print('data:', data)
        print(data['bbox1'])
        print(data['angle1'])

get_result_from_redis()
