"""
只做Maker的做多波动率交易策略
深度左侧交易
"""
from strategy import StrategyInterface
from log import *
import backtrader as bt



class MakerOnlyVolatilityStrategy(StrategyInterface):
    # 定义参数
    maker_price_offset = 50  # 假设买单卖单都离当前价格0.1单位
    order_size = 0.01  # 每次挂单的大小

    def __init__(self):
        self.buy_order = None  # 用于跟踪订单
        self.sell_order = None  # 用于跟踪订单
        self.super_strategy = None

    def next(self):
        logging.info(self.status())

        # 获取当前的收盘价
        current_price = self.super_strategy.data.close[0]

        # 挂买单
        if self.buy_order is not None:
            self.super_strategy.cancel(self.buy_order)
        # 创建限价单
        self.buy_order = self.super_strategy.buy(
            price=current_price - self.super_strategy.maker_price_offset,
            size=self.super_strategy.order_size,
            exectype=bt.Order.Limit
        )

        # 挂卖单
        if self.sell_order is not None:
            self.super_strategy.cancel(self.sell_order)
        # 创建限价单
        self.sell_order = self.super_strategy.buy(
            price=current_price + self.super_strategy.maker_price_offset,
            size=self.super_strategy.order_size,
            exectype=bt.Order.Limit
        )

    def notify_order(self, order: bt.Order):
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
        cash_balance = self.super_strategy.broker.get_cash()  # 获取当前现金余额
        total_value = self.super_strategy.broker.get_value()  # 获取当前账户总资产（现金 + 持仓市值）
        holding_value = self.super_strategy.broker.get_value() - self.super_strategy.broker.get_cash()  # 获取当前持仓市值
        current_price = self.super_strategy.data.close[0]  # 当前价格
        position_size = self.super_strategy.position.size  # 当前持仓币量
        result = f"BTC价格:{current_price}\t现金余额:{cash_balance}\t持仓BTC数量:{position_size}\t持仓市值:{holding_value}\t总资产:{total_value}"
        return result


def test():
    from trade.backtesting import by_backtrader
    by_backtrader.test()


if __name__ == '__main__':
    test()
