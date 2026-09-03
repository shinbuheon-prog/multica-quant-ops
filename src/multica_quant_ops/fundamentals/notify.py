"""CLI: send a fundamentals filing-alert notification to Discord and/or
Telegram, reusing the existing webhook/bot delivery code in
discord_notify.py / telegram_notify.py rather than duplicating HTTP logic.

Usage:
    python -m multica_quant_ops.fundamentals.notify \
        --filing-alert-json pipeline/out/filing_alert_latest.json \
        --channel discord --channel telegram

Sends nothing (exit 0, prints a skip message) when there are no active
alerts -- this is the noise-minimization behavior documented in
docs/FUNDAMENTALS_INTEGRATION.md section 6, mirrored from the existing
--alert-only flag on discord_notify.py / telegram_notify.py.
"""

import argparse
import os
from pathlib import Path

from multica_quant_ops.discord_notify import (
    DiscordConfig,
    DiscordDeliveryError,
    send_discord_message,
)
from multica_quant_ops.fundamentals.filing_alert import (
    build_filing_alert_message,
    load_filing_alerts,
)
from multica_quant_ops.telegram_notify import (
    TelegramConfig,
    TelegramDeliveryError,
    send_telegram_message,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--filing-alert-json",
        type=Path,
        default=Path("pipeline/out/filing_alert_latest.json"),
        help="Path to filing_alert_latest.json (from s9d_filing_alert.py).",
    )
    parser.add_argument(
        "--channel",
        action="append",
        choices=["discord", "telegram"],
        dest="channels",
        help="Channel(s) to notify. Repeatable. Defaults to both.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the message instead of sending it.",
    )
    return parser.parse_args(argv)


def run(
    filing_alert_json: Path,
    channels: list[str],
    dry_run: bool,
    env: dict[str, str] | None = None,
) -> int:
    env = env if env is not None else dict(os.environ)
    alerts = load_filing_alerts(filing_alert_json)
    message = build_filing_alert_message(alerts)

    if message is None:
        print("No active filing alerts. Notification skipped (noise minimization).")
        return 0

    if dry_run:
        print(message)
        return 0

    sent_any = False
    for channel in channels:
        if channel == "discord":
            webhook_url = env.get("DISCORD_WEBHOOK_URL")
            if not webhook_url:
                print("DISCORD_WEBHOOK_URL not set; skipping Discord.")
                continue
            try:
                send_discord_message(DiscordConfig(webhook_url=webhook_url), message)
            except DiscordDeliveryError as error:
                print(f"Discord delivery failed: {error}")
                continue
            print("Discord filing-alert notification sent.")
            sent_any = True
        elif channel == "telegram":
            bot_token = env.get("TELEGRAM_BOT_TOKEN")
            chat_id = env.get("TELEGRAM_CHAT_ID")
            if not bot_token or not chat_id:
                print("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set; skipping Telegram.")
                continue
            try:
                send_telegram_message(TelegramConfig(bot_token=bot_token, chat_id=chat_id), message)
            except TelegramDeliveryError as error:
                print(f"Telegram delivery failed: {error}")
                continue
            print("Telegram filing-alert notification sent.")
            sent_any = True

    return 0 if sent_any or dry_run else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    channels = args.channels or ["discord", "telegram"]
    return run(args.filing_alert_json, channels, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
