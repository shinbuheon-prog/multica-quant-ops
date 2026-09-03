"""Loader for the fundamentals pipeline's `sheet_export.csv` (current-state export).

`sheet_export.csv` is the flat, one-row-per-ticker export the Cowork pipeline
writes at the end of its run (`s9_sheet_export.py`) -- the same file that
feeds the Google Sheet ("지표 시트") and the dashboard. Its Korean column
headers are the pipeline's own field names; this loader keeps them as the
canonical source (see docs/FUNDAMENTALS_INTEGRATION.md and 온톨로지.md for the
field dictionary) and exposes them through English attribute names so the
rest of multica-quant-ops does not need to read Korean CSV headers directly.

Several columns are pipeline-owned *signals* that are read-only from this
repo's point of view (filing_alert, weekly_watch, recent_change,
prediction_check) -- they are not derived here and this loader never
recomputes them; it only parses and validates their shape.
"""

from csv import DictReader
from dataclasses import dataclass
from datetime import date
from pathlib import Path


class SnapshotFormatError(ValueError):
    """Raised when sheet_export.csv is missing required columns or has bad values."""


def _parse_date(raw: str) -> date | None:
    raw = raw.strip()
    return date.fromisoformat(raw) if raw else None


def _parse_float(raw: str) -> float | None:
    raw = raw.strip()
    return float(raw) if raw else None


def _parse_int(raw: str) -> int | None:
    raw = raw.strip()
    return int(raw) if raw else None


@dataclass(frozen=True)
class FundamentalsRow:
    ticker: str
    name: str
    sector: str
    basket: str
    reference_close_price: float | None
    price_date: date | None
    verdict: str
    investment_score: float | None
    attractiveness_grade: str
    holding_horizon: str
    health_grade: str
    key_multiples: str
    filing_alert: str
    weekly_watch: str
    recent_change: str
    prediction_check: str
    latest_opinion: str
    confidence: float | None
    price_observations: int | None
    financial_age_days: int | None
    price_basis_note: str
    latest_filing_date: date | None
    health_score: float | None
    cost_bp: float | None
    watch_start: date | None
    scored_date: date | None
    google_symbol: str


# Korean CSV header -> FundamentalsRow field name. Kept explicit (rather than
# guessed positionally) so a reordered or renamed column in a future pipeline
# export fails loudly via REQUIRED_COLUMNS below instead of silently
# misassigning values.
_COLUMN_MAP = {
    "티커": "ticker",
    "종목명": "name",
    "섹터": "sector",
    "바구니": "basket",
    "기준종가": "reference_close_price",
    "가격일": "price_date",
    "판정": "verdict",
    "투자점수": "investment_score",
    "매력도": "attractiveness_grade",
    "매매기간성향": "holding_horizon",
    "건전성등급": "health_grade",
    "핵심배수": "key_multiples",
    "공시신호": "filing_alert",
    "주간관측": "weekly_watch",
    "최근변화": "recent_change",
    "예측정확도": "prediction_check",
    "최근의견": "latest_opinion",
    "신뢰도": "confidence",
    "가격관측치": "price_observations",
    "재무경과일": "financial_age_days",
    "수정주가": "price_basis_note",
    "최근공시일": "latest_filing_date",
    "건전성점수": "health_score",
    "거래비용bp": "cost_bp",
    "감시시작": "watch_start",
    "채점일": "scored_date",
    "구글심볼": "google_symbol",
}

REQUIRED_COLUMNS = tuple(_COLUMN_MAP)

_DATE_FIELDS = {"price_date", "latest_filing_date", "watch_start", "scored_date"}
_FLOAT_FIELDS = {"reference_close_price", "investment_score", "confidence", "health_score", "cost_bp"}
_INT_FIELDS = {"price_observations", "financial_age_days"}


def load_sheet_export(path: Path) -> list[FundamentalsRow]:
    """Parse sheet_export.csv into typed rows.

    Raises `SnapshotFormatError` on a missing column or an unparseable value
    in a typed field -- signal columns (filing_alert/weekly_watch/
    recent_change/prediction_check) are free-text-or-empty by design and are
    never validated beyond "is a string", since their vocabulary is owned by
    the Cowork pipeline and may grow.
    """
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = DictReader(handle)
        header = reader.fieldnames or []
        if not set(REQUIRED_COLUMNS).issubset(header):
            missing = set(REQUIRED_COLUMNS) - set(header)
            raise SnapshotFormatError(
                f"sheet_export.csv is missing required column(s): {sorted(missing)}"
            )

        rows: list[FundamentalsRow] = []
        for line_no, raw_row in enumerate(reader, start=2):
            mapped = {_COLUMN_MAP[k]: v for k, v in raw_row.items() if k in _COLUMN_MAP}
            ticker = mapped["ticker"].strip()
            if not ticker:
                raise SnapshotFormatError(f"sheet_export.csv line {line_no}: empty ticker")
            try:
                values: dict[str, object] = {}
                for field, raw_value in mapped.items():
                    if field in _DATE_FIELDS:
                        values[field] = _parse_date(raw_value)
                    elif field in _FLOAT_FIELDS:
                        values[field] = _parse_float(raw_value)
                    elif field in _INT_FIELDS:
                        values[field] = _parse_int(raw_value)
                    else:
                        values[field] = raw_value.strip()
                rows.append(FundamentalsRow(**values))  # type: ignore[arg-type]
            except ValueError as exc:
                raise SnapshotFormatError(f"sheet_export.csv line {line_no} ({ticker}): {exc}") from exc

        return rows
