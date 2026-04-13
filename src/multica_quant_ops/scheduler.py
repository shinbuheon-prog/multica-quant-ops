import argparse
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, time as time_of_day, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from multica_quant_ops.api.service import build_request_from_payload, build_workflow_payload
from multica_quant_ops.cli import build_default_workflow
from multica_quant_ops.dashboard_export import build_dashboard_export
from multica_quant_ops.orchestrator.daily_workflow import DailyWorkflowRequest
from multica_quant_ops.reporting.daily_report import build_daily_report
from multica_quant_ops.telegram_notify import (
    TelegramConfig,
    build_telegram_message,
    has_alert_condition,
    send_telegram_message,
)


@dataclass(frozen=True)
class ScheduleConfig:
    run_time: time_of_day
    timezone: str = "America/New_York"


@dataclass(frozen=True)
class PostRunConfig:
    ops_dir: Path | None = None
    dashboard_output: Path | None = None
    telegram_enabled: bool = False
    telegram_alert_only: bool = False
    telegram_low_calls_threshold: int = 5


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
    post_run: PostRunConfig | None = None,
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
    if post_run is not None:
        run_post_run_actions(post_run)
    return target


def run_post_run_actions(config: PostRunConfig) -> None:
    if config.ops_dir is None or config.dashboard_output is None:
        return

    config.dashboard_output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_dashboard_export(config.ops_dir)
    config.dashboard_output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if not config.telegram_enabled:
        return

    if config.telegram_alert_only and not has_alert_condition(
        payload, config.telegram_low_calls_threshold
    ):
        return

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required when telegram notifications are enabled."
        )

    message = build_telegram_message(
        payload,
        low_calls_threshold=config.telegram_low_calls_threshold,
    )
    send_telegram_message(TelegramConfig(bot_token=bot_token, chat_id=chat_id), message)


def run_forever(
    input_path: str,
    output_dir: str,
    config: ScheduleConfig,
    json_output: bool = False,
    post_run: PostRunConfig | None = None,
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
            post_run=post_run,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or schedule the Multica Quant Ops daily workflow.")
    parser.add_argument("--input", required=True, help="Path to a JSON workflow request.")
    parser.add_argument("--output-dir", default="reports", help="Directory to save scheduled reports.")
    parser.add_argument("--time", default="09:30", help="Daily run time in HH:MM format.")
    parser.add_argument("--timezone", default="America/New_York", help="IANA timezone for scheduling.")
    parser.add_argument("--json", action="store_true", help="Write JSON reports instead of text reports.")
    parser.add_argument(
        "--ops-dir",
        default=None,
        help="Ops directory used to build dashboard exports after each run.",
    )
    parser.add_argument(
        "--dashboard-output",
        default=None,
        help="Path to write dashboard-export.json after each run.",
    )
    parser.add_argument(
        "--telegram-notify",
        action="store_true",
        help="Send Telegram notification after each run. Requires dashboard export configuration.",
    )
    parser.add_argument(
        "--telegram-alert-only",
        action="store_true",
        help="Only send Telegram notification when blocked tickers exist or remaining calls are low.",
    )
    parser.add_argument(
        "--telegram-low-calls-threshold",
        type=int,
        default=5,
        help="Threshold for low Alpha Vantage remaining-call alerts.",
    )
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
    post_run = None
    if args.ops_dir is not None or args.dashboard_output is not None or args.telegram_notify:
        if args.ops_dir is None or args.dashboard_output is None:
            raise SystemExit(
                "--ops-dir and --dashboard-output are required when post-run dashboard export or Telegram notification is enabled."
            )
        post_run = PostRunConfig(
            ops_dir=Path(args.ops_dir),
            dashboard_output=Path(args.dashboard_output),
            telegram_enabled=args.telegram_notify,
            telegram_alert_only=args.telegram_alert_only,
            telegram_low_calls_threshold=args.telegram_low_calls_threshold,
        )

    if args.once:
        target = run_once(
            input_path=args.input,
            output_dir=args.output_dir,
            json_output=args.json,
            post_run=post_run,
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
        post_run=post_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
