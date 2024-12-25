from collections import namedtuple
from datetime import datetime
from typing import List
import pandas as pd
import time

from data_collection.api.binance_api import get_binance_klines
from log import *
from data_collection.db import db

table_name = 'kline_btc_usdt_1m'

'''
Binance kline接口 返回字段解析

字段解释：
1.Open time (开盘时间)：
字段位置：[0]
类型：时间戳（毫秒）
解释：当前K线的开盘时间，表示K线开始的时间点。它是一个毫秒级的时间戳，可以转换为常见的日期时间格式。

2.Open price (开盘价)：
字段位置：[1]
类型：字符串（Decimal）
解释：当前K线的开盘价格，即K线开始时的交易价格。

3.High price (最高价)：
字段位置：[2]
类型：字符串（Decimal）
解释：当前K线的最高交易价格。在当前K线周期内，交易的最高价格。

4.Low price (最低价)：
字段位置：[3]
类型：字符串（Decimal）
解释：当前K线的最低交易价格。在当前K线周期内，交易的最低价格。

5.Close price (收盘价)：
字段位置：[4]
类型：字符串（Decimal）
解释：当前K线的收盘价格，即K线周期结束时的最后交易价格。

6.Volume (交易量)：
字段位置：[5]
类型：字符串（Decimal）
解释：当前K线周期内的交易量。它是当前K线周期内交易的总数量。

7.Close time (闭盘时间)：
字段位置：[6]
类型：时间戳（毫秒）
解释：当前K线的结束时间，表示K线周期的结束时间。它也是一个毫秒级的时间戳。

8.Quote asset volume (成交金额)：
字段位置：[7]
类型：字符串（Decimal）
解释：在当前K线周期内，以报价资产（比如 USDT）计算的交易量。例如，如果K线数据是BTC/USDT交易对，它表示的是该周期内交易的USDT总额。

9.Number of trades (交易笔数)：
字段位置：[8]
类型：整数
解释：当前K线周期内的交易次数（即交易的订单数量）。

10.Taker buy base asset volume (主动买入的基础资产数量)：
字段位置：[9]
类型：字符串（Decimal）
解释：当前K线周期内，主动买入的基础资产（如 BTC）的总量。主动买入意味着买方在订单簿的卖方价格上进行买入。

11.Taker buy quote asset volume (主动买入的报价资产数量)：
字段位置：[10]
类型：字符串（Decimal）
解释：当前K线周期内，主动买入的报价资产（如 USDT）的总量。

12.Ignore (忽略字段)：
字段位置：[11]
类型：整数（通常为0）
解释：该字段在币安API中一般不使用，可以忽略。
'''

KlineBtcUSDT1mDao = namedtuple(
    'KlineBtcUSDT1mDao',
    [
        'open_time', 'open_price', 'high_price', 'low_price', 'close_price', 'volume',
        'close_time', 'quote_asset_volume', 'num_of_trades',
        'taker_buy_base_volume', 'taker_buy_quote_volume'
    ]
)

KlineBtcUSDT1mDaoSimple = namedtuple(
    'KlineBtcUSDT1mDao',
    [
        'datetime', 'open', 'high', 'low', 'close', 'volume'
    ]
)


def from_KlineBtcUSDT1mDao_to_KlineBtcUSDT1mDaoSimple(data: KlineBtcUSDT1mDao) -> KlineBtcUSDT1mDaoSimple:
    return KlineBtcUSDT1mDaoSimple(data[0], data[1], data[2], data[3], data[4], data[5])


def from_list_KlineBtcUSDT1mDao_to_KlineBtcUSDT1mDaoSimple(data: List[KlineBtcUSDT1mDao]) -> List[
    KlineBtcUSDT1mDaoSimple]:
    result = []
    for x in data:
        result.append(from_KlineBtcUSDT1mDao_to_KlineBtcUSDT1mDaoSimple(x))
    return result


