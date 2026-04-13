import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from multica_quant_ops.agents.backtest_agent import BacktestAgentService
from multica_quant_ops.agents.data_agent import DataAgentService
from multica_quant_ops.agents.ops_agent import OpsAgentService
from multica_quant_ops.agents.registry import AgentRegistry
from multica_quant_ops.agents.signal_agent import SignalAgentService
from multica_quant_ops.api.service import build_request_from_payload, build_workflow_payload
from multica_quant_ops.backtest.engine import BacktestCriteria
from multica_quant_ops.data.quality import DataQualityCheck, PriceSnapshot
from multica_quant_ops.execution.safety import ExecutionSafetyPolicy
from multica_quant_ops.models import AgentProfile
from multica_quant_ops.orchestrator.board import InMemoryTaskBoard
from multica_quant_ops.orchestrator.daily_workflow import DailyWorkflowRequest, DailyWorkflowService
from multica_quant_ops.reporting.daily_report import build_daily_report
from multica_quant_ops.reporting.incident_summary import build_incident_summary, render_incident_summary
from multica_quant_ops.strategies.momentum import SimpleMomentumStrategy


def build_default_workflow() -> DailyWorkflowService:
    registry = AgentRegistry()
    registry.register(AgentProfile(name="DataAgent", role="data"))
    registry.register(AgentProfile(name="SignalAgent", role="signal"))
    registry.register(AgentProfile(name="BacktestAgent", role="backtest"))
    registry.register(AgentProfile(name="OpsAgent", role="ops"))

    board = InMemoryTaskBoard(registry, ExecutionSafetyPolicy())
    strategy = SimpleMomentumStrategy()
    return DailyWorkflowService(
        data_agent=DataAgentService(board),
        signal_agent=SignalAgentService(board, strategy),
        backtest_agent=BacktestAgentService(board, strategy),
        ops_agent=OpsAgentService(board, ExecutionSafetyPolicy()),
    )


def build_sample_request(
    symbol: str,
    quantity: int,
    stale_data: bool,
    weak_backtest: bool,
    outside_session: bool,
) -> DailyWorkflowRequest:
    now = (
        datetime(2026, 4, 13, 7, 0, 0)
        if outside_session
        else datetime(2026, 4, 13, 9, 35, 0)
    )
    snapshot_age = timedelta(minutes=20) if stale_data else timedelta(minutes=1)
    backtest_prices = (
        [100.0, 99.5, 99.0, 98.5, 98.0]
        if weak_backtest
        else [100.0, 101.0, 103.0, 104.0, 106.0]
    )
    return DailyWorkflowRequest(
        symbol=symbol,
        snapshot=PriceSnapshot(
            symbol=symbol,
            as_of=now - snapshot_age,
            open_price=200.0,
            high_price=202.0,
            low_price=199.0,
            close_price=201.0,
            volume=1000,
        ),
        now=now,
        quality_check=DataQualityCheck(max_age=timedelta(minutes=5)),
        signal_prices=[100.0, 101.0, 103.0],
        backtest_prices=backtest_prices,
        backtest_criteria=BacktestCriteria(min_total_return=0.01, min_win_rate=0.5),
        quantity=quantity,
    )

def load_request(
    input_path: str | None,
    symbol: str,
    quantity: int,
    stale_data: bool,
    weak_backtest: bool,
    outside_session: bool,
) -> DailyWorkflowRequest:
    if input_path is None:
        return build_sample_request(
            symbol=symbol,
            quantity=quantity,
            stale_data=stale_data,
            weak_backtest=weak_backtest,
            outside_session=outside_session,
        )

    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    return build_request_from_payload(payload)


def write_report(report: str, output_path: str | None) -> None:
    if output_path is None:
        print(report)
        return
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report + "\n", encoding="utf-8")
    print(f"Report written to {target}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Multica Quant Ops daily workflow.")
    parser.add_argument("--symbol", default="AAPL", help="Ticker symbol for the sample workflow.")
    parser.add_argument("--quantity", type=int, default=2, help="Paper order quantity for sample mode.")
    parser.add_argument("--input", help="Path to a JSON workflow request.")
    parser.add_argument("--output", help="Optional path to save the daily report.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a machine-readable JSON report including tasks and audit events.",
    )
    parser.add_argument(
        "--incident-summary",
        action="store_true",
        help="Emit an operator-focused incident summary instead of the full daily report.",
    )
    parser.add_argument(
        "--stale-data",
        action="store_true",
        help="Use a stale snapshot to trigger a data-quality block.",
    )
    parser.add_argument(
        "--weak-backtest",
        action="store_true",
        help="Use a weak backtest series to trigger a backtest block.",
    )
    parser.add_argument(
        "--outside-session",
        action="store_true",
        help="Use a timestamp outside the regular US market session to block paper execution.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workflow = build_default_workflow()
    request = load_request(
        input_path=args.input,
        symbol=args.symbol,
        quantity=args.quantity,
        stale_data=args.stale_data,
        weak_backtest=args.weak_backtest,
        outside_session=args.outside_session,
    )
    result = workflow.run(request)
    incident_summary = build_incident_summary(request, result, workflow.data_agent.board.audit_log())
    report = json.dumps(build_workflow_payload(request, result, workflow.data_agent.board), indent=2)
    if not args.json:
        report = (
            render_incident_summary(incident_summary)
            if args.incident_summary
            else build_daily_report(request, result)
        )
    write_report(report, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
