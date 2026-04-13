import json
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from multica_quant_ops.scheduler import (
    ScheduleConfig,
    build_report_filename,
    next_run_at,
    parse_run_time,
    run_once,
)


def test_parse_run_time_accepts_hh_mm() -> None:
    assert parse_run_time("09:30") == time(hour=9, minute=30)


def test_next_run_at_same_day_when_before_target() -> None:
    config = ScheduleConfig(run_time=time(hour=9, minute=30))
    now = datetime(2026, 4, 13, 9, 0, tzinfo=ZoneInfo("America/New_York"))

    target = next_run_at(now, config)

    assert target == datetime(2026, 4, 13, 9, 30, tzinfo=ZoneInfo("America/New_York"))


def test_next_run_at_next_day_when_after_target() -> None:
    config = ScheduleConfig(run_time=time(hour=9, minute=30))
    now = datetime(2026, 4, 13, 10, 0, tzinfo=ZoneInfo("America/New_York"))

    target = next_run_at(now, config)

    assert target == datetime(2026, 4, 14, 9, 30, tzinfo=ZoneInfo("America/New_York"))


def test_build_report_filename_contains_timestamp() -> None:
    when = datetime(2026, 4, 13, 9, 35, 0)

    assert build_report_filename("daily-workflow", when, "txt") == "daily-workflow-20260413-093500.txt"


def test_run_once_writes_text_report() -> None:
    runtime_dir = Path("test-artifacts") / "scheduler-text"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    input_path = runtime_dir / "request.json"
    input_path.write_text(
        Path("examples/sample_request.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    target = run_once(
        input_path=str(input_path),
        output_dir=str(runtime_dir),
        now=datetime(2026, 4, 13, 9, 35, 0),
    )

    assert target.name == "daily-workflow-20260413-093500.txt"
    assert "Daily Workflow Report: AAPL" in target.read_text(encoding="utf-8")


def test_run_once_writes_json_report() -> None:
    runtime_dir = Path("test-artifacts") / "scheduler-json"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    input_path = runtime_dir / "request.json"
    input_path.write_text(
        Path("examples/sample_request.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    target = run_once(
        input_path=str(input_path),
        output_dir=str(runtime_dir),
        json_output=True,
        now=datetime(2026, 4, 13, 9, 35, 0),
    )
    payload = json.loads(target.read_text(encoding="utf-8"))

    assert target.name == "daily-workflow-20260413-093500.json"
    assert payload["result"]["blocked_stage"] is None
    assert payload["result"]["paper_order"]["side"] == "buy"
