"""
只做Maker的做多波动率交易策略
深度左侧交易
"""
import math

import backtrader as bt

from log import *
from strategy import StrategyInterface
from strategy.order import MyOrderArrayTriple


class MakerOnlyLongOnlyVolatilityStrategy(StrategyInterface):
    """
    只做多策略
    """
    # 定义参数
    CASH_SLOT_NUM = 500  # 资产分割粒度
    OPEN_PRICE_SLOT_NUM = 400  # 开仓挂单价位粒度
    PERCENTAGE_MAX_OPEN_PRICE = 0.90  # 开仓最高价格（顶部的90%）
    PERCENTAGE_MIN_OPEN_PRICE = 0.50  # 开仓最低价格（顶部的50%）
    PERCENTAGE_MAX_CLOSE_PRICE = 0.95  # 平仓最高价格（顶部的95%）
    PERCENTAGE_MIN_CLOSE_PRICE = 0.50  # 平仓最低价格（顶部的50%）

    def __init__(self):
        self.super_strategy = None  # 由backtrader注入
        self.commission_rate = 0.0002  # todo 从backtrader注入

        self.bet_cash_size = self.get_cash() / self.CASH_SLOT_NUM  # 下单金额

        self.top = None  # 顶部
        self.bottom = None  # 底部

        self.max_open_price = None  # 开仓最高价格
        self.min_open_price = None  # 开仓最低价格

        self.max_close_price = None  # 平仓最高价格
        self.min_close_price = None  # 平仓最低价格

        self.bet_price_step = None  # 开仓下单价格跨度

        self.CLOSE_PRICE_SLOT_NUM = None

        self.data: None | MyOrderArrayTriple = None

        self.closed_order_list = [] # 保存已完成的订单

    def next(self):
        """
        每个周期（1m）的操作逻辑：
        1.self.update_param()-判断是否创新高，如果创新高则更新参数
        2.获取收盘价，保证收盘价下方有足够数量的开单，保证收盘价上方由足够数量的平单
        3.挂单时更新self.data
        :return:
        """
        logging.info(self.status())
        self.update_param()

        # 获取当前的收盘价
        current_price = self.get_price()

        # todo 向下挂满开单
        if self.buy_order is not None:
            self.super_strategy.cancel(self.buy_order)
        # 创建限价单
        self.buy_order = self.super_strategy.buy(
            price=current_price - self.maker_price_offset,
            size=self.order_size,
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
            # 如果订单已完成
            if order.isbuy():
                # todo 开单完成 挂上平单
                self.buy_order = None  # 清除买单状态
                self.sell_order = None  # 清除卖单状态
            elif order.issell():
                # todo 平单完成 保存订单
                self.buy_order = None  # 清除买单状态
                self.sell_order = None  # 清除卖单状态
        elif order.status in [order.Canceled]:
            logging.info(f"Order Canceled\tDirection: {direction}")
        elif order.status in [order.Margin]:
            logging.info(f"Order 保证金不足\tDirection: {direction}")
        elif order.status in [order.Rejected]:
            logging.info(f"Order Rejected\tDirection: {direction}")

    def status(self) -> str:
        cash_balance = self.get_cash()  # 获取当前现金余额
        total_value = self.get_total_value()  # 获取当前账户总资产（现金 + 持仓市值）
        holding_value = self.get_holding_value()  # 获取当前持仓市值
        current_price = self.get_price()  # 当前价格
        position_size = self.get_position_size()  # 当前持仓币量
        result = f"BTC价格:{current_price}\t现金余额:{cash_balance}\t持仓BTC数量:{position_size}\t持仓市值:{holding_value}\t总资产:{total_value}"
        return result

    def update_param(self):
        """
        更新所有参数
        当self.top不存在，或者当前价格大于self.top时，更新所有参数
        默认当前价格大于self.top时，没有任何close order
        :return:
        """
        price = self.get_price()
        if self.top is None or self.top < price:
            # 更新参数
            self.top = price
            self.bottom = price * 0.5

            self.bet_cash_size = self.get_cash() / self.CASH_SLOT_NUM  # 下单金额

            self.max_open_price = self.top * self.PERCENTAGE_MAX_OPEN_PRICE  # 开仓最高价格
            self.min_open_price = self.top * self.PERCENTAGE_MIN_OPEN_PRICE  # 开仓最低价格

            self.max_close_price = self.top * self.PERCENTAGE_MAX_CLOSE_PRICE  # 平仓最高价格
            self.min_close_price = self.top * self.PERCENTAGE_MIN_CLOSE_PRICE  # 平仓最低价格

            self.bet_price_step = (self.max_open_price - self.min_open_price) / self.OPEN_PRICE_SLOT_NUM  # 下单价格跨度

            self.CLOSE_PRICE_SLOT_NUM = math.floor(
                (self.max_close_price - self.min_close_price)
                * (self.max_open_price - self.min_open_price)
                / self.OPEN_PRICE_SLOT_NUM
            )
            # # 保存已完成的订单
            # if self.data is not None:
            #     self.closed_order_list.append(self.data.closed_order_array)
            # 重构数据结构
            direction = 'long'
            self.data = MyOrderArrayTriple(
                max_open_price=self.max_open_price, min_open_price=self.min_open_price,
                max_close_price=self.max_close_price, min_close_price=self.min_close_price,
                open_array_length=self.OPEN_PRICE_SLOT_NUM, close_array_length=self.CLOSE_PRICE_SLOT_NUM,
                direction=direction, commission_rate=self.commission_rate
            )

    def get_price(self):
        """获取当前BTC价格"""
        return self.super_strategy.data.close[0]

    def get_cash(self):
        """获取当前现金余额"""
        return self.super_strategy.broker.get_cash()

    def get_total_value(self):
        """获取当前账户总资产（现金 + 持仓市值）"""
        return self.super_strategy.broker.get_value()

    def get_holding_value(self):
        """获取当前持仓市值"""
        return self.get_total_value() - self.get_cash()

    def get_position_size(self):
        """当前持仓币量"""
        return self.super_strategy.position.size


def test_strategy():
    from trade.backtesting import by_backtrader
    by_backtrader.test()


if __name__ == '__main__':
    test_strategy()
