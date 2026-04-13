from multica_quant_ops.api.service import WorkflowAPI
from multica_quant_ops.cli import build_default_workflow


def build_sample_payload(now: str = "2026-04-13T09:35:00") -> dict[str, object]:
    return {
        "symbol": "AAPL",
        "now": now,
        "snapshot": {
            "symbol": "AAPL",
            "as_of": "2026-04-13T09:34:00",
            "open_price": 200.0,
            "high_price": 202.0,
            "low_price": 199.0,
            "close_price": 201.0,
            "volume": 1000,
        },
        "quality_check": {
            "max_age_minutes": 5,
        },
        "signal_prices": [100.0, 101.0, 103.0],
        "backtest_prices": [100.0, 101.0, 103.0, 104.0, 106.0],
        "backtest_criteria": {
            "min_total_return": 0.01,
            "min_win_rate": 0.5,
        },
        "quantity": 2,
    }


def test_healthcheck_returns_ok_payload() -> None:
    api = WorkflowAPI(build_default_workflow())

    status_code, payload = api.healthcheck()

    assert status_code == 200
    assert payload == {"status": "ok", "service": "multica-quant-ops"}


def test_run_daily_workflow_returns_structured_payload() -> None:
    api = WorkflowAPI(build_default_workflow())

    status_code, payload = api.run_daily_workflow(build_sample_payload())

    assert status_code == 200
    assert payload["result"]["blocked_stage"] is None
    assert payload["incident_summary"]["is_incident"] is False
    assert payload["result"]["paper_order"]["side"] == "buy"
    assert len(payload["tasks"]) == 4
    assert payload["audit_log"][0]["actor"] == "DataAgent"


def test_run_daily_workflow_returns_paper_execution_block() -> None:
    api = WorkflowAPI(build_default_workflow())

    status_code, payload = api.run_daily_workflow(
        build_sample_payload(now="2026-04-13T07:00:00")
    )

    assert status_code == 200
    assert payload["result"]["blocked_stage"] == "paper_execution"
    assert payload["incident_summary"]["stage"] == "paper_execution"
    assert payload["result"]["paper_execution_reason"] == (
        "Paper execution is blocked outside the regular US market session."
    )


def test_run_daily_workflow_rejects_invalid_payload() -> None:
    api = WorkflowAPI(build_default_workflow())

    status_code, payload = api.run_daily_workflow({"symbol": "AAPL"})

    assert status_code == 400
    assert "Invalid request payload" in payload["error"]
