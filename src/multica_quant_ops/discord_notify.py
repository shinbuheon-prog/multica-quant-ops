import argparse
import json
import os
from urllib.parse import urlsplit, urlunsplit
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from multica_quant_ops.telegram_notify import (
    classify_overall_status,
    has_alert_condition,
    load_dashboard_export,
)


@dataclass(frozen=True)
class DiscordConfig:
    webhook_url: str


@dataclass(frozen=True)
class DiscordOptions:
    dry_run: bool = False
    alert_only: bool = False
    low_calls_threshold: int = 5


class DiscordDeliveryError(RuntimeError):
    """Raised when Discord delivery fails with an operator-facing message."""


def normalize_discord_webhook_url(webhook_url: str) -> str:
    parts = urlsplit(webhook_url.strip())
    if parts.netloc == "discordapp.com":
        return urlunsplit((parts.scheme, "discord.com", parts.path, parts.query, parts.fragment))
    return webhook_url.strip()


def build_discord_message(payload: dict[str, Any], low_calls_threshold: int = 5) -> str:
    overview = payload.get("overview", {})
    dashboard_rows = payload.get("dashboard", [])
    incidents = payload.get("incidents", [])
    lines = [
        "[Quant Ops 알림]",
        f"상태: {classify_overall_status(payload)}",
        f"생성 시각: {payload.get('generated_at', '')}",
        f"표시 종목 수: {len(dashboard_rows)}",
        f"준비 완료 종목 수: {overview.get('ready_tickers', 0)}",
        f"차단 종목 수: {overview.get('blocked_tickers', 0)}",
        (
            "Alpha Vantage 사용량: "
            f"{overview.get('alpha_vantage_used_calls', '')}/"
            f"{overview.get('alpha_vantage_daily_limit', '')}"
        ),
        f"남은 호출 수: {overview.get('alpha_vantage_remaining_calls', '')}",
    ]
    remaining_calls = overview.get("alpha_vantage_remaining_calls")
    if isinstance(remaining_calls, int) and remaining_calls <= low_calls_threshold:
        lines.append(
            f"호출 경고: 남은 호출 수가 임계값 {low_calls_threshold} 이하입니다."
        )

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
        lines.extend(["", "최근 인시던트", f"- {top_incident.get('headline', '')}"])

    lines.extend(
        [
            "",
            "참고",
            "- 이 알림은 실거래 지시가 아니라 paper-trading 운영 상태 요약입니다.",
        ]
    )
    return "\n".join(lines)


def parse_discord_error_body(body: str) -> str | None:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body or None
    message = payload.get("message")
    if isinstance(message, str) and message:
        return message
    return body or None


def build_discord_network_error_message(error: urllib.error.URLError) -> str:
    reason = error.reason
    if isinstance(reason, OSError):
        if reason.errno == 10061:
            return (
                "Discord webhook connection was refused. Check outbound network access, "
                "firewall, proxy, or security software for discord.com."
            )
        if reason.errno == 11001:
            return (
                "Discord host could not be resolved. Check DNS or proxy settings for discord.com."
            )
    return f"Discord delivery failed due to a network error: {reason}"


def send_discord_message(config: DiscordConfig, message: str) -> None:
    webhook_url = normalize_discord_webhook_url(config.webhook_url)
    payload = json.dumps({"content": message}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = response.getcode()
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        detail = parse_discord_error_body(body) or "Unknown Discord API error."
        if error.code in {401, 403, 404}:
            raise DiscordDeliveryError(
                f"Discord webhook URL was rejected. Check DISCORD_WEBHOOK_URL. Detail: {detail}"
            ) from error
        if error.code == 400:
            raise DiscordDeliveryError(
                f"Discord rejected the payload. Detail: {detail}"
            ) from error
        raise DiscordDeliveryError(
            f"Discord API returned HTTP {error.code}. Detail: {detail}"
        ) from error
    except urllib.error.URLError as error:
        raise DiscordDeliveryError(build_discord_network_error_message(error)) from error
    except TimeoutError as error:
        raise DiscordDeliveryError(
            "Discord delivery timed out. Check network connectivity to discord.com."
        ) from error

    if status not in {200, 204}:
        detail = parse_discord_error_body(body) or body or f"HTTP {status}"
        raise DiscordDeliveryError(f"Discord send failed. Detail: {detail}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a Discord summary from the dashboard export payload."
    )
    parser.add_argument(
        "--dashboard-export",
        required=True,
        help="Path to dashboard-export.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the message instead of sending it to Discord.",
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
    options = DiscordOptions(
        dry_run=args.dry_run,
        alert_only=args.alert_only,
        low_calls_threshold=args.low_calls_threshold,
    )

    if options.alert_only and not has_alert_condition(payload, options.low_calls_threshold):
        print("No alert condition detected. Discord notification skipped.")
        return 0

    message = build_discord_message(payload, low_calls_threshold=options.low_calls_threshold)

    if options.dry_run:
        print(message)
        return 0

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise SystemExit("DISCORD_WEBHOOK_URL is required.")

    try:
        send_discord_message(DiscordConfig(webhook_url=webhook_url), message)
    except DiscordDeliveryError as error:
        raise SystemExit(str(error)) from error
    print("Discord notification sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
