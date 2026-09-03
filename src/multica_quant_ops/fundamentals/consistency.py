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

`universe.csv`'s `sector` and `sheet_export.csv`'s 섹터 are the same 7-value
taxonomy in two different spellings -- s0_universe.py's SECTOR dict uses
short internal codes (soft/aero/power/infra/fin/heal/semi) while
s9_sheet_export.py writes the Korean label (소비자·소프트웨어/항공우주·방위/
전력·에너지/AI 인프라/금융/헬스케어/반도체) into the sheet. Confirmed against
a real 44-ticker export on 2026-09-03: every ticker's pair of values matched
this exact 1:1 mapping, no third spelling appeared. SECTOR_CODE_LABELS below
is that mapping -- a structural fact about the pipeline's own two-file
schema, not a judgment call -- so the check translates before comparing
rather than expecting the raw strings to match verbatim.
"""

from collections.abc import Iterable

from multica_quant_ops.fundamentals.snapshot import FundamentalsRow
from multica_quant_ops.fundamentals.universe import UniverseEntry

VALID_HEALTH_GRADES = frozenset({"A", "B", "C", "D", "F", ""})
VALID_VERDICTS = frozenset(
    {"고위험 투기", "투기적", "중립 하단", "중립", "중립 상단", "미채점"}
)
VALID_ATTRACTIVENESS_GRADES = frozenset({"S", "A", "B", "C", "D", "평가불가"})

# universe.csv sector code -> sheet_export.csv 섹터 label (see module docstring).
SECTOR_CODE_LABELS: dict[str, str] = {
    "soft": "소비자·소프트웨어",
    "semi": "반도체",
    "heal": "헬스케어",
    "fin": "금융",
    "infra": "AI 인프라",
    "power": "전력·에너지",
    "aero": "항공우주·방위",
}


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
        expected_label = SECTOR_CODE_LABELS.get(entry.sector)
        if expected_label is None:
            issues.append(
                f"{row.ticker}: universe.csv sector code {entry.sector!r} is not in "
                f"SECTOR_CODE_LABELS -- update the mapping if the pipeline added a sector"
            )
        elif expected_label != row.sector:
            issues.append(
                f"{row.ticker}: sector mismatch (universe.csv={entry.sector!r} -> expected "
                f"{expected_label!r}, sheet_export.csv={row.sector!r})"
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
