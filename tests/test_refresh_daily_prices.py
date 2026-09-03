from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from multica_quant_ops.data.providers.base import MarketQuote
from multica_quant_ops.data.refresh_daily_prices import (
    PriceRow,
    load_existing_prices,
    load_ticker_list,
    main,
    refresh_prices,
    run,
    write_prices_csv,
)

NOW = datetime(2026, 9, 3, 0, 0, tzinfo=UTC)


class _StubProvider:
    """Returns a canned quote per ticker, or raises for tickers in `failing`."""

    def __init__(self, quotes: dict[str, MarketQuote], failing: set[str] | None = None) -> None:
        self.quotes = quotes
        self.failing = failing or set()

    def fetch_quote(self, symbol: str) -> MarketQuote:
        if symbol in self.failing:
            raise ValueError(f"no data for {symbol}")
        return self.quotes[symbol]

    def fetch_daily_closes(self, symbol: str, limit: int) -> list[float]:
        raise NotImplementedError


def _quote(symbol: str, close: float) -> MarketQuote:
    return MarketQuote(
        symbol=symbol,
        latest_trading_day=date(2026, 9, 2),
        open_price=close - 1,
        high_price=close + 1,
        low_price=close - 2,
        price=close,
        previous_close=close - 0.5,
        volume=1000,
        change_percent=0.01,
    )


def test_load_ticker_list_skips_blank_lines_and_comments(tmp_path: Path) -> None:
    path = tmp_path / "tickers.txt"
    path.write_text("AAPL\n# comment\n\nmsft\n  tsla  \n", encoding="utf-8")

    assert load_ticker_list(path) == ["AAPL", "MSFT", "TSLA"]


def test_load_ticker_list_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_ticker_list(tmp_path / "does-not-exist.txt")


def test_refresh_prices_all_succeed() -> None:
    provider = _StubProvider({"AAPL": _quote("AAPL", 200.0), "MSFT": _quote("MSFT", 400.0)})

    results, failures = refresh_prices(["AAPL", "MSFT"], provider, existing={}, now=NOW)

    assert failures == []
    assert results["AAPL"].close_price == 200.0
    assert results["AAPL"].stale is False
    assert results["MSFT"].close_price == 400.0


def test_refresh_prices_falls_back_to_previous_row_on_failure() -> None:
    provider = _StubProvider({"AAPL": _quote("AAPL", 200.0)}, failing={"MSFT"})
    previous_msft = PriceRow(
        ticker="MSFT",
        trading_day=date(2026, 8, 28),
        open_price=390.0,
        high_price=395.0,
        low_price=385.0,
        close_price=392.0,
        volume=500,
        updated_at=datetime(2026, 8, 28, tzinfo=UTC),
        source="stooq",
        stale=False,
    )

    results, failures = refresh_prices(
        ["AAPL", "MSFT"], provider, existing={"MSFT": previous_msft}, now=NOW
    )

    assert failures == [("MSFT", "no data for MSFT")]
    assert results["MSFT"].close_price == 392.0  # carried forward, not blanked
    assert results["MSFT"].stale is True
    assert results["AAPL"].stale is False


def test_refresh_prices_ticker_with_no_history_and_failure_is_simply_missing() -> None:
    provider = _StubProvider({}, failing={"NEWCO"})

    results, failures = refresh_prices(["NEWCO"], provider, existing={}, now=NOW)

    assert "NEWCO" not in results
    assert failures == [("NEWCO", "no data for NEWCO")]


def test_write_and_load_prices_csv_roundtrip(tmp_path: Path) -> None:
    output = tmp_path / "prices" / "daily_prices.csv"
    rows = {
        "AAPL": PriceRow(
            ticker="AAPL",
            trading_day=date(2026, 9, 2),
            open_price=199.0,
            high_price=201.0,
            low_price=198.0,
            close_price=200.0,
            volume=1000,
            updated_at=NOW,
            source="stooq",
            stale=False,
        )
    }

    write_prices_csv(output, rows)
    loaded = load_existing_prices(output)

    assert loaded == rows


