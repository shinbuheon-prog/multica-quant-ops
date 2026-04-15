import argparse
import json
import os
import urllib.parse
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    chat_id: str


@dataclass(frozen=True)
class TelegramOptions:
    dry_run: bool = False
    alert_only: bool = False
    low_calls_threshold: int = 5


class TelegramDeliveryError(RuntimeError):
    """Raised when Telegram delivery fails with an operator-facing message."""


def load_dashboard_export(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def classify_overall_status(payload: dict[str, Any]) -> str:
    overview = payload.get("overview", {})
    blocked_tickers = int(overview.get("blocked_tickers") or 0)
    ready_tickers = int(overview.get("ready_tickers") or 0)
    total_tickers = int(overview.get("total_tickers") or 0)
    if blocked_tickers > 0:
        return "주의"
    if ready_tickers > 0:
        return "준비 가능"
    if total_tickers > 0:
        return "관찰"
    return "데이터 없음"


def has_alert_condition(payload: dict[str, Any], low_calls_threshold: int) -> bool:
    overview = payload.get("overview", {})
    blocked_tickers = int(overview.get("blocked_tickers") or 0)
    remaining_calls = overview.get("alpha_vantage_remaining_calls")
    if blocked_tickers > 0:
        return True
    return isinstance(remaining_calls, int) and remaining_calls <= low_calls_threshold


def build_telegram_message(payload: dict[str, Any], low_calls_threshold: int = 5) -> str:
    overview = payload.get("overview", {})
    dashboard_rows = payload.get("dashboard", [])
    incidents = payload.get("incidents", [])
    lines = [
        "[Quant Ops 알림]",
        f"- 상태: {classify_overall_status(payload)}",
        f"- 생성 시각: {payload.get('generated_at', '')}",
        f"- 표시 종목 수: {len(dashboard_rows)}",
        f"- 준비 완료 종목 수: {overview.get('ready_tickers', 0)}",
        f"- 차단 종목 수: {overview.get('blocked_tickers', 0)}",
        f"- Alpha Vantage 사용량: {overview.get('alpha_vantage_used_calls', '')}/{overview.get('alpha_vantage_daily_limit', '')}",
        f"- 남은 호출 수: {overview.get('alpha_vantage_remaining_calls', '')}",
    ]
    remaining_calls = overview.get("alpha_vantage_remaining_calls")
    if isinstance(remaining_calls, int) and remaining_calls <= low_calls_threshold:
        lines.append(f"- 호출 경고: 남은 호출 수가 임계값 {low_calls_threshold} 이하입니다.")

    lines.extend(["", "종목별 상태"])

    for item in dashboard_rows[:5]:
        blocked_stage = item.get("blocked_stage") or "없음"
        readiness = "가능" if item.get("paper_execution_ready") else "보류"
        row = (
            f"- {item.get('symbol', '')}: 시그널 {item.get('signal_direction', '')}, "
            f"실행 {readiness}, 차단 {blocked_stage}, 남은 호출 {item.get('remaining_calls', '')}"
        )
        if item.get("latest_audit_actor") and item.get("latest_audit_task"):
            row += (
                f", 최근 작업 {item.get('latest_audit_actor')} -> "
                f"{item.get('latest_audit_task')} ({item.get('latest_audit_status')})"
            )
        lines.append(row)

    if incidents:
        top_incident = incidents[0]
        lines.extend(
            [
                "",
                "최근 인시던트",
                f"- {top_incident.get('headline', '')}",
            ]
        )

    lines.extend(
        [
            "",
            "참고",
            "- 이 알림은 실거래 지시가 아니라 paper-trading 운영 상태 요약입니다.",
        ]
    )
    return "\n".join(lines)


def parse_telegram_error_body(body: str) -> str | None:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    description = payload.get("description")
    if isinstance(description, str) and description:
        return description
    return None


def build_network_error_message(error: urllib.error.URLError) -> str:
    reason = error.reason
    if isinstance(reason, OSError):
        if reason.errno == 10061:
            return (
                "Telegram API connection was refused. Check outbound network access, "
                "firewall, proxy, or security software for api.telegram.org."
            )
        if reason.errno == 11001:
            return (
                "Telegram API host could not be resolved. Check DNS or proxy settings "
                "for api.telegram.org."
            )
    return f"Telegram delivery failed due to a network error: {reason}"


def send_telegram_message(config: TelegramConfig, message: str) -> None:
    payload = urllib.parse.urlencode(
        {
            "chat_id": config.chat_id,
            "text": message,
        }
    ).encode("utf-8")
    url = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
    request = urllib.request.Request(url, data=payload, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        description = parse_telegram_error_body(body)
        if error.code == 401:
            raise TelegramDeliveryError(
                "Telegram bot token was rejected. Check TELEGRAM_BOT_TOKEN."
            ) from error
        if error.code == 400:
            detail = description or "Unknown Telegram API error."
            raise TelegramDeliveryError(
                f"Telegram rejected the request. Check TELEGRAM_CHAT_ID and payload. Detail: {detail}"
            ) from error
        detail = description or body or str(error)
        raise TelegramDeliveryError(
            f"Telegram API returned HTTP {error.code}. Detail: {detail}"
        ) from error
    except urllib.error.URLError as error:
        raise TelegramDeliveryError(build_network_error_message(error)) from error
    except TimeoutError as error:
        raise TelegramDeliveryError(
            "Telegram delivery timed out. Check network connectivity to api.telegram.org."
        ) from error

    response_payload = json.loads(body)
    if not response_payload.get("ok"):
        description = response_payload.get("description") or response_payload
        raise TelegramDeliveryError(f"Telegram send failed: {description}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a Telegram summary from the dashboard export payload."
    )
    parser.add_argument(
        "--dashboard-export",
        required=True,
        help="Path to dashboard-export.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the message instead of sending it to Telegram.",
    )
    parser.add_argument(
        "--alert-only",
        action="store_true",
        help="Send only when blocked tickers exist or remaining calls are below threshold.",
    )
    parser.add_argument(
        "--low-calls-threshold",
        type=int,
        default=5,
        help="Alert threshold for remaining Alpha Vantage calls.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = load_dashboard_export(Path(args.dashboard_export))
    options = TelegramOptions(
        dry_run=args.dry_run,
        alert_only=args.alert_only,
        low_calls_threshold=args.low_calls_threshold,
    )

    if options.alert_only and not has_alert_condition(payload, options.low_calls_threshold):
        print("No alert condition detected. Telegram notification skipped.")
        return 0

    message = build_telegram_message(payload, low_calls_threshold=options.low_calls_threshold)

    if options.dry_run:
        print(message)
        return 0

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        raise SystemExit("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required.")

    try:
        send_telegram_message(TelegramConfig(bot_token=bot_token, chat_id=chat_id), message)
    except TelegramDeliveryError as error:
        raise SystemExit(str(error)) from error
    print("Telegram notification sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
