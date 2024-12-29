import math

from log import *


class MyOrderPair:
    """
    订单Pair
    包含一个open order和一个close order
    """

    def __init__(self, open_price: float, close_price: float, quantity: float,
                 commission_rate: float = 0.0002):
        """
        先有开仓单，然后才有MyOrderPair对象。
        属性：
        1.open_price 开仓价格
        2.close_price 平仓价格
        2.quantity (不可变)挂单量
        3.direction: (不可变)订单类型 做多long | 做空short
        4.status: 订单状态 待开仓opening | 待平仓closing | 已平仓closed
        5.expected_gross_value 期望毛利润
        6.actual_gross_value  实际毛利润
        7.expected_commission 期望佣金值
        7.actual_commission 实际佣金值
        :param open_price: 开仓价格
        :param quantity:  挂单量
        :param commission_rate: 佣金率
        """
        self.check_price(open_price)
        self.check_price(close_price)
        self.check_quantity(quantity)

        self.open_price = open_price
        self.close_price = close_price
        self.quantity = quantity
        self.status = 'opening'
        self.expected_gross_value = None
        self.actual_gross_value = None
        self.commission_rate = commission_rate
        self.expected_commission = None
        self.actual_commission = None

        self.update_open_price(open_price)
        self.update_close_price(close_price)

    def update_status_closing(self):
        """
        open订单成交
        将订单状态转换为 'closing'
        需计算open阶段产生的 实际佣金 和 实际毛利润
        :return:
        """
        self.status = 'closing'
        self.actual_commission = self.open_price * self.commission_rate * self.quantity
        # self.actual_gross_value = (self.open_price - self.close_price) * self.quantity
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
        self.open_price = price
        self.expected_commission = (self.open_price + self.close_price) * self.commission_rate * self.quantity
        self.expected_gross_value = (self.close_price - self.open_price) * self.quantity

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
        self.close_price = price
        if self.status == 'closing':
            """
            在 'closing' 状态下需要计算 期望佣金 和 期望毛利润
            """
            self.expected_commission = self.actual_commission + self.close_price * self.commission_rate * self.quantity
            self.expected_gross_value = (self.close_price - self.open_price) * self.quantity

    def actual_net_value(self) -> float | None:
        if self.status != 'closed':
            return None
        else:
            return self.actual_gross_value - self.actual_commission

    @staticmethod
    def check_price(price: float):
        if price <= 0:
            raise ValueError(f'open must be positive, not "{price}"')

    @staticmethod
    def check_quantity(quantity: float):
        if quantity <= 0:
            raise ValueError(f'quantity must be positive, not "{quantity}"')

    @staticmethod
    def check_status(status: str):
        if status not in ['opening', 'closing', 'closed']:
            raise ValueError(f'status must be "opening" or "closing" or "closed", not "{status}"')

    def __repr__(self):
        return f"MyOrderPair({self.status},{self.open_price},{self.close_price},{self.quantity},{self.expected_commission},{self.actual_commission},{self.expected_gross_value},{self.actual_gross_value},{self.actual_net_value()})"


class MyOrderArray:
    """
    订单簿数组
    使用定长list存储挂单数据
    可以实现订单冒泡操作
    self.data是一个list，存储None或者MyOrderPair：
    数组的每个下标表示订单的价格，None表示该价格不存在挂单，MyOrderPair表示该价格存在一个挂单
    """

    def __init__(self, length: int = -1, data: list = None):
        if data is None:
            self.length = length
            self.data = [None] * length
        else:
            self.length = len(data)
            self.data = data

    def get(self, position: int) -> MyOrderPair | None:
        return self.data[position]

    def pop(self, position: int) -> MyOrderPair | None:
        order = self.get(position)
        self.data[position] = None
        return order

    def add_order(self, position: int, order: MyOrderPair) -> MyOrderPair | None:
        result = self.bubble(position)
        self.data[position] = order
        return result

    def check_position(self, position: int):
        if position < 0 or position >= len(self.data):
            raise ValueError(f'position must be between 0 and {self.length - 1}, not "{position}"')

    def bubble(self, end: int) -> MyOrderPair | None:
        """
        对订单进行冒泡操作
        从end位置开始(包括end)，向前找一个None值的位置作为start
        将end与start之前的区间均左移一位，将None移至区间最右
        若无法左移，则返回最左的一个元素，并将其他元素左移
        若能左移 则返回None
        """
        start = -1
        for i in range(end, -1, -1):
            if self.data[i] is None:
                start = i
                break
        if start >= 0:
            # logging.info(f"bubble：start={start}, end={end}")
            self.slice_shift(start, end + 1)
            return None
        else:
            obj = self.pop(0)
            self.slice_shift(0, end + 1)
            # logging.info(f"bubble: pop head={obj}, end={end}")
            return obj

    def slice_shift(self, start: int, end: int, direction="left"):
        """
        对切片进行平移
        """
        sliced = self.data[start:end]
        if direction == "right":
            sliced = sliced[-1:] + sliced[:-1]  # 向右平移
        else:
            sliced = sliced[1:] + sliced[:1]  # 向左平移
        self.data[start:end] = sliced

    def __repr__(self):
        return f"OrderArray({self.data})"


