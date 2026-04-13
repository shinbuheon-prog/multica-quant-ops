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
from multica_quant_ops.strategies.momentum import SimpleMomentumStrategy
from multica_quant_ops.strategies.signals import SignalDirection


def build_workflow_service() -> DailyWorkflowService:
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


def test_daily_workflow_runs_end_to_end_when_all_gates_pass() -> None:
    service = build_workflow_service()
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

    assert result.blocked_stage is None
    assert result.signal is not None
    assert result.signal.direction == SignalDirection.LONG
    assert result.backtest_result is not None
    assert result.backtest_result.approved_for_paper_trading is True
    assert result.paper_order is not None
    assert result.paper_order.quantity == 2


def test_daily_workflow_stops_on_failed_data_quality() -> None:
    service = build_workflow_service()
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

    assert result.blocked_stage == "data_quality"
    assert result.signal is None
    assert result.backtest_result is None
    assert result.paper_order is None


def test_daily_workflow_stops_on_failed_backtest() -> None:
    service = build_workflow_service()
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
        backtest_prices=[100.0, 99.5, 99.0, 98.5, 98.0],
        backtest_criteria=BacktestCriteria(min_total_return=0.01, min_win_rate=0.5),
    )

    result = service.run(request)

    assert result.blocked_stage == "backtest"
    assert result.signal is not None
    assert result.backtest_result is not None
    assert result.backtest_result.approved_for_paper_trading is False
    assert result.paper_order is None


def test_daily_workflow_stops_on_failed_paper_execution_gate() -> None:
    service = build_workflow_service()
    now = datetime(2026, 4, 13, 7, 0, 0)
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
    )

    result = service.run(request)

    assert result.blocked_stage == "paper_execution"
    assert result.signal is not None
    assert result.backtest_result is not None
    assert result.paper_order is None
    assert result.paper_execution_reason is not None
