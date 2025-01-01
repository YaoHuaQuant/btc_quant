from decimal import Decimal

from strategy import StrategyInterface
from datetime import datetime
from data_collection.api.kline_btc_usdt_1m import KlineBTCUSDT1M
from data_collection.dao.kline_btc_usdt_1m import from_list_KlineBtcUSDT1mDao_to_KlineBtcUSDT1mDaoSimple
from log import *
import backtrader as bt
import pandas as pd

from strategy.maker_only_volatility_strategy import MakerOnlyLongOnlyVolatilityStrategy

# 0.02% 的交易手续费
COMMISSION = 0.0002
# 初始余额10000
BALANCE = 1000000
# 杠杆倍率
LEVERAGE = 1.0
# 数据区间
FROM_DATE = datetime(2024, 12, 5, 4, 0)
TO_DATE = datetime(2024, 12, 6, 4, 0)


class BacktraderStrategy(bt.Strategy):
    def __init__(self, strategy: StrategyInterface):
        self.strategy = strategy
        self.strategy.commission_rate = self.broker.getcommissioninfo(self.data).p.commission
        self.strategy.super_strategy = self

    def next(self):
        self.strategy.next()

    def notify_order(self, order):
        self.strategy.notify_order(order)


def test():
    # 加载数据
    kline_data = from_list_KlineBtcUSDT1mDao_to_KlineBtcUSDT1mDaoSimple(
        KlineBTCUSDT1M().get_kline(from_date=FROM_DATE, to_date=TO_DATE)
    )
    df = pd.DataFrame(kline_data, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'], format='%Y-%m-%d %H:%M:%S')
    # logging.info(df)
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=0,
        open=1,
        high=2,
        low=3,
        close=4,
        volume=5
    )

    # 创建回测引擎
    cerebro = bt.Cerebro()

    # 加载数据到引擎
    cerebro.adddata(data)

    # 加载策略
    strategy_interface = MakerOnlyLongOnlyVolatilityStrategy()
    cerebro.addstrategy(BacktraderStrategy, strategy_interface)

    # 设置初始资金
    cerebro.broker.set_cash(BALANCE)

    # 设置佣金&杠杆倍率
    cerebro.broker.setcommission(commission=COMMISSION, leverage=LEVERAGE)

    # 运行回测
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Ending Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # 绘制结果
    cerebro.plot()


if __name__ == '__main__':
    test()
