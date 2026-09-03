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


def _install_fake_urlopen(monkeypatch: pytest.MonkeyPatch, calls: list[str]) -> None:
    """Records which api key each request used (from the querystring) and
    returns a canned quote for whatever symbol was asked for.
    """

    def _fake_urlopen(url: str, timeout: float | None = None) -> _FakeResponse:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        calls.append(query["apikey"][0])
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