def test_load_existing_prices_missing_file_returns_empty_dict(tmp_path: Path) -> None:
    assert load_existing_prices(tmp_path / "nope.csv") == {}


def test_run_end_to_end_writes_csv_and_preserves_stale_row(tmp_path: Path) -> None:
    tickers_file = tmp_path / "tickers.txt"
    tickers_file.write_text("AAPL\nMSFT\n", encoding="utf-8")
    output_file = tmp_path / "daily_prices.csv"

    write_prices_csv(
        output_file,
        {
            "MSFT": PriceRow(
                ticker="MSFT",
                trading_day=date(2026, 8, 28),
                open_price=390.0,
                high_price=395.0,
                low_price=385.0,
                close_price=392.0,
                volume=500,
                updated_at=datetime(2026, 8, 28, tzinfo=UTC),
                source="stooq",
                stale=False,
            )
        },
    )

    provider = _StubProvider({"AAPL": _quote("AAPL", 200.0)}, failing={"MSFT"})
    exit_code = run(tickers_file, output_file, provider=provider)

    assert exit_code == 0
    reloaded = load_existing_prices(output_file)
    assert reloaded["AAPL"].close_price == 200.0
    assert reloaded["MSFT"].close_price == 392.0
    assert reloaded["MSFT"].stale is True


def test_run_passes_api_key_to_default_stooq_provider_when_none_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stooq's endpoint has required a key since 2026-03 (docs 9-7) -- when the
    caller doesn't supply a provider directly, run() must build the default
    StooqMarketDataProvider with whatever api_key it was given, not silently
    drop it.
    """
    import multica_quant_ops.data.refresh_daily_prices as refresh_module

    tickers_file = tmp_path / "tickers.txt"
    tickers_file.write_text("AAPL\n", encoding="utf-8")
    output_file = tmp_path / "daily_prices.csv"

    captured: dict[str, object] = {}

    class _CapturingProvider:
        def __init__(self, api_key: str | None = None) -> None:
            captured["api_key"] = api_key

        def fetch_quote(self, symbol: str) -> MarketQuote:
            raise ValueError("no data")

    monkeypatch.setattr(refresh_module, "StooqMarketDataProvider", _CapturingProvider)

    run(tickers_file, output_file, api_key="test-key-456")

    assert captured["api_key"] == "test-key-456"


def test_main_reads_stooq_api_key_from_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import multica_quant_ops.data.refresh_daily_prices as refresh_module

    tickers_file = tmp_path / "tickers.txt"
    tickers_file.write_text("AAPL\n", encoding="utf-8")
    output_file = tmp_path / "daily_prices.csv"

    captured: dict[str, object] = {}

    def _fake_run(
        tickers_file_arg: Path,
        output_file_arg: Path,
        provider: object | None = None,
        api_key: str | None = None,
    ) -> int:
        captured["api_key"] = api_key
        return 0

    monkeypatch.setattr(refresh_module, "run", _fake_run)
    monkeypatch.setenv("STOOQ_API_KEY", "env-key-789")

    exit_code = main(["--tickers-file", str(tickers_file), "--output", str(output_file)])

    assert exit_code == 0
    assert captured["api_key"] == "env-key-789"


def test_main_defaults_to_no_api_key_when_env_var_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import multica_quant_ops.data.refresh_daily_prices as refresh_module

    tickers_file = tmp_path / "tickers.txt"
    tickers_file.write_text("AAPL\n", encoding="utf-8")
    output_file = tmp_path / "daily_prices.csv"

    captured: dict[str, object] = {}

    def _fake_run(
        tickers_file_arg: Path,
        output_file_arg: Path,
        provider: object | None = None,
        api_key: str | None = None,
    ) -> int:
        captured["api_key"] = api_key
        return 0

    monkeypatch.setattr(refresh_module, "run", _fake_run)
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)

    main(["--tickers-file", str(tickers_file), "--output", str(output_file)])

    assert captured["api_key"] is None
