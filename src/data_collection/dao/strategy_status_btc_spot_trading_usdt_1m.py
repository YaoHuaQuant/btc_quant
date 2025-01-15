"""
保存策略的status信息
status：账户的现金、持仓、市值、借贷资金、期望收益等信息
"""
from collections import namedtuple
from datetime import datetime
from typing import List

from data_collection.db import db
from log import *

table_name = 'strategy_status_btc_usdt_1m'

StrategyStatusBtcUSDT1mDao = namedtuple(
    'StrategyStatusBtcUSDT1mDao',
    [
        'open_time',
        'version',
        'price',
        'opening_order_num',
        'opening_order_quantity',
        'opening_order_value',
        'closing_order_num',
        'closing_order_quantity',
        'closing_order_value',
        'closing_order_cost',
        'opened_order_num',
        'opened_order_quantity',
        'opened_order_value',
        'closed_order_num',
        'closed_order_quantity',
        'closed_order_value',
        'closed_order_cost',
        'cumulative_opening_order_num',
        'cumulative_opening_order_quantity',
        'cumulative_opening_order_value',
        'cumulative_closing_order_num',
        'cumulative_closing_order_quantity',
        'cumulative_closing_order_value',
        'cumulative_closing_order_cost',
        'cumulative_opened_order_num',
        'cumulative_opened_order_quantity',
        'cumulative_opened_order_value',
        'cumulative_closed_order_num',
        'cumulative_closed_order_quantity',
        'cumulative_closed_order_value',
        'cumulative_closed_order_cost',
        'cash',
        'loan',
        'holding_quantity',
        'holding_value',
        'total_value',
        'expected_closing_profit',
        'actual_closed_profit',
        'expected_market_close_profit',
        'expected_closed_profit',
        'expected_holding_value',
        'expected_total_value',
        'actual_net_value',
        'expected_net_value',
        'ave_profit_per_closed_order',
    ]
)


