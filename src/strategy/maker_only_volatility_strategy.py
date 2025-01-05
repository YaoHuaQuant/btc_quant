"""
只做Maker的做多波动率交易策略
深度左侧交易
"""
import logging
import math
from typing import Dict

import backtrader as bt

from log import *
from strategy import StrategyInterface
from strategy.order_array_triple import MyOrderArrayTriple, VirtualOrder


class MakerOnlyLongOnlyVolatilityStrategy(StrategyInterface):
    """
    只做多策略
    """
    # 定义参数
    CASH_SLOT_NUM = 1000  # 资产分割粒度
    OPEN_PRICE_SLOT_NUM = 800  # 开仓挂单价位粒度
    # PERCENTAGE_MAX_OPEN_PRICE = 0.90  # 开仓最高价格（顶部的90%）
    PERCENTAGE_MAX_OPEN_PRICE = 0.99  # 开仓最高价格（顶部的90%）
    # PERCENTAGE_MIN_OPEN_PRICE = 0.50  # 开仓最低价格（顶部的50%）
    PERCENTAGE_MIN_OPEN_PRICE = 0.59  # 开仓最低价格（顶部的50%）
    # PERCENTAGE_MAX_CLOSE_PRICE = 0.95  # 平仓最高价格（顶部的95%）
    PERCENTAGE_MAX_CLOSE_PRICE = 1.04  # 平仓最高价格（顶部的95%）
    # PERCENTAGE_MIN_CLOSE_PRICE = 0.50  # 平仓最低价格（顶部的50%）
    PERCENTAGE_MIN_CLOSE_PRICE = 0.59  # 平仓最低价格（顶部的50%）
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

        self.open_order_price_dict = dict()  # 价格->bt.order映射，用于判断每个价位是否已有订单: key为价格 value为order对象
        self.close_order_price_dict = dict()  # 价格->bt.order映射，用于判断每个价位是否已有订单: key为价格 value为order对象
        self.price_map_close2open = dict()  # close价格->open价格映射，用于查找对应close价格的open成本价格
        self.closed_order_list = []  # 保存已完成的订单 MyOrderPair类型 用于数据统计

        self.open_order_dict = dict()  # bt.order->MyOrderPair对象映射，用于统计结果：key为bt.order对象 value为MyOrderPair对象
        self.close_order_dict = dict()  # bt.order->MyOrderPair对象映射，用于统计结果：key为bt.order对象 value为MyOrderPair对象

        self.strategy_adaptor = OrderScheduler()

        # 分析数据
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
        open_order_array = self.data.open_order_array
        open_position = open_order_array.get_position_by_price(current_price)
        if 0 <= open_position <= self.OPEN_PRICE_SLOT_NUM:
            ## 在 open order array 上挂满开单
            open_price = open_order_array.get_price_by_position(open_position)
            for i in range(self.OPENING_ORDER_NUM):
                self.data.add_open_order(
                    open_price=open_price,
                    close_price=open_price,
                    quantity=0  # quantity在正式挂单时决定
                )
            ## 在盘口价下方挂上一定数量的开单
            for i in range(open_position, min(open_position + self.OPENING_ORDER_NUM, self.OPEN_PRICE_SLOT_NUM)):
                open_order = open_order_array.get_order_by_position(i)
                open_price = open_order.open_price
                open_quantity = self.bet_cash_size / open_price
                open_order.update_quantity(open_quantity)
                if not self.open_order_price_dict.__contains__(open_price):
                    ## 创建限价单
                    new_open_order = self.super_strategy.buy(
                        price=open_price,
                        size=open_quantity,
                        exectype=bt.Order.Limit
                    )
                    # 用于数据统计
                    self.analysis_add_open_order(open_price=open_price, quantity=open_quantity)
                    self.open_order_dict[new_open_order.ref] = open_order
                    # logging.info(f"Order Placed\tDirection: Buy,\tPrice: {new_open_order.price},\tSize: {new_open_order.size}")
                    # self.strategy_adaptor.bind(open_order, MyOrderPairObserver(strategy=self.super_strategy, bt_order=new_open_order))  # 将new_open_order委托给strategy_adaptor， 自动完成价格调整
                    self.open_order_price_dict[open_price] = new_open_order
        # todo 向上挂满平单
        # self.debug_log()

    def debug_log(self):

        #### debug 输出当前挂单
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
        ####

        # #### debug 输出当前挂单
        # ##### 买单列表
        # buy_order_price_list = []
        # for price in self.open_order_price_dict.keys():
        #     buy_order_price_list.append(price)
        # buy_order_price_list.sort(reverse=True)
        # logging.info(f"买单列表: {buy_order_price_list}")
        #
        # ##### 卖单列表
        # sell_order_price_list = []
        # for order in self.close_order_price_dict.values():
        #     sell_order_price_list.append(order.price)
        # sell_order_price_list.sort()
        # logging.info(f"卖单列表: {sell_order_price_list}")
        #
        # ##### data买单列表
        # data_buy_order_price_list = []
        # for o in self.data.open_order_array.data:
        #     if o is None:
        #         data_buy_order_price_list.append(None)
        #     else:
        #         data_buy_order_price_list.append(o.open_price)
        # logging.info(f"data买单列表: {data_buy_order_price_list}")
        #
        # ##### data卖单列表
        # data_sell_order_price_list = []
        # for o in self.data.close_order_array.data:
        #     if o is None:
        #         data_sell_order_price_list.append(None)
        #     else:
        #         data_sell_order_price_list.append(o.close_price)
        # logging.info(f"data卖单列表: {data_sell_order_price_list}")
        # ####

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
                ## 清除挂单
                open_price = order.price
                self.open_order_price_dict.pop(open_price)
                # quantity = order.executed.size
                ## 调整self.data
                open_order_array = self.data.open_order_array
                close_order_array = self.data.close_order_array
                # tmp_order = open_order_array.pop_by_price(open_price)
                # tmp_order.update_status_closing()
                if self.direction == 'long':
                    close_price = open_price * (1 + self.PERCENTAGE_MINIMUM_PROFIT)
                else:
                    close_price = open_price * (1 - self.PERCENTAGE_MINIMUM_PROFIT)
                close_position = close_order_array.get_position_by_price(close_price)

                # # 向上找一个空的slot挂close单
                # while close_position <= self.CLOSE_PRICE_SLOT_NUM:
                #     close_price = close_order_array.get_price_by_position(close_position)
                #     if not self.close_order_price_dict.__contains__(close_price):
                #         break
                #     close_position += 1

                # tmp_order.update_close_price(close_price)
                # (is_success, changed_list, pop_order) = close_order_array.add_order(order=tmp_order)
                ### todo add order过程中如果有订单价格发生改变 需要调整已经挂好的订单
                ### todo 如果close挂满 直接将顶部pop出来的close订单 用市价成交

                new_close_order = self.super_strategy.sell(
                    price=close_price,
                    size=order.size,
                    exectype=bt.Order.Limit
                )

                # if self.close_order_price_dict.__contains__(close_price):
                #     old_close_order: bt.Order = self.close_order_price_dict.pop(close_price)
                #     # 市价平掉旧order
                #     self.super_strategy.sell(
                #         size=old_close_order.size,
                #     )
                #     # 取消旧order挂单
                #     self.super_strategy.cancel(old_close_order)
                #     # logging.info(f"Order Market Sell,\tPrice: {new_close_order.price},\tSize: {new_close_order.size}")
                #
                #     ## 数据统计用 - START
                #     self.analysis_remove_close_order(
                #         close_price=close_price, quantity=old_close_order.size, market_price=self.get_price()
                #     )
                #     self.analysis_add_closed_order(
                #         close_price=close_price, quantity=old_close_order.size, market_price=self.get_price()
                #     )
                #     ## 数据统计用 - END

                self.close_order_price_dict[close_price] = new_close_order
                # logging.info(f"Order Placed\tDirection: Sell,\tPrice: {new_close_order.price},\tSize: {new_close_order.size}")
                # self.strategy_adaptor.bind(tmp_order, MyOrderPairObserver(strategy=self.super_strategy, bt_order=new_close_order))  # 将new_close_order委托给strategy_adaptor， 自动完成价格调整

                ## 数据统计用 - START
                self.price_map_close2open[close_price] = open_price
                self.analysis_remove_open_order(close_price=close_price, quantity=order.size)
                self.analysis_add_close_order(close_price=close_price, quantity=order.size)
                ## 数据统计用 - END

                # ## 在盘口价上方挂上一定数量的平单
                # ### 清除旧挂单
                # for o in self.close_order_price_dict.values():
                #     self.super_strategy.cancel(o)
                # self.close_order_price_dict = dict()
                # ### 添加新挂单
                # current_price = self.get_price()
                # close_position = close_order_array.get_position_by_price(current_price)
                # for i in range(close_position, min(close_position + self.CLOSING_ORDER_NUM, self.CLOSE_PRICE_SLOT_NUM)):
                #     close_order = close_order_array.get_order_by_position(i)
                #     if close_order is not None:
                #         idx = i + 1
                #         close_price = close_order.close_price
                #         close_quantity = close_order.quantity
                #         while self.close_order_price_dict.__contains__(close_price):
                #             if idx >= close_order_array.length:
                #                 # 创建市价单 直接卖
                #                 self.super_strategy.sell(
                #                     price=close_price,
                #                     size=close_quantity,
                #                 )
                #                 break
                #             close_price = self.data.close_order_array.get_price_by_position(idx)
                #             idx+=1
                #         ## 创建限价单
                #         new_close_order = self.super_strategy.sell(
                #             price=close_price,
                #             size=close_quantity,
                #             exectype=bt.Order.Limit
                #         )
                #         # logging.info(f"Order Placed\tDirection: Sell,\tPrice: {new_close_order.price},\tSize: {new_close_order.size}")
                #         # self.strategy_adaptor.bind(close_order, MyOrderPairObserver(strategy=self.super_strategy, bt_order=new_close_order))  # 将new_close_order委托给strategy_adaptor， 自动完成价格调整
                #         self.close_order_price_dict[close_price] = new_close_order
            elif order.issell():
                # todo 平单完成 保存订单
                # 数据统计用
                if order.price is not None:
                    self.analysis_remove_close_order(close_price=order.price, quantity=order.size)
                    self.analysis_add_closed_order(close_price=order.price, quantity=order.size)
                ## 调整self.data
                # close_price = order.price
                # if close_price is not None:
                #     close_order_array = self.data.close_order_array
                #     tmp_order = close_order_array.pop_by_price(close_price)
                #     tmp_order.update_status_closed()
                #     ## 保存订单
                #     self.closed_order_list.append(tmp_order)
        # elif order.status in [order.Canceled]:
        #     logging.info(f"Order Canceled\tDirection: {direction},\tPrice: {order.price},\tSize: {order.size}")
        # elif order.status in [order.Margin]:
        #     logging.info(f"Order 保证金不足\tDirection: {direction},\tPrice: {order.price},\tSize: {order.size}")
        # elif order.status in [order.Rejected]:
        #     logging.info(f"Order Rejected\tDirection: {direction},\tPrice: {order.price},\tSize: {order.size}")

    def analysis_add_open_order(self, open_price: float, quantity: float):
        """用于分析"""
        ## 挂单数据
        self.opening_amount += abs(quantity)  # 开仓挂单BTC总量
        self.opening_value += abs(quantity) * open_price  # 开仓挂单BTC总价

    def analysis_remove_open_order(self, close_price: float, quantity: float):
        """用于分析"""
        open_price = self.price_map_close2open[close_price]
        ## 挂单数据
        self.opening_amount -= abs(quantity)  # 开仓挂单BTC总量
        self.opening_value -= abs(quantity) * open_price  # 开仓挂单BTC总价
        ## 成交数据
        self.opening_amount_finished += abs(quantity)  # 已成交的开仓挂单BTC总量
        self.opening_value_finished += abs(quantity) * open_price  # 已成交的开仓挂单BTC总价

    def analysis_add_close_order(self, close_price: float, quantity: float):
        """用于分析"""
        open_price = self.price_map_close2open[close_price]
        ## 挂单数据
        self.closing_amount += abs(quantity)  # 平仓挂单BTC总量
        self.closing_value += abs(quantity) * close_price  # 平仓挂单BTC总价(期望持仓市值)
        self.closing_cost += abs(quantity) * open_price  # 平仓挂单BTC成本 = sum(每单BTC总量 * 每单开仓挂单价格)

    def analysis_remove_close_order(self, close_price: float, quantity: float, market_price: float = None):
        """用于分析"""
        open_price = self.price_map_close2open[close_price]
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

    def analysis_add_closed_order(self, close_price: float, quantity: float, market_price: float = None):
        """用于分析"""
        open_price = self.price_map_close2open[close_price]
        if market_price is not None:
            close_price = market_price
        order_pair = VirtualOrder(
            open_price=open_price, close_price=close_price,
            quantity=abs(quantity),
            commission_rate=self.commission_rate
        )
        order_pair.update_status_closing()
        order_pair.update_status_closed()
        self.closed_order_list.append(order_pair)

    def __repr__(self):
        expected_holding_value = self.get_expected_holding_value()  # 期望持仓市值
        expected_total_value = self.get_expected_total_value()  # 期望总资产
        expected_profit = self.get_expected_profit()  # 期望未成交收益
        actual_profit = self.get_actual_profit()  # 实际已成交收益
        ##
        # self.closing_value # 平仓挂单BTC总价
        # self.closing_cost # 平仓挂单BTC成本
        # self.expected_profit: float = 0  # 期望未成交收益 = 平仓挂单BTC总价 - 平仓挂单BTC成本
        # self.expected_holding_value: float = 0  # 期望持仓市值 = 平仓挂单BTC总价
        # self.expected_total_value: float = 0  # 期望总资产 = 现金余额 + 期望持仓市值（平仓挂单BTC总价）
        # self.not_yet_achieved_profit: float = 0  # 尚未达到的收益 = 平仓挂单BTC总价 - 持仓市值
        # self.actual_profit: float = 0  # 实际已成交收益 = 已成交的平仓挂单BTC总价 - 已成交的平仓挂单BTC成本
        return f"{self.super_strategy.data.datetime.date()} {self.super_strategy.data.datetime.time()}\tBTC价格:{self.get_price():.2f}\t现金余额:{self.get_cash():.2f}\t持仓BTC数量:{self.get_position_size():.4f}\t持仓市值:{self.get_holding_value():.2f}\t期望持仓市值:{expected_holding_value:.2f}\t总资产:{self.get_total_value():.2f}\t期望总资产:{expected_total_value:.2f}\t期望未成交收益:{expected_profit:.2f}\t实际已成交收益:{actual_profit:.2f}\t平仓挂单BTC总价:{self.closing_value:2f}\t平仓挂单BTC成本:{self.closing_cost:2f}"

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
                * self.OPEN_PRICE_SLOT_NUM
                / (self.max_open_price - self.min_open_price)
            )
            # 重构数据结构
            direction = 'long'
            self.data = MyOrderArrayTriple(
                max_open_price=self.max_open_price, min_open_price=self.min_open_price,
                max_close_price=self.max_close_price, min_close_price=self.min_close_price,
                open_array_length=self.OPEN_PRICE_SLOT_NUM, close_array_length=self.CLOSE_PRICE_SLOT_NUM,
                direction=direction, commission_rate=self.commission_rate
            )
            # 清除所有订单
            open_orders = self.super_strategy.broker.get_orders_open()
            if open_orders:
                for order in open_orders:
                    self.super_strategy.cancel(order)

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


