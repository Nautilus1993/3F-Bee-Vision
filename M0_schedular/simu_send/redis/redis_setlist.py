import redis
import json

# Initialize Redis
conn = redis.Redis(host='127.0.0.1', port=6379)
sub = conn.pubsub()
sub.subscribe("topic.img")

def pub_result(sat_bbox):
    # Define the key and dictionary value
    key = 'sat_bbox_det'
    value = sat_bbox
    # Serialize the dictionary to a JSON string
    serialized_value = json.dumps(value)
    # Set the key with the JSON string value
    conn.set(key, serialized_value)

sat_bbox = {'bbox': [1,1,1,1], 'img_name': 'hhhh'}
pub_result(sat_bbox)
