import argparse
import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    chat_id: str


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


def build_telegram_message(payload: dict[str, Any]) -> str:
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
        "",
        "종목별 상태",
    ]

    for item in dashboard_rows[:5]:
        blocked_stage = item.get("blocked_stage") or "없음"
        readiness = "가능" if item.get("paper_execution_ready") else "보류"
        lines.append(
            f"- {item.get('symbol', '')}: 시그널 {item.get('signal_direction', '')}, "
            f"실행 {readiness}, 차단 {blocked_stage}, 남은 호출 {item.get('remaining_calls', '')}"
        )

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


def send_telegram_message(config: TelegramConfig, message: str) -> None:
    payload = urllib.parse.urlencode(
        {
            "chat_id": config.chat_id,
            "text": message,
        }
    ).encode("utf-8")
    url = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
    request = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8")
    response_payload = json.loads(body)
    if not response_payload.get("ok"):
        raise RuntimeError(f"Telegram send failed: {response_payload}")


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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = load_dashboard_export(Path(args.dashboard_export))
    message = build_telegram_message(payload)

    if args.dry_run:
        print(message)
        return 0

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        raise SystemExit("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required.")

    send_telegram_message(TelegramConfig(bot_token=bot_token, chat_id=chat_id), message)
    print("Telegram notification sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