class MyOrderPairObserver:
    """
    观察者对象
    观察MyOrderPair
    持有bt.Order
    """

    def __init__(self, strategy: bt, bt_order: bt.Order):
        self.strategy = strategy
        self.bt_order = bt_order

    def update(self, open_price: float, close_price: float, quantity: float):
        """当被观察对象发生变化时调用"""
        self.check_value(open_price)
        self.check_value(close_price)
        self.check_value(quantity)
        # 检查参数与当前挂单是否相同
        # 如果参数发生变化 则取消原挂单 新建挂单
        is_buy = self.bt_order.isbuy()
        direction = 'Buy' if is_buy else 'Sell'
        if is_buy:
            order_price = open_price
        else:
            order_price = close_price
        if self.bt_order.price != order_price or self.bt_order.size != quantity:
            # logging.info(f"MyOrderPair changed. Direction:{direction}\tprice:{self.bt_order.price}=>{open_price}\tquantity:{self.bt_order.size}=>{quantity}")
            # 取消原挂单
            self.strategy.cancel(self.bt_order)
            # 新建挂单
            if is_buy:
                self.bt_order = self.strategy.buy(
                    price=order_price,
                    size=quantity,
                    exectype=bt.Order.Limit
                )
                # logging.info(f"Order Placed\tDirection: Buy,\tPrice: {self.bt_order.price},\tSize: {self.bt_order.size}")
            else:
                self.bt_order = self.strategy.sell(
                    price=order_price,
                    size=quantity,
                    exectype=bt.Order.Limit
                )
                # logging.info(f"Order Placed\tDirection: Sell,\tPrice: {self.bt_order.price},\tSize: {self.bt_order.size}")

    def check_value(self, value: float):
        if value < 0:
            raise ValueError(f'value must be >= 0, not {value}')


