import io
import json
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

import pytest

from multica_quant_ops.data.providers.alphavantage import (
    AlphaVantageMarketDataProvider,
    MultiKeyAlphaVantageProvider,
)
from multica_quant_ops.data.providers.usage import DailyCallLimitExceededError


def _quote_payload(symbol: str) -> dict:
    return {
        "Global Quote": {
            "01. symbol": symbol,
            "02. open": "100.0",
            "03. high": "101.0",
            "04. low": "99.0",
            "05. price": "100.5",
            "06. volume": "1000",
            "07. latest trading day": "2026-09-02",
            "08. previous close": "99.5",
            "10. change percent": "1.00%",
        }
    }


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._buffer = io.BytesIO(json.dumps(payload).encode("utf-8"))

    def read(self) -> bytes:
        return self._buffer.read()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None


def _provider(tmp_path: Path, name: str, daily_limit: int = 25) -> AlphaVantageMarketDataProvider:
    provider = AlphaVantageMarketDataProvider.build_free_mode(
        api_key=f"key-{name}",
        usage_file=tmp_path / f"usage_{name}.json",
        daily_limit=daily_limit,
    )
    provider.min_interval_seconds = 0.0  # no need to slow tests down with the real 1.1s throttle
    return provider


def _install_fake_urlopen(
    monkeypatch: pytest.MonkeyPatch, calls: list[str], rejected_keys: set[str] | None = None
) -> None:
    """Records which api key each request used (from the querystring) and
    returns a canned quote for whatever symbol was asked for -- unless that
    key is in `rejected_keys`, in which case it returns the same
    "Information: ... rate limit ..." payload Alpha Vantage's real server
    sends for a request it rejects as over quota (see
    docs/FUNDAMENTALS_INTEGRATION.md 9-12), which AlphaVantageMarketDataProvider
    turns into a `ProviderRateLimitError`.
    """
    rejected_keys = rejected_keys or set()

    def _fake_urlopen(url: str, timeout: float | None = None) -> _FakeResponse:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        api_key = query["apikey"][0]
        calls.append(api_key)
        if api_key in rejected_keys:
            return _FakeResponse(
                {
                    "Information": (
                        f"We have detected your API key as {api_key} and our standard "
                        "API rate limit is 25 requests per day."
                    )
                }
            )
        return _FakeResponse(_quote_payload(query["symbol"][0]))

    monkeypatch.setattr(
        "multica_quant_ops.data.providers.alphavantage.urllib.request.urlopen", _fake_urlopen
    )


def test_multi_key_provider_requires_at_least_one_provider() -> None:
    with pytest.raises(ValueError):
        MultiKeyAlphaVantageProvider([])


def test_multi_key_provider_uses_the_first_key_while_it_has_quota(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider1 = _provider(tmp_path, "a")
    provider2 = _provider(tmp_path, "b")
    calls: list[str] = []
    _install_fake_urlopen(monkeypatch, calls)

    multi = MultiKeyAlphaVantageProvider([provider1, provider2])
    multi.fetch_quote("AAPL")

    assert calls == ["key-a"]


def test_multi_key_provider_falls_through_once_the_first_key_is_exhausted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider1 = _provider(tmp_path, "a", daily_limit=1)
    provider2 = _provider(tmp_path, "b", daily_limit=1)
    calls: list[str] = []
    _install_fake_urlopen(monkeypatch, calls)

    multi = MultiKeyAlphaVantageProvider([provider1, provider2])
    multi.fetch_quote("AAPL")  # spends key-a's only call for today
    quote = multi.fetch_quote("MSFT")  # key-a is exhausted -> falls through to key-b

    assert calls == ["key-a", "key-b"]
    assert quote.symbol == "MSFT"


def test_multi_key_provider_raises_once_every_key_is_exhausted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider1 = _provider(tmp_path, "a", daily_limit=1)
    provider2 = _provider(tmp_path, "b", daily_limit=1)
    calls: list[str] = []
    _install_fake_urlopen(monkeypatch, calls)

    multi = MultiKeyAlphaVantageProvider([provider1, provider2])
    multi.fetch_quote("AAPL")  # exhausts key-a
    multi.fetch_quote("MSFT")  # exhausts key-b

    with pytest.raises(DailyCallLimitExceededError):
        multi.fetch_quote("TSLA")

    assert calls == ["key-a", "key-b"]  # the failing 3rd call never reaches urlopen at all


def test_multi_key_provider_falls_through_on_a_real_server_side_rate_limit_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A key can get rejected by Alpha Vantage's real server before our own
    local usage tracker believes it's out of room (docs/FUNDAMENTALS_INTEGRATION.md
    9-12) -- that must fall through to the next key exactly like local
    exhaustion does, not just fail the one ticker.
    """
    provider1 = _provider(tmp_path, "a")  # local tracker thinks it has 25 left
    provider2 = _provider(tmp_path, "b")
    calls: list[str] = []
    _install_fake_urlopen(monkeypatch, calls, rejected_keys={"key-a"})

    multi = MultiKeyAlphaVantageProvider([provider1, provider2])
    quote = multi.fetch_quote("AAPL")

    assert calls == ["key-a", "key-b"]
    assert quote.symbol == "AAPL"


def test_multi_key_provider_stops_retrying_a_key_the_server_already_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Once a key has been rejected server-side this run, later calls must
    skip straight past it instead of hitting its real (already-exhausted)
    quota again on every remaining ticker -- this is the fix for the
    all-19-remaining-tickers-fail pattern seen in the real run (9-12).
    """
    provider1 = _provider(tmp_path, "a")
    provider2 = _provider(tmp_path, "b")
    calls: list[str] = []
    _install_fake_urlopen(monkeypatch, calls, rejected_keys={"key-a"})

    multi = MultiKeyAlphaVantageProvider([provider1, provider2])
    multi.fetch_quote("AAPL")  # key-a rejected server-side, falls through to key-b
    calls.clear()
    multi.fetch_quote("MSFT")  # key-a must be skipped entirely this time

    assert calls == ["key-b"]  # not ["key-a", "key-b"] -- key-a isn't retried


def test_multi_key_provider_last_usage_snapshot_combines_every_key(tmp_path: Path) -> None:
    provider1 = _provider(tmp_path, "a", daily_limit=25)
    provider2 = _provider(tmp_path, "b", daily_limit=25)
    assert provider1.usage_tracker is not None
    assert provider2.usage_tracker is not None
    now = datetime.now(UTC)
    provider1.usage_tracker.reserve_call(now)
    provider2.usage_tracker.reserve_call(now)
    provider2.usage_tracker.reserve_call(now)

    multi = MultiKeyAlphaVantageProvider([provider1, provider2])
    snapshot = multi.last_usage_snapshot

    assert snapshot is not None
    assert snapshot.used_calls == 3
    assert snapshot.daily_limit == 50
