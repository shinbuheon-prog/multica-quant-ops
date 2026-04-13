from dataclasses import dataclass

from multica_quant_ops.strategies.base import SignalStrategy
from multica_quant_ops.strategies.signals import SignalDirection


@dataclass(frozen=True)
class BacktestCriteria:
    min_total_return: float
    min_win_rate: float


@dataclass(frozen=True)
class BacktestResult:
    total_return: float
    win_rate: float
    periods: int
    approved_for_paper_trading: bool


def run_backtest(strategy: SignalStrategy, symbol: str, prices: list[float], criteria: BacktestCriteria) -> BacktestResult:
    if len(prices) < 3:
        raise ValueError("At least three price points are required for backtesting.")

    wins = 0
    losses = 0
    equity = 1.0

    for index in range(1, len(prices) - 1):
        window = prices[: index + 1]
        signal = strategy.generate_signal(symbol=symbol, prices=window)
        current_price = prices[index]
        next_price = prices[index + 1]
        if current_price <= 0:
            raise ValueError("Encountered non-positive price in backtest.")

        forward_return = (next_price - current_price) / current_price
        realized_return = forward_return if signal.direction == SignalDirection.LONG else 0.0
        equity *= 1 + realized_return

        if realized_return > 0:
            wins += 1
        elif realized_return < 0:
            losses += 1

    periods = len(prices) - 2
    total_return = equity - 1
    decided_periods = wins + losses
    win_rate = wins / decided_periods if decided_periods else 0.0
    approved = total_return >= criteria.min_total_return and win_rate >= criteria.min_win_rate
    return BacktestResult(
        total_return=total_return,
        win_rate=win_rate,
        periods=periods,
        approved_for_paper_trading=approved,
    )
