# -*- coding: utf-8 -*-

"""
只做Maker的做多波动率交易策略
深度左侧交易
"""
import logging
import math

import backtrader as bt

from data_collection.dao.strategy_action_btc_spot_trading_usdt_1m import StrategyActionBtcUSDT1mConnector, \
    StrategyActionBtcUSDT1mInsertDao
from data_collection.dao.strategy_status_btc_spot_trading_usdt_1m import StrategyStatusBtcUSDT1mDao, \
    StrategyStatusBtcUSDT1mConnector
from log import *
from strategy import StrategyInterface, VirtualOrder
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

        # 分析数据 db相关
        # db相关
        self.STRATEGY_VERSION = self.generate_random_version()
        logging.info("Strategy Version: {}".format(self.STRATEGY_VERSION))
        self.db_status_connector = StrategyStatusBtcUSDT1mConnector()
        self.db_action_connector = StrategyActionBtcUSDT1mConnector()
        ##
        self.closed_order_list = []  # 保存已完成的订单 MyOrderPair类型 用于数据统计
        ## 原子指标
        ### opening
        self.opening_order_num = 0  # 开仓挂单数
        self.opening_order_quantity: float = 0  # 开仓挂单BTC总量
        self.opening_order_value: float = 0  # 开仓挂单BTC总价
        ### closing
        self.closing_order_num: float = 0  # 平仓挂单数
        self.closing_order_quantity: float = 0  # 平仓挂单BTC总量
        self.closing_order_value: float = 0  # 平仓挂单BTC总价(期望持仓市值)
        self.closing_order_cost: float = 0  # 平仓挂单BTC成本 = sum(每单BTC总量 * 每单开仓挂单价格)
        ## 成交数据
        ### opened
        self.opened_order_num: float = 0  # 开仓成交单数
        self.opened_order_quantity: float = 0  # 已成交的开仓挂单BTC总量
        self.opened_order_value: float = 0  # 已成交的开仓挂单BTC总价
        ### closed
        self.closed_order_num: float = 0  # 平仓成交单数
        self.closed_order_quantity: float = 0  # 已成交的平仓挂单BTC总量
        self.closed_order_value: float = 0  # 已成交的平仓挂单BTC总价
        self.closed_order_cost: float = 0  # 已成交的平仓挂单BTC成本 = sum(每单BTC总量 * 每单开仓挂单价格)
        ### 累计数据
        self.cumulative_opening_order_num: int = 0  # 累计开仓挂单数
        self.cumulative_opening_order_quantity: float = 0  # 累计开仓挂单BTC总量
        self.cumulative_opening_order_value: float = 0  # 累计开仓挂单总价 -- 开仓成本=开仓总价 因此不单独计算开仓成本
        self.cumulative_closing_order_num: int = 0  # 累计平仓挂单数
        self.cumulative_closing_order_quantity: float = 0  # 累计平仓挂单BTC总量
        self.cumulative_closing_order_value: float = 0  # 累计平仓挂单总价
        self.cumulative_closing_order_cost: float = 0  # 累计平仓挂单成本 = sum(每单成本(每单BTC总量 * 每单开仓挂单价格))
        self.cumulative_opened_order_num: int = 0  # 累计开仓成交单数
        self.cumulative_opened_order_quantity: float = 0  # 累计开仓成交BTC总量'
        self.cumulative_opened_order_value: float = 0  # 累计开仓成交总价 -- 开仓成本=开仓总价 因此不单独计算开仓成本
        self.cumulative_closed_order_num: int = 0  # 累计平仓成交单数（累计已成交订单数）
        self.cumulative_closed_order_quantity: float = 0  # 累计平仓成交BTC总量
        self.cumulative_closed_order_value: float = 0  # 累计平仓成交总价
        self.cumulative_closed_order_cost: float = 0  # 累计平仓成交成本 = sum(每单成本(每单BTC总量 * 每单开仓挂单价格))',
        ## 持仓数据
        self.cumulative_closed_order_num: int = 0  # 累计已成交订单数

    def next(self):
        """
        每个周期（1m）的操作逻辑：
        1.self.update_param()-判断是否创新高，如果创新高则更新参数
        2.获取收盘价，保证收盘价下方有足够数量的开单，保证收盘价上方由足够数量的平单
        3.挂单时更新self.data
        :return:
        """
        logging.info(self)
        self.upload_status_data()  # 状态数据落库
        self.reset_incremental_status()  # 重置增量数据
        self.update_param()  # 更新参数

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
                    self.analysis_opening_order(open_price=open_price, quantity=open_quantity)
                    # logging.info(f"Order Placed\tDirection: Buy,\tPrice: {new_open_order.price},\tSize: {new_open_order.size}")

                    # order_scheduler
                    self.order_scheduler.bind(virtual_order=virtual_order, actual_order=actual_order)

                    # 上传action数据
                    self.upload_action_data(virtual_order)
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

                # 上传action数据
                self.upload_action_data(virtual_order)

                ## 数据统计用 - START
                self.analysis_opened_order(
                    open_price=virtual_order.open_price, close_price=virtual_order.close_price, quantity=order.size
                )
                self.analysis_closing_order(
                    open_price=virtual_order.open_price, close_price=virtual_order.close_price, quantity=order.size
                )
                ## 数据统计用 - END

            elif order.issell():
                # 平单完成 保存订单
                virtual_order = self.order_scheduler.actual_sell_finished(order)

                # 上传action数据
                self.upload_action_data(virtual_order)

                # 调整借贷资金
                loan = virtual_order.loan
                self.loan -= loan
                self.super_strategy.broker.add_cash(-loan)

                ## 数据统计用 - START
                if order.price is not None:
                    self.analysis_closed_order(
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

                # 上传action数据 todo 手动cancel
                self.upload_action_data(virtual_order)

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

    def upload_status_data(self):
        """
        上传status数据至数据库
        :return:
        """
        open_time = bt.num2date(self.super_strategy.datetime[0])  # 开盘时间
        version = self.STRATEGY_VERSION  # 策略版本
        price = self.get_price()  # 市场价格

        opening_order_num = self.opening_order_num  # 开仓挂单数
        opening_order_quantity = self.opening_order_quantity  # 开仓挂单BTC总量
        opening_order_value = self.opening_order_value  # 开仓挂单总价；开仓成本=开仓总价 因此不单独计算开仓成本

        closing_order_num = self.closing_order_num  # 平仓挂单数
        closing_order_quantity = self.closing_order_quantity  # 平仓挂单BTC总量
        closing_order_value = self.closing_order_value  # 平仓挂单总价
        closing_order_cost = self.closing_order_cost  # 平仓挂单成本 = sum(每单成本(每单BTC总量 * 每单开仓挂单价格))

        opened_order_num = self.opened_order_num  # 开仓成交单数
        opened_order_quantity = self.opened_order_quantity  # 开仓成交BTC总量
        opened_order_value = self.opened_order_value  # 开仓成交总价；开仓成本=开仓总价 因此不单独计算开仓成本

        closed_order_num = self.closed_order_num  # 平仓成交单数
        closed_order_quantity = self.closed_order_quantity  # 平仓成交BTC总量
        closed_order_value = self.closed_order_value  # 平仓成交总价
        closed_order_cost = self.closed_order_cost  # 平仓成交成本 = sum(每单成本(每单BTC总量 * 每单开仓挂单价格))

        cumulative_opening_order_quantity = self.cumulative_opening_order_quantity  # 累计开仓挂单BTC总量
        cumulative_opening_order_num = self.cumulative_opening_order_num  # 累计开仓挂单数
        cumulative_opening_order_value = self.cumulative_opening_order_value  # 累计开仓挂单总价 -- 开仓成本=开仓总价 因此不单独计算开仓成本
        cumulative_closing_order_num = self.cumulative_closing_order_num  # 累计平仓挂单数
        cumulative_closing_order_quantity = self.cumulative_closing_order_quantity  # 累计平仓挂单BTC总量
        cumulative_closing_order_value = self.cumulative_closing_order_value  # 累计平仓挂单总价
        cumulative_closing_order_cost = self.cumulative_closing_order_cost  # 累计平仓挂单成本 = sum(每单成本(每单BTC总量 * 每单开仓挂单价格))
        cumulative_opened_order_num = self.cumulative_opened_order_num  # 累计开仓成交单数
        cumulative_opened_order_quantity = self.cumulative_opened_order_quantity  # 累计开仓成交BTC总量'
        cumulative_opened_order_value = self.cumulative_opened_order_value  # 累计开仓成交总价 -- 开仓成本=开仓总价 因此不单独计算开仓成本
        cumulative_closed_order_num = self.cumulative_closed_order_num  # 累计平仓成交单数（累计已成交订单数）
        cumulative_closed_order_quantity = self.cumulative_closed_order_quantity  # 累计平仓成交BTC总量
        cumulative_closed_order_value = self.cumulative_closed_order_value  # 累计平仓成交总价
        cumulative_closed_order_cost = self.cumulative_closed_order_cost  # 累计平仓成交成本 = sum(每单成本(每单BTC总量 * 每单开仓挂单价格))',

        cash = self.get_cash()  # 现金余额（包含本金和借贷资金）
        loan = self.loan  # 借贷资金（欠款）
        holding_quantity = self.get_hold_quantity()  # 实际持仓BTC总量
        holding_value = self.get_holding_value()  # 实际持仓BTC总价
        total_value = self.get_total_value()  # 实际总资产 = 现金 + 实际持仓BTC总价

        expected_closing_profit = self.get_expected_closing_profit()  # 期望未成交收益 = 平仓挂单总价 - 平仓挂单成本
        actual_closed_profit = self.get_actual_closed_profit()  # 实际已成交收益 =平仓成交总价 - 平仓成交成本
        expected_market_close_profit = self.get_expected_market_close_profit()  # 市价平仓期望收益(亏损) = sum((市场价格 - 每单开仓挂单价格) * 每单BTC总量）
        expected_closed_profit = self.get_expected_closed_profit()  # 期望总收益 = 实际已成交收益 + 期望未成交收益
        expected_holding_value = self.get_expected_holding_value()  # 期望持仓市值 = 平仓挂单总价
        expected_total_value = self.get_expected_total_value()  # 期望总资产 = 现金余额 + 期望持仓市值（平仓挂单BTC总价）
        actual_net_value = self.get_actual_net_value()  # 实际净资产 = 总资产 - 借贷资金；若净资产归零 则强制平仓
        expected_net_value = self.get_expected_net_value()  # 期望净资产 = 净资产 - 平仓挂单亏损

        ave_profit_per_closed_order = self.get_ave_profit_per_closed_order()  # 已成交订单平均每单盈利
        status = StrategyStatusBtcUSDT1mDao(
            open_time, version, price, opening_order_num, opening_order_quantity, opening_order_value,
            closing_order_num, closing_order_quantity, closing_order_value, closing_order_cost, opened_order_num,
            opened_order_quantity, opened_order_value, closed_order_num, closed_order_quantity, closed_order_value,
            closed_order_cost, cumulative_opening_order_num, cumulative_opening_order_quantity,
            cumulative_opening_order_value, cumulative_closing_order_num, cumulative_closing_order_quantity,
            cumulative_closing_order_value, cumulative_closing_order_cost, cumulative_opened_order_num,
            cumulative_opened_order_quantity, cumulative_opened_order_value, cumulative_closed_order_num,
            cumulative_closed_order_quantity, cumulative_closed_order_value, cumulative_closed_order_cost, cash, loan,
            holding_quantity, holding_value, total_value, expected_closing_profit,
            actual_closed_profit, expected_market_close_profit, expected_closed_profit, expected_holding_value,
            expected_total_value, actual_net_value, expected_net_value, ave_profit_per_closed_order
        )

        self.db_status_connector.insert_single_queue(status)

    def reset_incremental_status(self):
        """
        重置增量参数
        :return:
        """
        self.opening_order_num = 0  # 开仓挂单数
        self.opening_order_quantity = 0  # 开仓挂单BTC总量
        self.opening_order_value = 0  # 开仓挂单总价；开仓成本=开仓总价 因此不单独计算开仓成本
        self.closing_order_num = 0  # 平仓挂单数
        self.closing_order_quantity = 0  # 平仓挂单BTC总量
        self.closing_order_value = 0  # 平仓挂单总价
        self.closing_order_cost = 0  # 平仓挂单成本 = sum(每单成本(每单BTC总量 * 每单开仓挂单价格))
        self.opened_order_num = 0  # 开仓成交单数
        self.opened_order_quantity = 0  # 开仓成交BTC总量
        self.opened_order_value = 0  # 开仓成交总价；开仓成本=开仓总价 因此不单独计算开仓成本
        self.closed_order_num = 0  # 平仓成交单数
        self.closed_order_quantity = 0  # 平仓成交BTC总量
        self.closed_order_value = 0  # 平仓成交总价
        self.closed_order_cost = 0  # 平仓成交成本 = sum(每单成本(每单BTC总量 * 每单开仓挂单价格))

    def upload_action_data(self, order: VirtualOrder):
        """
        上传action数据至数据库
        :return:
        """
        """
            `version`              VARCHAR(255) comment '策略版本',
            `action_time`          DateTime comment '挂单时间/交易完成时间',
            `status`               Int8 comment '订单状态: 1.开仓挂单opening 2.已开仓opened 3.平仓挂单closing 4.已平仓closed 5.已取消canceled',
            `open_price`           DECIMAL(26, 6) comment '开仓价格',
            `close_price`          DECIMAL(26, 6) comment '平仓价格',
            `quantity`             Nullable(Decimal(26, 6)) comment '交易量',
            `open_cost`            DECIMAL(26, 6) comment '开仓成本 = 开仓价格 * 交易量',
            `expected_gross_value` Nullable(Decimal(26, 6)) comment '期望毛利润',
            `actual_gross_value`   Nullable(Decimal(26, 6)) comment '实际毛利润',
            `expected_commission`  Nullable(Decimal(26, 6)) comment '期望佣金值',
            `actual_commission`    Nullable(Decimal(26, 6)) comment '实际佣金值',
        """
        version = self.STRATEGY_VERSION  # 策略版本
        action_time = bt.num2date(self.super_strategy.datetime[0])  # 挂单时间/交易完成时间
        # 订单状态: 1.开仓挂单opening 2.已开仓opened 3.平仓挂单closing 4.已平仓closed 5.已取消canceled -1.未知
        if order.status == "opening":
            status = 1
        elif order.status == "opened":
            status = 2
        elif order.status == "closing":
            status = 3
        elif order.status == "closed":
            status = 4
        elif order.status == "canceled":
            status = 5
        else:
            status = -1
        open_price = order.open_price  # 开仓价格
        close_price = order.close_price  # 平仓价格
        quantity = order.quantity  # 交易量
        open_cost = open_price * quantity  # 开仓成本 = 开仓价格 * 交易量
        expected_gross_value = order.expected_gross_value  # 期望毛利润
        actual_gross_value = order.expected_gross_value  # 实际毛利润
        expected_commission = order.expected_commission  # 期望佣金值
        actual_commission = order.actual_commission  # 实际佣金值

        action = StrategyActionBtcUSDT1mInsertDao(
              version,
              action_time,
              status,
              open_price,
              close_price,
              quantity,
              open_cost,
              expected_gross_value,
              actual_gross_value,
              expected_commission,
              actual_commission,
        )
        self.db_action_connector.insert_single_queue(action)

    def analysis_opening_order(self, open_price: float, quantity: float):
        """
        用于分析
        新增开单
        """
        ## 增量数据
        self.opening_order_num += 1  # 开仓挂单数
        self.opening_order_quantity += abs(quantity)  # 开仓挂单BTC总量
        self.opening_order_value += abs(quantity) * open_price  # 开仓挂单BTC总价
        ## 累计数据
        self.cumulative_opening_order_num += 1  # 累计开仓挂单数
        self.cumulative_opening_order_quantity += abs(quantity)  # 累计开仓挂单BTC总量
        self.cumulative_opening_order_value += abs(quantity) * open_price  # 累计开仓挂单总价

    def analysis_opened_order(self, open_price: float, close_price: float, quantity: float):
        """用于分析"""
        # 增量数据
        ## 减少开单
        self.opening_order_num -= 1  # 开仓挂单数
        self.opening_order_quantity -= abs(quantity)  # 开仓挂单BTC总量
        self.opening_order_value -= abs(quantity) * open_price  # 开仓挂单BTC总价
        ## 增加平单
        self.opened_order_num += 1  # 平仓挂单数
        self.opened_order_quantity += abs(quantity)  # 已成交的开仓挂单BTC总量
        self.opened_order_value += abs(quantity) * open_price  # 已成交的开仓挂单BTC总价
        # 累计数据
        ## 增加平单
        self.cumulative_opening_order_num -= 1  # 开仓挂单数
        self.cumulative_opening_order_quantity -= abs(quantity)  # 开仓挂单BTC总量
        self.cumulative_opening_order_value -= abs(quantity) * open_price  # 开仓挂单BTC总价
        self.cumulative_closing_order_num += 1  # 平仓挂单数
        self.cumulative_opened_order_quantity += abs(quantity)  # 已成交的开仓挂单BTC总量
        self.cumulative_opened_order_value += abs(quantity) * open_price  # 已成交的开仓挂单BTC总价

    def analysis_closing_order(self, open_price: float, close_price: float, quantity: float):
        """用于分析"""
        # 增量数据
        self.closing_order_num += 1  # 平仓挂单数
        self.closing_order_quantity += abs(quantity)  # 平仓挂单BTC总量
        self.closing_order_value += abs(quantity) * close_price  # 平仓挂单BTC总价(期望持仓市值)
        self.closing_order_cost += abs(quantity) * open_price  # 平仓挂单BTC成本 = sum(每单BTC总量 * 每单开仓挂单价格)
        # 累计数据
        self.cumulative_closing_order_num += 1  # 平仓挂单数
        self.cumulative_closing_order_quantity += abs(quantity)  # 平仓挂单BTC总量
        self.cumulative_closing_order_value += abs(quantity) * close_price  # 平仓挂单BTC总价(期望持仓市值)
        self.cumulative_closing_order_cost += abs(quantity) * open_price  # 平仓挂单BTC成本 = sum(每单BTC总量 * 每单开仓挂单价格)

    def analysis_closed_order(self, open_price: float, close_price: float, quantity: float, ):
        """用于分析"""
        # 增量数据
        ## 减少平单
        self.closing_order_num -= 1  # 平仓挂单数
        self.closing_order_quantity -= abs(quantity)  # 平仓挂单BTC总量
        self.closing_order_value -= abs(quantity) * close_price  # 平仓挂单BTC总价(期望持仓市值)
        self.closing_order_cost -= abs(quantity) * open_price  # 平仓挂单BTC成本 = sum(每单BTC总量 * 每单开仓挂单价格)
        ## 成交数据
        self.closed_order_num += 1  # 平仓成交单数
        self.closed_order_quantity += abs(quantity)  # 已成交的平仓挂单BTC总量
        self.closed_order_value += abs(quantity) * close_price  # 已成交的平仓挂单BTC总价
        self.closed_order_cost += abs(quantity) * open_price  # 已成交的平仓挂单BTC成本 = sum(每单BTC总量 * 每单开仓挂单价格)
        # 累计数据
        self.cumulative_closing_order_num -= 1  # 平仓挂单数
        self.cumulative_closing_order_quantity -= abs(quantity)  # 平仓挂单BTC总量
        self.cumulative_closing_order_value -= abs(quantity) * close_price  # 平仓挂单BTC总价(期望持仓市值)
        self.cumulative_closing_order_cost -= abs(quantity) * open_price  # 平仓挂单BTC成本 = sum(每单BTC总量 * 每单开仓挂单价格)
        self.cumulative_closed_order_num += 1  # 平仓成交单数
        self.cumulative_closed_order_quantity += abs(quantity)  # 已成交的平仓挂单BTC总量
        self.cumulative_closed_order_value += abs(quantity) * close_price  # 已成交的平仓挂单BTC总价
        self.cumulative_closed_order_cost += abs(quantity) * open_price  # 已成交的平仓挂单BTC成本 = sum(每单BTC总量 * 每单开仓挂单价格)

    def analysis_add_closed_order(self, open_price: float, close_price: float, quantity: float, ):
        """用于分析"""
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
        expected_closing_profit = self.get_expected_closing_profit()  # 期望未成交收益
        actual_closed_profit = self.get_actual_closed_profit()  # 实际已成交收益
        expected_market_close_profit = self.get_expected_market_close_profit()  # 平仓挂单亏损：平仓挂单BTC量*BTC价格 - 平仓挂单BTC总价
        cumulative_closed_order_num = self.cumulative_closed_order_num  # 已成交订单数
        actual_net_value = self.get_actual_net_value()  # 净资产 = 总资产 - 借贷资金
        expected_net_value = self.get_expected_net_value()  # 期望净资产 = 净资产 - 平仓挂单亏损
        ave_profit_per_order = self.get_ave_profit_per_closed_order()
        # 爆仓判断：净资产 <= 0
        if actual_net_value <= 0:
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
                f"净资产:{actual_net_value:.2f}\t期望净资产:{expected_net_value:.2f}\t"
                f"现金余额:{cash:.2f}\t本金:{self.principal:.2f}\t持仓BTC数量:{self.get_hold_quantity():.4f}\t" +
                f"借贷资金:{self.loan:.2f}\t" +
                f"期望总资产:{expected_total_value:.2f}\t总资产:{self.get_total_value():.2f}\t" +
                f"期望持仓市值:{expected_holding_value:.2f}\t实际持仓市值:{self.get_holding_value():.2f}\t" +
                f"期望未成交收益:{expected_closing_profit:.2f}\t实际已成交收益:{actual_closed_profit:.2f}\t" +
                # f"平仓挂单BTC总价:{self.closing_value:2f}\t平仓挂单BTC成本:{self.closing_cost:2f}\t" +
                f"市价平仓亏损:{expected_market_close_profit:.2f}\t" +
                f"已成交订单数:{cumulative_closed_order_num}\t平均每单盈利:{ave_profit_per_order:.5f}\t"
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

    def get_hold_quantity(self):
        """当前持仓币量"""
        return self.super_strategy.position.size

    def get_expected_closing_profit(self) -> float:
        """
        用于分析
        期望未成交收益 = 累计平仓挂单BTC总价 - 累计平仓挂单BTC成本
        """
        return self.cumulative_closing_order_value - self.cumulative_closing_order_cost

    def get_expected_holding_value(self) -> float:
        """
        用于分析
        期望持仓市值 = 累计平仓挂单BTC总价
        """
        return self.cumulative_closing_order_value

    def get_expected_total_value(self) -> float:
        """
        用于分析
        期望总资产 = 现金余额 + 期望持仓市值（累计平仓挂单BTC总价）
        """
        return self.get_cash() + self.cumulative_closing_order_value

    def get_not_yet_achieved_profit(self) -> float:
        """
        用于分析
        尚未达到的收益 = 累计平仓挂单BTC总价 - 持仓市值
        """
        return self.cumulative_closing_order_value - self.get_holding_value()

    def get_actual_closed_profit(self) -> float:
        """
        用于分析
        实际已成交收益 = 累计已成交的平仓挂单BTC总价 - 累计已成交的平仓挂单BTC成本
        """
        return self.cumulative_closed_order_value - self.cumulative_closed_order_cost

    def get_expected_market_close_profit(self) -> float:
        """
        用于分析
        平仓挂单亏损：累计平仓挂单BTC量*BTC价格 - 累计平仓挂单BTC总价
        :return:
        """
        return self.cumulative_closing_order_quantity * self.get_price() - self.cumulative_closing_order_value

    def get_actual_net_value(self) -> float:
        """
        用于分析
        净资产 = 总资产 - 借贷资金
        :return:
        """
        return self.get_total_value() - self.loan

    def get_expected_closed_profit(self) -> float:
        """
        用于分析
        期望总收益 = 实际已成交收益 + 期望未成交收益
        :return:
        """
        return self.get_actual_closed_profit() + self.get_expected_closing_profit()

    def get_ave_profit_per_closed_order(self) -> float:
        """
        用于分析
        已成交订单平均每单盈利
        :return:
        """
        if self.cumulative_closed_order_num == 0:
            return 0
        else:
            return self.closed_order_value / self.cumulative_closed_order_num

    def get_expected_net_value(self) -> float:
        """
        用于分析
        期望净资产 = 净资产 - 平仓挂单亏损
        :return:
        """
        return self.get_actual_net_value() - self.get_expected_market_close_profit()


def test_strategy():
    from trade.backtesting import by_backtrader_btc
    by_backtrader_btc.test()


if __name__ == '__main__':
    test_strategy()
