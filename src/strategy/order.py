import math

import backtrader as bt
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
        8.actual_commission 实际佣金值
        9.present_order 关联backtrader.order
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
        self.expected_gross_value = (close_price - open_price) * quantity
        self.actual_gross_value = None
        self.commission_rate = commission_rate
        self.expected_commission = (open_price + close_price) * commission_rate * quantity
        self.actual_commission = None

        self.update_open_price(open_price)
        self.update_close_price(close_price)

        self.present_order: None | bt.order = None

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
        if self.open_price != price:
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
        if self.close_price != price:
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

    def link_order(self, order: bt.Order):
        self.present_order = order

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

    def __init__(self, max_open_price: float, min_open_price: float, max_close_price: float, min_close_price: float,
                 order_type: str, direction: str, length: int = -1):
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
        self.data = [None] * self.length

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

    def get(self, position: int) -> MyOrderPair | None:
        return self.data[position]

    def pop(self, position: int) -> MyOrderPair | None:
        order = self.get(position)
        self.data[position] = None
        return order

    def add_order(self, order: MyOrderPair, position: int | None = None) -> MyOrderPair | None:
        if position is None:
            if self.order_type == 'open':
                position = self.get_position_by_price(order.open_price)
                price = self.get_price_by_position(position)
                order.update_open_price(price)
            else:
                position = self.get_position_by_price(order.close_price)
                price = self.get_price_by_position(position)
                order.update_close_price(price)
        if self.check_position(position):
            result = self.bubble(position)
            self.data[position] = order
        else:
            result = False
        return result

    def get_order_by_position(self, position: int) -> MyOrderPair | None:
        return self.data[position]

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

    def get_order_by_price(self, price: float) -> MyOrderPair | None:
        position = self.get_position_by_price(price)
        return self.get_order_by_position(position)

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
        if position < 0 or position >= len(self.data):
            logging.info(f'ERROR-position must be between 0 and {self.length - 1}, not "{position}"')
            # raise ValueError(f'position must be between 0 and {self.length - 1}, not "{position}"')
            return False
        else:
            return True

    def check_price(self, price: float):
        if price <= 0:
            raise ValueError(f'open must be positive, not "{price}"')
        # if self.order_type == 'open':
        #     if price < self.min_open_price or price > self.max_open_price:
        #         raise ValueError(f'price must between {self.min_open_price} and {self.max_open_price}, not "{price}"')
        # else:
        #     if price < self.min_close_price or price > self.max_close_price:
        #         raise ValueError(f'price must between {self.min_close_price} and {self.max_close_price}, not "{price}"')

    def bubble(self, start: int) -> MyOrderPair | None:
        """
        对订单进行冒泡操作
        从start位置开始(包括start)，向后找一个None值的位置作为end
        将start与end之前的区间均左移一位，将最右的None弹出，最左位置填充None
        若无法右移，则返回最右的一个元素，并将其他元素右移
        若能右移 则返回None
        所有产生右移的订单 需要调整价格
        """
        end = self.length - 1
        for i in range(start, self.length):
            if self.data[i] is None:
                end = i
                break
        result: MyOrderPair | None = self.pop(end)
        for i in range(end - 1, start - 1, -1):
            new_data: MyOrderPair | None = self.data[i]
            if type(new_data) is MyOrderPair:
                if self.order_type == 'open':
                    new_data.update_open_price(self.get_price_by_position(i + 1))
                elif self.order_type == 'close':
                    new_data.update_close_price(self.get_price_by_position(i + 1))
                else:
                    raise ValueError(f'order_type must be "open" or "close", not "{self.order_type}"')
            self.data[i + 1] = new_data
            self.data[i] = None
        return result

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

        self.open_order_array = MyOrderArray(
            length=open_array_length,
            max_open_price=max_open_price,
            min_open_price=min_open_price,
            max_close_price=max_close_price,
            min_close_price=min_close_price,
            order_type='open',
            direction=direction
        )
        self.close_order_array = MyOrderArray(
            length=close_array_length,
            max_open_price=max_open_price,
            min_open_price=min_open_price,
            max_close_price=max_close_price,
            min_close_price=min_close_price,
            order_type='close',
            direction=direction
        )
        self.closed_order_array = []

    def add_open_order(self, open_price: float, close_price: float, quantity: int) -> MyOrderPair | None:
        order = MyOrderPair(open_price, close_price, quantity, commission_rate=self.commission_rate)
        return self.add_open_order_object(order)

    def add_open_order_object(self, order: MyOrderPair) -> MyOrderPair | None:
        return self.open_order_array.add_order(order)

    def get_open_order(self, open_price: float) -> MyOrderPair:
        order = self.open_order_array.get_order_by_price(open_price)
        if order is None:
            raise ValueError(f'can not find close order with open_price-"{open_price}"')
        return order

    def add_close_order_object(self, order: MyOrderPair) -> MyOrderPair | None:
        return self.close_order_array.add_order(order)

    def get_close_order(self, close_price: float) -> MyOrderPair:
        order = self.close_order_array.get_order_by_price(close_price)
        if order is None:
            raise ValueError(f'can not find close order with open_price-"{close_price}"')
        return order

    def open_order_complete(self, open_price: float) -> MyOrderPair | None:
        position = self.open_order_array.get_position_by_price(open_price)
        order = self.open_order_array.pop(position)
        if order is None:
            raise ValueError(f'can not find open order with open_price-"{open_price}" and position-"{position}"')
        order.update_status_closing()
        new_order = self.add_close_order_object(order)
        return new_order

    def close_order_complete(self, close_price: float):
        position = self.close_order_array.get_position_by_price(close_price)
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


