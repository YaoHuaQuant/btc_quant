from typing import Dict

import backtrader as bt

from strategy import VirtualOrderBookInterface, VirtualOrder
from strategy.virtual_order import VirtualOrderOne


class OrderScheduler:
    """
    订单调度器，用于对接MyOrderArrayTriple数据结构和backtrader.Order
    使用观察者模式 作为双向绑定管理器（BindingManager）
    作用：
    1.将MyOrderPair与backtrader.Order（存储在MyOrderPairObserver中）进行关联
    2.接受MyOrderPair的notify信号，并修改backtrader.Order的价格
    3.接受backtrader.Order的变更信号 并修改MyOrderPair的状态
    """

    def __init__(self, strategy: bt.Strategy):
        # 正向绑定
        self.order_bindings_virtual2actual: Dict[any, bt.Order] = {}
        # 反向绑定
        self.order_bindings_actual2virtual: Dict[any, VirtualOrder] = {}
        # 由上级Strategy提供的backtrader.Strategy 用于操作backtrader.Order
        self.strategy = strategy

        self.order_book: VirtualOrderBookInterface | None = None

    def bind(self, virtual_order: VirtualOrder, actual_order: bt.Order):
        virtual_order.link_observer(self.virtual_order_observe)
        self.order_bindings_virtual2actual[virtual_order] = actual_order
        self.order_bindings_actual2virtual[actual_order.ref] = virtual_order

    def unbind(self, virtual_order: VirtualOrder):
        virtual_order.link_observer(None)
        if self.order_bindings_virtual2actual.__contains__(virtual_order):
            actual_id = self.order_bindings_virtual2actual[virtual_order].ref
            del self.order_bindings_virtual2actual[virtual_order]
            if self.order_bindings_actual2virtual.__contains__(actual_id):
                del self.order_bindings_actual2virtual[actual_id]

    def virtual_order_observe(self, virtual_order: VirtualOrder):
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

    def link_order_book(self, order_book: VirtualOrderBookInterface):
        self.order_book = order_book

    def actual_buy_finished(self, actual_order: bt.Order) -> VirtualOrder | None:
        """
        实际买单成交
        修改VirtualOrder的状态
        解除绑定
        :param actual_order:
        """
        # 获取virtual_open_order
        virtual_order = self.order_bindings_actual2virtual[actual_order.ref]
        # virtual_order.update_status_closing()
        self.unbind(virtual_order)
        if self.order_book is not None:
            self.order_book.update_order_closing(virtual_order)
            actual_order = self.strategy.sell(
                price=virtual_order.close_price,
                size=virtual_order.quantity,
                exectype=bt.Order.Limit
            )
            self.bind(virtual_order=virtual_order, actual_order=actual_order)
            return virtual_order
        return None

    def actual_sell_finished(self, actual_order: bt.Order) -> VirtualOrder | None:
        """
        实际卖单成交
        修改VirtualOrder的状态

        解除绑定
        """
        virtual_order = self.order_bindings_actual2virtual[actual_order.ref]
        # virtual_order.update_status_closed()
        self.unbind(virtual_order)
        if self.order_book is not None:
            self.order_book.update_order_closed(virtual_order)
            return virtual_order
        return None

    def actual_order_cancelled(self, actual_order: bt.Order) -> VirtualOrder | None:
        virtual_order = self.order_bindings_actual2virtual[actual_order.ref]
        self.unbind(virtual_order)
        return virtual_order



def test():
    strategy = 1
    order_scheduler = OrderScheduler(strategy)
    virtual_order = VirtualOrderOne(open_price=10, close_price=10, quantity=1, direction='long')
    actual_order = 1
    order_scheduler.bind(virtual_order=virtual_order, actual_order=actual_order)
    virtual_order.update_open_price(20)


if __name__ == '__main__':
    test()