class OrderScheduler:
    """
    订单调度器，用于对接MyOrderArrayTriple数据结构和backtrader.Order
    使用观察者模式 作为双向绑定管理器（BindingManager）
    作用：
    1.将MyOrderPair与backtrader.Order（存储在MyOrderPairObserver中）进行关联
    2.接受MyOrderPair的notify信号，并修改backtrader.Order的价格
    3.接受backtrader.Order的变更信号 并修改MyOrderPair的状态
    """

    def __init__(self, strategy:bt.Strategy):
        # 正向绑定
        self.order_bindings_virtual2actual: Dict[any, bt.Order] = {}
        # 反向绑定
        self.order_bindings_actual2virtual: Dict[any, VirtualOrder] = {}
        # 由上级Strategy提供的backtrader.Strategy 用于操作backtrader.Order
        self.strategy = strategy

    def bind(self, virtual_order: VirtualOrder, actual_order: bt.Order):
        virtual_order.link_observer(self.virtual_observe)
        self.order_bindings_virtual2actual[virtual_order] = actual_order
        self.order_bindings_actual2virtual[id(actual_order)] = virtual_order

    def unbind(self, virtual_order: VirtualOrder):
        virtual_order.link_observer(None)
        if self.order_bindings_virtual2actual.__contains__(virtual_order):
            actual_id = self.order_bindings_virtual2actual[virtual_order]
            del self.order_bindings_virtual2actual[virtual_order]
            if self.order_bindings_actual2virtual.__contains__(actual_id):
                del self.order_bindings_actual2virtual[actual_id]

    def virtual_observe(self, virtual_order: VirtualOrder):
        """
        当VirtualOrder发生变更时，触发该函数
        :param virtual_order:
        :return:
        """
        # 对比订单买卖方向 对比挂单价格 对比挂单量
        # 如果数据存在差异 则取消旧挂单 提交新挂单
        actual_order = self.order_bindings_virtual2actual.get(virtual_order)
        # 如果virtual_order没有关联的actual_order 则抛出异常
        if actual_order is None:
            raise RuntimeError(f'virtual order {virtual_order} not found')
        virtual_is_buy = virtual_order.is_buy()
        actual_is_buy = actual_order.isbuy()
        if actual_is_buy:
            order_price = virtual_order.open_price
        else:
            order_price = virtual_order.close_price
        quantity = virtual_order.quantity
        if actual_order.price != order_price or actual_order.size != quantity or virtual_is_buy != actual_is_buy:
            # logging.info(f"MyOrderPair changed. Direction:{'Buy' if actual_is_buy else 'Sell'}\tprice:{actual_order.price}=>{order_price}\tquantity:{actual_order.size}=>{quantity}")
            # 取消原挂单
            self.strategy.cancel(actual_order)
            # 新建挂单
            if virtual_is_buy:
                new_actual_order = self.strategy.buy(
                    price=order_price,
                    size=quantity,
                    exectype=bt.Order.Limit
                )
                # logging.info(f"Order Placed\tDirection: Buy,\tPrice: {self.bt_order.price},\tSize: {self.bt_order.size}")
            else:
                new_actual_order = self.strategy.sell(
                    price=order_price,
                    size=quantity,
                    exectype=bt.Order.Limit
                )
                # logging.info(f"Order Placed\tDirection: Sell,\tPrice: {self.bt_order.price},\tSize: {self.bt_order.size}")
            self.unbind(virtual_order)
            self.bind(virtual_order, new_actual_order)

    def actual_buy_finished(self, actual_order: bt.Order):
        """
        实际买单成交
        修改VirtualOrder的状态
        :param actual_order:
        """
        # todo
        pass

    def actual_sell_finished(self, actual_order: bt.Order):
        """实际卖单成交"""
        # todo
        pass



def test_strategy():
    from trade.backtesting import by_backtrader
    by_backtrader.test()


if __name__ == '__main__':
    test_strategy()
