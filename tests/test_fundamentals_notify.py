import json
from pathlib import Path

import pytest

from multica_quant_ops.fundamentals.notify import run


def _write_alerts(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "filing_alert_latest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_run_no_alerts_skips_send(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _write_alerts(tmp_path, {})

    exit_code = run(path, channels=["discord", "telegram"], dry_run=False, env={})

    assert exit_code == 0
    assert "skipped" in capsys.readouterr().out.lower()


def test_run_dry_run_prints_message_without_sending(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write_alerts(
        tmp_path, {"AAPL": {"filed_date": "2026-08-30", "form": "8-K", "reason": "", "detected_on": ""}}
    )

    exit_code = run(path, channels=["discord"], dry_run=True, env={})

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "AAPL" in out


def test_run_missing_credentials_skips_channel_gracefully(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write_alerts(
        tmp_path, {"AAPL": {"filed_date": "2026-08-30", "form": "8-K", "reason": "", "detected_on": ""}}
    )

    exit_code = run(path, channels=["discord", "telegram"], dry_run=False, env={})

    out = capsys.readouterr().out
    assert "DISCORD_WEBHOOK_URL not set" in out
    assert "TELEGRAM_BOT_TOKEN" in out
    assert exit_code == 1


def test_run_sends_via_configured_discord_webhook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write_alerts(
        tmp_path, {"AAPL": {"filed_date": "2026-08-30", "form": "8-K", "reason": "", "detected_on": ""}}
    )
    sent = {}

    def _fake_send(config, message):  # type: ignore[no-untyped-def]
        sent["webhook_url"] = config.webhook_url
        sent["message"] = message

    monkeypatch.setattr("multica_quant_ops.fundamentals.notify.send_discord_message", _fake_send)

    exit_code = run(
        path, channels=["discord"], dry_run=False, env={"DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/x"}
    )

    assert exit_code == 0
    assert sent["webhook_url"] == "https://discord.com/api/webhooks/x"
    assert "AAPL" in sent["message"]
    assert "sent" in capsys.readouterr().out.lower()
