import json
import shutil
from pathlib import Path

from multica_quant_ops.dashboard_export import build_dashboard_export, main


def _write_brief(
    path: Path,
    *,
    symbol: str,
    current_price: float,
    signal_direction: str,
    ready: bool,
    blocked_stage: str | None,
    remaining_calls: int,
) -> None:
    payload = {
        "brief": {
            "symbol": symbol,
            "current_price": current_price,
            "previous_close": current_price - 1,
            "change_percent": 0.01,
            "session_high": current_price + 1,
            "session_low": current_price - 2,
            "signal_direction": signal_direction,
            "signal_confidence": 0.1234,
            "paper_execution_ready": ready,
            "blocked_stage": blocked_stage,
            "incident_headline": f"Incident detected for {symbol}: {blocked_stage}.",
            "alpha_vantage_used_calls": 15,
            "alpha_vantage_daily_limit": 25,
            "alpha_vantage_remaining_calls": remaining_calls,
            "note": "paper only",
        },
        "workflow": {
            "request": {
                "now": "2026-04-13T09:35:00-04:00",
                "snapshot": {"as_of": "2026-04-13T09:34:00-04:00"},
            },
            "incident_summary": {
                "recommended_actions": ["Review thresholds."],
                "details": ["Blocked at backtest."],
            },
            "audit_log": [
                {
                    "actor": "BacktestAgent",
                    "task_title": f"Backtest strategy for {symbol}",
                    "to_status": "blocked",
                    "reason": "Backtest failed promotion criteria.",
                }
            ],
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _prepare_clean_dir(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_build_dashboard_export_collects_latest_rows() -> None:
    root_dir = _prepare_clean_dir(Path("test-artifacts") / "dashboard-export")
    ops_dir = root_dir / "ops"
    runtime_dir = ops_dir / "runtime"
    reports_dir = ops_dir / "reports"
    incidents_dir = ops_dir / "incidents"
    batch_dir = runtime_dir / "batch-20260413-172753"
    batch_dir.mkdir(parents=True)
    reports_dir.mkdir(parents=True)
    incidents_dir.mkdir(parents=True)

    _write_brief(
        batch_dir / "AAPL-brief.json",
        symbol="AAPL",
        current_price=260.48,
        signal_direction="long",
        ready=False,
        blocked_stage="backtest",
        remaining_calls=10,
    )
    (batch_dir / "AAPL-request.json").write_text("{}", encoding="utf-8")
    (batch_dir / "AAPL-operator-report-ko.txt").write_text(
        "[당일 준비 리포트] AAPL\n관찰 포인트\n", encoding="utf-8"
    )
    _write_brief(
        batch_dir / "MSFT-brief.json",
        symbol="MSFT",
        current_price=370.87,
        signal_direction="flat",
        ready=False,
        blocked_stage="backtest",
        remaining_calls=7,
    )
    (batch_dir / "MSFT-request.json").write_text("{}", encoding="utf-8")
    (batch_dir / "MSFT-operator-report-ko.txt").write_text(
        "[당일 준비 리포트] MSFT\n관찰 포인트\n", encoding="utf-8"
    )
    (batch_dir / "batch-summary.json").write_text('{"tickers": []}', encoding="utf-8")
    (batch_dir / "batch-summary-ko.txt").write_text(
        "[멀티 티커 운영 요약]\n- 준비 완료 종목: 0 / 2\n",
        encoding="utf-8",
    )

    _write_brief(
        runtime_dir / "TSLA-brief-20260413-180000.json",
        symbol="TSLA",
        current_price=348.95,
        signal_direction="flat",
        ready=False,
        blocked_stage="backtest",
        remaining_calls=4,
    )
    (runtime_dir / "TSLA-request-20260413-180000.json").write_text("{}", encoding="utf-8")
    (runtime_dir / "TSLA-operator-report-ko-20260413-180000.txt").write_text(
        "[당일 준비 리포트] TSLA\n관찰 포인트\n", encoding="utf-8"
    )
    (runtime_dir / "alpha-vantage-usage.json").write_text('{"2026-04-13": 21}', encoding="utf-8")
    (reports_dir / "daily-report-20260413-154714.txt").write_text(
        "Daily Workflow Report: AAPL\nBlocked stage: none\n", encoding="utf-8"
    )
    (incidents_dir / "incident-summary-20260413-154714.txt").write_text(
        "Incident detected for AAPL: backtest.\nWorkflow blocked at stage: backtest.\n",
        encoding="utf-8",
    )

    payload = build_dashboard_export(ops_dir)

    assert payload["overview"]["total_tickers"] == 3
    assert payload["overview"]["blocked_tickers"] == 3
    assert payload["overview"]["alpha_vantage_used_calls"] == 21
    assert payload["overview"]["alpha_vantage_remaining_calls"] == 4
    assert payload["dashboard"][0]["symbol"] == "AAPL"
    assert payload["dashboard"][0]["latest_audit_actor"] == "BacktestAgent"
    assert payload["dashboard"][2]["symbol"] == "TSLA"
    assert payload["batch_runs"][0]["batch_name"] == "batch-20260413-172753"
    assert payload["incidents"][0]["headline"] == "Incident detected for AAPL: backtest."


def test_main_writes_dashboard_export_file(monkeypatch) -> None:
    root_dir = _prepare_clean_dir(Path("test-artifacts") / "dashboard-export-main")
    ops_dir = root_dir / "ops"
    (ops_dir / "runtime").mkdir(parents=True)
    (ops_dir / "reports").mkdir(parents=True)
    (ops_dir / "incidents").mkdir(parents=True)
    output_path = root_dir / "dashboard" / "dashboard-export.json"

    monkeypatch.setattr(
        "sys.argv",
        [
            "dashboard_export",
            "--ops-dir",
            str(ops_dir),
            "--output",
            str(output_path),
        ],
    )

    assert main() == 0
    assert output_path.exists()
