from datetime import datetime, timedelta

import pytest

from multica_quant_ops.agents.registry import AgentRegistry
from multica_quant_ops.agents.signal_agent import SignalAgentService
from multica_quant_ops.data.quality import DataQualityCheck, DataQualityStatus, PriceSnapshot, evaluate_snapshot
from multica_quant_ops.execution.safety import ExecutionSafetyPolicy
from multica_quant_ops.models import AgentProfile, TaskStatus
from multica_quant_ops.orchestrator.board import InMemoryTaskBoard
from multica_quant_ops.strategies.momentum import SimpleMomentumStrategy
from multica_quant_ops.strategies.signals import SignalDirection


def build_signal_board() -> InMemoryTaskBoard:
    registry = AgentRegistry()
    registry.register(AgentProfile(name="SignalAgent", role="signal"))
    return InMemoryTaskBoard(registry, ExecutionSafetyPolicy())


def build_quality_result(pass_result: bool):
    now = datetime(2026, 4, 13, 9, 35, 0)
    snapshot = PriceSnapshot(
        symbol="AAPL",
        as_of=now - timedelta(minutes=1 if pass_result else 20),
        open_price=200.0,
        high_price=202.0,
        low_price=199.0,
        close_price=201.0,
        volume=1000,
    )
    return evaluate_snapshot(
        snapshot=snapshot,
        now=now,
        check=DataQualityCheck(max_age=timedelta(minutes=5)),
    )


def test_momentum_strategy_generates_long_signal_for_positive_trend() -> None:
    strategy = SimpleMomentumStrategy()

    signal = strategy.generate_signal(symbol="AAPL", prices=[100.0, 101.5, 103.0])

    assert signal.direction == SignalDirection.LONG
    assert signal.confidence > 0


def test_signal_agent_completes_task_when_data_quality_passes() -> None:
    board = build_signal_board()
    service = SignalAgentService(board, SimpleMomentumStrategy())
    task = service.create_signal_task("AAPL")
    board.transition(task.task_id, TaskStatus.CLAIMED, "SignalAgent", "Claiming task.")

    run = service.run_signal_task(
        task_id=task.task_id,
        actor="SignalAgent",
        symbol="AAPL",
        prices=[100.0, 102.0, 104.0],
        data_quality=build_quality_result(True),
    )

    assert run.task.status == TaskStatus.DONE
    assert run.signal.direction == SignalDirection.LONG


def test_signal_agent_blocks_failed_data_quality() -> None:
    board = build_signal_board()
    service = SignalAgentService(board, SimpleMomentumStrategy())
    task = service.create_signal_task("AAPL")
    board.transition(task.task_id, TaskStatus.CLAIMED, "SignalAgent", "Claiming task.")

    with pytest.raises(ValueError, match="blocked by failed data quality"):
        service.run_signal_task(
            task_id=task.task_id,
            actor="SignalAgent",
            symbol="AAPL",
            prices=[100.0, 102.0, 104.0],
            data_quality=build_quality_result(False),
        )


def test_signal_agent_requires_claimed_task() -> None:
    board = build_signal_board()
    service = SignalAgentService(board, SimpleMomentumStrategy())
    task = service.create_signal_task("AAPL")

    with pytest.raises(ValueError, match="must be claimed"):
        service.run_signal_task(
            task_id=task.task_id,
            actor="SignalAgent",
            symbol="AAPL",
            prices=[100.0, 99.0],
            data_quality=build_quality_result(True),
        )


def test_momentum_strategy_returns_flat_for_non_positive_trend() -> None:
    strategy = SimpleMomentumStrategy()

    signal = strategy.generate_signal(symbol="AAPL", prices=[100.0, 99.5, 99.0])

    assert signal.direction == SignalDirection.FLAT


def test_quality_result_builder_covers_both_outcomes() -> None:
    assert build_quality_result(True).status == DataQualityStatus.PASS
    assert build_quality_result(False).status == DataQualityStatus.FAIL
