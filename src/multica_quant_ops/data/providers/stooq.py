"""Stooq-based market data provider.

Stooq (https://stooq.com) publishes daily OHLCV CSV downloads. This provider
exists specifically for the high-volume, low-value-per-call use case that
Alpha Vantage's free tier cannot cover: refreshing daily closes for dozens of
tickers every day (see docs/FUNDAMENTALS_INTEGRATION.md, section 9-3).
`AlphaVantageMarketDataProvider` remains the provider for the existing
low-frequency same-day preparation flow; this one is for daily batch refresh.

As of 2026-09 a plain `urllib.request.urlopen(url)` call to `/q/d/l/` gets
back a 404 for every symbol, and a browser-like User-Agent header alone
did not fix it either (confirmed by an actual GitHub Actions run -- see
docs/FUNDAMENTALS_INTEGRATION.md section 9-9), even though the exact same
URL works with no login, key, or CAPTCHA when a real browser requests it
(section 9-8). A real browser also does something a single bare request
doesn't: it visits a Stooq page first (picking up session cookies and a
referer) before ever requesting `/q/d/l/`. So every fetch now primes a
session once per provider instance -- one GET to the site root with
`_BROWSER_HEADERS`, keeping whatever `Set-Cookie` comes back -- and sends
that cookie plus a matching `Referer` on the real request. Priming is
best-effort: any failure there (network error, unexpected response shape)
is swallowed and the real request proceeds without a cookie, exactly like
it did before this existed. `api_key`, if the caller has one (obtained by
a human passing a CAPTCHA at `https://stooq.com/q/d/?s=<any-ticker>&
get_apikey` -- this class cannot get one itself and never will), is still
appended as the `apikey` query parameter as a further fallback.

Stooq has no published SLA or rate-limit contract, so callers that need
resilience across a batch (continue past one failed symbol, keep the previous
value rather than crash the whole run) should catch `StooqDataError` per
symbol rather than relying on this class to hide failures.
"""

import csv
import io
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date

from multica_quant_ops.data.providers.base import MarketDataProvider, MarketQuote


class StooqDataError(ValueError):
    """Raised when Stooq returns no data, or data this provider cannot parse."""


# Stooq's CSV endpoint 404s on Python's default User-Agent
# ("Python-urllib/x.y") but serves the same URL fine to a normal browser
# (see the module docstring and docs/FUNDAMENTALS_INTEGRATION.md 9-8) --
# this is a plain UA string, not anything that solves a challenge, so it
# does not touch Stooq's actual bot-detection mechanism (if any) beyond
# looking like an ordinary browser request.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,*/*",
}


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
        api_key: str | None = None,
    ) -> None:
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key
        self._session_primed = False
        self._cookie_header: str | None = None

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
        if not self._session_primed:
            self._prime_session()

        url = self._build_url(symbol)
        headers = dict(_BROWSER_HEADERS)
        headers["Referer"] = self._site_root()
        if self._cookie_header:
            headers["Cookie"] = self._cookie_header
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except OSError as exc:
            raise StooqDataError(f"Stooq request failed for {symbol}: {exc}") from exc

        bars = self._parse_csv(raw, symbol)
        if not bars:
            raise StooqDataError(f"Stooq returned no usable daily bars for {symbol}.")

        return bars[-limit:] if limit > 0 else bars

    def _site_root(self) -> str:
        parts = urllib.parse.urlsplit(self.base_url)
        return f"{parts.scheme}://{parts.netloc}/"

    def _prime_session(self) -> None:
        """Best-effort: visit the site root once to pick up session cookies,
        the way a browser would before ever requesting /q/d/l/. Never raises
        -- any failure here (network error, odd response shape from a test
        double, missing headers) just means the real request goes out
        without a cookie, same as before this existed.
        """
        self._session_primed = True  # only ever try once per instance
        try:
            request = urllib.request.Request(self._site_root(), headers=_BROWSER_HEADERS)
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response.read()
                headers = getattr(response, "headers", None)
                set_cookie_lines = headers.get_all("Set-Cookie", []) if headers else []
        except (OSError, AttributeError):
            # OSError: the priming request itself failed (network, timeout).
            # AttributeError: a response shape priming didn't expect (e.g. a
            # test double with no real `headers.get_all`). Either way this
            # is best-effort, so just proceed without a cookie.
            return

        pairs = [line.split(";", 1)[0].strip() for line in set_cookie_lines if line.strip()]
        if pairs:
            self._cookie_header = "; ".join(pairs)

    def _build_url(self, symbol: str) -> str:
        stooq_symbol = symbol.strip().lower()
        if "." not in stooq_symbol:
            stooq_symbol = f"{stooq_symbol}.us"
        url = f"{self.base_url}?s={stooq_symbol}&i=d"
        if self.api_key:
            url += f"&apikey={self.api_key}"
        return url

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
