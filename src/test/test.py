from data_collection.dao.kline_btc_spot_trading_usdt_1m import KlineBtcUSDT1mConnector
from datetime import datetime
from log import *


connection = KlineBtcUSDT1mConnector()
first_date = datetime(2019, 5, 15, 2, 55)
connection.collect_up2date_data(first_date)