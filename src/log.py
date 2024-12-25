import logging

logging.basicConfig(
    level=logging.INFO,                  # 设置日志级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # 设置日志格式
    handlers=[
        logging.StreamHandler(),         # 输出到控制台
        # logging.FileHandler('app.log')   # 输出到文件
    ]
)