"""
保存策略的action数据
action：即挂单信息和成交信息
"""
import time
from collections import namedtuple
from datetime import datetime
from typing import List
import queue
import threading

from data_collection.db import new_db_connection
from log import *

table_name = 'strategy_action_btc_usdt_1m'

StrategyActionBtcUSDT1mDao = namedtuple(
    'StrategyActionBtcUSDT1mDao',
    [
        'id', 'version', 'action_time', 'status', 'open_price', 'close_price', 'quantity', 'open_cost',
        'expected_gross_value',
        'actual_gross_value', 'expected_commission', 'actual_commission',
    ]
)

StrategyActionBtcUSDT1mInsertDao = namedtuple(
    'StrategyActionBtcUSDT1mInsertDao',
    [
        'version', 'action_time', 'status', 'open_price', 'close_price', 'quantity', 'open_cost',
        'expected_gross_value',
        'actual_gross_value', 'expected_commission', 'actual_commission',
    ]
)


def from_StrategyActionBtcUSDT1mDao_to_StrategyActionBtcUSDT1mInsertDao(
        data: StrategyActionBtcUSDT1mDao) -> StrategyActionBtcUSDT1mInsertDao:
    return StrategyActionBtcUSDT1mInsertDao(data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8],
                                            data[9], data[10], data[11])


class StrategyActionBtcUSDT1mConnector:
    def __init__(self):
        self.db_connection = new_db_connection()
        self.data_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._queue_worker, daemon=True)
        self.thread.start()

    def select(self, from_timestamp: datetime, to_timestamp: datetime, order: str = 'ASC') -> List[
        StrategyActionBtcUSDT1mDao]:
        if order != 'ASC' and order != 'DESC':
            raise ValueError('order is not ASC or DESC')
        query = f"SELECT DISTINCT * FROM strategy_action_btc_usdt_1m \
        WHERE action_time BETWEEN %(from_timestamp)s AND %(to_timestamp)s ORDER BY action_time {order}"
        params = {'from_timestamp': from_timestamp, 'to_timestamp': to_timestamp}
        result = self.db_connection.execute(query, params)
        return result

    def insert_single(self, data: StrategyActionBtcUSDT1mInsertDao):
        query = f"INSERT INTO strategy_action_btc_usdt_1m (version, action_time, status, open_price, close_price, quantity,\
        open_cost, expected_gross_value, actual_gross_value, expected_commission, actual_commission) \
            VALUES (%(version)s, %(action_time)s, %(status)s, %(open_price)s, %(close_price)s, %(quantity)s, \
            %(open_cost)s, %(expected_gross_value)s, %(actual_gross_value)s, %(expected_commission)s, \
            %(actual_commission)s)"
        params = {
            'version': data.version,
            'action_time': data.action_time,
            'status': data.status,
            'open_price': data.open_price,
            'close_price': data.close_price,
            'quantity': data.quantity,
            'open_cost': data.open_cost,
            'expected_gross_value': data.expected_gross_value,
            'actual_gross_value': data.actual_gross_value,
            'expected_commission': data.expected_commission,
            'actual_commission': data.actual_commission,
        }
        self.db_connection.execute(query, params)
        # logging.info(f"Data insert into {table_name} successfully.")

    def insert_single_queue(self, data: StrategyActionBtcUSDT1mInsertDao):
        """
        使用队列进行异步写入
        :param data: StrategyActionBtcUSDT1mInsertDao
        :return:
        """
        self.data_queue.put(data)

    def insert_many(self, data: List[StrategyActionBtcUSDT1mInsertDao]):
        query = f"INSERT INTO strategy_action_btc_usdt_1m (version, action_time, status, open_price, close_price, quantity,\
        open_cost, expected_gross_value, actual_gross_value, expected_commission, actual_commission) VALUES"
        # logging.info(f"sql:{query}")
        # logging.info(f"data:{data}")
        self.db_connection.execute(query, data)
        # logging.info(f"Data inserted into {table_name} successfully.")

    def insert_many_queue(self, data: List[StrategyActionBtcUSDT1mInsertDao]):
        """
        使用队列进行异步写入
        :param data: List[StrategyActionBtcUSDT1mInsertDao]
        :return:
        """
        for d in data:
            self.data_queue.put(d)

    def _queue_worker(self):
        """
        后台线程
        从队列读取数据
        并写入clickhouse
        :return:
        """
        while not self.stop_event.is_set():
            queries: List[StrategyActionBtcUSDT1mInsertDao] = []
            try:
                # 批量写入数据
                while True:
                    while True:
                        try:
                            query = self.data_queue.get_nowait()
                            # logging.info(f"append query {query}")
                        except Exception as e:
                            break
                        queries.append(query)
                    # logging.info(f"try to insert {queries}")
                    if len(queries) > 0:
                        self.insert_many(queries)
                        # logging.info(f"successfully insert {queries}")
                    time.sleep(1)   # 控制qps
            except queue.Empty:
                continue  # 如果队列为空，继续等待
            except Exception as e:
                print(f"Error writing to ClickHouse: {e}")
                # 回写未完成插入的数据
                for query in queries:
                    self.data_queue.put(query)

    def __del__(self):
        """停止线程"""
        self.stop_event.set()
        self.thread.join()


