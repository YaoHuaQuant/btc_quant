from log import *


class MyOrder:
    def __init__(self, price: float, quantity: float, order_type: str = 'open', status: str = 'submitted'):
        """
        :param price: 挂单价格
        :param quantity:  挂单量
        :param order_type:  订单类型 开单open | 平单close
        :param status: 订单状态 submitted | completed
        """
        self.check_price(price)
        self.check_type(order_type)
        self.check_quantity(quantity)
        self.check_status(status)

        self.price = price
        self.quantity = quantity
        self.order_type = order_type
        self.status = status

    def update_price(self, price: float):
        self.check_price(price)
        self.price = price

    def update_quantity(self, quantity: float):
        self.check_quantity(quantity)
        self.quantity = quantity

    def update_status(self, status: str):
        self.check_status(status)
        self.status = status

    def update_type(self, order_type: str):
        self.check_type(order_type)
        self.order_type = order_type

    @staticmethod
    def check_price(price: float):
        if price <= 0:
            raise ValueError(f'price must be positive, not "{price}"')

    @staticmethod
    def check_quantity(quantity: float):
        if quantity <= 0:
            raise ValueError(f'quantity must be positive, not "{quantity}"')

    @staticmethod
    def check_type(order_type: str):
        if order_type not in ['open', 'close']:
            raise ValueError(f'order_type must be "open" or "close", not "{order_type}"')

    @staticmethod
    def check_status(status: str):
        if status not in ['submitted', 'completed']:
            raise ValueError(f'status must be "submitted" or "completed", not "{status}"')

    def __repr__(self):
        # return f"MyOrder(type={self.order_type}, status={self.status}, price={self.price}, quantity={self.quantity})"
        return f"MyOrder({self.price},{self.quantity})"


class MyOrderArray:
    """
    订单簿数组
    定长list
    可以实现订单冒泡操作
    """

    def __init__(self, length: int = -1, data: list = None):
        if data is None:
            self.length = length
            self.data = [None] * length
        else:
            self.length = len(data)
            self.data = data

    def add_order(self, position: int, order: MyOrder) -> bool:
        self.check_order_position(position)
        if self.data[position] is not None:
            # position位置已有order的情况
            # 先尝试bubble
            if self.bubble(position):
                # 若bubble成功，直接插入，返回True
                self.data[position] = order
                return True
            else:
                # 若bubble失败，返回False
                return False
        else:
            # position位置为空时，直接插入，返回True
            self.data[position] = order
            return True

    def check_order_position(self, position: int):
        if position < 0 or position >= len(self.data):
            raise ValueError(f'position must be between 0 and {self.length - 1}, not "{position}"')

    def bubble(self, end: int) -> bool:
        """
        对订单进行冒泡操作
        从end位置开始(包括end)，向前找一个None值的位置作为start
        将end与start之前的区间均左移一位，将None移至区间最右
        """
        start = -1
        for i in range(end, -1, -1):
            if self.data[i] is None:
                start = i
                break
        if start >= 0:
            logging.info(f"start={start}, end={end}")
            self.slice_shift(start, end + 1)
            return True
        else:
            logging.info(f"can not find start, end={end}")
            return False

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


def test_order_array():
    # 使用自定义的定长数组类
    arr = MyOrderArray(length=10)
    print(arr)
    result = arr.add_order(order=MyOrder(price=2, quantity=2), position=2)
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrder(price=3, quantity=3), position=3)
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrder(price=4, quantity=4), position=3)
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrder(price=5, quantity=5), position=3)
    print(f"result={result}, arr={arr}")
    result = arr.add_order(order=MyOrder(price=6, quantity=6), position=3)
    print(f"result={result}, arr={arr}")

    result = arr.add_order(order=MyOrder(price=7, quantity=7), position=7)
    print(f"result={result}, arr={arr}")

    result = arr.add_order(order=MyOrder(price=8, quantity=8), position=8)
    print(f"result={result}, arr={arr}")

    result = arr.add_order(order=MyOrder(price=9, quantity=9), position=8)
    print(f"result={result}, arr={arr}")

    result = arr.add_order(order=MyOrder(price=10, quantity=10), position=8)
    print(f"result={result}, arr={arr}")


if __name__ == '__main__':
    test_order_array()
