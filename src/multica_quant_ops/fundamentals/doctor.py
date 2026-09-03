"""The "Doctor" role (docs/FUNDAMENTALS_INTEGRATION.md section 3): a
deterministic health check over the fundamentals adapter's own inputs,
in the same spirit as the Cowork pipeline's own `verify_pipeline.py`
(286 checks, re-run every pipeline execution) -- except this Doctor only
checks what this repo's adapter layer can see (universe.csv,
sheet_export.csv, filing_alert_latest.json), not the scoring logic itself,
which stays out of scope per the Phase 6 thin-adapter decision.

Doctor never re-derives a score or a judgment call. It only catches the
kind of thing that would otherwise fail silently downstream: a broken sync
between universe.csv and sheet_export.csv, a snapshot that has gone stale,
a filing-alert log that doesn't parse. "무음 실패 탐지" (silent-failure
detection) is the point -- an issue here means something to look at, not
that a score is wrong.
"""

import argparse
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from multica_quant_ops.fundamentals.consistency import check_snapshot_against_universe
from multica_quant_ops.fundamentals.filing_alert import validate_filing_alerts_log
from multica_quant_ops.fundamentals.snapshot import (
    FundamentalsRow,
    SnapshotFormatError,
    load_sheet_export,
)
from multica_quant_ops.fundamentals.universe import UniverseFormatError, load_universe


@dataclass(frozen=True)
class DoctorReport:
    checks_run: int
    issues: list[str]

    @property
    def is_healthy(self) -> bool:
        return not self.issues


def check_snapshot_freshness(
    snapshot_rows: list[FundamentalsRow], as_of_date: date, max_age_days: int = 14
) -> list[str]:
    """Flag scored tickers whose price_date is older than `max_age_days`.

    A ticker with no price_date at all (e.g. an unscored placeholder row)
    is not flagged here -- that is a normal "미채점" state, not staleness.
    """
    issues: list[str] = []
    for row in snapshot_rows:
        if row.price_date is None:
            continue
        age = (as_of_date - row.price_date).days
        if age > max_age_days:
            issues.append(
                f"{row.ticker}: price_date {row.price_date.isoformat()} is {age} days old "
                f"(> {max_age_days})"
            )
    return issues


def run_doctor(
    universe_csv: Path,
    sheet_export_csv: Path,
    filing_alerts_csv: Path | None = None,
    as_of_date: date | None = None,
    max_price_age_days: int = 14,
) -> DoctorReport:
    issues: list[str] = []
    checks_run = 0

    try:
        universe_entries = load_universe(universe_csv)
        checks_run += 1
    except (UniverseFormatError, FileNotFoundError) as exc:
        return DoctorReport(checks_run=1, issues=[f"universe.csv failed to load: {exc}"])

    try:
        snapshot_rows = load_sheet_export(sheet_export_csv)
        checks_run += 1
    except (SnapshotFormatError, FileNotFoundError) as exc:
        return DoctorReport(checks_run=2, issues=[f"sheet_export.csv failed to load: {exc}"])

    issues.extend(check_snapshot_against_universe(snapshot_rows, universe_entries))
    checks_run += 1

    issues.extend(
        check_snapshot_freshness(
            snapshot_rows, as_of_date or datetime.now(UTC).date(), max_price_age_days
        )
    )
    checks_run += 1

    if filing_alerts_csv is not None:
        issues.extend(validate_filing_alerts_log(filing_alerts_csv))
        checks_run += 1

    return DoctorReport(checks_run=checks_run, issues=issues)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe-csv", type=Path, required=True)
    parser.add_argument("--sheet-export-csv", type=Path, required=True)
    parser.add_argument("--filing-alerts-csv", type=Path, default=None)
    parser.add_argument("--max-price-age-days", type=int, default=14)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_doctor(
        universe_csv=args.universe_csv,
        sheet_export_csv=args.sheet_export_csv,
        filing_alerts_csv=args.filing_alerts_csv,
        max_price_age_days=args.max_price_age_days,
    )

    print(f"Doctor ran {report.checks_run} check group(s).")
    if report.is_healthy:
        print("OK -- no issues found.")
        return 0

    print(f"NG -- {len(report.issues)} issue(s):")
    for issue in report.issues:
        print(f"  - {issue}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
