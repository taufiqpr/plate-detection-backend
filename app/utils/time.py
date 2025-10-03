from datetime import datetime
import pytz

WIB = pytz.timezone("Asia/Jakarta")

def now_wib() -> str:
    return datetime.now(WIB).strftime("%Y-%m-%dT%H:%M:%S")
