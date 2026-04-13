import json
import urllib.parse
import urllib.request
from datetime import date
from typing import Any

from multica_quant_ops.data.providers.base import MarketDataProvider, MarketQuote


class AlphaVantageMarketDataProvider(MarketDataProvider):
    def __init__(
        self,
        api_key: str,
        entitlement: str | None = None,
        base_url: str = "https://www.alphavantage.co/query",
    ) -> None:
        self.api_key = api_key
        self.entitlement = entitlement
        self.base_url = base_url

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

    def _get_json(self, params: dict[str, str]) -> dict[str, Any]:
        query = urllib.parse.urlencode(params)
        url = f"{self.base_url}?{query}"
        with urllib.request.urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Alpha Vantage response was not a JSON object.")
        return payload
