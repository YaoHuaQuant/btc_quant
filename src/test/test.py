import time
import random
from datetime import datetime


def generate_version():
    timestamp = int(time.time())  # 当前时间戳（秒）
    dt_object = datetime.fromtimestamp(timestamp)  # 转换时间戳为 datetime 对象
    readable_format = dt_object.strftime("%Y-%m-%d %H:%M:%S")  # 格式化为易读格式
    random_number = random.randint(1000, 9999)  # 四位随机数
    version = f"{readable_format}:{random_number}"  # 组合成版本号
    return version

print(generate_version())  # 输出类似：1673456789.1234
