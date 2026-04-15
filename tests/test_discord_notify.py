import json
import urllib.error
from pathlib import Path

import pytest

from multica_quant_ops.discord_notify import (
    DiscordConfig,
    DiscordDeliveryError,
    build_discord_message,
    build_discord_network_error_message,
    main,
    normalize_discord_webhook_url,
    parse_discord_error_body,
    send_discord_message,
)


def build_sample_payload() -> dict[str, object]:
    return {
        "generated_at": "2026-04-13T17:37:39",
        "overview": {
            "total_tickers": 3,
            "ready_tickers": 0,
            "blocked_tickers": 3,
            "alpha_vantage_used_calls": 21,
            "alpha_vantage_daily_limit": 25,
            "alpha_vantage_remaining_calls": 4,
        },
        "dashboard": [
            {
                "symbol": "AAPL",
                "signal_direction": "long",
                "paper_execution_ready": False,
                "blocked_stage": "backtest",
                "remaining_calls": 10,
                "latest_audit_actor": "BacktestAgent",
                "latest_audit_task": "Backtest strategy for AAPL",
                "latest_audit_status": "blocked",
            },
            {
                "symbol": "MSFT",
                "signal_direction": "flat",
                "paper_execution_ready": False,
                "blocked_stage": "backtest",
                "remaining_calls": 7,
            },
        ],
        "incidents": [
            {
                "headline": "Incident detected for AAPL: backtest.",
            }
        ],
    }


def test_build_discord_message_contains_key_sections() -> None:
    message = build_discord_message(build_sample_payload())

    assert "[Quant Ops 알림]" in message
    assert "상태: 주의" in message
    assert "AAPL: 시그널 long" in message
    assert "최근 인시던트" in message
    assert "paper-trading 운영 상태 요약" in message


def test_parse_discord_error_body_returns_message() -> None:
    body = json.dumps({"message": "Unknown Webhook"})
    assert parse_discord_error_body(body) == "Unknown Webhook"


def test_normalize_discord_webhook_url_rewrites_legacy_domain() -> None:
    url = "https://discordapp.com/api/webhooks/1/token"
    assert normalize_discord_webhook_url(url) == "https://discord.com/api/webhooks/1/token"


def test_build_discord_network_error_message_for_connection_refused() -> None:
    error = urllib.error.URLError(ConnectionRefusedError(10061, "connection refused"))
    message = build_discord_network_error_message(error)
    assert "connection was refused" in message
    assert "discord.com" in message


def test_send_discord_message_reports_invalid_webhook(monkeypatch) -> None:
    class FakeHttpError(urllib.error.HTTPError):
        def __init__(self) -> None:
            super().__init__(
                url="https://discord.com/api/webhooks/1/abc",
                code=404,
                msg="Not Found",
                hdrs=None,
                fp=None,
            )

        def read(self) -> bytes:
            return json.dumps({"message": "Unknown Webhook"}).encode("utf-8")

    def fake_urlopen(*args: object, **kwargs: object) -> object:
        raise FakeHttpError()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(DiscordDeliveryError, match="DISCORD_WEBHOOK_URL"):
        send_discord_message(DiscordConfig(webhook_url="https://discord.invalid"), "hello")


def test_main_prints_message_in_dry_run(monkeypatch) -> None:
    export_path = Path("test-artifacts") / "discord-dashboard-export.json"
    export_path.write_text(json.dumps(build_sample_payload(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "discord_notify",
            "--dashboard-export",
            str(export_path),
            "--dry-run",
        ],
    )

    assert main() == 0


def test_main_exits_with_operator_friendly_message_on_delivery_error(
    monkeypatch,
) -> None:
    export_path = Path("test-artifacts") / "discord-dashboard-export-delivery-error.json"
    export_path.write_text(json.dumps(build_sample_payload(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["discord_notify", "--dashboard-export", str(export_path)])
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.invalid")

    def fake_send(*args: object, **kwargs: object) -> None:
        raise DiscordDeliveryError("Discord webhook connection was refused.")

    monkeypatch.setattr("multica_quant_ops.discord_notify.send_discord_message", fake_send)

    with pytest.raises(SystemExit, match="Discord webhook connection was refused."):
        main()
