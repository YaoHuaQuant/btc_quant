import queue
import threading
from clickhouse_driver import Client


class ClickHouseManager:
    def __init__(self, host: str, user: str, password: str, database: str):
        self.client = Client(
            host=host,
            user=user,
            password=password,
            database=database
        )
        self.data_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._queue_worker, daemon=True)
        self.thread.start()


    def execute(self, query, params=None):
        return self.client.execute(query, params)

    def execute_queue(self, query, params=None):
        """
        使用队列进行异步计算
        只执行写入
        :param query:
        :param params:
        :return:
        """
        self.data_queue.put((query, params))

    def _queue_worker(self):
        """
        后台线程
        从队列读取数据
        并写入clickhouse
        :return:
        """
        while not self.stop_event.is_set():
            try:
                # 批量写入数据
                while True:
                    query, params = self.data_queue.get()
                    if query is not None:
                        self.execute_queue(query, params)
            except queue.Empty:
                continue  # 如果队列为空，继续等待
            except Exception as e:
                print(f"Error writing to ClickHouse: {e}")

def new_db_connection() -> ClickHouseManager:
    return ClickHouseManager(host='localhost', user='gx', password='1234566', database='btc_quant')
