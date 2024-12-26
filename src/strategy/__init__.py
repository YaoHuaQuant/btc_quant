from abc import ABC, abstractmethod
import backtrader as bt


class StrategyInterface(ABC):
    @abstractmethod
    def next(self):
        pass

    @abstractmethod
    def notify_order(self, order: bt.Order):
        pass
