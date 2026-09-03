import json
from datetime import date
from pathlib import Path

import pytest

from multica_quant_ops.fundamentals.filing_alert import (
    FilingAlertFormatError,
    build_filing_alert_message,
    load_filing_alerts,
    validate_filing_alerts_log,
)


def test_load_filing_alerts_missing_file_returns_empty_dict(tmp_path: Path) -> None:
    assert load_filing_alerts(tmp_path / "nope.json") == {}


def test_load_filing_alerts_parses_entries(tmp_path: Path) -> None:
    path = tmp_path / "filing_alert_latest.json"
    path.write_text(
        json.dumps(
            {
                "AAPL": {
                    "filed_date": "2026-08-30",
                    "form": "8-K",
                    "reason": "실적 발표",
                    "detected_on": "2026-08-31",
                }
            }
        ),
        encoding="utf-8",
    )

    alerts = load_filing_alerts(path)

    assert set(alerts) == {"AAPL"}
    assert alerts["AAPL"].filed_date == date(2026, 8, 30)
    assert alerts["AAPL"].form == "8-K"


def test_load_filing_alerts_empty_object_is_fine(tmp_path: Path) -> None:
    path = tmp_path / "filing_alert_latest.json"
    path.write_text("{}", encoding="utf-8")

    assert load_filing_alerts(path) == {}


def test_load_filing_alerts_invalid_json_raises(tmp_path: Path) -> None:
    path = tmp_path / "filing_alert_latest.json"
    path.write_text("not json", encoding="utf-8")

    with pytest.raises(FilingAlertFormatError):
        load_filing_alerts(path)


def test_load_filing_alerts_missing_filed_date_raises(tmp_path: Path) -> None:
    path = tmp_path / "filing_alert_latest.json"
    path.write_text(json.dumps({"AAPL": {"form": "8-K"}}), encoding="utf-8")

    with pytest.raises(FilingAlertFormatError):
        load_filing_alerts(path)


def test_build_filing_alert_message_empty_returns_none() -> None:
    assert build_filing_alert_message({}) is None


def test_build_filing_alert_message_lists_tickers_sorted(tmp_path: Path) -> None:
    path = tmp_path / "filing_alert_latest.json"
    path.write_text(
        json.dumps(
            {
                "MSFT": {"filed_date": "2026-08-29", "form": "10-Q", "reason": "", "detected_on": ""},
                "AAPL": {
                    "filed_date": "2026-08-30",
                    "form": "8-K",
                    "reason": "실적 발표",
                    "detected_on": "2026-08-31",
                },
            }
        ),
        encoding="utf-8",
    )
    alerts = load_filing_alerts(path)

    message = build_filing_alert_message(alerts)

    assert message is not None
    assert "AAPL" in message
    assert "MSFT" in message
    assert message.index("AAPL") < message.index("MSFT")
    assert "2개" in message


def test_validate_filing_alerts_log_missing_file_is_clean(tmp_path: Path) -> None:
    assert validate_filing_alerts_log(tmp_path / "nope.csv") == []


def test_validate_filing_alerts_log_missing_column_is_flagged(tmp_path: Path) -> None:
    path = tmp_path / "filing_alerts.csv"
    path.write_text("ticker,filed_date\nAAPL,2026-08-30\n", encoding="utf-8")

    issues = validate_filing_alerts_log(path)

    assert any("missing required column" in issue for issue in issues)


def test_validate_filing_alerts_log_bad_date_is_flagged(tmp_path: Path) -> None:
    path = tmp_path / "filing_alerts.csv"
    path.write_text(
        "ticker,filed_date,form,accession,detected_on,reason\n"
        "AAPL,not-a-date,8-K,0000320193-26-000001,2026-08-31,실적 발표\n",
        encoding="utf-8",
    )

    issues = validate_filing_alerts_log(path)

    assert any("unparseable filed_date" in issue for issue in issues)


def test_validate_filing_alerts_log_clean_log_has_no_issues(tmp_path: Path) -> None:
    path = tmp_path / "filing_alerts.csv"
    path.write_text(
        "ticker,filed_date,form,accession,detected_on,reason\n"
        "AAPL,2026-08-30,8-K,0000320193-26-000001,2026-08-31,실적 발표\n",
        encoding="utf-8",
    )

    assert validate_filing_alerts_log(path) == []
