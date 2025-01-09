# -*- coding: utf-8 -*-

"""
只做Maker的做多波动率交易策略
深度左侧交易
"""
import logging
import math

import backtrader as bt

from log import *
from strategy import StrategyInterface
from strategy.maker_only_volatility_strategy.order_scheduler import OrderScheduler
from strategy.virtual_order import VirtualOrderOne
from strategy.maker_only_volatility_strategy.order_book import PriceOrderGroupVirtualOrderBook


class MakerOnlyLongOnlyVolatilityStrategy(StrategyInterface):
    """
    只做多策略
    """
    # 定义参数
    CASH_SLOT_NUM = 2000  # 资产分割粒度
    OPEN_PRICE_SLOT_NUM = 400  # 开仓挂单价位粒度
    # PERCENTAGE_MAX_OPEN_PRICE = 0.90  # 开仓最高价格（顶部的90%）
    PERCENTAGE_MAX_OPEN_PRICE = 0.95  # 开仓最高价格（顶部的95%）
    # PERCENTAGE_MIN_OPEN_PRICE = 0.50  # 开仓最低价格（顶部的50%）
    PERCENTAGE_MIN_OPEN_PRICE = 0.55  # 开仓最低价格（顶部的55%）
    # PERCENTAGE_MAX_CLOSE_PRICE = 0.95  # 平仓最高价格（顶部的95%）
    PERCENTAGE_MAX_CLOSE_PRICE = 1.00  # 平仓最高价格（顶部的100%）
    # PERCENTAGE_MIN_CLOSE_PRICE = 0.50  # 平仓最低价格（顶部的50%）
    PERCENTAGE_MIN_CLOSE_PRICE = 0.55  # 平仓最低价格（顶部的55%）
    PERCENTAGE_MINIMUM_PROFIT = 0.002  # 最低利润百分比
    PERCENTAGE_CLOSE_PRICE_STEP = 0.001  # 即close_price调整比例
    PERCENTAGE_MAXIMUM_PROFIT = 0.01  # 最高利润百分比
    OPENING_ORDER_NUM = 20  # 盘口附近的开单数量
    LEVERAGE = 100  # 杠杆率

    # CLOSING_ORDER_NUM = 20  # 盘口附近的平单数量

    def __init__(self):
        self.super_strategy: bt.Strategy | None = None  # 由backtrader注入
        self.order_scheduler: OrderScheduler | None = None  # 由backtrader注入
        self.order_book: PriceOrderGroupVirtualOrderBook | None = None  # 由self.update_param()生成
        self.commission_rate: float | None = None  # 由backtrader注入

        # 杠杆相关
        self.principal = 0  # 本金
        self.loan = 0  # 借贷资金

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

        # 分析数据
        self.closed_order_list = []  # 保存已完成的订单 MyOrderPair类型 用于数据统计
        ## 挂单数据
        self.opening_amount: float = 0  # 开仓挂单BTC总量
        self.opening_value: float = 0  # 开仓挂单BTC总价
        self.closing_amount: float = 0  # 平仓挂单BTC总量
        self.closing_value: float = 0  # 平仓挂单BTC总价(期望持仓市值)
        self.closing_cost: float = 0  # 平仓挂单BTC成本 = sum(每单BTC总量 * 每单开仓挂单价格)
        ## 成交数据
        self.opening_amount_finished: float = 0  # 已成交的开仓挂单BTC总量
        self.opening_value_finished: float = 0  # 已成交的开仓挂单BTC总价
        self.closing_amount_finished: float = 0  # 已成交的平仓挂单BTC总量
        self.closing_value_finished: float = 0  # 已成交的平仓挂单BTC总价
        self.closing_cost_finished: float = 0  # 已成交的平仓挂单BTC成本 = sum(每单BTC总量 * 每单开仓挂单价格)
        ## 期望数据
        # self.expected_profit: float = 0  # 期望未成交收益 = 平仓挂单BTC总价 - 平仓挂单BTC成本
        # self.expected_holding_value: float = 0  # 期望持仓市值 = 平仓挂单BTC总价
        # self.expected_total_value: float = 0  # 期望总资产 = 现金余额 + 期望持仓市值（平仓挂单BTC总价）
        # self.not_yet_achieved_profit: float = 0  # 尚未达到的收益 = 平仓挂单BTC总价 - 持仓市值
        # self.actual_profit: float = 0  # 实际已成交收益 = 已成交的平仓挂单BTC总价 - 已成交的平仓挂单BTC成本
        # self.market_sell_profit: float = 0 # 市价平仓收益 = sum((市价 - 每单开仓挂单价格) * 每单BTC总量）

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

        # 获取当前的收盘价
        current_price = self.get_price()

        # self.debug_log()
        # 向下挂满开单
        open_order_array = self.order_book.open_order_array
        current_position = self.order_book.open_order_array.get_position_by_price(current_price)

        for position_diff in range(0, self.OPENING_ORDER_NUM):
            open_position = current_position + position_diff
            if (
                    0 <= open_position <= self.OPEN_PRICE_SLOT_NUM  # 判断position是否合法
                    and self.get_cash() >= self.bet_cash_size  # 判断现金是否足够
            ):
                open_price = open_order_array.get_price_by_position(open_position)
                leverage = self.get_leverage_by_price(open_price)  # 计算杠杆率
                loan = self.bet_cash_size * (leverage - 1)  # 需要借入的资金量
                quantity = self.bet_cash_size / current_price * leverage  # 计算带杠杆的买入BTC总量
                # 向 virtual_open_order_array 上挂开单
                virtual_order = self.order_book.add_order(
                    VirtualOrderOne(
                        open_price=open_price,
                        close_price=open_price,
                        quantity=quantity,
                        direction=self.direction,
                        leverage=leverage
                    )
                )
                # 生成 actual_order
                if virtual_order is not None:
                    # 借入杠杆资金
                    self.loan += loan
                    self.super_strategy.broker.add_cash(loan)
                    # 创建限价单
                    open_price = virtual_order.open_price
                    open_quantity = virtual_order.quantity
                    actual_order = self.super_strategy.buy(
                        price=open_price,
                        size=open_quantity,
                        exectype=bt.Order.Limit
                    )
                    # 用于数据统计
                    self.analysis_add_open_order(open_price=open_price, quantity=open_quantity)
                    # logging.info(f"Order Placed\tDirection: Buy,\tPrice: {new_open_order.price},\tSize: {new_open_order.size}")

                    # order_scheduler
                    self.order_scheduler.bind(virtual_order=virtual_order, actual_order=actual_order)
        # self.debug_log()

    def debug_log(self):
        # debug 输出当前挂单
        open_orders = self.super_strategy.broker.get_orders_open()
        if open_orders:
            order_num = len(open_orders)
            buy_order_num = 0
            sell_order_num = 0
            for order in open_orders:
                if order.isbuy():
                    buy_order_num += 1
                else:
                    sell_order_num += 1
            logging.info(f"order_num:{order_num}, buy_order_num:{buy_order_num}, sell_order_num:{sell_order_num}")

    def notify_order(self, order: bt.Order):
        if order.isbuy():
            direction = "Buy"
        else:
            direction = "Sell"
        if order.status in [bt.Order.Submitted, bt.Order.Accepted]:
            # 如果订单已经提交或已接受，则跳过
            return
        if order.status in [order.Completed]:
            # logging.info(f"Order executed: Direction: {direction},\tPrice: {order.price},\tSize: {order.size}")
            # self.debug_log()
            # 如果订单已完成
            if order.isbuy():
                # 开单完成 挂上平单
                # open_price = order.price
                virtual_order = self.order_scheduler.actual_buy_finished(order)

                ## 数据统计用 - START
                self.analysis_remove_open_order(
                    open_price=virtual_order.open_price, close_price=virtual_order.close_price, quantity=order.size
                )
                self.analysis_add_close_order(
                    open_price=virtual_order.open_price, close_price=virtual_order.close_price, quantity=order.size
                )
                ## 数据统计用 - END

            elif order.issell():
                # 平单完成 保存订单
                virtual_order = self.order_scheduler.actual_sell_finished(order)
                # 调整借贷资金
                loan = virtual_order.loan
                self.loan -= loan
                self.super_strategy.broker.add_cash(-loan)

                ## 数据统计用 - START
                if order.price is not None:
                    self.analysis_remove_close_order(
                        open_price=virtual_order.open_price, close_price=virtual_order.close_price, quantity=order.size
                    )
                    self.analysis_add_closed_order(
                        open_price=virtual_order.open_price, close_price=virtual_order.close_price, quantity=order.size
                    )
                ## 数据统计用 - END
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # if order.status in [order.Canceled]:
            #     logging.info(f"Order Canceled\tDirection: {direction},\tPrice: {order.price},\tSize: {order.size}")
            # elif order.status in [order.Margin]:
            #     logging.info(f"Order 保证金不足\tDirection: {direction},\tPrice: {order.price},\tSize: {order.size}")
            # elif order.status in [order.Rejected]:
            #     logging.info(f"Order Rejected\tDirection: {direction},\tPrice: {order.price},\tSize: {order.size}")
            # 订单回撤 调整借贷资金
            if order.isbuy():
                virtual_order = self.order_scheduler.actual_order_cancelled(order)
                loan = virtual_order.loan
                self.loan -= loan
                self.super_strategy.broker.add_cash(-loan)

    def update_param(self):
        """
        更新所有参数
        当self.top不存在，或者当前价格大于self.top时，更新所有参数
        默认当前价格大于self.top时，没有任何close order
        :return:
        """
        price = self.get_price()
        # 当价格创新高时更新参数
        if self.top is None or self.top < price:
            # 更新参数
            self.principal = self.get_cash() - self.loan  # 本金

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
                * self.OPEN_PRICE_SLOT_NUM
                / (self.max_open_price - self.min_open_price)
            )
            # 重构数据结构
            direction = 'long'
            order_book = PriceOrderGroupVirtualOrderBook(
                max_open_price=self.max_open_price,
                min_open_price=self.min_open_price,
                max_close_price=self.max_close_price,
                min_close_price=self.min_close_price,
                direction=direction,
                open_array_length=self.OPEN_PRICE_SLOT_NUM,
                close_array_length=self.CLOSE_PRICE_SLOT_NUM,
                percentage_minimum_profit=self.PERCENTAGE_MINIMUM_PROFIT,
                percentage_close_price_step=self.PERCENTAGE_CLOSE_PRICE_STEP,
                percentage_maximum_profit=self.PERCENTAGE_MAXIMUM_PROFIT
            )
            self.order_book = order_book
            self.order_scheduler.link_order_book(order_book)
            # self.data = MyOrderArrayTriple(
            #     max_open_price=self.max_open_price, min_open_price=self.min_open_price,
            #     max_close_price=self.max_close_price, min_close_price=self.min_close_price,
            #     open_array_length=self.OPEN_PRICE_SLOT_NUM, close_array_length=self.CLOSE_PRICE_SLOT_NUM,
            #     direction=direction, commission_rate=self.commission_rate
            # )
            # 清除所有订单
            open_orders = self.super_strategy.broker.get_orders_open()
            if open_orders:
                for order in open_orders:
                    self.super_strategy.cancel(order)

    def analysis_add_open_order(self, open_price: float, quantity: float):
        """用于分析"""
        ## 挂单数据
        self.opening_amount += abs(quantity)  # 开仓挂单BTC总量
        self.opening_value += abs(quantity) * open_price  # 开仓挂单BTC总价

    def analysis_remove_open_order(self, open_price: float, close_price: float, quantity: float):
        """用于分析"""
        ## 挂单数据
        self.opening_amount -= abs(quantity)  # 开仓挂单BTC总量
        self.opening_value -= abs(quantity) * open_price  # 开仓挂单BTC总价
        ## 成交数据
        self.opening_amount_finished += abs(quantity)  # 已成交的开仓挂单BTC总量
        self.opening_value_finished += abs(quantity) * open_price  # 已成交的开仓挂单BTC总价

    def analysis_add_close_order(self, open_price: float, close_price: float, quantity: float):
        """用于分析"""
        ## 挂单数据
        self.closing_amount += abs(quantity)  # 平仓挂单BTC总量
        self.closing_value += abs(quantity) * close_price  # 平仓挂单BTC总价(期望持仓市值)
        self.closing_cost += abs(quantity) * open_price  # 平仓挂单BTC成本 = sum(每单BTC总量 * 每单开仓挂单价格)

    def analysis_remove_close_order(self, open_price: float, close_price: float, quantity: float,
                                    market_price: float = None):
        """用于分析"""
        if market_price is not None:
            close_price_finish = market_price
        else:
            close_price_finish = close_price
        ## 挂单数据
        self.closing_amount -= abs(quantity)  # 平仓挂单BTC总量
        self.closing_value -= abs(quantity) * close_price  # 平仓挂单BTC总价(期望持仓市值)
        self.closing_cost -= abs(quantity) * open_price  # 平仓挂单BTC成本 = sum(每单BTC总量 * 每单开仓挂单价格)
        ## 成交数据
        self.closing_amount_finished += abs(quantity)  # 已成交的平仓挂单BTC总量
        self.closing_value_finished += abs(quantity) * close_price_finish  # 已成交的平仓挂单BTC总价
        self.closing_cost_finished += abs(quantity) * open_price  # 已成交的平仓挂单BTC成本 = sum(每单BTC总量 * 每单开仓挂单价格)

    def analysis_add_closed_order(self, open_price: float, close_price: float, quantity: float,
                                  market_price: float = None):
        """用于分析"""
        if market_price is not None:
            close_price = market_price
        virtual_order = VirtualOrderOne(
            open_price=open_price, close_price=close_price,
            quantity=abs(quantity),
            commission_rate=self.commission_rate,
            direction=self.direction,
        )
        virtual_order.update_status_closing()
        virtual_order.update_status_closed()
        self.closed_order_list.append(virtual_order)

    def get_leverage_by_price(self, open_price: float) -> float:
        """
        给定open_price，计算杠杆率
        :param open_price:
        :return: 杠杆率
        """
        if open_price <= self.min_open_price:
            raise ValueError(f"Error open_price: {open_price} must be greater than {self.min_open_price}")
        else:
            return min(open_price / (open_price - self.min_open_price), self.LEVERAGE)

    def __repr__(self):
        cash = self.get_cash()  # 现金余额
        expected_holding_value = self.get_expected_holding_value()  # 期望持仓市值
        expected_total_value = self.get_expected_total_value()  # 期望总资产
        expected_profit = self.get_expected_profit()  # 期望未成交收益
        actual_profit = self.get_actual_profit()  # 实际已成交收益
        market_close_profit = self.closing_amount * self.get_price() - self.closing_value  # 平仓挂单亏损：平仓挂单BTC量*BTC价格 - 平仓挂单BTC总价
        closed_order_num = len(self.closed_order_list)  # 已成交订单数
        net_value = self.get_total_value() - self.loan  # 净资产 = 总资产 - 借贷资金
        expected_net_value = net_value - market_close_profit  # 期望净资产 = 净资产 - 平仓挂单亏损
        if closed_order_num == 0:
            ave_profit_per_order = 0
        else:
            ave_profit_per_order = actual_profit / closed_order_num  # 平均每单盈利

        # 爆仓判断：净资产 <= 0
        if net_value <= 0:
            logging.error(
                f"WARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\tWARNING 爆仓\t")
        ##
        # self.closing_value # 平仓挂单BTC总价
        # self.closing_cost # 平仓挂单BTC成本
        # self.expected_profit: float = 0  # 期望未成交收益 = 平仓挂单BTC总价 - 平仓挂单BTC成本
        # self.expected_holding_value: float = 0  # 期望持仓市值 = 平仓挂单BTC总价
        # self.expected_total_value: float = 0  # 期望总资产 = 现金余额 + 期望持仓市值（平仓挂单BTC总价）
        # self.not_yet_achieved_profit: float = 0  # 尚未达到的收益 = 平仓挂单BTC总价 - 持仓市值
        # self.actual_profit: float = 0  # 实际已成交收益 = 已成交的平仓挂单BTC总价 - 已成交的平仓挂单BTC成本
        return (
                f"{self.super_strategy.data.datetime.date()} {self.super_strategy.data.datetime.time()}\t" +
                f"BTC价格:{self.get_price():.2f}\t" +
                f"净资产:{net_value:.2f}\t期望净资产:{expected_net_value:.2f}\t"
                f"现金余额:{cash:.2f}\t本金:{self.principal:.2f}\t持仓BTC数量:{self.get_position_size():.4f}\t" +
                f"借贷资金:{self.loan:.2f}\t" +
                f"期望总资产:{expected_total_value:.2f}\t总资产:{self.get_total_value():.2f}\t" +
                f"期望持仓市值:{expected_holding_value:.2f}\t实际持仓市值:{self.get_holding_value():.2f}\t" +
                f"期望未成交收益:{expected_profit:.2f}\t实际已成交收益:{actual_profit:.2f}\t" +
                # f"平仓挂单BTC总价:{self.closing_value:2f}\t平仓挂单BTC成本:{self.closing_cost:2f}\t" +
                f"市价平仓亏损:{market_close_profit:.2f}\t" +
                f"已成交订单数:{closed_order_num}\t平均每单盈利:{ave_profit_per_order:.5f}\t"
        )

    def init(self, super_strategy: bt.Strategy):
        self.commission_rate = super_strategy.broker.getcommissioninfo(super_strategy.data).p.commission
        self.super_strategy = super_strategy
        self.order_scheduler = OrderScheduler(super_strategy)
        self.principal = self.get_cash()  # 本金

    def get_price(self):
        """获取当前BTC价格"""
        return self.super_strategy.data.close[0]

    def get_cash(self):
        """获取当前可用现金余额"""
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

    def get_expected_profit(self) -> float:
        """
        用于分析
        期望未成交收益 = 平仓挂单BTC总价 - 平仓挂单BTC成本
        """
        return self.closing_value - self.closing_cost

    def get_expected_holding_value(self) -> float:
        """
        用于分析
        期望持仓市值 = 平仓挂单BTC总价
        """
        return self.closing_value

    def get_expected_total_value(self) -> float:
        """
        用于分析
        期望总资产 = 现金余额 + 期望持仓市值（平仓挂单BTC总价）
        """
        return self.get_cash() + self.closing_value

    def get_not_yet_achieved_profit(self) -> float:
        """
        用于分析
        尚未达到的收益 = 平仓挂单BTC总价 - 持仓市值
        """
        return self.closing_value - self.get_holding_value()

    def get_actual_profit(self) -> float:
        """
        用于分析
        实际已成交收益 = 已成交的平仓挂单BTC总价 - 已成交的平仓挂单BTC成本
        """
        return self.closing_value_finished - self.closing_cost_finished


def test_strategy():
    from trade.backtesting import by_backtrader
    by_backtrader.test()


if __name__ == '__main__':
    test_strategy()
