from typing import List, Callable
from log import *
from strategy import VirtualOrderArrayInterface, VirtualOrder


class VirtualOrderOne(VirtualOrder):
    """
    虚拟订单
    """

    def __init__(
            self, open_price: float, close_price: float, quantity: float, direction: str,
            leverage: float = 1.0,
            commission_rate: float = 0.0002, observer: Callable[[any], None] | None = None,
            actual_order_hash: any = None
    ):
        """
        先有开仓单，然后才有MyOrderPair对象。
        属性：
        1.open_price 开仓价格
        2.close_price 平仓价格
        2.quantity (不可变)挂单量
        3.direction: (不可变)订单类型 做多long | 做空short
        4.status: 订单状态 待开仓opening | 已开仓opened | 待平仓closing | 已平仓closed | 已取消canceled | 未知unknown
        5.expected_gross_value 期望毛利润
        6.actual_gross_value  实际毛利润
        7.expected_commission 期望佣金值
        8.actual_commission 实际佣金值
        :param open_price: 开仓价格
        :param quantity:  挂单量
        :param commission_rate: 佣金率
        :param observer: 观察者 参数[self]
        :param actual_order_hash: 实际订单的hash
        """
        super().__init__(open_price, close_price, quantity, direction, leverage=leverage)
        self.expected_gross_value = (close_price - open_price) * quantity
        self.actual_gross_value = None
        self.commission_rate = commission_rate
        self.expected_commission = (open_price + close_price) * commission_rate * quantity
        self.actual_commission = None

        self.update_open_price(open_price)
        self.update_close_price(close_price)

        self.observer: Callable[[any], None] = observer
        self.actual_order_hash = actual_order_hash

    def update_status_opened(self):
        self.status = 'opened'

    def update_status_canceled(self):
        self.status = 'canceled'

    def update_status_closing(self):
        """
        open订单成交
        将订单状态转换为 'closing'
        需计算open阶段产生的 实际佣金 和 实际毛利润
        :return:
        """
        self.status = 'closing'
        self.actual_commission = self.open_price * self.commission_rate * self.quantity
        self.update_close_price(self.close_price)

    def update_status_closed(self):
        """
        close订单成交
        将订单状态转换为 'closed'
        需计算close阶段产生的 实际佣金 和 实际毛利润
        :return:
        """
        self.status = 'closed'
        self.actual_commission = self.expected_commission
        self.actual_gross_value = self.expected_gross_value

    def update_open_price(self, price: float):
        """
        修改open_price
        只有在 'opening' 状态下可以调用
        :param price:
        :return:
        """
        if self.status != 'opening':
            raise ValueError(f'open_price can not be update while in statue:"{self.status}"')
        self.check_price(price)
        if self.open_price != price:
            # 为保证订单的总金额不变 需要调整quantity
            self.update_quantity(self.quantity * self.open_price / price, self.leverage)

            self.open_price = price
            self.expected_commission = (self.open_price + self.close_price) * self.commission_rate * self.quantity
            self.expected_gross_value = (self.close_price - self.open_price) * self.quantity
            self.notify_observer()

    def update_close_price(self, price: float):
        """
        修改close_price
        在 'opening' 和 'closing' 状态下均可使用
        :param price:
        :return:
        """
        if self.status == 'closed':
            raise ValueError(f'close_price can not be update while in statue:"closed"')
        self.check_price(price)
        if self.close_price != price:
            self.close_price = price
            if self.status == 'closing':
                """
                在 'closing' 状态下需要计算 期望佣金 和 期望毛利润
                """
                self.expected_commission = self.actual_commission + self.close_price * self.commission_rate * self.quantity
                self.expected_gross_value = (self.close_price - self.open_price) * self.quantity
            self.notify_observer()

    def update_quantity(self, quantity: float, leverage: float = 1):
        self.check_quantity(quantity)
        self.quantity = quantity
        self.leverage = leverage
        self.principal = quantity * self.open_price / leverage  # 本金
        self.loan = quantity * self.open_price - self.principal  # 借贷资金
        # 强平价格（只作为标记 不触发实际平仓操作）
        if self.direction == 'long':
            self.forced_liquidation_price = self.open_price * (1 - 1 / leverage)
        else:
            self.forced_liquidation_price = self.open_price * (1 + 1 / leverage)
        self.notify_observer()

    def actual_net_value(self) -> float | None:
        if self.status != 'closed':
            return None
        else:
            return self.actual_gross_value - self.actual_commission

    def link_observer(self, observer: Callable[[any], None] | None):
        """
        链接观察者方法
        :param observer: 观察者方法
        :return:
        """
        self.observer = observer

    def notify_observer(self):
        if self.observer is not None:
            self.observer(self)

    def link_actual_order_hash(self, actual_order_hash: any):
        self.actual_order_hash = actual_order_hash

    def is_buy(self) -> bool:
        if self.status == 'opening':
            if self.direction == 'long':
                return True
            else:
                return False
        elif self.status == 'closing':
            if self.direction == 'short':
                return False
            else:
                return True
        else:
            raise ValueError(f'is_buy can not be updated while in statue:"{self.status}"')

    def __repr__(self):
        return f"MyOrderPair({self.status},{self.open_price},{self.close_price},{self.quantity},{self.expected_commission},{self.actual_commission},{self.expected_gross_value},{self.actual_gross_value},{self.actual_net_value()})"
