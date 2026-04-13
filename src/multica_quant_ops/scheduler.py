import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime, time as time_of_day, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from multica_quant_ops.api.service import build_request_from_payload, build_workflow_payload
from multica_quant_ops.cli import build_default_workflow
from multica_quant_ops.orchestrator.daily_workflow import DailyWorkflowRequest
from multica_quant_ops.reporting.daily_report import build_daily_report


@dataclass(frozen=True)
class ScheduleConfig:
    run_time: time_of_day
    timezone: str = "America/New_York"


def next_run_at(now: datetime, config: ScheduleConfig) -> datetime:
    run_zone = ZoneInfo(config.timezone)
    zoned_now = now.astimezone(run_zone) if now.tzinfo is not None else now.replace(tzinfo=run_zone)
    candidate = datetime.combine(
        zoned_now.date(),
        config.run_time,
        tzinfo=run_zone,
    )
    if candidate <= zoned_now:
        candidate += timedelta(days=1)
    return candidate


def load_request_from_file(input_path: str) -> DailyWorkflowRequest:
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    return build_request_from_payload(payload)


def build_report_filename(prefix: str, when: datetime, extension: str) -> str:
    return f"{prefix}-{when.strftime('%Y%m%d-%H%M%S')}.{extension}"


def run_once(
    input_path: str,
    output_dir: str,
    json_output: bool = False,
    now: datetime | None = None,
) -> Path:
    workflow = build_default_workflow()
    request = load_request_from_file(input_path)
    result = workflow.run(request)

    report_time = now or datetime.now()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if json_output:
        report = json.dumps(
            build_workflow_payload(request, result, workflow.data_agent.board),
            indent=2,
        )
        target = output_path / build_report_filename("daily-workflow", report_time, "json")
    else:
        report = build_daily_report(request, result)
        target = output_path / build_report_filename("daily-workflow", report_time, "txt")

    target.write_text(report + "\n", encoding="utf-8")
    return target


def run_forever(
    input_path: str,
    output_dir: str,
    config: ScheduleConfig,
    json_output: bool = False,
) -> None:
    while True:
        now = datetime.now(ZoneInfo(config.timezone))
        target_time = next_run_at(now, config)
        sleep_seconds = max(0.0, (target_time - now).total_seconds())
        time.sleep(sleep_seconds)
        run_once(
            input_path=input_path,
            output_dir=output_dir,
            json_output=json_output,
            now=target_time,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or schedule the Multica Quant Ops daily workflow.")
    parser.add_argument("--input", required=True, help="Path to a JSON workflow request.")
    parser.add_argument("--output-dir", default="reports", help="Directory to save scheduled reports.")
    parser.add_argument("--time", default="09:30", help="Daily run time in HH:MM format.")
    parser.add_argument("--timezone", default="America/New_York", help="IANA timezone for scheduling.")
    parser.add_argument("--json", action="store_true", help="Write JSON reports instead of text reports.")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run the workflow once immediately instead of starting the scheduling loop.",
    )
    return parser.parse_args()


def parse_run_time(value: str) -> time_of_day:
    return time_of_day.fromisoformat(value)


def main() -> int:
    args = parse_args()
    if args.once:
        target = run_once(
            input_path=args.input,
            output_dir=args.output_dir,
            json_output=args.json,
        )
        print(f"Scheduled report written to {target}")
        return 0

    run_forever(
        input_path=args.input,
        output_dir=args.output_dir,
        config=ScheduleConfig(
            run_time=parse_run_time(args.time),
            timezone=args.timezone,
        ),
        json_output=args.json,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
