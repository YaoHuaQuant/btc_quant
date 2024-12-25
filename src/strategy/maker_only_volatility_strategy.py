"""
只做Maker的做多波动率交易策略
深度左侧交易
"""
import logging

from strategy import StrategyInterface
from datetime import datetime
from data_collection.api.kline_btc_usdt_1m import KlineBTCUSDT1M
from data_collection.dao.kline_btc_usdt_1m import from_list_KlineBtcUSDT1mDao_to_KlineBtcUSDT1mDaoSimple
from log import *
import backtrader as bt
import pandas as pd

# 0.02% 的交易手续费
COMMISSION = 0.0002
# 初始余额10000
BALANCE = 1000000
# 杠杆倍率为125
LEVERAGE = 1.0
# 开始结束如期
FROM_DATE = datetime(2024, 9, 1, 0, 0)
TO_DATE = datetime(2024, 12, 24, 0, 0)


class MakerOnlyVolatilityStrategy(StrategyInterface):
    # 定义参数
    maker_price_offset = 50  # 假设买单卖单都离当前价格0.1单位
    order_size = 0.01  # 每次挂单的大小

    def __init__(self):
        self.buy_order = None  # 用于跟踪订单
        self.sell_order = None  # 用于跟踪订单

    def next(self):
        logging.info(self.status())

        # 获取当前的收盘价
        current_price = self.data.close[0]

        # 挂买单
        if self.buy_order is not None:
            self.cancel(self.buy_order)
        # 创建限价单
        self.buy_order = self.buy(
            price=current_price - self.maker_price_offset,
            size=self.order_size,
            exectype=bt.Order.Limit
        )

        # 挂卖单
        if self.sell_order is not None:
            self.cancel(self.sell_order)
        # 创建限价单
        self.sell_order = self.buy(
            price=current_price + self.maker_price_offset,
            size=self.order_size,
            exectype=bt.Order.Limit
        )

    def notify_order(self, order):
        if order.isbuy():
            direction = "Buy"
        else:
            direction = "Sell"
        if order.status in [bt.Order.Submitted, bt.Order.Accepted]:
            # 如果订单已经提交或已接受，则跳过
            return
        if order.status in [order.Completed]:
            logging.info(
                f"Order executed: Direction: {direction},\tPrice: {order.executed.price},\tSize: {order.executed.size}")
            # 如果订单已完成，继续挂新的订单
            if order.isbuy():
                self.buy_order = None  # 清除买单状态
                self.sell_order = None  # 清除卖单状态
                # # 挂新的买单
                # self.buy_order = self.buy(
                #     price=self.data.close[0] - self.maker_price_offset,
                #     size=self.order_size,
                #     exectype=bt.Order.Limit
                # )
            elif order.issell():
                self.buy_order = None  # 清除买单状态
                self.sell_order = None  # 清除卖单状态
                # # 挂新的卖单
                # self.sell_order = self.sell(
                #     price=self.data.close[0] + self.maker_price_offset,
                #     size=self.order_size,
                #     exectype=bt.Order.Limit
                # )
        elif order.status in [order.Canceled]:
            logging.info(f"Order Canceled\tDirection: {direction}")
        elif order.status in [order.Margin]:
            logging.info(f"Order 保证金不足\tDirection: {direction}")
        elif order.status in [order.Rejected]:
            logging.info(f"Order Rejected\tDirection: {direction}")

    def status(self) -> str:
        cash_balance = self.broker.get_cash()  # 获取当前现金余额
        total_value = self.broker.get_value()  # 获取当前账户总资产（现金 + 持仓市值）
        holding_value = self.broker.get_value() - self.broker.get_cash()  # 获取当前持仓市值
        current_price = self.data.close[0]  # 当前价格
        position_size = self.position.size  # 当前持仓币量
        result = f"BTC价格:{current_price}\t现金余额:{cash_balance}\t持仓BTC数量:{position_size}\t持仓市值:{holding_value}\t总资产:{total_value}"
        return result


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
    cerebro.addstrategy(MakerOnlyVolatilityStrategy)

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
