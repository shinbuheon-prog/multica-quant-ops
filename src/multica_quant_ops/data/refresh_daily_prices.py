"""Daily batch price refresh for the full ticker universe.

This is the deterministic, network-dependent counterpart to the low-frequency
same-day preparation flow: it is meant to run once a day (see
`.github/workflows/refresh-daily-prices.yml`), independent of whether a
Cowork session happens to be open, which is what fixes the price-staleness
gap described in docs/FUNDAMENTALS_INTEGRATION.md section 5-4.

Design point (section 9-3 of that doc): one bad ticker must never fail the
whole run. Each symbol is fetched independently; on failure the previous
row is carried forward and flagged `stale=true` rather than dropped, so a
transient provider hiccup degrades gracefully instead of blanking a price.

Provider history (see docs/FUNDAMENTALS_INTEGRATION.md 9-3, 9-6..9-11):
Stooq was the original choice specifically because it needed no key, but by
2026-09 it requires passing a JavaScript proof-of-work challenge that only a
real browser's JS engine can complete -- automating that is bot-detection
bypass, which this project does not do, so the default provider is now
Alpha Vantage (`--provider alphavantage`, the default). A single Alpha
Vantage free-tier key is 25 calls/day, well under 44 tickers, so with only
`ALPHAVANTAGE_API_KEY` set a run only *attempts* `--batch-size` tickers
(default 20, leaving headroom under the 25 cap) and rotates through the
ticker list across runs via a persisted cursor file -- every ticker gets
refreshed roughly every couple of days rather than daily. Registering
additional *dedicated* keys as `ALPHAVANTAGE_API_KEY_2`, `_3`, ... (see
9-11) raises the combined daily budget by 25 calls each, and once that
combined budget covers the whole ticker list the rotation naturally
disappears (every ticker refreshes every run instead of every couple of
days) -- no flag needed, `--batch-size` still overrides this if set
explicitly. `--provider stooq` is kept available (with the same-day-flow
degrade-per-ticker behavior) in case Stooq's requirement changes again.
"""

import argparse
import csv
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from pathlib import Path

from multica_quant_ops.data.providers.alphavantage import (
    AlphaVantageMarketDataProvider,
    MultiKeyAlphaVantageProvider,
)
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


def select_ticker_batch(tickers: list[str], cursor: int, batch_size: int) -> tuple[list[str], int]:
    """Pick the next `batch_size` tickers starting at `cursor`, wrapping
    around the list, and return (this run's tickers, the cursor to persist
    for the next run).

    This is how a free-tier daily call quota turns into "every ticker gets
    refreshed roughly every len(tickers)/batch_size runs" instead of
    "daily" -- see the module docstring and docs/FUNDAMENTALS_INTEGRATION.md
    9-10.
    """
    if not tickers or batch_size <= 0:
        return [], cursor
    n = len(tickers)
    start = cursor % n
    size = min(batch_size, n)
    batch = [tickers[(start + i) % n] for i in range(size)]
    next_cursor = (start + size) % n
    return batch, next_cursor


def load_cursor(path: Path) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8").strip()
    try:
        return int(text)
    except ValueError:
        return 0


def save_cursor(path: Path, cursor: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(cursor), encoding="utf-8")


def collect_alphavantage_api_keys(env: Mapping[str, str] = os.environ) -> list[str]:
    """`ALPHAVANTAGE_API_KEY` plus any `ALPHAVANTAGE_API_KEY_2`,
    `_3`, ... found in order (see docs/FUNDAMENTALS_INTEGRATION.md 9-11).
    Stops at the first missing/blank suffix, so keys must be numbered
    contiguously from 2. Each should be a key *dedicated* to this workflow
    (see the workflow file's header comment) -- sharing one with another
    flow just moves the quota-collision problem instead of solving it.
    """
    keys: list[str] = []
    primary = env.get("ALPHAVANTAGE_API_KEY")
    if primary:
        keys.append(primary)
    index = 2
    while True:
        extra = env.get(f"ALPHAVANTAGE_API_KEY_{index}")
        if not extra:
            break
        keys.append(extra)
        index += 1
    return keys


