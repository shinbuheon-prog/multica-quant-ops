"""Stooq-based market data provider.

Stooq (https://stooq.com) publishes free, key-less daily OHLCV CSV downloads.
This provider exists specifically for the high-volume, low-value-per-call use
case that Alpha Vantage's free tier cannot cover: refreshing daily closes for
dozens of tickers every day (see docs/FUNDAMENTALS_INTEGRATION.md, section
9-3). `AlphaVantageMarketDataProvider` remains the provider for the existing
low-frequency same-day preparation flow; this one is for daily batch refresh.

Stooq has no published SLA or rate-limit contract, so callers that need
resilience across a batch (continue past one failed symbol, keep the previous
value rather than crash the whole run) should catch `StooqDataError` per
symbol rather than relying on this class to hide failures.
"""

import csv
import io
import urllib.request
from dataclasses import dataclass
from datetime import date

from multica_quant_ops.data.providers.base import MarketDataProvider, MarketQuote


class StooqDataError(ValueError):
    """Raised when Stooq returns no data, or data this provider cannot parse."""


@dataclass(frozen=True)
class StooqDailyBar:
    trading_day: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int


class StooqMarketDataProvider(MarketDataProvider):
    def __init__(
        self,
        base_url: str = "https://stooq.com/q/d/l/",
        timeout_seconds: float = 20.0,
    ) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def fetch_quote(self, symbol: str) -> MarketQuote:
        bars = self._fetch_daily_bars(symbol, limit=2)
        if not bars:
            raise StooqDataError(f"Stooq returned no daily bars for {symbol}.")

        latest = bars[-1]
        previous_close = bars[-2].close_price if len(bars) >= 2 else latest.close_price
        change_percent = (
            (latest.close_price - previous_close) / previous_close if previous_close else 0.0
        )

        return MarketQuote(
            symbol=symbol.upper(),
            latest_trading_day=latest.trading_day,
            open_price=latest.open_price,
            high_price=latest.high_price,
            low_price=latest.low_price,
            price=latest.close_price,
            previous_close=previous_close,
            volume=latest.volume,
            change_percent=change_percent,
        )

    def fetch_daily_closes(self, symbol: str, limit: int) -> list[float]:
        bars = self._fetch_daily_bars(symbol, limit=limit)
        return [bar.close_price for bar in bars]

    def fetch_daily_bars(self, symbol: str, limit: int) -> list[StooqDailyBar]:
        return self._fetch_daily_bars(symbol, limit=limit)

    def _fetch_daily_bars(self, symbol: str, limit: int) -> list[StooqDailyBar]:
        url = self._build_url(symbol)
        try:
            with urllib.request.urlopen(url, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except OSError as exc:
            raise StooqDataError(f"Stooq request failed for {symbol}: {exc}") from exc

        bars = self._parse_csv(raw, symbol)
        if not bars:
            raise StooqDataError(f"Stooq returned no usable daily bars for {symbol}.")

        return bars[-limit:] if limit > 0 else bars

    def _build_url(self, symbol: str) -> str:
        stooq_symbol = symbol.strip().lower()
        if "." not in stooq_symbol:
            stooq_symbol = f"{stooq_symbol}.us"
        return f"{self.base_url}?s={stooq_symbol}&i=d"

    @staticmethod
    def _parse_csv(raw: str, symbol: str) -> list[StooqDailyBar]:
        stripped = raw.strip()
        if not stripped or stripped.lower().startswith("no data"):
            raise StooqDataError(f"Stooq has no data for {symbol}.")

        reader = csv.DictReader(io.StringIO(stripped))
        bars: list[StooqDailyBar] = []
        for row in reader:
            try:
                bars.append(
                    StooqDailyBar(
                        trading_day=date.fromisoformat(row["Date"]),
                        open_price=float(row["Open"]),
                        high_price=float(row["High"]),
                        low_price=float(row["Low"]),
                        close_price=float(row["Close"]),
                        volume=int(float(row["Volume"])),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise StooqDataError(f"Stooq daily row was malformed for {symbol}: {row}") from exc

        bars.sort(key=lambda bar: bar.trading_day)
        return bars
