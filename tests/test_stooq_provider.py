import io
from datetime import date
from typing import Self
from urllib.error import URLError

import pytest

from multica_quant_ops.data.providers.stooq import (
    StooqDailyBar,
    StooqDataError,
    StooqMarketDataProvider,
)

SAMPLE_CSV = (
    "Date,Open,High,Low,Close,Volume\n"
    "2026-08-25,100.0,102.0,99.0,101.0,1000000\n"
    "2026-08-26,101.0,103.5,100.5,103.0,1100000\n"
    "2026-08-27,103.0,104.0,101.0,102.5,900000\n"
)


class _FakeHeaders:
    def __init__(self, set_cookie_lines: list[str] | None = None) -> None:
        self._set_cookie_lines = set_cookie_lines or []

    def get_all(self, name: str, default: list[str] | None = None) -> list[str]:
        if name == "Set-Cookie":
            return self._set_cookie_lines
        return default if default is not None else []


class _FakeResponse:
    def __init__(self, payload: str, set_cookie_lines: list[str] | None = None) -> None:
        self._buffer = io.BytesIO(payload.encode("utf-8"))
        self.headers = _FakeHeaders(set_cookie_lines)

    def read(self) -> bytes:
        return self._buffer.read()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def test_fetch_daily_bars_parses_and_sorts_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "multica_quant_ops.data.providers.stooq.urllib.request.urlopen",
        lambda url, timeout=None: _FakeResponse(SAMPLE_CSV),
    )
    provider = StooqMarketDataProvider()

    bars = provider.fetch_daily_bars("AAPL", limit=10)

    assert bars == [
        StooqDailyBar(date(2026, 8, 25), 100.0, 102.0, 99.0, 101.0, 1_000_000),
        StooqDailyBar(date(2026, 8, 26), 101.0, 103.5, 100.5, 103.0, 1_100_000),
        StooqDailyBar(date(2026, 8, 27), 103.0, 104.0, 101.0, 102.5, 900_000),
    ]


def test_fetch_daily_bars_respects_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "multica_quant_ops.data.providers.stooq.urllib.request.urlopen",
        lambda url, timeout=None: _FakeResponse(SAMPLE_CSV),
    )
    provider = StooqMarketDataProvider()

    bars = provider.fetch_daily_bars("AAPL", limit=1)

    assert bars == [StooqDailyBar(date(2026, 8, 27), 103.0, 104.0, 101.0, 102.5, 900_000)]


def test_fetch_daily_closes_returns_close_prices_oldest_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "multica_quant_ops.data.providers.stooq.urllib.request.urlopen",
        lambda url, timeout=None: _FakeResponse(SAMPLE_CSV),
    )
    provider = StooqMarketDataProvider()

    closes = provider.fetch_daily_closes("AAPL", limit=10)

    assert closes == [101.0, 103.0, 102.5]


def test_fetch_quote_uses_latest_bar_and_prior_close(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "multica_quant_ops.data.providers.stooq.urllib.request.urlopen",
        lambda url, timeout=None: _FakeResponse(SAMPLE_CSV),
    )
    provider = StooqMarketDataProvider()

    quote = provider.fetch_quote("aapl")

    assert quote.symbol == "AAPL"
    assert quote.latest_trading_day == date(2026, 8, 27)
    assert quote.price == 102.5
    assert quote.previous_close == 103.0
    assert quote.volume == 900_000
    assert quote.change_percent == pytest.approx((102.5 - 103.0) / 103.0)


def test_no_data_response_raises_stooq_data_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "multica_quant_ops.data.providers.stooq.urllib.request.urlopen",
        lambda url, timeout=None: _FakeResponse("N/D\n"),
    )
    provider = StooqMarketDataProvider()

    with pytest.raises(StooqDataError):
        provider.fetch_quote("NOSUCHTICKER")


def test_malformed_row_raises_stooq_data_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "multica_quant_ops.data.providers.stooq.urllib.request.urlopen",
        lambda url, timeout=None: _FakeResponse("Date,Open,High,Low,Close,Volume\n2026-08-25,x,102.0,99.0,101.0,1000\n"),
    )
    provider = StooqMarketDataProvider()

    with pytest.raises(StooqDataError):
        provider.fetch_daily_bars("AAPL", limit=10)


def test_network_failure_raises_stooq_data_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(url: str, timeout: float | None = None) -> None:
        raise URLError("connection refused")

    monkeypatch.setattr("multica_quant_ops.data.providers.stooq.urllib.request.urlopen", _raise)
    provider = StooqMarketDataProvider()

    with pytest.raises(StooqDataError):
        provider.fetch_daily_bars("AAPL", limit=10)


def test_build_url_appends_us_suffix_when_missing() -> None:
    provider = StooqMarketDataProvider()

    assert provider._build_url("AAPL") == "https://stooq.com/q/d/l/?s=aapl.us&i=d"
    assert provider._build_url("7203.jp") == "https://stooq.com/q/d/l/?s=7203.jp&i=d"


