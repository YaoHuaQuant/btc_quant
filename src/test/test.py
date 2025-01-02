from typing import Callable, Dict, List


class Observable:
    """可观察的对象（数组A的元素）"""
    def __init__(self, value: any):
        self._value = value
        self._observers: List[Callable[[any], None]] = []

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value: any):
        self._value = new_value
        self.notify_observers()  # 数据变化时通知观察者

    def add_observer(self, observer: Callable[[any], None]):
        self._observers.append(observer)

    def remove_observer(self, observer: Callable[[any], None]):
        self._observers.remove(observer)

    def notify_observers(self):
        for observer in self._observers:
            observer(self._value)


class Observer:
    """观察者对象（数组B的元素）"""
    def __init__(self, name: str):
        self.name = name
        self.data = None

    def update(self, new_value: any):
        """当被观察对象发生变化时调用"""
        self.data = new_value
        print(f"{self.name} updated with new value: {new_value}")


class BindingManager:
    """绑定数组A和数组B的管理器"""
    def __init__(self):
        self.bindings: Dict[Observable, Observer] = {}

    def bind(self, observable: Observable, observer: Observer):
        observable.add_observer(observer.update)
        self.bindings[observable] = observer

    def unbind(self, observable: Observable):
        if observable in self.bindings:
            observer = self.bindings.pop(observable)
            observable.remove_observer(observer.update)


# 示例使用
if __name__ == "__main__":
    # 初始化数组A和B
    A = [Observable(value) for value in [1, 2, 3]]
    B = [Observer(f"Observer {i}") for i in range(len(A))]

    # 创建绑定管理器
    manager = BindingManager()

    # 绑定数组A和数组B的对象
    for a, b in zip(A, B):
        manager.bind(a, b)

    # 修改数组A中的数据
    A[0].value = 10  # 将触发 Observer 0 的更新
    A[1].value = 20  # 将触发 Observer 1 的更新
