import csv
import io
from datetime import date
from pathlib import Path

from multica_quant_ops.fundamentals.doctor import (
    check_snapshot_freshness,
    run_doctor,
)
from multica_quant_ops.fundamentals.snapshot import FundamentalsRow

UNIVERSE_HEADER = (
    "ticker,name,sector,cik,fye_month,watch_added,list_date,exit_date,status,"
    "fin_first,fin_last,fin_quarters,px_first,px_last,px_obs,px_source,periodic_filer,note"
)

SNAPSHOT_HEADER = [
    "티커", "종목명", "섹터", "바구니", "기준종가", "가격일", "판정", "투자점수", "매력도",
    "매매기간성향", "건전성등급", "핵심배수", "공시신호", "주간관측", "최근변화", "예측정확도",
    "최근의견", "신뢰도", "가격관측치", "재무경과일", "수정주가", "최근공시일", "건전성점수",
    "거래비용bp", "감시시작", "채점일", "구글심볼",
]


def _write_universe(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "universe.csv"
    path.write_text(UNIVERSE_HEADER + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def _snapshot_dict_row(ticker: str, sector: str, price_date: str) -> dict[str, str]:
    row = {h: "" for h in SNAPSHOT_HEADER}
    row.update(
        {
            "티커": ticker, "종목명": ticker, "섹터": sector, "바구니": "basket",
            "기준종가": "100.0", "가격일": price_date, "판정": "중립", "투자점수": "7.0",
            "매력도": "B", "매매기간성향": "장기보유형", "건전성등급": "B",
            "신뢰도": "0.9", "가격관측치": "100", "재무경과일": "1", "채점일": price_date,
            "구글심볼": ticker,
        }
    )
    return row


def _write_snapshot(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    path = tmp_path / "sheet_export.csv"
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=SNAPSHOT_HEADER)
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8-sig")
    return path


def _row(ticker: str, price_date: date | None) -> FundamentalsRow:
    return FundamentalsRow(
        ticker=ticker, name=ticker, sector="soft", basket="b",
        reference_close_price=100.0, price_date=price_date, verdict="중립",
        investment_score=7.0, attractiveness_grade="B", holding_horizon="장기보유형",
        health_grade="B", key_multiples="", filing_alert="", weekly_watch="",
        recent_change="", prediction_check="", latest_opinion="", confidence=0.9,
        price_observations=100, financial_age_days=1, price_basis_note="",
        latest_filing_date=None, health_score=75.0, cost_bp=1.0,
        watch_start=date(2026, 8, 26), scored_date=date(2026, 8, 26), google_symbol=ticker,
    )


def test_check_snapshot_freshness_flags_stale_price_date() -> None:
    rows = [_row("AAPL", date(2026, 8, 1)), _row("MSFT", date(2026, 8, 25))]

    issues = check_snapshot_freshness(rows, as_of_date=date(2026, 9, 3), max_age_days=14)

    assert any("AAPL" in issue for issue in issues)
    assert not any("MSFT" in issue for issue in issues)


def test_check_snapshot_freshness_ignores_unscored_rows() -> None:
    rows = [_row("MUFG", None)]

    assert check_snapshot_freshness(rows, as_of_date=date(2026, 9, 3)) == []


def test_run_doctor_clean_inputs_is_healthy(tmp_path: Path) -> None:
    universe = _write_universe(
        tmp_path,
        ["AAPL,Apple,soft,0000320193,9,2026-08-26,,,active,,,0,,,0,,yes,"],
    )
    snapshot = _write_snapshot(
        tmp_path, [_snapshot_dict_row("AAPL", "soft", "2026-09-01")]
    )

    report = run_doctor(universe, snapshot, as_of_date=date(2026, 9, 3))

    assert report.is_healthy
    assert report.checks_run >= 4


def test_run_doctor_flags_sector_mismatch_and_stale_price(tmp_path: Path) -> None:
    universe = _write_universe(
        tmp_path,
        ["AAPL,Apple,soft,0000320193,9,2026-08-26,,,active,,,0,,,0,,yes,"],
    )
    snapshot = _write_snapshot(
        tmp_path, [_snapshot_dict_row("AAPL", "heal", "2026-08-01")]
    )

    report = run_doctor(universe, snapshot, as_of_date=date(2026, 9, 3), max_price_age_days=14)

    assert not report.is_healthy
    assert any("sector mismatch" in issue for issue in report.issues)
    assert any("days old" in issue for issue in report.issues)


def test_run_doctor_missing_universe_file_reports_issue(tmp_path: Path) -> None:
    snapshot = _write_snapshot(tmp_path, [_snapshot_dict_row("AAPL", "soft", "2026-09-01")])

    report = run_doctor(tmp_path / "nope.csv", snapshot)

    assert not report.is_healthy
    assert any("universe.csv failed to load" in issue for issue in report.issues)


def test_run_doctor_includes_filing_alerts_log_validation(tmp_path: Path) -> None:
    universe = _write_universe(
        tmp_path,
        ["AAPL,Apple,soft,0000320193,9,2026-08-26,,,active,,,0,,,0,,yes,"],
    )
    snapshot = _write_snapshot(
        tmp_path, [_snapshot_dict_row("AAPL", "soft", "2026-09-01")]
    )
    bad_log = tmp_path / "filing_alerts.csv"
    bad_log.write_text("ticker,filed_date\nAAPL,2026-08-30\n", encoding="utf-8")

    report = run_doctor(universe, snapshot, filing_alerts_csv=bad_log, as_of_date=date(2026, 9, 3))

    assert not report.is_healthy
    assert any("missing required column" in issue for issue in report.issues)
