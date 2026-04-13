import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from multica_quant_ops.api.service import build_workflow_payload
from multica_quant_ops.cli import build_default_workflow
from multica_quant_ops.data.providers.alphavantage import AlphaVantageMarketDataProvider
from multica_quant_ops.data.providers.base import MarketDataProvider
from multica_quant_ops.orchestrator.daily_workflow import DailyWorkflowRequest
from multica_quant_ops.reporting.incident_summary import build_incident_summary


@dataclass(frozen=True)
class PaperTradingPrepBrief:
    symbol: str
    current_price: float
    previous_close: float
    change_percent: float
    session_high: float
    session_low: float
    signal_direction: str
    signal_confidence: float
    paper_execution_ready: bool
    blocked_stage: str | None
    incident_headline: str
    note: str


def serialize_request(request: DailyWorkflowRequest) -> dict[str, object]:
    return {
        "symbol": request.symbol,
        "now": request.now.isoformat(),
        "snapshot": {
            "symbol": request.snapshot.symbol,
            "as_of": request.snapshot.as_of.isoformat(),
            "open_price": request.snapshot.open_price,
            "high_price": request.snapshot.high_price,
            "low_price": request.snapshot.low_price,
            "close_price": request.snapshot.close_price,
            "volume": request.snapshot.volume,
        },
        "quality_check": {
            "max_age_minutes": int(request.quality_check.max_age.total_seconds() / 60),
            "min_price": request.quality_check.min_price,
            "min_volume": request.quality_check.min_volume,
        },
        "signal_prices": request.signal_prices,
        "backtest_prices": request.backtest_prices,
        "backtest_criteria": {
            "min_total_return": request.backtest_criteria.min_total_return,
            "min_win_rate": request.backtest_criteria.min_win_rate,
        },
        "quantity": request.quantity,
    }


def serialize_brief(brief: PaperTradingPrepBrief) -> dict[str, object]:
    return {
        "symbol": brief.symbol,
        "current_price": brief.current_price,
        "previous_close": brief.previous_close,
        "change_percent": brief.change_percent,
        "session_high": brief.session_high,
        "session_low": brief.session_low,
        "signal_direction": brief.signal_direction,
        "signal_confidence": brief.signal_confidence,
        "paper_execution_ready": brief.paper_execution_ready,
        "blocked_stage": brief.blocked_stage,
        "incident_headline": brief.incident_headline,
        "note": brief.note,
    }


def build_same_day_request(
    symbol: str,
    provider: MarketDataProvider,
    quantity: int = 1,
    max_age_minutes: int = 15,
) -> DailyWorkflowRequest:
    quote = provider.fetch_quote(symbol)
    closes = provider.fetch_daily_closes(symbol, limit=30)
    if len(closes) < 5:
        raise ValueError(f"Not enough daily close history to build a same-day request for {symbol}.")

    now = datetime.combine(
        quote.latest_trading_day,
        time(hour=9, minute=35),
        tzinfo=ZoneInfo("America/New_York"),
    )
    snapshot_time = datetime.combine(
        quote.latest_trading_day,
        time(hour=9, minute=34),
        tzinfo=ZoneInfo("America/New_York"),
    )

    from multica_quant_ops.backtest.engine import BacktestCriteria
    from multica_quant_ops.data.quality import DataQualityCheck, PriceSnapshot

    return DailyWorkflowRequest(
        symbol=symbol,
        snapshot=PriceSnapshot(
            symbol=symbol,
            as_of=snapshot_time,
            open_price=quote.open_price,
            high_price=quote.high_price,
            low_price=quote.low_price,
            close_price=quote.price,
            volume=quote.volume,
        ),
        now=now,
        quality_check=DataQualityCheck(max_age=timedelta(minutes=max_age_minutes)),
        signal_prices=closes[-5:],
        backtest_prices=closes,
        backtest_criteria=BacktestCriteria(min_total_return=0.01, min_win_rate=0.5),
        quantity=quantity,
    )


def build_paper_trading_prep_brief(
    request: DailyWorkflowRequest,
    provider: MarketDataProvider,
) -> tuple[PaperTradingPrepBrief, dict[str, object]]:
    workflow = build_default_workflow()
    result = workflow.run(request)
    incident_summary = build_incident_summary(request, result, workflow.data_agent.board.audit_log())
    quote = provider.fetch_quote(request.symbol)

    brief = PaperTradingPrepBrief(
        symbol=request.symbol,
        current_price=quote.price,
        previous_close=quote.previous_close,
        change_percent=quote.change_percent,
        session_high=quote.high_price,
        session_low=quote.low_price,
        signal_direction=result.signal.direction.value if result.signal is not None else "none",
        signal_confidence=result.signal.confidence if result.signal is not None else 0.0,
        paper_execution_ready=result.paper_order is not None,
        blocked_stage=result.blocked_stage,
        incident_headline=incident_summary.headline,
        note=(
            "Research and paper-trading preparation only. "
            "This output is not a live-trading instruction or personalized investment advice."
        ),
    )
    payload = build_workflow_payload(request, result, workflow.data_agent.board)
    return brief, payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a same-day paper-trading request and research brief from a ticker."
    )
    parser.add_argument("--ticker", required=True, help="US equity ticker symbol.")
    parser.add_argument("--quantity", type=int, default=1, help="Paper order quantity.")
    parser.add_argument("--output-request", required=True, help="Path to write the generated request JSON.")
    parser.add_argument("--output-brief", required=True, help="Path to write the research brief JSON.")
    parser.add_argument(
        "--max-age-minutes",
        type=int,
        default=15,
        help="Maximum acceptable age for the quote snapshot.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not api_key:
        raise SystemExit("ALPHAVANTAGE_API_KEY is required to prepare a same-day request.")

    provider = AlphaVantageMarketDataProvider(
        api_key=api_key,
        entitlement=os.environ.get("ALPHAVANTAGE_ENTITLEMENT"),
    )
    request = build_same_day_request(
        symbol=args.ticker,
        provider=provider,
        quantity=args.quantity,
        max_age_minutes=args.max_age_minutes,
    )
    brief, payload = build_paper_trading_prep_brief(request, provider)

    request_output = Path(args.output_request)
    request_output.parent.mkdir(parents=True, exist_ok=True)
    request_output.write_text(
        json.dumps(serialize_request(request), indent=2),
        encoding="utf-8",
    )

    brief_output = Path(args.output_brief)
    brief_output.parent.mkdir(parents=True, exist_ok=True)
    brief_output.write_text(
        json.dumps(
            {
                "brief": serialize_brief(brief),
                "workflow": payload,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Same-day request written to {request_output}")
    print(f"Paper-trading prep brief written to {brief_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
