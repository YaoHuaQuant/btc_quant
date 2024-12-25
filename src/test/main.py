import backtrader as bt
import pandas as pd


# 定义策略
class SmaCrossStrategy(bt.Strategy):
    params = (
        ('short_period', 10),  # 短期均线周期
        ('long_period', 20),  # 长期均线周期
    )

    def __init__(self):
        # 初始化指标
        self.sma_short = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.short_period)
        self.sma_long = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params.long_period)
        self.crossover = bt.indicators.CrossOver(self.sma_short, self.sma_long)

    def next(self):
        if self.crossover > 0:  # 短期均线上穿长期均线，买入
            self.buy(size=0.1)  # 假设购买 0.1 BTC
        elif self.crossover < 0:  # 短期均线下穿长期均线，卖出
            self.sell(size=0.1)


# 加载数据
data = bt.feeds.GenericCSVData(
    dataname='btc_data.csv',
    dtformat='%Y-%m-%d %H:%M:%S',
    timeframe=bt.TimeFrame.Minutes,
    compression=60,  # 1小时数据
    openinterest=-1
)

# 创建回测引擎
cerebro = bt.Cerebro()

# 加载数据到引擎
cerebro.adddata(data)

# 加载策略
cerebro.addstrategy(SmaCrossStrategy)

# 设置初始资金
cerebro.broker.set_cash(10000)  # 账户初始余额 $10,000

# 设置佣金
cerebro.broker.setcommission(commission=0.001)  # 0.1% 的交易手续费

# 运行回测
print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
cerebro.run()
print('Ending Portfolio Value: %.2f' % cerebro.broker.getvalue())

# 绘制结果
cerebro.plot()