def usage_file_for_key(base: Path, key_index: int) -> Path:
    """Each Alpha Vantage key needs its own usage-tracking file -- sharing
    one file across keys would conflate independent quotas into a single
    (wrong) count. Key 1 keeps the original path unchanged (so single-key
    setups, and history already on disk, are untouched); key N>=2 gets a
    sibling file named `<stem>_<N><suffix>`.
    """
    if key_index <= 1:
        return base
    return base.with_name(f"{base.stem}_{key_index}{base.suffix}")


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
    cursor_file: Path | None = None,
    batch_size: int | None = None,
    source_name: str = "stooq",
) -> int:
    provider = provider or StooqMarketDataProvider(api_key=api_key)
    tickers = load_ticker_list(tickers_file)
    existing = load_existing_prices(output_file)
    now = datetime.now(UTC)

    rotating = cursor_file is not None and batch_size is not None
    if rotating:
        assert cursor_file is not None and batch_size is not None  # narrowed by `rotating`
        cursor = load_cursor(cursor_file)
        batch, next_cursor = select_ticker_batch(tickers, cursor, batch_size)
    else:
        batch, next_cursor = tickers, None

    batch_results, failures = refresh_prices(batch, provider, existing, now, source_name=source_name)
    # Tickers outside this run's batch keep whatever row they already had --
    # they're not "failed", just not due for a refresh yet under rotation.
    merged = {**existing, **batch_results}
    write_prices_csv(output_file, merged)

    if rotating:
        assert cursor_file is not None and next_cursor is not None
        save_cursor(cursor_file, next_cursor)

    print(f"Refreshed {len(batch_results)}/{len(batch)} tickers in this run's batch -> {output_file}")
    if batch_size is not None and len(batch) < len(tickers):
        print(
            f"Batch covered {len(batch)}/{len(tickers)} tickers total "
            f"(rotating via {cursor_file} -- see docs/FUNDAMENTALS_INTEGRATION.md 9-10)."
        )
    if failures:
        print(f"{len(failures)} ticker(s) fell back to the previous price (stale=true):")
        for ticker, reason in failures:
            print(f"  {ticker}: {reason}")

    missing_overall = [t for t in tickers if t not in merged]
    if missing_overall:
        print(
            f"{len(missing_overall)} ticker(s) have no price at all yet "
            f"(never successfully fetched): {missing_overall}"
        )

    usage = getattr(provider, "last_usage_snapshot", None)
    if usage is not None:
        print(
            f"Provider usage today ({usage.date}): {usage.used_calls}/{usage.daily_limit} "
            f"calls used, {usage.remaining_calls} remaining."
        )

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
    parser.add_argument(
        "--provider",
        choices=["alphavantage", "stooq"],
        default="alphavantage",
        help=(
            "Which market data provider to use. alphavantage (default) requires "
            "ALPHAVANTAGE_API_KEY and rotates through the ticker list under its "
            "free-tier daily call cap (see --batch-size). stooq requires no key "
            "but as of 2026-09 fails a JavaScript bot-verification challenge from "
            "automated environments (docs/FUNDAMENTALS_INTEGRATION.md 9-9) -- kept "
            "available in case that changes."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help=(
            "Alpha Vantage only: max tickers to attempt in this run. Defaults to "
            "20 with a single key (leaving headroom under the free tier's "
            "25-calls/day cap), or to the full ticker list once enough "
            "ALPHAVANTAGE_API_KEY_2/_3/... keys are registered to cover it in one "
            "run (see docs/FUNDAMENTALS_INTEGRATION.md 9-11). Ignored for "
            "--provider stooq, which always attempts every ticker."
        ),
    )
    parser.add_argument(
        "--cursor-file",
        type=Path,
        default=Path("ops/prices/refresh_cursor.txt"),
        help="Alpha Vantage only: where to persist rotation position between runs.",
    )
    parser.add_argument(
        "--alphavantage-usage-file",
        type=Path,
        default=Path("ops/prices/alphavantage_usage.json"),
        help="Alpha Vantage only: where to persist today's call count between runs.",
    )
    parser.add_argument(
        "--alphavantage-daily-limit",
        type=int,
        default=25,
        help="Alpha Vantage only: the account's actual daily call cap.",
    )
    args = parser.parse_args(argv)

    if args.provider == "stooq":
        # Stooq's /q/d/l/ endpoint has required a key since 2026-03 (see
        # docs/FUNDAMENTALS_INTEGRATION.md 9-7) -- read it from the environment
        # rather than a CLI flag so it never appears in a shell history or a
        # workflow log. Missing/empty is fine: every request will 404 and each
        # ticker degrades to stale=true via the same per-symbol failure path as
        # any other Stooq outage.
        stooq_provider = StooqMarketDataProvider(api_key=os.environ.get("STOOQ_API_KEY") or None)
        return run(args.tickers_file, args.output, provider=stooq_provider, source_name="stooq")

    api_keys = collect_alphavantage_api_keys()
    if not api_keys:
        raise SystemExit(
            "ALPHAVANTAGE_API_KEY is required for --provider alphavantage (the default). "
            "Set --provider stooq to use the key-less (currently blocked, see "
            "docs/FUNDAMENTALS_INTEGRATION.md 9-9) Stooq provider instead."
        )

    if len(api_keys) == 1:
        alphavantage_provider: MarketDataProvider = AlphaVantageMarketDataProvider.build_free_mode(
            api_key=api_keys[0],
            usage_file=args.alphavantage_usage_file,
            daily_limit=args.alphavantage_daily_limit,
        )
    else:
        alphavantage_provider = MultiKeyAlphaVantageProvider(
            [
                AlphaVantageMarketDataProvider.build_free_mode(
                    api_key=key,
                    usage_file=usage_file_for_key(args.alphavantage_usage_file, index),
                    daily_limit=args.alphavantage_daily_limit,
                )
                for index, key in enumerate(api_keys, start=1)
            ]
        )

    batch_size = args.batch_size
    if batch_size is None:
        if len(api_keys) == 1:
            batch_size = 20
        else:
            # Enough keys can cover the whole list in one run -- let them,
            # rather than keeping the single-key rotation cadence around
            # once it's no longer necessary (docs/FUNDAMENTALS_INTEGRATION.md 9-11).
            total_capacity = len(api_keys) * args.alphavantage_daily_limit
            batch_size = min(len(load_ticker_list(args.tickers_file)), total_capacity)

    return run(
        args.tickers_file,
        args.output,
        provider=alphavantage_provider,
        cursor_file=args.cursor_file,
        batch_size=batch_size,
        source_name="alphavantage",
    )


if __name__ == "__main__":
    sys.exit(main())
