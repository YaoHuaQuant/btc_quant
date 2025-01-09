from typing import List, Dict

from strategy import VirtualOrderArrayInterface, VirtualOrderBookInterface, VirtualOrder
from strategy.virtual_order import VirtualOrderOne
from log import *


class OrderGroup:
    """
    订单组：表示在同一open价格下的订单集合。
    """

    def __init__(self):
        self.data: List[VirtualOrder] = []

    def add(self, order: VirtualOrder):
        self.data.append(order)

    def remove(self, order: VirtualOrder):
        self.data.remove(order)

    def get(self, index: int):
        return self.data[index]

    def get_last(self) -> VirtualOrder | None:
        if len(self.data) == 0:
            return None
        else:
            return self.data[-1]

    def len(self):
        return len(self.data)


class PriceOrderGroupVirtualCloseOrderArray(VirtualOrderArrayInterface):
    """
    在固定价格使用订单组的虚拟订单集合

    只存储close订单

    使用定长list(price_list)存储价格数据

    在每个价格存储一个list(order_group)，存储在该价格open的所有close订单。

    新增order操作：
    1.根据order的open_price 在 price_list 中查找对应的 order_group
    2.根据order_group的末端元素(last_order)的价格 调整新order的close_price
    3.close_price的计算逻辑：
        3.1 close_price = last_order.close_price + close_price_step
        3.2 if close_price > MAX_CLOSE_PRICE: close_price = open_price + close_price_step
    """

    def __init__(
            self, max_open_price: float, min_open_price: float, max_close_price: float, min_close_price: float,
            direction: str, length: int, percentage_minimum_profit: float, percentage_close_price_step: float,
            percentage_maximum_profit: float
    ):
        """

        :param max_open_price:
        :param min_open_price:
        :param max_close_price:
        :param min_close_price:
        :param direction: 'long' or 'short'
        :param length:
        :param percentage_minimum_profit:   最低利润率
        :param percentage_close_price_step: bubble价格梯度 即每次close_price上涨的比例
        :param percentage_maximum_profit:
        """

        super().__init__(
            max_open_price=max_open_price,
            min_open_price=min_open_price,
            max_close_price=max_close_price,
            min_close_price=min_close_price,
            order_type="close",
            direction=direction,
            length=length
        )

        self.percentage_minimum_profit = percentage_minimum_profit
        self.percentage_close_price_step = percentage_close_price_step
        self.percentage_maximum_profit = percentage_maximum_profit

        self.price_list: List[float] = list()
        self.price_order_group_dict: Dict[int, OrderGroup] = dict()

        # 初始化 self.price_list 和 self.price_order_group_dict
        for position in range(self.length):
            price = self.get_price_by_position(position)
            self.price_list.append(price)
            self.price_order_group_dict[position] = OrderGroup()

    def add_order(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        向self.price_order_group_dict中插入一个order
        如果order.open_price不符合预期 则会插入失败
        :param order:
        :return: VirtualOrder | None
        若插入成功 返回VirtualOrder对象
        若插入失败 返回None
        """
        position = self.get_position_by_price(order.open_price)
        if self.check_position(position):
            order_group = self.price_order_group_dict[position]

            close_price_step = order.open_price * self.percentage_close_price_step
            if order_group.len() == 0:
                close_price = order.open_price * (1 + self.percentage_minimum_profit)
            else:
                last_close_order: VirtualOrder = order_group.get_last()

                close_price = last_close_order.close_price + close_price_step

                # 最高价：单笔订单收益超过percentage_maximum_profit百分比的价格
                max_price = order.open_price * (1 + self.percentage_maximum_profit)
                if close_price >= max_price:  # 挂单价格不得超过最高价
                    # if close_price > self.max_close_price - self.price_step:    # 挂单价格不得超过 self.max_close_price
                    close_price = order_group.get(0).close_price
            order.update_close_price(close_price)
            order_group.add(order)
            return order
        return None

    def remove_order(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        删除一个order
        :param order:
        :return: VirtualOrder | None
        若删除成功 返回VirtualOrder对象
        若删除失败 返回None
        """
        position = self.get_position_by_price(order.open_price)
        if self.check_position(position):
            order_group = self.price_order_group_dict[position]
            for o in order_group.data:
                if o.close_price == order.close_price:
                    order_group.remove(o)
                    return o
        return None

    def check_order(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        不使用该函数
        :param order:
        :return:
        """
        return None

    def log(self):
        for position in range(self.length):
            price = self.price_list[position]
            order_group = self.price_order_group_dict[position]
            logging.info(f'{price}: {order_group.data}')


class PriceOrderGroupVirtualOpenOrderArray(VirtualOrderArrayInterface):
    """
    固定价格虚拟订单集合
    只存储open订单
    使用定长list存储挂单数据
    """

    def __init__(self, max_open_price: float, min_open_price: float, max_close_price: float, min_close_price: float,
                 direction: str, length: int = -1):
        """

        :param max_open_price:
        :param min_open_price:
        :param max_close_price:
        :param min_close_price:
        :param direction: 'long' or 'short'
        :param length:
        """
        super().__init__(
            max_open_price=max_open_price,
            min_open_price=min_open_price,
            max_close_price=max_close_price,
            min_close_price=min_close_price,
            order_type="open",
            direction=direction,
            length=length
        )
        self.price_list: List[float] = list()
        self.position_order_dict: Dict[int, VirtualOrder] = dict()

        for position in range(self.length):
            price = self.get_price_by_position(position)
            self.price_list.append(price)

    def add_order(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        插入一个order
        如果order.open_price不符合预期 则会插入失败
        :param order:
        :return: VirtualOrder | None
        若插入成功 返回VirtualOrder对象
        若插入失败 返回None
        """
        position = self.get_position_by_price(order.open_price)
        if self.check_position(position):
            # 判断当前position是否有order 若无 则插入
            if not self.position_order_dict.__contains__(position):
                price = self.get_price_by_position(position)
                order.update_open_price(price)
                self.position_order_dict[position] = order
                return order
        return None

    def remove_order(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        删除一个order
        :param order:
        :return: VirtualOrder | None
        若删除成功 返回VirtualOrder对象
        若删除失败 返回None
        """
        position = self.get_position_by_price(order.open_price)
        if self.check_position(position):
            if self.position_order_dict.__contains__(position):
                order = self.position_order_dict.pop(position)
                return order
        return None

    def check_order(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        判断一个order是否存在
        :param order:
        :return: VirtualOrder | None
        若order存在 返回VirtualOrder对象
        若order不存在 返回None
        """
        position = self.get_position_by_price(order.open_price)
        if self.position_order_dict.__contains__(position):
            return self.position_order_dict.get(position)
        else:
            return None

    def __repr__(self):
        return f"PriceOrderGroupVirtualOpenOrderArray({self.position_order_dict})"


class PriceOrderGroupVirtualOrderBook(VirtualOrderBookInterface):
    def __init__(
            self, max_open_price: float, min_open_price: float, max_close_price: float, min_close_price: float,
            open_array_length: int, close_array_length: int,
            percentage_minimum_profit: float,
            percentage_close_price_step: float,
            percentage_maximum_profit: float,
            direction: str = 'long',
            commission_rate: float = 0.0002
    ):
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
        :param percentage_minimum_profit:   最低利润率
        :param percentage_close_price_step: bubble价格梯度 即每次close_price上涨的比例
        :param percentage_maximum_profit:
        :param direction: 订单类型 做多long | 做空short
        :param commission_rate: 佣金率
        """

        super().__init__(max_open_price, min_open_price, max_close_price, min_close_price, open_array_length,
                         close_array_length, direction, commission_rate)

        self.open_order_array: VirtualOrderArrayInterface = PriceOrderGroupVirtualOpenOrderArray(
            max_open_price=max_open_price,
            min_open_price=min_open_price,
            max_close_price=max_close_price,
            min_close_price=min_close_price,
            direction=direction,
            length=open_array_length,
        )
        self.close_order_array: VirtualOrderArrayInterface = PriceOrderGroupVirtualCloseOrderArray(
            max_open_price=max_open_price,
            min_open_price=min_open_price,
            max_close_price=max_close_price,
            min_close_price=min_close_price,
            direction=direction,
            length=close_array_length,
            percentage_minimum_profit=percentage_minimum_profit,
            percentage_close_price_step=percentage_close_price_step,
            percentage_maximum_profit=percentage_maximum_profit
        )

    def add_order(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        插入一个open order
        如果order.open_price不符合预期 则会插入失败
        :param order:
        :return: VirtualOrder | None
        若插入成功 返回VirtualOrder对象
        若插入失败 返回None
        """
        return self.open_order_array.add_order(order)

    def update_order_closing(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        将一个open order 变为close order
        :param order:
        :return: VirtualOrder | None
        若成功 返回VirtualOrder对象
        若失败 返回None
        """
        order = self.open_order_array.remove_order(order)
        if order is not None:
            return self.close_order_array.add_order(order)
        else:
            return None

    def update_order_closed(self, order: VirtualOrder) -> VirtualOrder | None:
        """
        将一个close order 变为closed order
        :param order:
        :return: VirtualOrder | None
        若成功 返回VirtualOrder对象
        若失败 返回None
        """
        order = self.close_order_array.remove_order(order)
        if order is not None:
            self.closed_order_list.append(order)
            return order
        else:
            return None


def test_close_array():
    max_open_price: float = 30
    min_open_price: float = 0
    max_close_price: float = 31
    min_close_price: float = 1
    direction: str = 'long'
    length: int = 10
    percentage_minimum_profit: float = 0.5
    percentage_close_price_step: float = 0.25
    array = PriceOrderGroupVirtualCloseOrderArray(
        max_open_price=max_open_price,
        min_open_price=min_open_price,
        max_close_price=max_close_price,
        min_close_price=min_close_price,
        direction=direction,
        length=length,
        percentage_minimum_profit=percentage_minimum_profit,
        percentage_close_price_step=percentage_close_price_step,
    )

    logging.info(f"======== add =========")
    order = array.add_order(VirtualOrderOne(open_price=10, close_price=10, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")
    order = array.add_order(VirtualOrderOne(open_price=10, close_price=10, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")
    order = array.add_order(VirtualOrderOne(open_price=10, close_price=10, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")
    order = array.add_order(VirtualOrderOne(open_price=10, close_price=10, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")
    order = array.add_order(VirtualOrderOne(open_price=10, close_price=10, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")
    order = array.add_order(VirtualOrderOne(open_price=10, close_price=10, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")
    order = array.add_order(VirtualOrderOne(open_price=10, close_price=10, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")
    order = array.add_order(VirtualOrderOne(open_price=10, close_price=10, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")
    order = array.add_order(VirtualOrderOne(open_price=10, close_price=10, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")
    order = array.add_order(VirtualOrderOne(open_price=10, close_price=10, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")

    logging.info(f"======== remove =========")
    order = array.remove_order(VirtualOrderOne(open_price=10, close_price=15, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")
    order = array.remove_order(VirtualOrderOne(open_price=10, close_price=15, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")
    order = array.remove_order(VirtualOrderOne(open_price=10, close_price=15, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")
    order = array.remove_order(VirtualOrderOne(open_price=10, close_price=15, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")
    order = array.remove_order(VirtualOrderOne(open_price=10, close_price=20, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")
    order = array.remove_order(VirtualOrderOne(open_price=10, close_price=20, quantity=1, direction='long'))
    array.log()
    logging.info(f"order:{order}\n")


def test_open_array():
    max_open_price: float = 30
    min_open_price: float = 0
    max_close_price: float = 31
    min_close_price: float = 1
    direction: str = 'long'
    length: int = 10
    array = PriceOrderGroupVirtualOpenOrderArray(
        max_open_price=max_open_price,
        min_open_price=min_open_price,
        max_close_price=max_close_price,
        min_close_price=min_close_price,
        direction=direction,
        length=length,
    )

    logging.info(f"======== add =========")

    order = array.add_order(VirtualOrderOne(open_price=10, close_price=10, quantity=1, direction='long'))
    logging.info(f"order:{order}\tarray:{array}")
    order = array.add_order(VirtualOrderOne(open_price=9, close_price=10, quantity=1, direction='long'))
    logging.info(f"order:{order}\tarray:{array}")
    order = array.add_order(VirtualOrderOne(open_price=8, close_price=10, quantity=1, direction='long'))
    logging.info(f"order:{order}\tarray:{array}")
    order = array.add_order(VirtualOrderOne(open_price=7, close_price=10, quantity=1, direction='long'))
    logging.info(f"order:{order}\tarray:{array}")
    order = array.add_order(VirtualOrderOne(open_price=6, close_price=10, quantity=1, direction='long'))
    logging.info(f"order:{order}\tarray:{array}")

    logging.info(f"======== remove =========")

    order = array.remove_order(VirtualOrderOne(open_price=10, close_price=10, quantity=1, direction='long'))
    logging.info(f"order:{order}\tarray:{array}")
    order = array.remove_order(VirtualOrderOne(open_price=9, close_price=10, quantity=1, direction='long'))
    logging.info(f"order:{order}\tarray:{array}")
    order = array.remove_order(VirtualOrderOne(open_price=8, close_price=10, quantity=1, direction='long'))
    logging.info(f"order:{order}\tarray:{array}")
    order = array.remove_order(VirtualOrderOne(open_price=7, close_price=10, quantity=1, direction='long'))
    logging.info(f"order:{order}\tarray:{array}")
    order = array.remove_order(VirtualOrderOne(open_price=6, close_price=10, quantity=1, direction='long'))
    logging.info(f"order:{order}\tarray:{array}")


def test_order_book():
    max_open_price: float = 30
    min_open_price: float = 0
    max_close_price: float = 31
    min_close_price: float = 1
    direction: str = 'long'
    open_array_length: int = 10
    close_array_length: int = 10
    percentage_minimum_profit: float = 0.5
    percentage_close_price_step: float = 0.25
    book = PriceOrderGroupVirtualOrderBook(
        max_open_price=max_open_price,
        min_open_price=min_open_price,
        max_close_price=max_close_price,
        min_close_price=min_close_price,
        direction=direction,
        open_array_length=open_array_length,
        close_array_length=close_array_length,
        percentage_minimum_profit=percentage_minimum_profit,
        percentage_close_price_step=percentage_close_price_step,
    )

    open_array = book.open_order_array
    close_array: PriceOrderGroupVirtualCloseOrderArray = book.close_order_array
    open_order_list = []
    closing_order_list = []

    logging.info(f"======== open =========")
    logging.info(f"======== closing =========")

    for open_price in [15, 15, 15, 15, 15, 15, 15, 15]:
        order = book.add_order(VirtualOrderOne(open_price=open_price, close_price=10, quantity=1, direction='long'))
        logging.info(f"order:{order}\nopen_array:{open_array}")
        logging.info(f"close_array:")
        close_array.log()
        logging.info(f"\n")
        if order is not None:
            open_order_list.append(order)

        order = book.update_order_closing(order)
        logging.info(f"order:{order}\nopen_array:{open_array}")
        logging.info(f"close_array:")
        close_array.log()
        logging.info(f"\n")
        if order is not None:
            closing_order_list.append(order)

    logging.info(f"======== closed =========")
    for o in closing_order_list:
        order = book.update_order_closed(o)
        logging.info(f"order:{order}\nopen_array:{open_array}")
        logging.info(f"close_array:")
        close_array.log()
        logging.info(f"\n")
        logging.info(f"order:{order}\narray:{book.close_order_array}")


if __name__ == '__main__':
    # test_open_array()
    # test_close_array()
    test_order_book()