class KlineBtcUSDT1mConnector:
    def __init__(self):
        self.db_connection = db

    def select(self, from_timestamp: datetime, to_timestamp: datetime, order: str = 'ASC') -> List[KlineBtcUSDT1mDao]:
        if order != 'ASC' and order != 'DESC':
            raise ValueError('order is not ASC or DESC')
        query = f"SELECT DISTINCT * FROM kline_btc_usdt_1m WHERE open_time BETWEEN %(from_timestamp)s AND %(to_timestamp)s ORDER BY open_time {order}"
        params = {'from_timestamp': from_timestamp, 'to_timestamp': to_timestamp}
        result = self.db_connection.execute(query, params)
        return result

    def insert_single(self, data: KlineBtcUSDT1mDao):
        query = f"INSERT INTO kline_btc_usdt_1m (open_time, open_price, high_price, low_price, close_price, volume, \
            close_time, quote_asset_volume, num_of_trades,taker_buy_base_volume, taker_buy_quote_volume) \
            VALUES (%(open_time)s, %(open_price)s, %(high_price)s, %(low_price)s, %(close_price)s, %(volume)s, \
                %(close_time)s, %(quote_asset_volume)s, %(num_of_trades)s, %(taker_buy_base_volume)s, %(taker_buy_quote_volume)s)"
        params = {
            'open_time': data.open_time,
            'open_price': data.open_price,
            'high_price': data.high_price,
            'low_price': data.low_price,
            'close_price': data.close_price,
            'volume': data.volume,
            'close_time': data.close_time,
            'quote_asset_volume': data.quote_asset_volume,
            'num_of_trades': data.num_of_trades,
            'taker_buy_base_volume': data.taker_buy_base_volume,
            'taker_buy_quote_volume': data.taker_buy_quote_volume,
        }
        self.db_connection.execute(query, params)
        # logging.info(f"Data insert into kline_btc_usdt_1m successfully.")

    def insert_many(self, data: List[KlineBtcUSDT1mDao]):
        query = f"INSERT INTO kline_btc_usdt_1m (open_time, open_price, high_price, low_price, close_price, volume, \
            close_time, quote_asset_volume, num_of_trades,taker_buy_base_volume, taker_buy_quote_volume) VALUES"
        self.db_connection.execute(query, data)
        # logging.info(f"Data inserted into {table_name} successfully.")

    def last_date(self) -> datetime:
        query = f"SELECT MAX(close_time) FROM kline_btc_usdt_1m"
        result = self.db_connection.execute(query)[0][0]
        return result

    def save_dataframe_to_db(self, df: pd.DataFrame):
        tuples = [KlineBtcUSDT1mDao(
            x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5]), x[6], float(x[7]), float(x[8]),
            float(x[9]), float(x[10]),
        ) for x in df.values]
        self.insert_many(tuples)

    def collect_up2date_data(
            self, from_date:
            datetime,
            limit: int = 1000,
            sleep_pre_loop: int = 1,
            rest_every_n_loop: int = 100,
            rest_sleep_time: int = 60
    ):
        index = 0
        date_timestamp = from_date
        df = get_binance_klines(date_timestamp)
        self.save_dataframe_to_db(df)
        while len(df) == limit:
            logging.info("collection data from:" + str(date_timestamp))
            # logging.info("len(df):" + str(len(df)))
            date_timestamp = df["Close Time"].max()
            df = get_binance_klines(date_timestamp, limit=limit)
            self.save_dataframe_to_db(df)
            index += 1
            time.sleep(sleep_pre_loop)
            if index > rest_every_n_loop:
                time.sleep(rest_sleep_time)
                index = 0
        logging.info("history of kline_btc_usdt_1m is up2date")


def test_select():
    connector = KlineBtcUSDT1mConnector()

    from_timestamp = datetime(2023, 12, 1, 0, 0)
    to_timestamp = datetime(2023, 12, 2, 0, 0)

    result = connector.select(from_timestamp, to_timestamp)
    # 输出查询结果
    for row in result:
        logging.info(row)


def test_insert_many():
    connector = KlineBtcUSDT1mConnector()

    from_timestamp = datetime(2023, 12, 1, 0, 0)
    to_timestamp = datetime(2023, 12, 2, 0, 0)
    data: List[KlineBtcUSDT1mDao] = connector.select(from_timestamp, to_timestamp)

    # 输出查询结果
    for row in data:
        logging.info(row)

    connector.insert_many(data)


def test_insert_single():
    connector = KlineBtcUSDT1mConnector()

    data: KlineBtcUSDT1mDao = KlineBtcUSDT1mDao('2023-12-01 04:01:00', 1, 1, 1, 1, 1, '2023-12-01 04:02:00', 1, 1, 1, 1)
    connector.insert_single(data)

    from_timestamp = datetime(2023, 12, 1, 0, 0)
    to_timestamp = datetime(2023, 12, 2, 0, 0)
    data: List[KlineBtcUSDT1mDao] = connector.select(from_timestamp, to_timestamp)

    # 输出查询结果
    for row in data:
        logging.info(row)


def test_last_date():
    connector = KlineBtcUSDT1mConnector()
    last_date = connector.last_date()
    logging.info(last_date)


if __name__ == '__main__':
    # test_select()
    # test_insert_many()
    # test_insert_single()
    test_last_date()
