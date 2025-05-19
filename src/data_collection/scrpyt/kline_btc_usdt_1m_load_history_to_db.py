from data_collection.dao.kline_btc_spot_trading_usdt_1m import KlineBtcUSDT1mConnector
from datetime import datetime
from log import *


def scrypt(first_date: datetime = datetime(2020, 1, 1, 0, 0)):
    connection = KlineBtcUSDT1mConnector()
    logging.info(f'first_date {first_date}')
    last_date = connection.last_date()
    logging.info(f'last_date {last_date}')
    # if last_date > first_date:
    #     first_date = last_date
    first_date = datetime(2019, 5, 15, 2, 55)
    connection.collect_up2date_data(first_date)


if __name__ == '__main__':
    # test()
    # first_date = datetime(2020, 1, 1, 0, 0)
    scrypt()
