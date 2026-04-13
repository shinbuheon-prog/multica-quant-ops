from datetime import date

from multica_quant_ops.data.providers.base import MarketQuote
from multica_quant_ops.same_day import (
    build_paper_trading_prep_brief,
    build_same_day_request,
    serialize_brief,
    serialize_request,
)


class FakeMarketDataProvider:
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
