from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class MarketQuote:
    symbol: str
    latest_trading_day: date
    open_price: float
    high_price: float
    low_price: float
    price: float
    previous_close: float
    volume: int
    change_percent: float


class MarketDataProvider(Protocol):
    def fetch_quote(self, symbol: str) -> MarketQuote:
        raise NotImplementedError

    def fetch_daily_closes(self, symbol: str, limit: int) -> list[float]:
        raise NotImplementedError
