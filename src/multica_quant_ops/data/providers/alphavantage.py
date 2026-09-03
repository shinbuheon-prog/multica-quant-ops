import json
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from multica_quant_ops.data.providers.base import MarketDataProvider, MarketQuote
from multica_quant_ops.data.providers.usage import (
    DailyCallLimitExceededError,
    FileBackedUsageTracker,
    ProviderRateLimitError,
    ProviderUsageSnapshot,
)


class AlphaVantageMarketDataProvider(MarketDataProvider):
    def __init__(
        self,
        api_key: str,
        entitlement: str | None = None,
        base_url: str = "https://www.alphavantage.co/query",
        usage_tracker: FileBackedUsageTracker | None = None,
        min_interval_seconds: float = 0.0,
    ) -> None:
        self.api_key = api_key
        self.entitlement = entitlement
        self.base_url = base_url
        self.usage_tracker = usage_tracker
        self._last_usage_snapshot: ProviderUsageSnapshot | None = None
        self.min_interval_seconds = min_interval_seconds
        self._last_request_monotonic: float | None = None

    def fetch_quote(self, symbol: str) -> MarketQuote:
        payload = self._get_json(
            {
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.api_key,
                "datatype": "json",
                **({"entitlement": self.entitlement} if self.entitlement else {}),
            }
        )
        quote_payload = payload.get("Global Quote")
        if not isinstance(quote_payload, dict) or not quote_payload:
            raise ValueError(f"Alpha Vantage quote response did not include quote data for {symbol}.")

        try:
            return MarketQuote(
                symbol=quote_payload["01. symbol"],
                open_price=float(quote_payload["02. open"]),
                high_price=float(quote_payload["03. high"]),
                low_price=float(quote_payload["04. low"]),
                price=float(quote_payload["05. price"]),
                volume=int(float(quote_payload["06. volume"])),
                latest_trading_day=date.fromisoformat(quote_payload["07. latest trading day"]),
                previous_close=float(quote_payload["08. previous close"]),
                change_percent=float(quote_payload["10. change percent"].rstrip("%")) / 100.0,
            )
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Alpha Vantage quote data was malformed for {symbol}.") from exc

    def fetch_daily_closes(self, symbol: str, limit: int) -> list[float]:
        payload = self._get_json(
            {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "apikey": self.api_key,
                "outputsize": "compact",
                "datatype": "json",
            }
        )
        series = payload.get("Time Series (Daily)")
        if not isinstance(series, dict) or not series:
            raise ValueError(f"Alpha Vantage daily series response did not include time series for {symbol}.")

        ordered_days = sorted(series.keys(), reverse=True)
        closes: list[float] = []
        for day in ordered_days[:limit]:
            try:
                day_payload = series[day]
                if not isinstance(day_payload, dict):
                    raise ValueError("Daily series item is not a JSON object.")
                closes.append(float(day_payload["4. close"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Alpha Vantage daily series was malformed for {symbol}.") from exc

        return list(reversed(closes))

    @property
    def last_usage_snapshot(self) -> ProviderUsageSnapshot | None:
        return self._last_usage_snapshot

    @classmethod
    def build_free_mode(
        cls,
        api_key: str,
        usage_file: Path,
        daily_limit: int = 25,
        entitlement: str | None = None,
    ) -> "AlphaVantageMarketDataProvider":
        return cls(
            api_key=api_key,
            entitlement=entitlement,
            usage_tracker=FileBackedUsageTracker(path=usage_file, daily_limit=daily_limit),
            min_interval_seconds=1.1,
        )

    def _get_json(self, params: dict[str, str]) -> dict[str, Any]:
        self._respect_min_interval()
        if self.usage_tracker is not None:
            self._last_usage_snapshot = self.usage_tracker.reserve_call(datetime.utcnow())
        query = urllib.parse.urlencode(params)
        url = f"{self.base_url}?{query}"
        with urllib.request.urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        self._last_request_monotonic = time.monotonic()
        if not isinstance(payload, dict):
            raise ValueError("Alpha Vantage response was not a JSON object.")
        if "Information" in payload or "Note" in payload:
            message = payload.get("Information") or payload.get("Note")
            raise ProviderRateLimitError(str(message))
        return payload

    def _respect_min_interval(self) -> None:
        if self.min_interval_seconds <= 0 or self._last_request_monotonic is None:
            return
        elapsed = time.monotonic() - self._last_request_monotonic
        remaining = self.min_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)


class MultiKeyAlphaVantageProvider(MarketDataProvider):
    """Spreads calls across several Alpha Vantage free-tier keys, each meant
    to have its own independent daily quota (see
    docs/FUNDAMENTALS_INTEGRATION.md 9-11). Whether that quota is actually
    independent per key, per account, or per source IP is something Alpha
    Vantage does not publish and this class cannot verify -- see 9-12 for
    the real-run evidence that it may not scale as cleanly as "N keys = N *
    25 calls/day" suggests, especially when every key is called from the
    same machine/IP (e.g. one GitHub Actions run).

    Every call tries the underlying providers **in the order given** and
    advances to the next one once the current key looks exhausted for the
    day -- either because our own local tracker says so
    (`DailyCallLimitExceededError`), or because Alpha Vantage's server
    itself just rejected a request as over the daily limit
    (`ProviderRateLimitError`, which our local tracker has no way to
    predict in advance). Once a key has been rejected either way, it is
    remembered as exhausted **for the rest of this run** and skipped
    entirely on subsequent calls -- without this, a key whose *real* quota
    ran out before our local counter caught up would otherwise get
    retried, and rejected again, on every single remaining ticker in the
    batch (see 9-12).
    """

    def __init__(self, providers: list[AlphaVantageMarketDataProvider]) -> None:
        if not providers:
            raise ValueError("MultiKeyAlphaVantageProvider requires at least one provider.")
        self._providers = providers
        self._exhausted_indices: set[int] = set()

    def fetch_quote(self, symbol: str) -> MarketQuote:
        return self._call(lambda provider: provider.fetch_quote(symbol))

    def fetch_daily_closes(self, symbol: str, limit: int) -> list[float]:
        return self._call(lambda provider: provider.fetch_daily_closes(symbol, limit))

    def _call(self, invoke: "Callable[[AlphaVantageMarketDataProvider], Any]") -> Any:
        last_exc: DailyCallLimitExceededError | ProviderRateLimitError | None = None
        for index, provider in enumerate(self._providers):
            if index in self._exhausted_indices:
                continue
            try:
                return invoke(provider)
            except (DailyCallLimitExceededError, ProviderRateLimitError) as exc:
                self._exhausted_indices.add(index)
                last_exc = exc
                continue
        if last_exc is None:
            # Every provider was already marked exhausted from an earlier
            # call this run, so the loop above never even tried one --
            # surface that plainly rather than raising `None`.
            raise DailyCallLimitExceededError(
                "Every configured Alpha Vantage key is exhausted for today."
            )
        raise last_exc

    @property
    def last_usage_snapshot(self) -> ProviderUsageSnapshot | None:
        """Combined usage across *every* underlying key, not just whichever
        one happened to serve the most recent call -- reporting only the
        last key's count would understate how much of the total budget is
        actually left once an earlier key is exhausted.
        """
        now = datetime.now(UTC)
        snapshots = [
            provider.usage_tracker.snapshot(now)
            for provider in self._providers
            if provider.usage_tracker is not None
        ]
        if not snapshots:
            return None
        return ProviderUsageSnapshot(
            date=snapshots[0].date,
            used_calls=sum(s.used_calls for s in snapshots),
            daily_limit=sum(s.daily_limit for s in snapshots),
        )
