from abc import ABC, abstractmethod

from multica_quant_ops.strategies.signals import Signal


class SignalStrategy(ABC):
    @abstractmethod
    def generate_signal(self, symbol: str, prices: list[float]) -> Signal:
        raise NotImplementedError
