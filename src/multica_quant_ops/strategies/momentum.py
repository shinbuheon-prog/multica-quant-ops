from multica_quant_ops.strategies.base import SignalStrategy
from multica_quant_ops.strategies.signals import Signal, SignalDirection


class SimpleMomentumStrategy(SignalStrategy):
    def generate_signal(self, symbol: str, prices: list[float]) -> Signal:
        if len(prices) < 2:
            raise ValueError("At least two price points are required.")

        first = prices[0]
        last = prices[-1]
        if first <= 0:
            raise ValueError("Price history must start above zero.")

        return_ratio = (last - first) / first
        if return_ratio > 0:
            return Signal(
                symbol=symbol,
                direction=SignalDirection.LONG,
                confidence=min(return_ratio, 1.0),
                rationale="Positive momentum over the provided window.",
            )
        return Signal(
            symbol=symbol,
            direction=SignalDirection.FLAT,
            confidence=min(abs(return_ratio), 1.0),
            rationale="Momentum is non-positive over the provided window.",
        )
