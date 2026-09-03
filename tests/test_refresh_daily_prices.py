from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from multica_quant_ops.data.providers.base import MarketQuote
from multica_quant_ops.data.refresh_daily_prices import (
    PriceRow,
    collect_alphavantage_api_keys,
    load_cursor,
    load_existing_prices,
    load_ticker_list,
    main,
    refresh_prices,
    run,
    save_cursor,
    select_ticker_batch,
    usage_file_for_key,
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


def test_main_provider_stooq_reads_stooq_api_key_from_environment(
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
        **kwargs: object,
    ) -> int:
        captured["provider"] = provider
        return 0

    monkeypatch.setattr(refresh_module, "run", _fake_run)
    monkeypatch.setenv("STOOQ_API_KEY", "env-key-789")

    exit_code = main(
        ["--provider", "stooq", "--tickers-file", str(tickers_file), "--output", str(output_file)]
    )

    assert exit_code == 0
    assert captured["provider"].api_key == "env-key-789"  # type: ignore[attr-defined]


def test_main_provider_stooq_defaults_to_no_api_key_when_env_var_unset(
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
        **kwargs: object,
    ) -> int:
        captured["provider"] = provider
        return 0

    monkeypatch.setattr(refresh_module, "run", _fake_run)
    monkeypatch.delenv("STOOQ_API_KEY", raising=False)

    main(
        ["--provider", "stooq", "--tickers-file", str(tickers_file), "--output", str(output_file)]
    )

    assert captured["provider"].api_key is None  # type: ignore[attr-defined]


def test_main_defaults_to_alphavantage_provider_and_requires_its_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tickers_file = tmp_path / "tickers.txt"
    tickers_file.write_text("AAPL\n", encoding="utf-8")
    output_file = tmp_path / "daily_prices.csv"

    monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)

    with pytest.raises(SystemExit):
        main(["--tickers-file", str(tickers_file), "--output", str(output_file)])


def test_main_defaults_to_alphavantage_provider_when_key_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import multica_quant_ops.data.refresh_daily_prices as refresh_module
    from multica_quant_ops.data.providers.alphavantage import AlphaVantageMarketDataProvider

    tickers_file = tmp_path / "tickers.txt"
    tickers_file.write_text("AAPL\n", encoding="utf-8")
    output_file = tmp_path / "daily_prices.csv"

    captured: dict[str, object] = {}

    def _fake_run(
        tickers_file_arg: Path,
        output_file_arg: Path,
        provider: object | None = None,
        **kwargs: object,
    ) -> int:
        captured["provider"] = provider
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(refresh_module, "run", _fake_run)
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "av-key-123")

    exit_code = main(["--tickers-file", str(tickers_file), "--output", str(output_file)])

    assert exit_code == 0
    assert isinstance(captured["provider"], AlphaVantageMarketDataProvider)
    assert captured["provider"].api_key == "av-key-123"  # type: ignore[attr-defined]
    assert captured["source_name"] == "alphavantage"
    assert captured["batch_size"] == 20
    assert captured["cursor_file"] == Path("ops/prices/refresh_cursor.txt")


def test_select_ticker_batch_takes_batch_size_from_cursor() -> None:
    tickers = ["A", "B", "C", "D", "E"]

    batch, next_cursor = select_ticker_batch(tickers, cursor=0, batch_size=2)

    assert batch == ["A", "B"]
    assert next_cursor == 2


def test_select_ticker_batch_wraps_around_the_end_of_the_list() -> None:
    tickers = ["A", "B", "C", "D", "E"]

    batch, next_cursor = select_ticker_batch(tickers, cursor=4, batch_size=3)

    assert batch == ["E", "A", "B"]
    assert next_cursor == 2


def test_select_ticker_batch_caps_at_the_full_list_when_batch_size_is_larger() -> None:
    tickers = ["A", "B", "C"]

    batch, next_cursor = select_ticker_batch(tickers, cursor=0, batch_size=10)

    assert batch == ["A", "B", "C"]
    assert next_cursor == 0


def test_select_ticker_batch_handles_empty_ticker_list() -> None:
    assert select_ticker_batch([], cursor=0, batch_size=5) == ([], 0)


