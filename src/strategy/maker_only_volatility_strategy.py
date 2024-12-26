"""
只做Maker的做多波动率交易策略
深度左侧交易
"""
import logging

from strategy import StrategyInterface
from log import *
import backtrader as bt

from strategy.order import MyOrderArray


class MakerOnlyLongOnlyVolatilityStrategy(StrategyInterface):
    """
    只做多策略
    """
    # 定义参数
    SLOT_NUM = 500  # 资产分割粒度
    PERCENTAGE_MAX_OPEN_PRICE = 0.90  # 开仓最高价格（顶部的90%）
    PERCENTAGE_MIN_OPEN_PRICE = 0.50  # 开仓最低价格（顶部的50%）
    PERCENTAGE_MAX_CLOSE_PRICE = 0.95  # 平仓最高价格（顶部的50%）
    PERCENTAGE_MIN_CLOSE_PRICE = 0.50  # 平仓最低价格（顶部的50%）

    def __init__(self):
        self.super_strategy = None  # 由backtrader注入

        self.bet_cash_size = self.get_cash() / self.SLOT_NUM  # 下单金额
        self.bat_price_step = None  # 下单价格跨度

        self.top = None  # 顶部
        self.bottom = None  # 底部

        self.max_open_price = None  # 开仓最高价格
        self.min_open_price = None  # 开仓最低价格

        self.max_close_price = None  # 平仓最高价格
        self.min_close_price = None  # 平仓最低价格

        self.order_list_open_submitted = MyOrderArray(self.SLOT_NUM)  # 订单列表：已提交开仓订单（未完成）
        self.order_list_open_completed = []  # 历史订单列表:已完成开仓订单
        self.order_list_close_submitted = MyOrderArray(self.SLOT_NUM)  # 订单列表：已提交平仓订单（未完成）
        self.order_list_close_completed = []  # 历史订单列表:已完成平仓订单

        self.order_dict_open2close = dict()  # 订单字典 将open单映射到close单
        self.order_dict_close2open = dict()  # 订单字典 将close单映射到open单

    def next(self):
        """
        每个周期（1m）的操作逻辑：
        1.self.update_param()-判断是否创新高，如果创新高则更新参数
        2.获取收盘价，保证收盘价下方有足够数量的开单，保证收盘价上方由足够数量的平单
        3.挂单时更新MyOrderArray
        :return:
        """
        logging.info(self.status())
        self.update_param()

        # 获取当前的收盘价
        current_price = self.get_price()

        # todo 挂买单 更新order_list_open_submitted
        if self.buy_order is not None:
            self.super_strategy.cancel(self.buy_order)
        # 创建限价单
        self.buy_order = self.super_strategy.buy(
            price=current_price - self.maker_price_offset,
            size=self.order_size,
            exectype=bt.Order.Limit
        )

        # todo 挂卖单 更新order_list_close_submitted
        if self.sell_order is not None:
            self.super_strategy.cancel(self.sell_order)
        # 创建限价单
        self.sell_order = self.super_strategy.buy(
            price=current_price + self.maker_price_offset,
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
            # todo 如果订单已完成 更新MyOrderArray与dict
            if order.isbuy():
                self.buy_order = None  # 清除买单状态
                self.sell_order = None  # 清除卖单状态
            elif order.issell():
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
            self.top = price
            self.bottom = price * 0.5

            self.bet_cash_size = self.get_cash() / self.SLOT_NUM  # 下单金额

            self.max_open_price = self.top * self.PERCENTAGE_MAX_OPEN_PRICE  # 开仓最高价格
            self.min_open_price = self.top * self.PERCENTAGE_MIN_OPEN_PRICE  # 开仓最低价格

            self.max_close_price = self.top * self.PERCENTAGE_MAX_CLOSE_PRICE  # 平仓最高价格
            self.min_close_price = self.top * self.PERCENTAGE_MIN_CLOSE_PRICE  # 平仓最低价格

            self.bat_price_step = (self.max_close_price - self.min_close_price) / self.SLOT_NUM  # 下单价格跨度

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
