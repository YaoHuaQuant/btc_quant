from abc import ABC, abstractmethod
from typing import List, Callable
from log import *

import backtrader as bt


class StrategyInterface(ABC):
    @abstractmethod
    def next(self):
        pass

    @abstractmethod
    def notify_order(self, order: bt.Order):
        pass

    @abstractmethod
    def init(self, super_strategy: bt.Strategy):
        pass


class VirtualOrder(ABC):
    def __init__(self, open_price: float, close_price: float, quantity: float, direction: str, leverage: float = 1):
        """

        :param open_price:
        :param close_price:
        :param quantity:
        :param direction: 订单类型 做多long | 做空short
        :param leverage: 杠杆率
        """
        self.check_price(open_price)
        self.check_price(close_price)
        self.check_quantity(quantity)
        self.check_direction(direction)
        self.check_leverage(leverage)

        self.open_price = open_price
        self.close_price = close_price
        self.quantity = quantity
        self.direction = direction
        self.status = 'opening'
        self.leverage = leverage  # 杠杆率
        self.principal = quantity * open_price / leverage  # 本金
        self.loan = quantity * open_price - self.principal  # 借贷资金

        # 强平价格（只作为标记 不触发实际平仓操作）
        if direction == 'long':
            self.forced_liquidation_price = open_price * (1 - 1 / leverage)
        else:
            self.forced_liquidation_price = open_price * (1 + 1 / leverage)

        self.observer: Callable[[any], None] | None = None

    def is_buy(self) -> bool:
        if self.direction == 'long':
            if self.status == 'opening':
                return True
            else:
                return False
        else:
            if self.status == 'opening':
                return False
            else:
                return True

    def is_sell(self):
        return self.quantity < 0

    @abstractmethod
    def update_open_price(self, open_price: float):
        pass

    @abstractmethod
    def update_close_price(self, close_price: float):
        pass

    @abstractmethod
    def update_quantity(self, quantity: float):
        pass

    @abstractmethod
    def update_status_closed(self):
        pass

    @abstractmethod
    def update_status_closing(self):
        pass

    @staticmethod
    def check_price(price: float):
        if price < 0:
            raise ValueError(f'open must be positive, not "{price}"')

    @staticmethod
    def check_quantity(quantity: float):
        if quantity < 0:
            raise ValueError(f'quantity must be positive, not "{quantity}"')

    @staticmethod
    def check_direction(direction: str):
        if direction not in ['long', 'short']:
            raise ValueError(f'direction must be "long" or "short", not "{direction}"')

    @staticmethod
    def check_status(status: str):
        if status not in ['opening', 'closing', 'closed']:
            raise ValueError(f'status must be "opening" or "closing" or "closed", not "{status}"')

    @staticmethod
    def check_leverage(leverage: float):
        if leverage <= 0:
            raise ValueError(f'leverage must >= 0, not "{leverage}"')

    def link_observer(self, observer: Callable[[any], None] | None):
        """
        链接观察者方法
        :param observer: 观察者方法
        :return:
        """
        self.observer = observer