def test_order_array1():
    # 使用自定义的定长数组类

    arr = MyOrderArray(
        length=10, max_open_price=11, min_open_price=1, max_close_price=21, min_close_price=11, order_type='open',
        direction='short'
    )
    print(arr)
    result = arr.add_order(order=MyOrderPair(open_price=3, close_price=10, quantity=10))
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrderPair(open_price=3, close_price=10, quantity=10))
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrderPair(open_price=6, close_price=10, quantity=10))
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrderPair(open_price=6, close_price=10, quantity=10))
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrderPair(open_price=6, close_price=10, quantity=10))
    print(f"result={result}, arr={arr}")

    result = arr.add_order(order=MyOrderPair(open_price=2, close_price=10, quantity=10))
    print(f"result={result}, arr={arr}")

    result = arr.add_order(order=MyOrderPair(open_price=2, close_price=10, quantity=10))
    print(f"result={result}, arr={arr}")

    result = arr.add_order(order=MyOrderPair(open_price=2, close_price=10, quantity=10))
    print(f"result={result}, arr={arr}")

    result = arr.add_order(order=MyOrderPair(open_price=2, close_price=10, quantity=10))
    print(f"result={result}, arr={arr}")


def test_order_array2():
    # 使用自定义的定长数组类

    arr = MyOrderArray(
        length=5, max_open_price=11, min_open_price=1, max_close_price=21, min_close_price=11, order_type='close',
        direction='short'
    )
    print(arr)
    result = arr.add_order(order=MyOrderPair(open_price=7, close_price=17, quantity=10))
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrderPair(open_price=7, close_price=17, quantity=10))
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrderPair(open_price=7, close_price=17, quantity=10))
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrderPair(open_price=7, close_price=17, quantity=10))
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrderPair(open_price=7, close_price=17, quantity=10))
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrderPair(open_price=7, close_price=17, quantity=10))
    print(f"result={result}, arr={arr}")


def test_order_array3():
    # 使用自定义的定长数组类

    arr = MyOrderArray(
        length=5, max_open_price=11, min_open_price=1, max_close_price=11, min_close_price=1, order_type='open',
        direction='short'
    )
    print(arr)
    price = 4
    position = arr.get_position_by_price(price)
    new_price = arr.get_price_by_position(position)
    logging.info(f"price={price}, position={position}, new_price={new_price}")

    position = 5
    price = arr.get_price_by_position(position)
    logging.info(f"position={position}, price={price}")


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


