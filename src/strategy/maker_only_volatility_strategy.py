"""
只做Maker的做多波动率交易策略
深度左侧交易
"""
import math
import backtrader as bt

from log import *
from strategy import StrategyInterface
from strategy.order import MyOrderArrayTriple, test_my_order_pair


class MakerOnlyLongOnlyVolatilityStrategy(StrategyInterface):
    """
    只做多策略
    """
    # 定义参数
    CASH_SLOT_NUM = 500  # 资产分割粒度
    OPEN_PRICE_SLOT_NUM = 400  # 开仓挂单价位粒度
    # PERCENTAGE_MAX_OPEN_PRICE = 0.90  # 开仓最高价格（顶部的90%）
    PERCENTAGE_MAX_OPEN_PRICE = 1  # 开仓最高价格（顶部的90%）
    PERCENTAGE_MIN_OPEN_PRICE = 0.50  # 开仓最低价格（顶部的50%）
    # PERCENTAGE_MAX_CLOSE_PRICE = 0.95  # 平仓最高价格（顶部的95%）
    PERCENTAGE_MAX_CLOSE_PRICE = 1.05  # 平仓最高价格（顶部的95%）
    PERCENTAGE_MIN_CLOSE_PRICE = 0.50  # 平仓最低价格（顶部的50%）
    PERCENTAGE_MINIMUM_PROFIT = 0.002  # 最低利润百分比
    OPENING_ORDER_NUM = 20  # 盘口附近的开单数量
    CLOSING_ORDER_NUM = 20  # 盘口附近的平单数量

    def __init__(self):
        self.super_strategy: bt.Strategy | None = None  # 由backtrader注入
        self.commission_rate: float | None = None  # 由backtrader注入

        self.direction = 'long'

        self.bet_cash_size = None  # 下单金额

        self.top = None  # 顶部
        self.bottom = None  # 底部

        self.max_open_price = None  # 开仓最高价格
        self.min_open_price = None  # 开仓最低价格

        self.max_close_price = None  # 平仓最高价格
        self.min_close_price = None  # 平仓最低价格

        self.bet_price_step = None  # 开仓下单价格跨度

        self.CLOSE_PRICE_SLOT_NUM = None

        self.data: None | MyOrderArrayTriple = None

        self.open_order_price_dict = dict()  # 保存挂单的开单价格
        self.close_order_price_list = []  # 保存挂单的平单价格
        self.closed_order_list = []  # 保存已完成的订单

    def next(self):
        """
        每个周期（1m）的操作逻辑：
        1.self.update_param()-判断是否创新高，如果创新高则更新参数
        2.获取收盘价，保证收盘价下方有足够数量的开单，保证收盘价上方由足够数量的平单
        3.挂单时更新self.data
        :return:
        """
        logging.info(self)
        self.update_param()

        ####
        # open_orders = self.super_strategy.broker.get_orders_open()
        # if open_orders:
        #     print(f"Number of open orders: {len(open_orders)}")
        #     for order in open_orders:
        #         print(f"Order ID: {order.ref}, Status: {order.getstatusname()}, Type: {order.ordtypename()}")
        ####

        # 获取当前的收盘价
        current_price = self.get_price()

        # 向下挂满开单
        ## 在 open order array 上挂满开单
        open_order_array = self.data.open_order_array
        open_position = open_order_array.get_position_by_price(current_price)
        open_price = open_order_array.get_price_by_position(open_position)
        tmp_order = None
        while tmp_order is None:
            tmp_order = self.data.add_open_order(open_price=open_price, close_price=open_price,
                                                 quantity=self.bet_cash_size/current_price)
        ## 在盘口价下方挂上一定数量的开单
        for i in range(open_position, open_position + self.OPENING_ORDER_NUM):
            open_order = open_order_array.get_order_by_position(i)
            open_price = open_order.open_price
            open_quantity = open_order.quantity
            if not self.open_order_price_dict.__contains__(open_price):
                ## 创建限价单
                new_open_order = self.super_strategy.buy(
                    price=open_price,
                    size=open_quantity,
                    exectype=bt.Order.Limit
                )
                self.open_order_price_dict[open_price] = new_open_order

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
                # 开单完成 挂上平单
                ## 清除挂单
                open_price = order.price
                self.open_order_price_dict.pop(open_price)
                # quantity = order.executed.size
                ## 调整self.data
                open_order_array = self.data.open_order_array
                close_order_array = self.data.close_order_array
                open_order_position = open_order_array.get_position_by_price(open_price)
                tmp_order = open_order_array.pop(open_order_position)
                tmp_order.update_status_closing()
                if self.direction == 'long':
                    close_price = open_price * (1 + self.PERCENTAGE_MAX_OPEN_PRICE)
                else:
                    close_price = open_price * (1 - self.PERCENTAGE_MAX_OPEN_PRICE)
                tmp_order.update_close_price(close_price)
                close_order_array.add_order(order=tmp_order)
                ## 在盘口价上方挂上一定数量的平单
                ### 清除旧挂单
                for o in self.close_order_price_list:
                    self.super_strategy.cancel(o)
                ### 添加新挂单
                current_price = self.get_price()
                close_position = close_order_array.get_position_by_price(current_price)
                for i in range(close_position, close_position + self.CLOSING_ORDER_NUM):
                    close_order = close_order_array.get_order_by_position(i)
                    if close_order is not None:
                        close_price = close_order.close_price
                        close_quantity = close_order.quantity
                        ## 创建限价单
                        new_close_order = self.super_strategy.sell(
                            price=close_price,
                            size=close_quantity,
                            exectype=bt.Order.Limit
                        )
                        self.close_order_price_list.append(new_close_order)
            elif order.issell():
                # 平单完成 保存订单
                ## 调整self.data
                close_price = order.price
                close_order_array = self.data.close_order_array
                close_order_position = close_order_array.get_position_by_price(close_price)
                tmp_order = close_order_array.pop(close_order_position)
                tmp_order.update_status_closed()
                ## 保存订单
                self.closed_order_list.append(tmp_order)
        elif order.status in [order.Canceled]:
            logging.info(f"Order Canceled\tDirection: {direction}")
        elif order.status in [order.Margin]:
            logging.info(f"Order 保证金不足\tDirection: {direction}")
        elif order.status in [order.Rejected]:
            logging.info(f"Order Rejected\tDirection: {direction}")

    def __repr__(self):
        return f"{self.super_strategy.data.datetime.date()} {self.super_strategy.data.datetime.time()}\tBTC价格:{self.get_price()}\t现金余额:{self.get_cash()}\t持仓BTC数量:{self.get_position_size()}\t持仓市值:{self.get_holding_value()}\t总资产:{self.get_total_value()}"

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
