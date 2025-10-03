import json
from flask import current_app

def set_cache(key: str, value= dict, expire: int = 300):
    redis_client = current_app.extensions.get("redis")
    redis_client.set(key, json.dumps(value), ex=expire)

def get_cache(key: str):
    redis_client = current_app.extensions.get("redis")
    cached = redis_client.get(key)
    return json.loads(cached) if cached else None