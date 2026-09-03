"""Cross-checks between universe.csv and sheet_export.csv, plus shape checks
on sheet_export.csv's typed fields.

None of these checks re-derive a score or re-run the pipeline's own
judgment -- they only catch the kind of thing a broken or partial export
(truncated file, stale copy from before a ticker was added, hand edit) would
produce: a scored ticker with no universe entry, a sector that drifted
between the two files, a score or grade outside its documented range.

Field vocabularies (health_grade, verdict, attractiveness_grade ranges) are
sourced from 온톨로지.md (the pipeline's own field dictionary) as of
2026-09-03 and may need updating if that dictionary changes.
"""

from collections.abc import Iterable

from multica_quant_ops.fundamentals.snapshot import FundamentalsRow
from multica_quant_ops.fundamentals.universe import UniverseEntry

VALID_HEALTH_GRADES = frozenset({"A", "B", "C", "D", "F", ""})
VALID_VERDICTS = frozenset(
    {"고위험 투기", "투기적", "중립 하단", "중립", "중립 상단", "미채점"}
)
VALID_ATTRACTIVENESS_GRADES = frozenset({"S", "A", "B", "C", "D", "평가불가"})


def check_snapshot_against_universe(
    snapshot_rows: Iterable[FundamentalsRow],
    universe_entries: Iterable[UniverseEntry],
) -> list[str]:
    """Return a list of human-readable issues; an empty list means clean.

    Checks performed:
      - every snapshot ticker has a matching universe entry
      - every *active* (non-exited) universe ticker appears in the snapshot
      - sector agrees between the two files for tickers present in both
      - investment_score is within [0, 10] when present
      - confidence is within [0, 1] when present
      - health_grade, verdict, attractiveness_grade are within their known
        vocabularies
    """
    issues: list[str] = []
    snapshot_rows = list(snapshot_rows)
    universe_entries = list(universe_entries)

    universe_by_ticker = {e.ticker: e for e in universe_entries}
    snapshot_tickers = {r.ticker for r in snapshot_rows}

    for row in snapshot_rows:
        entry = universe_by_ticker.get(row.ticker)
        if entry is None:
            issues.append(f"{row.ticker}: in sheet_export.csv but missing from universe.csv")
            continue
        if entry.sector != row.sector:
            issues.append(
                f"{row.ticker}: sector mismatch (universe.csv={entry.sector!r}, "
                f"sheet_export.csv={row.sector!r})"
            )
        if row.investment_score is not None and not (0.0 <= row.investment_score <= 10.0):
            issues.append(f"{row.ticker}: investment_score {row.investment_score} outside [0, 10]")
        if row.confidence is not None and not (0.0 <= row.confidence <= 1.0):
            issues.append(f"{row.ticker}: confidence {row.confidence} outside [0, 1]")
        if row.health_grade not in VALID_HEALTH_GRADES:
            issues.append(f"{row.ticker}: unrecognized health_grade {row.health_grade!r}")
        if row.verdict not in VALID_VERDICTS:
            issues.append(f"{row.ticker}: unrecognized verdict {row.verdict!r}")
        if row.attractiveness_grade not in VALID_ATTRACTIVENESS_GRADES:
            issues.append(
                f"{row.ticker}: unrecognized attractiveness_grade {row.attractiveness_grade!r}"
            )

    active_tickers = {e.ticker for e in universe_entries if e.exit_date is None}
    for missing in sorted(active_tickers - snapshot_tickers):
        issues.append(f"{missing}: active in universe.csv but missing from sheet_export.csv")

    return issues