def test_my_order_array_consistency():
    # 一致性测试
    #
    max_open_price = 102504.3525
    min_open_price = 61088.4525
    max_close_price = 108716.7375
    min_close_price = 62123.85
    open_array_length = 401
    close_array_length = 501
    commission_rate = 0.0002
    direction = 'long'
    data = MyOrderArrayTriple(max_open_price=max_open_price, min_open_price=min_open_price,
                              max_close_price=max_close_price, min_close_price=min_close_price,
                              open_array_length=open_array_length, close_array_length=close_array_length,
                              direction=direction, commission_rate=commission_rate)
    for test_price in [102297.27299999999, 102194.50786159601, 102193.73324999999, 102091.22631546135]:
        position = data.open_order_array.get_position_by_price(test_price)
        new_price = data.open_order_array.get_price_by_position(position)
        new_position = data.open_order_array.get_position_by_price(new_price)
        logging.info(f"price={test_price}, position={position}, new_price={new_price}, new_position={new_position}")
        assert (position == new_position)


def test_my_order_array_consistency2():
    # 一致性测试
    #
    max_open_price = 102504.3525
    min_open_price = 61088.4525
    max_close_price = 108716.7375
    min_close_price = 62123.85
    open_array_length = 400
    close_array_length = 500
    direction = 'long'
    commission_rate = 0.0002
    data = MyOrderArrayTriple(max_open_price=max_open_price, min_open_price=min_open_price,
                              max_close_price=max_close_price, min_close_price=min_close_price,
                              open_array_length=open_array_length, close_array_length=close_array_length,
                              direction=direction, commission_rate=commission_rate)
    for position in range(10):
        price1 = data.open_order_array.get_price_by_position(position)
        position2 = data.open_order_array.get_position_by_price(price1)
        price2 = data.open_order_array.get_price_by_position(position2)
        position3 = data.open_order_array.get_position_by_price(price2)
        price3 = data.open_order_array.get_price_by_position(position3)
        logging.info(
            f"position={position}\tprice1={price1}\tposition2={position2}\tprice2={price2}\tposition3={position3}\tprice3={price3}")
        if position2 != position3:
            logging.info(f"ERROR-position not consistent: position2={position2}, position3={position3}")
        if price2 != price3:
            logging.info(f"ERROR-price not consistent: price2={price2}, price3={price3}")


def test_my_order_array_consistency3():
    # 一致性测试
    #
    max_open_price = 102504.3525
    min_open_price = 61088.4525
    max_close_price = 108716.7375
    min_close_price = 62123.85
    open_array_length = 400
    close_array_length = 500
    direction = 'long'
    commission_rate = 0.0002
    data = MyOrderArrayTriple(max_open_price=max_open_price, min_open_price=min_open_price,
                              max_close_price=max_close_price, min_close_price=min_close_price,
                              open_array_length=open_array_length, close_array_length=close_array_length,
                              direction=direction, commission_rate=commission_rate)
    for position in range(380,400):
        price1 = data.close_order_array.get_price_by_position(position)
        position2 = data.close_order_array.get_position_by_price(price1)
        price2 = data.close_order_array.get_price_by_position(position2)
        position3 = data.close_order_array.get_position_by_price(price2)
        price3 = data.close_order_array.get_price_by_position(position3)
        logging.info(
            f"position={position}\tprice1={price1}\tposition2={position2}\tprice2={price2}\tposition3={position3}\tprice3={price3}")
        if position2 != position3:
            logging.info(f"ERROR-position not consistent: position2={position2}, position3={position3}")
        if price2 != price3:
            logging.info(f"ERROR-price not consistent: price2={price2}, price3={price3}")


if __name__ == '__main__':
    # test_order_array3()
    # test_my_order_pair()
    # test_my_order_array_triple()
    test_my_order_array_consistency3()
