from abc import ABC, abstractmethod
from datetime import datetime


class KlineInterface(ABC):
    @abstractmethod
    def get_kline(self, from_date: datetime, to_date: datetime, granularity: str = '1m') -> list:
        pass


class OrderInterface(ABC):
    @abstractmethod
    def get_order(self) -> list:
        pass


class BalanceInterface(ABC):
    @abstractmethod
    def get_order(self) -> list:
        pass
