import threading
import queue
import clickhouse_connect  # 假设你使用 clickhouse-connect 库
import backtrader as bt

class AsyncClickHouseWriter:
    def __init__(self, db_config):
        self.db_config = db_config
        self.data_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        """后台线程从队列中读取数据并写入 ClickHouse"""
        client = clickhouse_connect.get_client(**self.db_config)
        while not self.stop_event.is_set():
            try:
                # 批量写入数据
                batch = []
                while not self.data_queue.empty():
                    batch.append(self.data_queue.get_nowait())
                if batch:
                    client.insert("kline_data_table", batch)
            except queue.Empty:
                continue  # 如果队列为空，继续等待
            except Exception as e:
                print(f"Error writing to ClickHouse: {e}")
            finally:
                client.close()

    def write(self, data):
        """将数据放入队列"""
        self.data_queue.put(data)

    def stop(self):
        """停止线程"""
        self.stop_event.set()
        self.thread.join()

class MyStrategy(bt.Strategy):
    def __init__(self, writer):
        self.writer = writer

    def next(self):
        """每根K线触发"""
        data = {
            "datetime": self.data.datetime.datetime(0),
            "open": self.data.open[0],
            "high": self.data.high[0],
            "low": self.data.low[0],
            "close": self.data.close[0],
            "volume": self.data.volume[0],
        }
        # 将数据传递到后台线程
        self.writer.write(data)

# 配置 ClickHouse 数据库
db_config = {
    "host": "localhost",
    "port": 8123,
    "username": "default",
    "password": "",
    "database": "test",
}

if __name__ == "__main__":
    # 创建异步写入器
    writer = AsyncClickHouseWriter(db_config)

    # 设置 Backtrader 策略
    cerebro = bt.Cerebro()
    cerebro.addstrategy(MyStrategy, writer)

    # 添加数据
    data = bt.feeds.GenericCSVData(
        dataname="your_data.csv",
        dtformat="%Y-%m-%d %H:%M:%S",
        timeframe=bt.TimeFrame.Minutes,
    )
    cerebro.adddata(data)

    # 启动回测
    try:
        cerebro.run()
    finally:
        # 确保后台线程停止
        writer.stop()
