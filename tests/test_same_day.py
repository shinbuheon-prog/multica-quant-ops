from datetime import date
from pathlib import Path

from multica_quant_ops.data.providers.base import MarketQuote
from multica_quant_ops.data.providers.usage import (
    DailyCallLimitExceededError,
    FileBackedUsageTracker,
)
from multica_quant_ops.same_day import (
    build_paper_trading_prep_brief,
    build_same_day_request,
    serialize_brief,
    serialize_request,
)
from multica_quant_ops.reporting.korean_operator import render_korean_prep_report


class FakeMarketDataProvider:
    def __init__(self) -> None:
        self.last_usage_snapshot = None

    def fetch_quote(self, symbol: str) -> MarketQuote:
        return MarketQuote(
            symbol=symbol,
            latest_trading_day=date(2026, 4, 13),
            open_price=200.0,
            high_price=202.0,
            low_price=199.0,
            price=201.0,
            previous_close=198.5,
            volume=1000,
            change_percent=0.0126,
        )

    def fetch_daily_closes(self, symbol: str, limit: int) -> list[float]:
        closes = [190.0, 192.0, 194.0, 196.0, 198.0, 200.0, 201.0]
        return closes[-limit:]


def test_build_same_day_request_from_provider() -> None:
    request = build_same_day_request("AAPL", FakeMarketDataProvider(), quantity=2, max_age_minutes=10)

    assert request.symbol == "AAPL"
    assert request.snapshot.close_price == 201.0
    assert request.quantity == 2
    assert len(request.signal_prices) == 5
    assert len(request.backtest_prices) == 7


def test_build_paper_trading_prep_brief_returns_non_action_payload() -> None:
    provider = FakeMarketDataProvider()
    request = build_same_day_request("AAPL", provider, quantity=2)

    brief, workflow_payload = build_paper_trading_prep_brief(request, provider)

    assert brief.paper_execution_ready is True
    assert brief.signal_direction == "long"
    assert "not a live-trading instruction" in brief.note
    assert workflow_payload["result"]["blocked_stage"] is None


def test_same_day_serializers_emit_expected_fields() -> None:
    provider = FakeMarketDataProvider()
    request = build_same_day_request("AAPL", provider, quantity=2)
    brief, _ = build_paper_trading_prep_brief(request, provider)

    request_payload = serialize_request(request)
    brief_payload = serialize_brief(brief)

    assert request_payload["symbol"] == "AAPL"
    assert request_payload["snapshot"]["close_price"] == 201.0
    assert brief_payload["current_price"] == 201.0
    assert brief_payload["paper_execution_ready"] is True


def test_file_backed_usage_tracker_enforces_daily_limit() -> None:
    usage_file = Path("test-artifacts") / "alpha-vantage-usage-test.json"
    if usage_file.exists():
        usage_file.unlink()

    tracker = FileBackedUsageTracker(path=usage_file, daily_limit=2)
    now = build_same_day_request("AAPL", FakeMarketDataProvider()).now

    first = tracker.reserve_call(now)
    second = tracker.reserve_call(now)

    assert first.used_calls == 1
    assert second.used_calls == 2
    assert second.remaining_calls == 0

    try:
        tracker.reserve_call(now)
    except DailyCallLimitExceededError:
        pass
    else:
        raise AssertionError("Expected the daily limit guard to block the third call.")


def test_same_day_brief_serializer_includes_usage_fields() -> None:
    provider = FakeMarketDataProvider()
    request = build_same_day_request("AAPL", provider, quantity=2)
    brief, _ = build_paper_trading_prep_brief(request, provider)

    brief_payload = serialize_brief(brief)

    assert "alpha_vantage_remaining_calls" in brief_payload


def test_korean_operator_report_renders_korean_summary() -> None:
    provider = FakeMarketDataProvider()
    request = build_same_day_request("AAPL", provider, quantity=2)
    brief, _ = build_paper_trading_prep_brief(request, provider)

    report = render_korean_prep_report(brief)

    assert "[당일 준비 리포트] AAPL" in report
    assert "관찰 포인트" in report
    assert "판단 상태" in report
    assert "다음 액션" in report
    assert "실거래 지시가 아니라" in report