class VirtualOrderArrayInterface(ABC):
    """
    虚拟订单集合
    """

    def __init__(self, max_open_price: float, min_open_price: float, max_close_price: float, min_close_price: float,
                 order_type: str, direction: str, length):
        """

        :param max_open_price:
        :param min_open_price:
        :param max_close_price:
        :param min_close_price:
        :param order_type: 'open' or 'close'
        :param direction: 'long' or 'short'
        :param length:
        """
        if max_open_price <= min_open_price:
            raise ValueError(f'max_open_price{max_open_price} must be greater than min_open_price({min_open_price})')
        if max_close_price <= min_close_price:
            raise ValueError(
                f'max_close_price{max_close_price} must be greater than min_close_price({min_close_price})')
        if max_open_price < 0:
            raise ValueError(f'max_open_price{max_open_price} must be greater than 0')
        if min_close_price < 0:
            raise ValueError(f'min_close_price{min_close_price} must be greater than 0')
        if max_close_price < 0:
            raise ValueError(f'max_close_price{max_close_price} must be greater than 0')
        if min_open_price < 0:
            raise ValueError(f'min_open_price{min_open_price} must be greater than 0')

        self.length = length + 1

        self.max_open_price = max_open_price  # 开仓最高价格
        self.min_open_price = min_open_price  # 开仓最低价格
        self.max_close_price = max_close_price  # 平仓最高价格
        self.min_close_price = min_close_price  # 平仓最低价格

        if order_type not in ['open', 'close']:
            raise ValueError(f'order_type must be "open" or "close", not "{order_type}"')
        self.order_type = order_type

        if direction not in ['long', 'short']:
            raise ValueError(f'direction must be "long" or "short", not "{direction}"')
        self.direction = direction

        # 调整价格区间 保证各个MIN MAX值均在数组区间内
        self.price_step = (max_close_price - min_close_price) / length
        if order_type == 'open':
            if direction == 'long':
                # 做多开仓 将开仓最低价下移
                self.min_open_price -= (max_open_price - min_open_price) / length
            else:
                # 做空开仓 将开仓最高价上移
                self.max_open_price += (max_open_price - min_open_price) / length
        else:
            if direction == 'long':
                # 做多平仓 将平仓最高价上移
                self.max_close_price += (max_close_price - min_close_price) / length
            else:
                # 做空平仓 将平仓最低价下移
                self.min_close_price -= (max_close_price - min_close_price) / length

    @abstractmethod
    def add_order(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        插入一个order
        如果order.open_price不符合预期 则会插入失败
        :param order:
        :return: VirtualOrder | None
        若插入成功 返回VirtualOrder对象
        若插入失败 返回None
        """

    @abstractmethod
    def remove_order(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        删除一个order
        :param order:
        :return: VirtualOrder | None
        若删除成功 返回VirtualOrder对象
        若删除失败 返回None
        """

    @abstractmethod
    def check_order(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        判断一个order是否存在
        :param order:
        :return: VirtualOrder | None
        若order存在 返回VirtualOrder对象
        若order不存在 返回None
        """

    def get_position_by_price(self, price: float) -> int:
        self.check_price(price)
        if self.order_type == 'open':
            if self.direction == 'long':
                # 做多开仓 买入 按价格降序排列
                position = round(
                    (self.max_open_price - price) * self.length / (self.max_open_price - self.min_open_price))
            else:
                # 做空开仓 卖出 按价格升序排列
                position = round(
                    (price - self.min_open_price) * self.length / (self.max_open_price - self.min_open_price))
        else:
            if self.direction == 'long':
                # 做多平仓 卖出 按价格升序排列
                position = round(
                    (price - self.min_close_price) * self.length / (self.max_close_price - self.min_close_price))
            else:
                # 做空平仓 买入 按价格降序排列
                position = round(
                    (self.max_close_price - price) * self.length / (self.max_close_price - self.min_close_price))
        return position

    def get_price_by_position(self, position: int) -> float:
        self.check_position(position)
        if self.order_type == 'open':
            if self.direction == 'long':
                # 做多开仓 买入 按价格降序排列
                price = self.max_open_price - (self.max_open_price - self.min_open_price) * position / self.length
            else:
                # 做空开仓 卖出 按价格升序排列
                price = self.min_open_price + (self.max_open_price - self.min_open_price) * position / self.length
        else:
            if self.direction == 'long':
                # 做多平仓 卖出 按价格升序排列
                price = self.min_close_price + (self.max_close_price - self.min_close_price) * position / self.length
            else:
                # 做空平仓 买入 按价格降序排列
                price = self.max_close_price - (self.max_close_price - self.min_close_price) * position / self.length
        return price

    def check_position(self, position: int) -> bool:
        if position < 0 or position >= self.length:
            logging.info(f'ERROR-position must be between 0 and {self.length - 1}, not "{position}"')
            # raise ValueError(f'position must be between 0 and {self.length - 1}, not "{position}"')
            return False
        else:
            return True

    @staticmethod
    def check_price(price: float):
        if price <= 0:
            raise ValueError(f'open must be positive, not "{price}"')


class VirtualOrderBookInterface(ABC):
    """
    虚拟订单簿
    """

    def __init__(self, max_open_price: float, min_open_price: float, max_close_price: float, min_close_price: float,
                 open_array_length: int, close_array_length: int, direction: str, commission_rate: float):
        """
        1.open_order_array: open订单集合 继承VirtualOrderArrayInterface的类型
        2.close_order_array: close订单集合 继承VirtualOrderArrayInterface的类型
        3.closed_order_list: close订单集合 list类型
        :param max_open_price: 开仓最高价格
        :param min_open_price: 开仓最低价格
        :param max_close_price: 平仓最高价格
        :param min_close_price: 平仓最低价格
        :param open_array_length: open价格数量
        :param close_array_length: close价格数量
        :param direction: 订单类型 做多long | 做空short
        :param commission_rate: 佣金率
        """

        self.check_direction(direction)
        self.check_price(max_open_price)
        self.check_price(min_open_price)
        self.check_price(max_close_price)
        self.check_price(min_close_price)

        self.max_open_price = max_open_price  # 开仓最高价格
        self.min_open_price = min_open_price  # 开仓最低价格
        self.max_close_price = max_close_price  # 平仓最高价格
        self.min_close_price = min_close_price  # 平仓最低价格
        self.commission_rate = commission_rate
        self.direction = direction

        self.open_array_length = open_array_length
        self.close_array_length = close_array_length

        self.open_order_array: VirtualOrderArrayInterface | None = None  # 由子类注入
        self.close_order_array: VirtualOrderArrayInterface | None = None  # 由子类注入
        self.closed_order_list: List[VirtualOrder] = []

    @staticmethod
    def check_direction(direction: str):
        if direction not in ['long', 'short']:
            raise ValueError(f'direction must be "long" or "short", not "{direction}"')

    @staticmethod
    def check_price(price: float):
        if price < 0:
            raise ValueError(f'price must be positive, not "{price}"')

    @abstractmethod
    def add_order(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        插入一个open order
        如果order.open_price不符合预期 则会插入失败
        :param order:
        :return: VirtualOrder | None
        若插入成功 返回VirtualOrder对象
        若插入失败 返回None
        """

    @abstractmethod
    def update_order_closing(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        将一个open order 变为close order
        :param order:
        :return: VirtualOrder | None
        若成功 返回VirtualOrder对象
        若失败 返回None
        """

    @abstractmethod
    def update_order_closed(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        将一个close order 变为closed order
        :param order:
        :return: VirtualOrder | None
        若成功 返回VirtualOrder对象
        若失败 返回None
        """
