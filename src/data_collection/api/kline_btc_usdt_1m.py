from data_collection.api import KlineInterface
from datetime import datetime
from data_collection.dao.kline_btc_spot_trading_usdt_1m import KlineBtcUSDT1mConnector, KlineBtcUSDT1mDao
from log import *
from typing import List


class KlineBTCUSDT1M(KlineInterface):
    def get_kline(self, from_date: datetime, to_date: datetime, granularity: str = '1m', order: str = 'ASC') -> List[
        KlineBtcUSDT1mDao]:
        if from_date > to_date:
            logging.error("from_date must be lower than to_date!")
            logging.error("from_date is {}".format(from_date))
            logging.error("to_date is {}".format(to_date))
            return []
        connection = KlineBtcUSDT1mConnector()
        db_last_date = connection.last_date()
        if db_last_date < to_date:
            # 历史数据不足 刷历史数据
            connection.collect_up2date_data(db_last_date)
        # 读取数据
        return connection.select(from_date, to_date, order=order)


def test():
    from_date = datetime(2024, 12, 23, 0, 0)
    to_date = datetime(2024, 12, 23, 0, 5)
    result = KlineBTCUSDT1M().get_kline(from_date=from_date, to_date=to_date)
    for row in result:
        logging.info(row[0])
    # logging.info(result)


if __name__ == '__main__':
    test()