def test_load_cursor_missing_file_returns_zero(tmp_path: Path) -> None:
    assert load_cursor(tmp_path / "nope.txt") == 0


def test_load_cursor_ignores_corrupt_content(tmp_path: Path) -> None:
    path = tmp_path / "cursor.txt"
    path.write_text("not-a-number", encoding="utf-8")

    assert load_cursor(path) == 0


def test_save_and_load_cursor_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "cursor.txt"

    save_cursor(path, 17)

    assert load_cursor(path) == 17


def test_run_with_rotation_only_fetches_this_runs_batch_and_keeps_the_rest(
    tmp_path: Path,
) -> None:
    """With a 4-ticker universe and batch_size=2, one run must only spend
    provider calls on 2 of them, and the other 2 must keep whatever row they
    already had -- this is the free-tier rotation from
    docs/FUNDAMENTALS_INTEGRATION.md 9-10, not a failure.
    """
    tickers_file = tmp_path / "tickers.txt"
    tickers_file.write_text("AAPL\nMSFT\nGOOGL\nAMZN\n", encoding="utf-8")
    output_file = tmp_path / "daily_prices.csv"
    cursor_file = tmp_path / "cursor.txt"

    existing_googl = PriceRow(
        ticker="GOOGL",
        trading_day=date(2026, 8, 20),
        open_price=100.0,
        high_price=101.0,
        low_price=99.0,
        close_price=100.5,
        volume=10,
        updated_at=datetime(2026, 8, 20, tzinfo=UTC),
        source="alphavantage",
        stale=False,
    )
    write_prices_csv(output_file, {"GOOGL": existing_googl})

    provider = _StubProvider({"AAPL": _quote("AAPL", 200.0), "MSFT": _quote("MSFT", 400.0)})

    exit_code = run(
        tickers_file, output_file, provider=provider, cursor_file=cursor_file, batch_size=2
    )

    assert exit_code == 0
    reloaded = load_existing_prices(output_file)
    assert reloaded["AAPL"].close_price == 200.0
    assert reloaded["MSFT"].close_price == 400.0
    # GOOGL wasn't in this run's batch at all -- untouched, not marked stale.
    assert reloaded["GOOGL"] == existing_googl
    assert "AMZN" not in reloaded
    assert load_cursor(cursor_file) == 2


def test_run_with_rotation_advances_cursor_across_successive_runs(tmp_path: Path) -> None:
    tickers_file = tmp_path / "tickers.txt"
    tickers_file.write_text("AAPL\nMSFT\nGOOGL\n", encoding="utf-8")
    output_file = tmp_path / "daily_prices.csv"
    cursor_file = tmp_path / "cursor.txt"

    provider = _StubProvider(
        {
            "AAPL": _quote("AAPL", 200.0),
            "MSFT": _quote("MSFT", 400.0),
            "GOOGL": _quote("GOOGL", 150.0),
        }
    )

    run(tickers_file, output_file, provider=provider, cursor_file=cursor_file, batch_size=2)
    assert load_cursor(cursor_file) == 2

    run(tickers_file, output_file, provider=provider, cursor_file=cursor_file, batch_size=2)
    assert load_cursor(cursor_file) == 1  # wrapped around after GOOGL

    reloaded = load_existing_prices(output_file)
    assert set(reloaded) == {"AAPL", "MSFT", "GOOGL"}


def test_collect_alphavantage_api_keys_returns_only_primary_when_no_extras() -> None:
    assert collect_alphavantage_api_keys({"ALPHAVANTAGE_API_KEY": "av-key-123"}) == ["av-key-123"]


def test_collect_alphavantage_api_keys_returns_empty_list_when_unset() -> None:
    assert collect_alphavantage_api_keys({}) == []


def test_collect_alphavantage_api_keys_picks_up_numbered_extras_in_order() -> None:
    env = {
        "ALPHAVANTAGE_API_KEY": "key-1",
        "ALPHAVANTAGE_API_KEY_2": "key-2",
        "ALPHAVANTAGE_API_KEY_3": "key-3",
    }

    assert collect_alphavantage_api_keys(env) == ["key-1", "key-2", "key-3"]