class StrategyStatusBtcUSDT1mConnector:
    def __init__(self):
        self.db_connection = db

    def select(self, from_timestamp: datetime, to_timestamp: datetime, order: str = 'ASC') -> List[
        StrategyStatusBtcUSDT1mDao]:
        if order != 'ASC' and order != 'DESC':
            raise ValueError('order is not ASC or DESC')
        query = f"SELECT DISTINCT * FROM strategy_status_btc_usdt_1m \
        WHERE open_time BETWEEN %(from_timestamp)s AND %(to_timestamp)s ORDER BY open_time {order}"
        params = {'from_timestamp': from_timestamp, 'to_timestamp': to_timestamp}
        result = self.db_connection.execute(query, params)
        return result

    def insert_single(self, data: StrategyStatusBtcUSDT1mDao):
        query = f"INSERT INTO strategy_status_btc_usdt_1m (open_time, version, price, opening_order_num, \
        opening_order_quantity, opening_order_value, closing_order_num, closing_order_quantity, closing_order_value, \
        closing_order_cost, opened_order_num, opened_order_quantity, opened_order_value, closed_order_num, \
        closed_order_quantity, closed_order_value, closed_order_cost,cumulative_opening_order_num, \
        cumulative_opening_order_quantity, cumulative_opening_order_value, cumulative_closing_order_num, \
        cumulative_closing_order_quantity, cumulative_closing_order_value, cumulative_closing_order_cost, \
        cumulative_opened_order_num, cumulative_opened_order_quantity, cumulative_opened_order_value, \
        cumulative_closed_order_num, cumulative_closed_order_quantity, cumulative_closed_order_value, \
        cumulative_closed_order_cost, cash, loan, holding_quantity, holding_value, \
        total_value, expected_closing_profit, actual_closed_profit, expected_market_close_profit, \
        expected_closed_profit, expected_holding_value, expected_total_value, actual_net_value, \
        expected_net_value, ave_profit_per_closed_order) \
            VALUES (%(open_time)s, %(version)s, %(price)s, %(opening_order_num)s, %(opening_order_quantity)s, \
            %(opening_order_value)s, %(closing_order_num)s, %(closing_order_quantity)s, %(closing_order_value)s, \
            %(closing_order_cost)s, %(opened_order_num)s, %(opened_order_quantity)s, %(opened_order_value)s, \
            %(closed_order_num)s, %(closed_order_quantity)s, %(closed_order_value)s, %(closed_order_cost)s, \
            %(cumulative_opening_order_num)s, %(cumulative_opening_order_quantity)s, \
            %(cumulative_opening_order_value)s, %(cumulative_closing_order_num)s, \
            %(cumulative_closing_order_quantity)s, %(cumulative_closing_order_value)s, \
            %(cumulative_closing_order_cost)s, %(cumulative_opened_order_num)s, %(cumulative_opened_order_quantity)s, \
            %(cumulative_opened_order_value)s, %(cumulative_closed_order_num)s, %(cumulative_closed_order_quantity)s, \
            %(cumulative_closed_order_value)s, %(cumulative_closed_order_cost)s, %(cash)s, \
            %(loan)s, %(holding_quantity)s, %(holding_value)s, %(total_value)s, %(expected_closing_profit)s, \
            %(actual_closed_profit)s, %(expected_market_close_profit)s, %(expected_closed_profit)s, \
            %(expected_holding_value)s, %(expected_total_value)s, %(actual_net_value)s, \
            %(expected_net_value)s, %(ave_profit_per_closed_order)s)"

        params = {
            'open_time': data.open_time,
            'version': data.version,
            'price': data.price,
            'opening_order_num': data.opening_order_num,
            'opening_order_quantity': data.opening_order_quantity,
            'opening_order_value': data.opening_order_value,
            'closing_order_num': data.closing_order_num,
            'closing_order_quantity': data.closing_order_quantity,
            'closing_order_value': data.closing_order_value,
            'closing_order_cost': data.closing_order_cost,
            'opened_order_num': data.opened_order_num,
            'opened_order_quantity': data.opened_order_quantity,
            'opened_order_value': data.opened_order_value,
            'closed_order_num': data.closed_order_num,
            'closed_order_quantity': data.closed_order_quantity,
            'closed_order_value': data.closed_order_value,
            'closed_order_cost': data.closed_order_cost,
            'cumulative_opening_order_num': data.cumulative_opening_order_num,
            'cumulative_opening_order_quantity': data.cumulative_opening_order_quantity,
            'cumulative_opening_order_value': data.cumulative_opening_order_value,
            'cumulative_closing_order_num': data.cumulative_closing_order_num,
            'cumulative_closing_order_quantity': data.cumulative_closing_order_quantity,
            'cumulative_closing_order_value': data.cumulative_closing_order_value,
            'cumulative_closing_order_cost': data.cumulative_closing_order_cost,
            'cumulative_opened_order_num': data.cumulative_opened_order_num,
            'cumulative_opened_order_quantity': data.cumulative_opened_order_quantity,
            'cumulative_opened_order_value': data.cumulative_opened_order_value,
            'cumulative_closed_order_num': data.cumulative_closed_order_num,
            'cumulative_closed_order_quantity': data.cumulative_closed_order_quantity,
            'cumulative_closed_order_value': data.cumulative_closed_order_value,
            'cumulative_closed_order_cost': data.cumulative_closed_order_cost,
            'cash': data.cash,
            'loan': data.loan,
            'holding_quantity': data.holding_quantity,
            'holding_value': data.holding_value,
            'total_value': data.total_value,
            'expected_closing_profit': data.expected_closing_profit,
            'actual_closed_profit': data.actual_closed_profit,
            'expected_market_close_profit': data.expected_market_close_profit,
            'expected_closed_profit': data.expected_closed_profit,
            'expected_holding_value': data.expected_holding_value,
            'expected_total_value': data.expected_total_value,
            'actual_net_value': data.actual_net_value,
            'expected_net_value' : data.expected_net_value,
            'ave_profit_per_closed_order': data.ave_profit_per_closed_order,
        }
        self.db_connection.execute(query, params)
        # logging.info(f"Data insert into {table_name} successfully.")

    def insert_many(self, data: List[StrategyStatusBtcUSDT1mDao]):
        query = f"INSERT INTO strategy_status_btc_usdt_1m (open_time, version, price, opening_order_num, \
        opening_order_quantity, opening_order_value, closing_order_num, closing_order_quantity, closing_order_value, \
        closing_order_cost, opened_order_num, opened_order_quantity, opened_order_value, closed_order_num, \
        closed_order_quantity, closed_order_value, closed_order_cost, cumulative_opening_order_num, \
        cumulative_opening_order_quantity, cumulative_opening_order_value, cumulative_closing_order_num, \
        cumulative_closing_order_quantity, cumulative_closing_order_value, cumulative_closing_order_cost, \
        cumulative_opened_order_num, cumulative_opened_order_quantity, cumulative_opened_order_value, \
        cumulative_closed_order_num, cumulative_closed_order_quantity, cumulative_closed_order_value, \
        cumulative_closed_order_cost, cash, loan, holding_quantity, holding_value, \
        total_value, expected_closing_profit, actual_closed_profit, expected_market_close_profit, \
        expected_closed_profit, expected_holding_value, expected_total_value, actual_net_value, \
        expected_net_value, ave_profit_per_closed_order) VALUES"
        logging.info(f"sql:{query}")
        logging.info(f"data:{data}")
        self.db_connection.execute(query, data)
        logging.info(f"Data inserted into {table_name} successfully.")


def test_select():
    connector = StrategyStatusBtcUSDT1mConnector()

    from_timestamp = datetime(2023, 12, 1, 0, 0)
    to_timestamp = datetime(2023, 12, 2, 0, 0)

    result = connector.select(from_timestamp, to_timestamp)
    # 输出查询结果
    for row in result:
        logging.info(row)


def test_insert_many():
    connector = StrategyStatusBtcUSDT1mConnector()

    from_timestamp = datetime(2023, 12, 1, 0, 0)
    to_timestamp = datetime(2023, 12, 2, 0, 0)
    data: List[StrategyStatusBtcUSDT1mDao] = connector.select(from_timestamp, to_timestamp)

    # 输出查询结果
    for row in data:
        logging.info(row)

    connector.insert_many(data)


def test_insert_single():
    connector = StrategyStatusBtcUSDT1mConnector()

    data: StrategyStatusBtcUSDT1mDao = StrategyStatusBtcUSDT1mDao(
        '2023-12-01 04:03:00', 'version1', 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 23, 14, 15, 2, 3, 4, 5, 6, 7, 8, 9,
        10, 11, 12, 23, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29)
    connector.insert_single(data)

    from_timestamp = datetime(2023, 12, 1, 0, 0)
    to_timestamp = datetime(2023, 12, 2, 0, 0)
    data: List[StrategyStatusBtcUSDT1mDao] = connector.select(from_timestamp, to_timestamp)

    # 输出查询结果
    for row in data:
        logging.info(row)


if __name__ == '__main__':
    # test_select()
    test_insert_many()
    # test_insert_single()
