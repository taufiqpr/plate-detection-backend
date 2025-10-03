import redis
import os

redis_client = None

def init_extensions(app):
    global redis_client
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv('REDIS_DB', 0))

    redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db)
    app.extensions = getattr(app, "extensions", {})
    app.extensions["redis"] = redis_client