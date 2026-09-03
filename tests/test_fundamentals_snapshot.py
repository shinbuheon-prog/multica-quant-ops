import csv
import io
from datetime import date
from pathlib import Path

import pytest

from multica_quant_ops.fundamentals.snapshot import SnapshotFormatError, load_sheet_export

HEADER = [
    "티커", "종목명", "섹터", "바구니", "기준종가", "가격일", "판정", "투자점수", "매력도",
    "매매기간성향", "건전성등급", "핵심배수", "공시신호", "주간관측", "최근변화", "예측정확도",
    "최근의견", "신뢰도", "가격관측치", "재무경과일", "수정주가", "최근공시일", "건전성점수",
    "거래비용bp", "감시시작", "채점일", "구글심볼",
]

DEFAULT_ROW = {h: "" for h in HEADER}
DEFAULT_ROW.update(
    {
        "티커": "AAPL",
        "종목명": "Apple",
        "섹터": "소비자·소프트웨어",
        "바구니": "테크·소프트웨어·반도체",
        "기준종가": "319.7000",
        "가격일": "2026-08-28",
        "판정": "중립 상단",
        "투자점수": "7.5",
        "매력도": "A",
        "매매기간성향": "장기보유형",
        "건전성등급": "B",
        "핵심배수": "PER 36.1배 · 베타 1.09",
        "신뢰도": "0.908",
        "가격관측치": "1000",
        "재무경과일": "34",
        "수정주가": "수정주가",
        "최근공시일": "2026-07-31",
        "건전성점수": "75",
        "거래비용bp": "1.3316",
        "감시시작": "2026-08-28",
        "채점일": "2026-08-28",
        "구글심볼": "AAPL",
    }
)


def _write(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "sheet_export.csv"
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=HEADER)
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8-sig")
    return path


def test_load_sheet_export_parses_typed_fields(tmp_path: Path) -> None:
    path = _write(tmp_path, [dict(DEFAULT_ROW)])

    rows = load_sheet_export(path)

    assert len(rows) == 1
    r = rows[0]
    assert r.ticker == "AAPL"
    assert r.sector == "소비자·소프트웨어"
    assert r.reference_close_price == pytest.approx(319.7)
    assert r.price_date == date(2026, 8, 28)
    assert r.investment_score == pytest.approx(7.5)
    assert r.attractiveness_grade == "A"
    assert r.health_grade == "B"
    assert r.filing_alert == ""
    assert r.confidence == pytest.approx(0.908)
    assert r.price_observations == 1000
    assert r.financial_age_days == 34
    assert r.scored_date == date(2026, 8, 28)
    assert r.google_symbol == "AAPL"


def test_load_sheet_export_missing_column_raises(tmp_path: Path) -> None:
    path = tmp_path / "sheet_export.csv"
    path.write_text("티커,종목명\nAAPL,Apple\n", encoding="utf-8-sig")

    with pytest.raises(SnapshotFormatError):
        load_sheet_export(path)


def test_load_sheet_export_empty_ticker_raises(tmp_path: Path) -> None:
    row = dict(DEFAULT_ROW)
    row["티커"] = ""
    path = _write(tmp_path, [row])

    with pytest.raises(SnapshotFormatError):
        load_sheet_export(path)


def test_load_sheet_export_blank_optional_fields_become_none(tmp_path: Path) -> None:
    row = {h: "" for h in HEADER}
    row.update({"티커": "MUFG", "종목명": "MUFG", "섹터": "fin", "바구니": "핀테크", "판정": "미채점", "매력도": "평가불가", "채점일": "2026-08-26", "구글심볼": "MUFG"})
    path = _write(tmp_path, [row])

    rows = load_sheet_export(path)

    r = rows[0]
    assert r.reference_close_price is None
    assert r.price_date is None
    assert r.investment_score is None
    assert r.health_grade == ""
    assert r.confidence is None
