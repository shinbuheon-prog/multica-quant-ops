from datetime import datetime, timedelta

import pytest

from multica_quant_ops.agents.ops_agent import OpsAgentService
from multica_quant_ops.agents.registry import AgentRegistry
from multica_quant_ops.backtest.engine import BacktestCriteria, BacktestResult, run_backtest
from multica_quant_ops.data.quality import DataQualityCheck, PriceSnapshot, evaluate_snapshot
from multica_quant_ops.execution.paper import build_paper_order_proposal
from multica_quant_ops.execution.safety import ExecutionSafetyPolicy
from multica_quant_ops.models import AgentProfile, TaskStatus
from multica_quant_ops.orchestrator.board import InMemoryTaskBoard
from multica_quant_ops.strategies.momentum import SimpleMomentumStrategy
from multica_quant_ops.strategies.signals import Signal, SignalDirection


def build_execution_board(policy: ExecutionSafetyPolicy | None = None) -> InMemoryTaskBoard:
    registry = AgentRegistry()
    registry.register(AgentProfile(name="OpsAgent", role="ops"))
    return InMemoryTaskBoard(registry, policy or ExecutionSafetyPolicy())


def passing_data_quality():
    now = datetime(2026, 4, 13, 9, 35, 0)
    return evaluate_snapshot(
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
        check=DataQualityCheck(max_age=timedelta(minutes=5)),
    )


def passing_backtest() -> BacktestResult:
    return run_backtest(
        strategy=SimpleMomentumStrategy(),
        symbol="AAPL",
        prices=[100.0, 101.0, 103.0, 104.0, 106.0],
        criteria=BacktestCriteria(min_total_return=0.01, min_win_rate=0.5),
    )


def test_build_paper_order_proposal_requires_all_gates() -> None:
    signal = Signal(
        symbol="AAPL",
        direction=SignalDirection.LONG,
        confidence=0.7,
        rationale="Positive momentum.",
    )

    proposal = build_paper_order_proposal(
        signal=signal,
        data_quality=passing_data_quality(),
        backtest_result=passing_backtest(),
        safety_policy=ExecutionSafetyPolicy(),
        quantity=5,
    )

    assert proposal.side == "buy"
    assert proposal.quantity == 5


def test_paper_execution_rejects_failed_backtest() -> None:
    signal = Signal(
        symbol="AAPL",
        direction=SignalDirection.LONG,
        confidence=0.7,
        rationale="Positive momentum.",
    )
    failed_backtest = BacktestResult(
        total_return=-0.02,
        win_rate=0.2,
        periods=5,
        approved_for_paper_trading=False,
    )

    with pytest.raises(ValueError, match="failed backtest criteria"):
        build_paper_order_proposal(
            signal=signal,
            data_quality=passing_data_quality(),
            backtest_result=failed_backtest,
            safety_policy=ExecutionSafetyPolicy(),
        )


def test_paper_execution_respects_kill_switch() -> None:
    signal = Signal(
        symbol="AAPL",
        direction=SignalDirection.LONG,
        confidence=0.7,
        rationale="Positive momentum.",
    )

    with pytest.raises(ValueError, match="kill switch"):
        build_paper_order_proposal(
            signal=signal,
            data_quality=passing_data_quality(),
            backtest_result=passing_backtest(),
            safety_policy=ExecutionSafetyPolicy(kill_switch_enabled=True),
        )


def test_ops_agent_creates_paper_order_when_all_gates_pass() -> None:
    board = build_execution_board()
    service = OpsAgentService(board, ExecutionSafetyPolicy())
    task = service.create_paper_execution_task("AAPL")
    board.transition(task.task_id, TaskStatus.CLAIMED, "OpsAgent", "Claiming paper execution.")

    run = service.run_paper_execution_task(
        task_id=task.task_id,
        actor="OpsAgent",
        signal=Signal(
            symbol="AAPL",
            direction=SignalDirection.LONG,
            confidence=0.6,
            rationale="Positive momentum.",
        ),
        data_quality=passing_data_quality(),
        backtest_result=passing_backtest(),
        quantity=3,
    )

    assert run.task.status == TaskStatus.DONE
    assert run.proposal.quantity == 3
    assert run.proposal.side == "buy"


def test_ops_agent_requires_claimed_task() -> None:
    board = build_execution_board()
    service = OpsAgentService(board, ExecutionSafetyPolicy())
    task = service.create_paper_execution_task("AAPL")

    with pytest.raises(ValueError, match="must be claimed"):
        service.run_paper_execution_task(
            task_id=task.task_id,
            actor="OpsAgent",
            signal=Signal(
                symbol="AAPL",
                direction=SignalDirection.LONG,
                confidence=0.6,
                rationale="Positive momentum.",
            ),
            data_quality=passing_data_quality(),
            backtest_result=passing_backtest(),
        )
