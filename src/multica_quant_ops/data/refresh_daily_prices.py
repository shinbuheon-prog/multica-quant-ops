"""Daily batch price refresh for the full ticker universe.

This is the deterministic, network-dependent counterpart to the low-frequency
same-day preparation flow: it is meant to run once a day (see
`.github/workflows/refresh-daily-prices.yml`), independent of whether a
Cowork session happens to be open, which is what fixes the price-staleness
gap described in docs/FUNDAMENTALS_INTEGRATION.md section 5-4.

Design point (section 9-3 of that doc): one bad ticker must never fail the
whole run. Each symbol is fetched independently; on failure the previous
row is carried forward and flagged `stale=true` rather than dropped, so a
transient Stooq hiccup degrades gracefully instead of blanking a price.
"""

import argparse
import csv
import os
import sys
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from pathlib import Path

from multica_quant_ops.data.providers.base import MarketDataProvider
from multica_quant_ops.data.providers.stooq import StooqDataError, StooqMarketDataProvider

CSV_FIELDS = [
    "ticker",
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "updated_at",
    "source",
    "stale",
]


@dataclass(frozen=True)
class PriceRow:
    ticker: str
    trading_day: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    updated_at: datetime
    source: str
    stale: bool

    def to_csv_row(self) -> dict[str, str]:
        return {
            "ticker": self.ticker,
            "date": self.trading_day.isoformat(),
            "open": f"{self.open_price:.4f}",
            "high": f"{self.high_price:.4f}",
            "low": f"{self.low_price:.4f}",
            "close": f"{self.close_price:.4f}",
            "volume": str(self.volume),
            "updated_at": self.updated_at.isoformat(),
            "source": self.source,
            "stale": "true" if self.stale else "false",
        }

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> "PriceRow":
        return cls(
            ticker=row["ticker"],
            trading_day=date.fromisoformat(row["date"]),
            open_price=float(row["open"]),
            high_price=float(row["high"]),
            low_price=float(row["low"]),
            close_price=float(row["close"]),
            volume=int(row["volume"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            source=row["source"],
            stale=row["stale"].strip().lower() == "true",
        )


def load_ticker_list(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(
            f"Ticker list not found at {path}. Populate it (one ticker per line, "
            f"'#' comments allowed) before running the daily refresh."
        )
    tickers: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tickers.append(stripped.upper())
    return tickers


def load_existing_prices(path: Path) -> dict[str, PriceRow]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return {row["ticker"]: PriceRow.from_csv_row(row) for row in reader}


def refresh_prices(
    tickers: list[str],
    provider: MarketDataProvider,
    existing: dict[str, PriceRow],
    now: datetime,
    source_name: str = "stooq",
) -> tuple[dict[str, PriceRow], list[tuple[str, str]]]:
    """Fetch a fresh quote per ticker; fall back to the previous row on failure.

    Returns the merged {ticker: PriceRow} map and a list of (ticker, reason)
    failures so the caller can surface them (log, alert) without the run
    itself failing.
    """
    results: dict[str, PriceRow] = {}
    failures: list[tuple[str, str]] = []

    for ticker in tickers:
        try:
            quote = provider.fetch_quote(ticker)
            results[ticker] = PriceRow(
                ticker=ticker,
                trading_day=quote.latest_trading_day,
                open_price=quote.open_price,
                high_price=quote.high_price,
                low_price=quote.low_price,
                close_price=quote.price,
                volume=quote.volume,
                updated_at=now,
                source=source_name,
                stale=False,
            )
        except (StooqDataError, ValueError) as exc:
            failures.append((ticker, str(exc)))
            previous = existing.get(ticker)
            if previous is not None:
                results[ticker] = replace(previous, stale=True)

    return results, failures


def write_prices_csv(path: Path, rows: dict[str, PriceRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for ticker in sorted(rows):
            writer.writerow(rows[ticker].to_csv_row())


def run(
    tickers_file: Path,
    output_file: Path,
    provider: MarketDataProvider | None = None,
    api_key: str | None = None,
) -> int:
    provider = provider or StooqMarketDataProvider(api_key=api_key)
    tickers = load_ticker_list(tickers_file)
    existing = load_existing_prices(output_file)
    now = datetime.now(UTC)

    results, failures = refresh_prices(tickers, provider, existing, now)
    write_prices_csv(output_file, results)

    print(f"Refreshed {len(results)}/{len(tickers)} tickers -> {output_file}")
    if failures:
        print(f"{len(failures)} ticker(s) fell back to the previous price (stale=true):")
        for ticker, reason in failures:
            print(f"  {ticker}: {reason}")

    missing = [t for t in tickers if t not in results]
    if missing:
        print(f"{len(missing)} ticker(s) have no price at all yet (no previous row to fall back to): {missing}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tickers-file",
        type=Path,
        default=Path("ops/tickers.txt"),
        help="Newline-separated ticker list ('#' comments allowed).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ops/prices/daily_prices.csv"),
        help="CSV file to write/update.",
    )
    args = parser.parse_args(argv)
    # Stooq's /q/d/l/ endpoint has required a key since 2026-03 (see
    # docs/FUNDAMENTALS_INTEGRATION.md 9-7) -- read it from the environment
    # rather than a CLI flag so it never appears in a shell history or a
    # workflow log. Missing/empty is fine: every request will 404 and each
    # ticker degrades to stale=true via the same per-symbol failure path as
    # any other Stooq outage.
    return run(args.tickers_file, args.output, api_key=os.environ.get("STOOQ_API_KEY") or None)


if __name__ == "__main__":
    sys.exit(main())
