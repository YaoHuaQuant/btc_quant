"""
保存策略的action数据
action：即挂单信息和成交信息
"""
from collections import namedtuple
from datetime import datetime
from typing import List

from data_collection.db import db
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
    'StrategyActionBtcUSDT1mDao',
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
        self.db_connection = db

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

    def insert_many(self, data: List[StrategyActionBtcUSDT1mInsertDao]):
        query = f"INSERT INTO strategy_action_btc_usdt_1m (version, action_time, status, open_price, close_price, quantity,\
        open_cost, expected_gross_value, actual_gross_value, expected_commission, actual_commission) VALUES"
        # logging.info(f"sql:{query}")
        # logging.info(f"data:{data}")
        self.db_connection.execute(query, data)
        # logging.info(f"Data inserted into {table_name} successfully.")


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
    new_data: List[StrategyActionBtcUSDT1mInsertDao] = []

    # 输出查询结果
    for row in data:
        logging.info(row)
        new_data.append(from_StrategyActionBtcUSDT1mDao_to_StrategyActionBtcUSDT1mInsertDao(row))

    connector.insert_many(new_data)


def test_insert_single():
    connector = StrategyActionBtcUSDT1mConnector()

    data: StrategyActionBtcUSDT1mInsertDao = StrategyActionBtcUSDT1mInsertDao(
        'version1', '2023-12-01 04:01:00', 1, 2, 3, 4, 5, 6, 7, 8, 9)
    connector.insert_single(data)

    from_timestamp = datetime(2023, 12, 1, 0, 0)
    to_timestamp = datetime(2023, 12, 2, 0, 0)
    data: List[StrategyActionBtcUSDT1mDao] = connector.select(from_timestamp, to_timestamp)

    # 输出查询结果
    for row in data:
        logging.info(row)


if __name__ == '__main__':
    # test_select()
    test_insert_many()
    # test_insert_single()
