from datetime import datetime, timedelta

from multica_quant_ops.agents.backtest_agent import BacktestAgentService
from multica_quant_ops.agents.data_agent import DataAgentService
from multica_quant_ops.agents.ops_agent import OpsAgentService
from multica_quant_ops.agents.registry import AgentRegistry
from multica_quant_ops.agents.signal_agent import SignalAgentService
from multica_quant_ops.backtest.engine import BacktestCriteria
from multica_quant_ops.data.quality import DataQualityCheck, PriceSnapshot
from multica_quant_ops.execution.safety import ExecutionSafetyPolicy
from multica_quant_ops.models import AgentProfile
from multica_quant_ops.orchestrator.board import InMemoryTaskBoard
from multica_quant_ops.orchestrator.daily_workflow import DailyWorkflowRequest, DailyWorkflowService
from multica_quant_ops.reporting.incident_summary import build_incident_summary, render_incident_summary
from multica_quant_ops.strategies.momentum import SimpleMomentumStrategy


def build_workflow() -> DailyWorkflowService:
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


def test_incident_summary_reports_no_incident_for_successful_run() -> None:
    service = build_workflow()
    now = datetime(2026, 4, 13, 9, 35, 0)
    request = DailyWorkflowRequest(
        symbol="AAPL",
        snapshot=PriceSnapshot(
            symbol="AAPL",
            as_of=now - timedelta(minutes=1),
            open_price=200.0,
            high_price=202.0,
            low_price=199.0,
            close_price=201.0,
            volume=1000,
        ),
        now=now,
        quality_check=DataQualityCheck(max_age=timedelta(minutes=5)),
        signal_prices=[100.0, 101.0, 103.0],
        backtest_prices=[100.0, 101.0, 103.0, 104.0, 106.0],
        backtest_criteria=BacktestCriteria(min_total_return=0.01, min_win_rate=0.5),
        quantity=2,
    )

    result = service.run(request)
    summary = build_incident_summary(request, result, service.data_agent.board.audit_log())

    assert summary.is_incident is False
    assert summary.stage is None
    assert "No incident" in render_incident_summary(summary)


def test_incident_summary_reports_data_quality_failure() -> None:
    service = build_workflow()
    now = datetime(2026, 4, 13, 9, 35, 0)
    request = DailyWorkflowRequest(
        symbol="AAPL",
        snapshot=PriceSnapshot(
            symbol="AAPL",
            as_of=now - timedelta(minutes=20),
            open_price=200.0,
            high_price=202.0,
            low_price=199.0,
            close_price=201.0,
            volume=1000,
        ),
        now=now,
        quality_check=DataQualityCheck(max_age=timedelta(minutes=5)),
        signal_prices=[100.0, 101.0, 103.0],
        backtest_prices=[100.0, 101.0, 103.0, 104.0, 106.0],
        backtest_criteria=BacktestCriteria(min_total_return=0.01, min_win_rate=0.5),
    )

    result = service.run(request)
    summary = build_incident_summary(request, result, service.data_agent.board.audit_log())
    rendered = render_incident_summary(summary)

    assert summary.is_incident is True
    assert summary.stage == "data_quality"
    assert "snapshot is stale" in rendered
    assert "Refresh or correct the market snapshot." in rendered
