import json
from pathlib import Path

from multica_quant_ops.telegram_notify import build_telegram_message, main


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


def test_build_telegram_message_contains_key_sections() -> None:
    message = build_telegram_message(build_sample_payload())

    assert "[Quant Ops 알림]" in message
    assert "- 상태: 주의" in message
    assert "- AAPL: 시그널 long, 실행 보류, 차단 backtest, 남은 호출 10" in message
    assert "최근 인시던트" in message
    assert "paper-trading 운영 상태 요약" in message


def test_main_prints_message_in_dry_run(monkeypatch) -> None:
    export_path = Path("test-artifacts") / "telegram-dashboard-export.json"
    export_path.write_text(json.dumps(build_sample_payload(), ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "telegram_notify",
            "--dashboard-export",
            str(export_path),
            "--dry-run",
        ],
    )

    assert main() == 0