def test_select():
    connector = StrategyActionBtcUSDT1mConnector()

    from_timestamp = datetime(2023, 12, 1, 0, 0)
    to_timestamp = datetime(2023, 12, 2, 0, 0)

    result = connector.select(from_timestamp, to_timestamp)
    # 输出查询结果
    for row in result:
        logging.info(row)


def test_insert_many():
    connector = StrategyActionBtcUSDT1mConnector()

    from_timestamp = datetime(2023, 12, 1, 0, 0)
    to_timestamp = datetime(2023, 12, 2, 0, 0)
    data: List[StrategyActionBtcUSDT1mDao] = connector.select(from_timestamp, to_timestamp)


    data1: StrategyActionBtcUSDT1mInsertDao = StrategyActionBtcUSDT1mInsertDao(
        'version1', '2023-12-01 04:01:00', 1, 2, 3, 4, 5, 6, 7, 8, 9)
    data2: StrategyActionBtcUSDT1mInsertDao = StrategyActionBtcUSDT1mInsertDao(
        'version1', '2023-12-01 04:02:00', 1, 2, 3, 4, 5, 6, 7, 8, 9)

    new_data: List[StrategyActionBtcUSDT1mInsertDao] = [data1, data2]
    logging.info(f"insert {new_data}")

    # # 输出查询结果
    # for row in data:
    #     logging.info(row)
    #     new_data.append(from_StrategyActionBtcUSDT1mDao_to_StrategyActionBtcUSDT1mInsertDao(row))

    connector.insert_many(new_data)


def test_insert_single():
    connector = StrategyActionBtcUSDT1mConnector()

    data1: StrategyActionBtcUSDT1mInsertDao = StrategyActionBtcUSDT1mInsertDao(
        'version1',
        datetime(2023, 12, 1, 4, 1),
        1, 2, 3, 4, 5, 6, 7, 8, 9)
    data2: StrategyActionBtcUSDT1mInsertDao = StrategyActionBtcUSDT1mInsertDao(
        'version1',
        datetime(2023, 12, 1, 4, 2),
        1, 2, 3, 4, 5, 6, 7, 8, 9)
    connector.insert_single_queue(data1)
    connector.insert_single_queue(data2)
    # connector.insert_single(data1)
    # connector.insert_single(data2)

    from_timestamp = datetime(2023, 12, 1, 0, 0)
    to_timestamp = datetime(2023, 12, 2, 0, 0)
    data: List[StrategyActionBtcUSDT1mDao] = connector.select(from_timestamp, to_timestamp)

    # 输出查询结果
    for row in data:
        logging.info(row)


if __name__ == '__main__':
    # test_insert_many()
    test_insert_single()
    time.sleep(50000)
    test_select()