class MyOrderArrayTriple:
    """
    三订单队列组
    包含：
    1.open OrderArray
    2.close OrderArray
    3.closed OrderArray
    """

    def __init__(self, max_open_price: float, min_open_price: float, max_close_price: float, min_close_price: float,
                 open_array_length: int, close_array_length: int, direction: str = 'long',
                 commission_rate: float = 0.0002):
        """
        属性：
        1.open_order_array: MyOrderArray类型
        2.close_order_array: MyOrderArray类型
        3.closed_order_array: python list类似
        :param max_open_price: 开仓最高价格
        :param min_open_price: 开仓最低价格
        :param max_close_price: 平仓最高价格
        :param min_close_price: 平仓最低价格
        :param open_array_length:
        :param close_array_length:
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

        self.open_order_array = MyOrderArray(length=open_array_length)
        self.close_order_array = MyOrderArray(length=close_array_length)
        self.closed_order_array = []

    def add_open_order(self, open_price: float, close_price: float, quantity: int) -> MyOrderPair | None:
        order = MyOrderPair(open_price, close_price, quantity, commission_rate=self.commission_rate)
        return self.add_open_order_object(order)

    def add_open_order_object(self, order: MyOrderPair) -> MyOrderPair | None:
        position = self.get_open_order_position(order.open_price)
        return self.open_order_array.add_order(position, order)

    def get_open_order_position(self, open_price: float) -> int:
        position = math.floor(
            (open_price - self.min_open_price) * self.open_array_length / (self.max_open_price - self.min_open_price))
        return position

    def get_open_order(self, open_price: float) -> MyOrderPair:
        position = self.get_open_order_position(open_price)
        order = self.open_order_array.get(position)
        if order is None:
            raise ValueError(f'can not find close order with open_price-"{open_price}" and position-"{position}"')
        return order

    def add_close_order_object(self, order: MyOrderPair) -> MyOrderPair | None:
        position = self.get_close_order_position(order.close_price)
        return self.close_order_array.add_order(position, order)

    def get_close_order_position(self, close_price: float) -> int:
        position = math.floor(
            (close_price - self.min_close_price) * self.close_array_length / (
                        self.max_close_price - self.min_close_price))
        return position

    def get_close_order(self, close_price: float) -> MyOrderPair:
        position = self.get_close_order_position(close_price)
        order = self.close_order_array.get(position)
        if order is None:
            raise ValueError(f'can not find close order with open_price-"{close_price}" and position-"{position}"')
        return order

    def open_order_complete(self, open_price: float) -> MyOrderPair | None:
        position = self.get_open_order_position(open_price)
        order = self.open_order_array.pop(position)
        if order is None:
            raise ValueError(f'can not find open order with open_price-"{open_price}" and position-"{position}"')
        order.update_status_closing()
        new_order = self.add_close_order_object(order)
        return new_order

    def close_order_complete(self, close_price: float):
        position = self.get_close_order_position(close_price)
        order = self.close_order_array.pop(position)
        if order is None:
            raise ValueError(f'can not find close order with close_price-"{close_price}" and position-"{position}"')
        order.update_status_closed()
        self.closed_order_array.append(order)

    @staticmethod
    def check_direction(direction: str):
        if direction not in ['long', 'short']:
            raise ValueError(f'direction must be "long" or "short", not "{direction}"')

    @staticmethod
    def check_price(price: float):
        if price <= 0:
            raise ValueError(f'open must be positive, not "{price}"')

    def __repr__(self):
        return f"MyOrderArrayPair:\nOpenArray:{self.open_order_array}\nCloseArray:{self.close_order_array}\nClosedArray:{self.closed_order_array}"


def test_order_array():
    # 使用自定义的定长数组类
    arr = MyOrderArray(length=10)
    print(arr)
    result = arr.add_order(order=MyOrderPair(open_price=2, close_price=1, quantity=2), position=2)
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrderPair(open_price=3, close_price=1, quantity=3), position=3)
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrderPair(open_price=4, close_price=1, quantity=4), position=3)
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrderPair(open_price=5, close_price=1, quantity=5), position=3)
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrderPair(open_price=6, close_price=1, quantity=6), position=3)
    print(f"result={result}, arr={arr}")

    result = arr.add_order(order=MyOrderPair(open_price=7, close_price=1, quantity=7), position=7)
    print(f"result={result}, arr={arr}")

    result = arr.add_order(order=MyOrderPair(open_price=8, close_price=1, quantity=8), position=8)
    print(f"result={result}, arr={arr}")

    result = arr.add_order(order=MyOrderPair(open_price=9, close_price=1, quantity=9), position=8)
    print(f"result={result}, arr={arr}")

    result = arr.add_order(order=MyOrderPair(open_price=10, close_price=1, quantity=10), position=8)
    print(f"result={result}, arr={arr}")


def test_my_order_pair():
    order = MyOrderPair(open_price=1, close_price=2, quantity=10)
    logging.info(f"order={order}")
    order.update_status_closing()
    logging.info(f"order={order}")
    order.update_close_price(3)
    logging.info(f"order={order}")
    order.update_close_price(4)
    logging.info(f"order={order}")
    order.update_status_closed()
    logging.info(f"order={order}")


def test_my_order_array_triple():
    max_open_price = 100
    min_open_price = 50
    max_close_price = 110
    min_close_price = 50
    open_array_length = 5
    close_array_length = 6
    direction = 'long'
    commission_rate = 0.0002
    data = MyOrderArrayTriple(max_open_price=max_open_price, min_open_price=min_open_price,
                            max_close_price=max_close_price, min_close_price=min_close_price,
                            open_array_length=open_array_length, close_array_length=close_array_length,
                            direction=direction, commission_rate=commission_rate)
    logging.info(f"data={data}")
    data.add_open_order(open_price=50, close_price=60, quantity=1)
    data.add_open_order(open_price=60, close_price=70, quantity=1)
    data.add_open_order(open_price=70, close_price=80, quantity=1)
    logging.info(f"data={data}")
    data.open_order_complete(open_price=50)
    data.open_order_complete(open_price=60)
    logging.info(f"data={data}")
    data.close_order_complete(close_price=70)
    logging.info(f"data={data}")


if __name__ == '__main__':
    test_order_array()
    # test_my_order_pair()
    # test_my_order_array_triple()