def test_collect_alphavantage_api_keys_stops_at_the_first_missing_suffix() -> None:
    # _4 is set but _3 (the gap right before it) is not -- numbering must be
    # contiguous from 2, so collection stops at the gap and _4 is ignored.
    env = {
        "ALPHAVANTAGE_API_KEY": "key-1",
        "ALPHAVANTAGE_API_KEY_2": "key-2",
        "ALPHAVANTAGE_API_KEY_4": "key-4",
    }

    assert collect_alphavantage_api_keys(env) == ["key-1", "key-2"]


def test_collect_alphavantage_api_keys_treats_blank_extras_as_unset() -> None:
    env = {"ALPHAVANTAGE_API_KEY": "key-1", "ALPHAVANTAGE_API_KEY_2": ""}

    assert collect_alphavantage_api_keys(env) == ["key-1"]


def test_usage_file_for_key_one_keeps_the_original_path() -> None:
    base = Path("ops/prices/alphavantage_usage.json")

    assert usage_file_for_key(base, 1) == base


def test_usage_file_for_key_two_and_three_get_sibling_files() -> None:
    base = Path("ops/prices/alphavantage_usage.json")

    assert usage_file_for_key(base, 2) == Path("ops/prices/alphavantage_usage_2.json")
    assert usage_file_for_key(base, 3) == Path("ops/prices/alphavantage_usage_3.json")


def test_main_builds_multi_key_provider_and_full_coverage_batch_size_when_extra_keys_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With enough keys to cover the whole ticker list in one run (2 keys *
    25/day = 50 >= 3 tickers here), main() should stop rotating and attempt
    every ticker every run (docs/FUNDAMENTALS_INTEGRATION.md 9-11)."""
    import multica_quant_ops.data.refresh_daily_prices as refresh_module
    from multica_quant_ops.data.providers.alphavantage import MultiKeyAlphaVantageProvider

    tickers_file = tmp_path / "tickers.txt"
    tickers_file.write_text("AAPL\nMSFT\nGOOGL\n", encoding="utf-8")
    output_file = tmp_path / "daily_prices.csv"

    captured: dict[str, object] = {}

    def _fake_run(
        tickers_file_arg: Path,
        output_file_arg: Path,
        provider: object | None = None,
        **kwargs: object,
    ) -> int:
        captured["provider"] = provider
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(refresh_module, "run", _fake_run)
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "key-1")
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY_2", "key-2")

    exit_code = main(["--tickers-file", str(tickers_file), "--output", str(output_file)])

    assert exit_code == 0
    assert isinstance(captured["provider"], MultiKeyAlphaVantageProvider)
    assert captured["batch_size"] == 3  # all 3 tickers, no rotation needed


def test_main_respects_explicit_batch_size_even_with_multiple_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import multica_quant_ops.data.refresh_daily_prices as refresh_module

    tickers_file = tmp_path / "tickers.txt"
    tickers_file.write_text("AAPL\nMSFT\nGOOGL\n", encoding="utf-8")
    output_file = tmp_path / "daily_prices.csv"

    captured: dict[str, object] = {}

    def _fake_run(
        tickers_file_arg: Path,
        output_file_arg: Path,
        provider: object | None = None,
        **kwargs: object,
    ) -> int:
        captured.update(kwargs)
        return 0

    monkeypatch.setattr(refresh_module, "run", _fake_run)
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "key-1")
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY_2", "key-2")

    exit_code = main(
        ["--tickers-file", str(tickers_file), "--output", str(output_file), "--batch-size", "1"]
    )

    assert exit_code == 0
    assert captured["batch_size"] == 1


def test_run_reports_provider_usage_snapshot_when_available(tmp_path: Path) -> None:
    tickers_file = tmp_path / "tickers.txt"
    tickers_file.write_text("AAPL\n", encoding="utf-8")
    output_file = tmp_path / "daily_prices.csv"

    class _UsageSnapshot:
        date = "2026-09-03"
        used_calls = 5
        daily_limit = 25
        remaining_calls = 20

    class _ProviderWithUsage(_StubProvider):
        @property
        def last_usage_snapshot(self) -> _UsageSnapshot:
            return _UsageSnapshot()

    provider = _ProviderWithUsage({"AAPL": _quote("AAPL", 200.0)})

    exit_code = run(tickers_file, output_file, provider=provider)

    assert exit_code == 0  # the important thing: a usage snapshot never breaks the run
