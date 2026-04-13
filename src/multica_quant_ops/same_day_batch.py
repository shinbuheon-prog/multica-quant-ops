import argparse
import json
import os
from pathlib import Path

from multica_quant_ops.data.providers.alphavantage import AlphaVantageMarketDataProvider
from multica_quant_ops.reporting.korean_operator import render_korean_prep_report
from multica_quant_ops.same_day import (
    build_paper_trading_prep_brief,
    build_same_day_request,
    serialize_brief,
    serialize_request,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare same-day paper-trading files for multiple tickers."
    )
    parser.add_argument(
        "--tickers",
        required=True,
        help="Comma-separated ticker list. Example: AAPL,MSFT,TSLA",
    )
    parser.add_argument("--quantity", type=int, default=1, help="Paper order quantity.")
    parser.add_argument("--output-dir", required=True, help="Directory to write batch outputs.")
    parser.add_argument("--usage-file", required=True, help="Path to the Alpha Vantage usage tracker JSON file.")
    parser.add_argument("--daily-limit", type=int, default=25, help="Daily Alpha Vantage call limit.")
    parser.add_argument("--max-age-minutes", type=int, default=15, help="Maximum acceptable quote age.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    api_key = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not api_key:
        raise SystemExit("ALPHAVANTAGE_API_KEY is required for multi-ticker preparation.")

    provider = AlphaVantageMarketDataProvider.build_free_mode(
        api_key=api_key,
        usage_file=Path(args.usage_file),
        daily_limit=args.daily_limit,
        entitlement=os.environ.get("ALPHAVANTAGE_ENTITLEMENT"),
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tickers = [ticker.strip().upper() for ticker in args.tickers.split(",") if ticker.strip()]
    batch_summary: list[dict[str, object]] = []

    for ticker in tickers:
        request = build_same_day_request(
            symbol=ticker,
            provider=provider,
            quantity=args.quantity,
            max_age_minutes=args.max_age_minutes,
        )
        brief, workflow_payload = build_paper_trading_prep_brief(request, provider)

        request_path = output_dir / f"{ticker}-request.json"
        brief_path = output_dir / f"{ticker}-brief.json"
        report_path = output_dir / f"{ticker}-operator-report-ko.txt"

        request_path.write_text(json.dumps(serialize_request(request), indent=2), encoding="utf-8")
        brief_path.write_text(
            json.dumps({"brief": serialize_brief(brief), "workflow": workflow_payload}, indent=2),
            encoding="utf-8",
        )
        report_path.write_text(render_korean_prep_report(brief) + "\n", encoding="utf-8")

        batch_summary.append(
            {
                "ticker": ticker,
                "paper_execution_ready": brief.paper_execution_ready,
                "blocked_stage": brief.blocked_stage,
                "signal_direction": brief.signal_direction,
                "current_price": brief.current_price,
                "remaining_calls": brief.alpha_vantage_remaining_calls,
            }
        )

    summary_path = output_dir / "batch-summary.json"
    summary_path.write_text(json.dumps({"tickers": batch_summary}, indent=2), encoding="utf-8")
    print(f"Multi-ticker preparation written to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
