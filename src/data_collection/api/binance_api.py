from datetime import datetime

import requests
import pandas as pd

proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}

'''
limit:返回值数量 最小500 最大1000
'''


def get_binance_klines(start_time: datetime, symbol='BTCUSDT', interval='1m', limit: int = 1000) -> pd.DataFrame:
    url = 'https://api.binance.com/api/v3/klines'
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
