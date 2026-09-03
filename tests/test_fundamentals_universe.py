from datetime import date
from pathlib import Path

import pytest

from multica_quant_ops.fundamentals.universe import (
    UniverseFormatError,
    as_of,
    load_universe,
    survivorship_gap_days,
)

HEADER = (
    "ticker,name,sector,cik,fye_month,watch_added,list_date,exit_date,status,"
    "fin_first,fin_last,fin_quarters,px_first,px_last,px_obs,px_source,periodic_filer,note"
)


def _write(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "universe.csv"
    path.write_text(HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_load_universe_parses_dates_and_flags(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            (
                "AAPL,Apple,soft,0000320193,9,2026-08-28,,,active,"
                "2023-12-30,2026-06-27,11,2022-09-02,2026-08-28,1000,long,yes,"
            ),
            "MUFG,MUFG,fin,0000067088,3,2026-08-26,,,active,,,0,,,0,,no,20-F filer",
        ],
    )

    entries = load_universe(path)

    assert len(entries) == 2
    aapl = entries[0]
    assert aapl.ticker == "AAPL"
    assert aapl.watch_added == date(2026, 8, 28)
    assert aapl.exit_date is None
    assert aapl.periodic_filer is True
    assert aapl.fin_quarters == 11
    mufg = entries[1]
    assert mufg.periodic_filer is False
    assert mufg.fin_first is None


def test_load_universe_missing_column_raises(tmp_path: Path) -> None:
    path = tmp_path / "universe.csv"
    path.write_text("ticker,name\nAAPL,Apple\n", encoding="utf-8")

    with pytest.raises(UniverseFormatError):
        load_universe(path)


def test_load_universe_duplicate_ticker_raises(tmp_path: Path) -> None:
    row = (
        "AAPL,Apple,soft,0000320193,9,2026-08-28,,,active,"
        "2023-12-30,2026-06-27,11,2022-09-02,2026-08-28,1000,long,yes,"
    )
    path = _write(tmp_path, [row, row])

    with pytest.raises(UniverseFormatError):
        load_universe(path)


def test_load_universe_missing_watch_added_raises(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            (
                "AAPL,Apple,soft,0000320193,9,,,,active,"
                "2023-12-30,2026-06-27,11,2022-09-02,2026-08-28,1000,long,yes,"
            ),
        ],
    )

    with pytest.raises(UniverseFormatError):
        load_universe(path)


def test_as_of_excludes_tickers_before_watch_added_and_after_exit(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            "AAPL,Apple,soft,0000320193,9,2026-08-26,,,active,,,0,,,0,,yes,",
            "OLD,Old Co,soft,0000000001,12,2026-08-26,,2026-09-01,delisted,,,0,,,0,,yes,",
            "NEW,New Co,soft,0000000002,12,2026-09-02,,,active,,,0,,,0,,yes,",
        ],
    )
    entries = load_universe(path)

    assert as_of(entries, date(2026, 8, 25)) == []
    assert as_of(entries, date(2026, 8, 26)) == ["AAPL", "OLD"]
    assert as_of(entries, date(2026, 9, 1)) == ["AAPL"]  # OLD exited on 9/1
    assert as_of(entries, date(2026, 9, 2)) == ["AAPL", "NEW"]


def test_survivorship_gap_days_measures_pre_watch_price_history(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        [
            "AAPL,Apple,soft,0000320193,9,2026-08-28,,,active,,,0,2026-08-01,2026-08-28,20,long,yes,",
        ],
    )
    entries = load_universe(path)

    assert survivorship_gap_days(entries) == 27


def test_survivorship_gap_days_none_when_no_price_history(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        ["AAPL,Apple,soft,0000320193,9,2026-08-28,,,active,,,0,,,0,,yes,"],
    )
    entries = load_universe(path)

    assert survivorship_gap_days(entries) is None
