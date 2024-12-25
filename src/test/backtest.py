from datetime import datetime

from data_collection.api.kline_btc_usdt_1m import KlineBTCUSDT1M
from data_collection.dao.kline_btc_usdt_1m import from_list_KlineBtcUSDT1mDao_to_KlineBtcUSDT1mDaoSimple
from log import *

import backtrader as bt
import pandas as pd

# 0.02% 的交易手续费
COMMISSION = 0.0002
# 初始余额10000
INITIAL_BALANCE = 10000


# 定义策略
class SmaCrossStrategy(bt.Strategy):
    params = (
        ('short_period', 10*60),  # 短期均线周期
        ('long_period', 20*60),  # 长期均线周期
    )

    def __init__(self):
        # 初始化指标
        self.sma_short = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.short_period)
        self.sma_long = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.long_period)
        self.crossover = bt.indicators.CrossOver(self.sma_short, self.sma_long)

    def next(self):
        logging.info(self.status())

        if self.crossover > 0:  # 短期均线上穿长期均线，买入
            self.buy(size=0.1)  # 假设购买 0.1 BTC
            logging.info("购买 0.1 BTC")
        elif self.crossover < 0:  # 短期均线下穿长期均线，卖出
            self.sell(size=0.1)
            logging.info("出售 0.1 BTC")

    def status(self) -> str:
        cash_balance = self.broker.get_cash()  # 获取当前现金余额
        total_value = self.broker.get_value()  # 获取当前账户总资产（现金 + 持仓市值）
        holding_value = self.broker.get_value() - self.broker.get_cash()  # 获取当前持仓市值
        result = f"现金余额:\t{cash_balance}\t总资产:\t{total_value}\t持仓市值:\t{holding_value}"
        return result


def test():
    # 加载数据
    # data = bt.feeds.GenericCSVData(
    #     dataname='btc_data.csv',
    #     dtformat='%Y-%m-%d %H:%M:%S',
    #     timeframe=bt.TimeFrame.Minutes,
    #     compression=60,  # 1小时数据
    #     openinterest=-1
    # )
    # logging.info(data)

    from_date = datetime(2024, 11, 24, 0, 0)
    to_date = datetime(2024, 12, 24, 0, 0)
    kline_data = from_list_KlineBtcUSDT1mDao_to_KlineBtcUSDT1mDaoSimple(
        KlineBTCUSDT1M().get_kline(from_date=from_date, to_date=to_date)
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
    cerebro.addstrategy(SmaCrossStrategy)

    # 设置初始资金
    cerebro.broker.set_cash(INITIAL_BALANCE)

    # 设置佣金
    cerebro.broker.setcommission(commission=COMMISSION)

    # 运行回测
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Ending Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # 绘制结果
    cerebro.plot()


if __name__ == '__main__':
    test()
