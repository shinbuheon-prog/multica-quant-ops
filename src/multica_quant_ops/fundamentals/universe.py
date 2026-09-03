"""Loader for the fundamentals pipeline's `universe.csv` (survivorship registry).

`universe.csv` is produced by the Cowork pipeline's `pipeline/s0_universe.py`
(0-layer). Each row records, per ticker: when it was first watched
(`watch_added`), whether/when it was delisted from the watch list
(`exit_date`), and how much financial/price history is actually available.
The pipeline uses this to compute an "as-of" universe for any historical
date so a backtest cannot accidentally include a ticker before the day it
was actually selected -- see the module docstring of s0_universe.py for the
full survivorship-bias discussion, which this loader intentionally does not
duplicate, only consumes.
"""

from collections.abc import Iterable
from csv import DictReader
from dataclasses import dataclass
from datetime import date
from pathlib import Path


class UniverseFormatError(ValueError):
    """Raised when universe.csv is missing required columns or has bad values."""


def _parse_date(raw: str) -> date | None:
    raw = raw.strip()
    return date.fromisoformat(raw) if raw else None


def _parse_int(raw: str) -> int:
    return int(raw.strip()) if raw.strip() else 0


@dataclass(frozen=True)
class UniverseEntry:
    ticker: str
    name: str
    sector: str
    cik: str
    fye_month: int
    watch_added: date
    list_date: date | None
    exit_date: date | None
    status: str
    fin_first: date | None
    fin_last: date | None
    fin_quarters: int
    px_first: date | None
    px_last: date | None
    px_obs: int
    px_source: str
    periodic_filer: bool
    note: str

    def is_active_as_of(self, as_of_date: date) -> bool:
        """Mirror s0_universe.py's `as_of()` predicate for a single entry.

        A ticker counts as "in the universe" on `as_of_date` only if it had
        already been watch-added by that date and had not yet exited.
        """
        if self.watch_added > as_of_date:
            return False
        return not (self.exit_date is not None and self.exit_date <= as_of_date)


REQUIRED_COLUMNS = (
    "ticker",
    "name",
    "sector",
    "cik",
    "fye_month",
    "watch_added",
    "list_date",
    "exit_date",
    "status",
    "fin_first",
    "fin_last",
    "fin_quarters",
    "px_first",
    "px_last",
    "px_obs",
    "px_source",
    "periodic_filer",
    "note",
)


def load_universe(path: Path) -> list[UniverseEntry]:
    """Parse universe.csv into typed, validated entries.

    Raises `UniverseFormatError` on a missing column, an unparseable date, or
    a duplicate ticker -- these indicate the export from the Cowork pipeline
    was truncated, hand-edited, or from an incompatible schema version, and
    should stop the caller rather than silently produce partial data.
    """
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = DictReader(handle)
        if reader.fieldnames is None or not set(REQUIRED_COLUMNS).issubset(reader.fieldnames):
            missing = set(REQUIRED_COLUMNS) - set(reader.fieldnames or [])
            raise UniverseFormatError(f"universe.csv is missing required column(s): {sorted(missing)}")

        entries: list[UniverseEntry] = []
        seen: set[str] = set()
        for line_no, row in enumerate(reader, start=2):
            ticker = row["ticker"].strip()
            if not ticker:
                raise UniverseFormatError(f"universe.csv line {line_no}: empty ticker")
            if ticker in seen:
                raise UniverseFormatError(f"universe.csv line {line_no}: duplicate ticker {ticker}")
            seen.add(ticker)
            try:
                watch_added = _parse_date(row["watch_added"])
                if watch_added is None:
                    raise UniverseFormatError(
                        f"universe.csv line {line_no}: {ticker} has no watch_added date"
                    )
                entries.append(
                    UniverseEntry(
                        ticker=ticker,
                        name=row["name"].strip(),
                        sector=row["sector"].strip(),
                        cik=row["cik"].strip(),
                        fye_month=_parse_int(row["fye_month"]),
                        watch_added=watch_added,
                        list_date=_parse_date(row["list_date"]),
                        exit_date=_parse_date(row["exit_date"]),
                        status=row["status"].strip(),
                        fin_first=_parse_date(row["fin_first"]),
                        fin_last=_parse_date(row["fin_last"]),
                        fin_quarters=_parse_int(row["fin_quarters"]),
                        px_first=_parse_date(row["px_first"]),
                        px_last=_parse_date(row["px_last"]),
                        px_obs=_parse_int(row["px_obs"]),
                        px_source=row["px_source"].strip(),
                        periodic_filer=row["periodic_filer"].strip().lower() == "yes",
                        note=row["note"].strip(),
                    )
                )
            except ValueError as exc:
                raise UniverseFormatError(f"universe.csv line {line_no} ({ticker}): {exc}") from exc

        return entries


def as_of(entries: Iterable[UniverseEntry], as_of_date: date) -> list[str]:
    """Tickers that were part of the watch universe on `as_of_date`, sorted.

    This is the survivorship-bias-safe query every backtest must go through
    (see UniverseEntry.is_active_as_of and s0_universe.py section 4).
    """
    return sorted(e.ticker for e in entries if e.is_active_as_of(as_of_date))


def survivorship_gap_days(entries: Iterable[UniverseEntry]) -> int | None:
    """Days between the earliest available price observation and the earliest
    watch_added date across the universe -- the size of the pre-watch window
    for which any backtest is unavoidably survivorship-biased (see
    s0_universe.py section 3). Returns None if no entry has price history.
    """
    entries = list(entries)
    px_firsts = [e.px_first for e in entries if e.px_first is not None]
    if not px_firsts or not entries:
        return None
    first_watch = min(e.watch_added for e in entries)
    earliest_price = min(px_firsts)
    return (first_watch - earliest_price).days
