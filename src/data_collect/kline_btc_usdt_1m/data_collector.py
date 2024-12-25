import logging
import time
from datetime import datetime

import requests
import pandas as pd

from data_collect.kline_btc_usdt_1m.db_connector import KlineBtcUSDT1mConnector, KlineBtcUSDT1mDao

proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
url = 'https://api.binance.com/api/v3/klines'

'''
limit:返回值数量 最小500 最大1000
'''


def get_binance_klines(start_time: datetime, symbol='BTCUSDT', interval='1m',
                       limit: int = 1000) -> pd.DataFrame:
    params = {
        'symbol': symbol,
        'interval': interval,
        'startTime': int(start_time.timestamp() * 1000),
        'limit': limit
    }
    response = requests.get(url, params=params, proxies=proxies)
    data = response.json()
    # print("data:")
    # print(data)
    df = pd.DataFrame(data, columns=[
        'Open Time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close Time', 'Quote Asset Volume', 'Number of Trades',
        'Taker Buy Base Volume', 'Taker Buy Quote Volume', 'Ignore'
    ])
    df['Open Time'] = pd.to_datetime(df['Open Time'], unit='ms')
    df['Close Time'] = pd.to_datetime(df['Close Time'], unit='ms')

    # 将'Open Time'列指定为索引
    # df.set_index('Open Time', inplace=True)

    return df[['Open Time', 'Open', 'High', 'Low', 'Close', 'Volume',
               'Close Time', 'Quote Asset Volume', 'Number of Trades',
               'Taker Buy Base Volume', 'Taker Buy Quote Volume']]


def save_dataframe_to_db(df: pd.DataFrame):
    connection = KlineBtcUSDT1mConnector()
    tuples = [KlineBtcUSDT1mDao(
        x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5]), x[6], float(x[7]), float(x[8]),
        float(x[9]), float(x[10]),
    ) for x in df.values]
    # logging.info(tuples)
    # logging.info(type(tuples))
    connection.insert_many(tuples)


def collet_update_data(from_date: datetime, limit: int = 1000, max_loop: int = 100) -> bool:
    index = 0
    date_timestamp = from_date
    df = get_binance_klines(date_timestamp)
    while len(df) == limit:
        logging.info("date_timestamp:" + str(date_timestamp))
        logging.info("len(df):" + str(len(df)))
        save_dataframe_to_db(df)
        date_timestamp = df["Close Time"].max()
        df = get_binance_klines(date_timestamp, limit=limit)
        index += 1
        time.sleep(2)
        if index > max_loop:
            return True
    return False


def test():
    df = get_binance_klines(datetime(2020, 1, 1, 0, 0))
    save_dataframe_to_db(df)


if __name__ == '__main__':
    # test()
    # first_date = datetime(2020, 1, 1, 0, 0)
    flag = True
    while flag:
        first_date = KlineBtcUSDT1mConnector().last_date()
        flag = collet_update_data(first_date)
        logging.info("rest for 60 seconds")
        time.sleep(60)

