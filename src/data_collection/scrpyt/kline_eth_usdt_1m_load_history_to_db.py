from data_collection.dao.kline_eth_spot_trading_usdt_1m import KlineEthUSDT1mConnector
from datetime import datetime
from log import *


def scrypt(first_date: datetime = datetime(2020, 1, 1, 0, 0)):
    connection = KlineEthUSDT1mConnector()
    logging.info(f'first_date {first_date}')
    last_date = connection.last_date()
    logging.info(f'last_date {last_date}')
    if last_date > first_date:
        first_date = last_date
    connection.collect_up2date_data(first_date)


if __name__ == '__main__':
    # test()
    # first_date = datetime(2020, 1, 1, 0, 0)
    scrypt()