def test_build_url_omits_apikey_param_when_no_key_configured() -> None:
    provider = StooqMarketDataProvider()

    assert "apikey" not in provider._build_url("AAPL")


def test_build_url_appends_apikey_param_when_key_configured() -> None:
    provider = StooqMarketDataProvider(api_key="test-key-123")

    assert provider._build_url("AAPL") == "https://stooq.com/q/d/l/?s=aapl.us&i=d&apikey=test-key-123"


def test_fetch_daily_bars_sends_a_browser_like_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stooq 404s Python's default urllib User-Agent but serves a real
    browser's request fine (docs/FUNDAMENTALS_INTEGRATION.md 9-8) -- every
    request must look like it came from a browser, not from
    Python-urllib/x.y.
    """
    captured: dict[str, object] = {}

    def _fake_urlopen(request: object, timeout: float | None = None) -> _FakeResponse:
        captured["request"] = request
        return _FakeResponse(SAMPLE_CSV)

    monkeypatch.setattr(
        "multica_quant_ops.data.providers.stooq.urllib.request.urlopen", _fake_urlopen
    )
    provider = StooqMarketDataProvider()

    provider.fetch_daily_bars("AAPL", limit=1)

    request = captured["request"]
    user_agent = request.get_header("User-agent")  # urllib title-cases header keys
    assert user_agent is not None
    assert "python-urllib" not in user_agent.lower()
    assert "mozilla" in user_agent.lower()


def test_first_fetch_primes_a_session_before_requesting_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """A real browser visits a Stooq page (picking up cookies/referer) before
    ever requesting /q/d/l/. A single bare request doesn't do that, so the
    provider must prime once -- a GET to the site root -- before the first
    real data request (docs/FUNDAMENTALS_INTEGRATION.md 9-9).
    """
    requested_urls: list[str] = []

    def _fake_urlopen(request: object, timeout: float | None = None) -> _FakeResponse:
        requested_urls.append(request.full_url)  # type: ignore[attr-defined]
        return _FakeResponse(SAMPLE_CSV)

    monkeypatch.setattr(
        "multica_quant_ops.data.providers.stooq.urllib.request.urlopen", _fake_urlopen
    )
    provider = StooqMarketDataProvider()

    provider.fetch_daily_bars("AAPL", limit=1)

    assert requested_urls[0] == "https://stooq.com/"
    assert requested_urls[1] == "https://stooq.com/q/d/l/?s=aapl.us&i=d"


def test_session_priming_only_happens_once_per_provider_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_urls: list[str] = []

    def _fake_urlopen(request: object, timeout: float | None = None) -> _FakeResponse:
        requested_urls.append(request.full_url)  # type: ignore[attr-defined]
        return _FakeResponse(SAMPLE_CSV)

    monkeypatch.setattr(
        "multica_quant_ops.data.providers.stooq.urllib.request.urlopen", _fake_urlopen
    )
    provider = StooqMarketDataProvider()

    provider.fetch_daily_bars("AAPL", limit=1)
    provider.fetch_daily_bars("MSFT", limit=1)

    priming_calls = [u for u in requested_urls if u == "https://stooq.com/"]
    assert len(priming_calls) == 1


def test_cookie_from_priming_request_is_sent_on_the_data_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def _fake_urlopen(request: object, timeout: float | None = None) -> _FakeResponse:
        url = request.full_url  # type: ignore[attr-defined]
        if url == "https://stooq.com/":
            return _FakeResponse("<html></html>", set_cookie_lines=["session=abc123; Path=/; HttpOnly"])
        captured["data_request"] = request
        return _FakeResponse(SAMPLE_CSV)

    monkeypatch.setattr(
        "multica_quant_ops.data.providers.stooq.urllib.request.urlopen", _fake_urlopen
    )
    provider = StooqMarketDataProvider()

    provider.fetch_daily_bars("AAPL", limit=1)

    data_request = captured["data_request"]
    assert data_request.get_header("Cookie") == "session=abc123"  # type: ignore[attr-defined]


def test_priming_failure_does_not_block_the_real_data_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Priming is best-effort -- if the site-root request itself fails, the
    real /q/d/l/ request must still go out (without a cookie) rather than
    the whole fetch blowing up.
    """

    def _fake_urlopen(request: object, timeout: float | None = None) -> _FakeResponse:
        url = request.full_url  # type: ignore[attr-defined]
        if url == "https://stooq.com/":
            raise URLError("priming connection refused")
        return _FakeResponse(SAMPLE_CSV)

    monkeypatch.setattr(
        "multica_quant_ops.data.providers.stooq.urllib.request.urlopen", _fake_urlopen
    )
    provider = StooqMarketDataProvider()

    bars = provider.fetch_daily_bars("AAPL", limit=1)

    assert bars == [StooqDailyBar(date(2026, 8, 27), 103.0, 104.0, 101.0, 102.5, 900_000)]
