from datetime import datetime, timedelta

import pytest

from multica_quant_ops.agents.data_agent import DataAgentService
from multica_quant_ops.agents.registry import AgentRegistry
from multica_quant_ops.data.quality import DataQualityCheck, DataQualityStatus, PriceSnapshot, evaluate_snapshot
from multica_quant_ops.execution.safety import ExecutionSafetyPolicy
from multica_quant_ops.models import AgentProfile, TaskStatus
from multica_quant_ops.orchestrator.board import InMemoryTaskBoard


def test_quality_check_passes_for_fresh_consistent_snapshot() -> None:
    now = datetime(2026, 4, 13, 9, 35, 0)
    snapshot = PriceSnapshot(
        symbol="AAPL",
        as_of=now - timedelta(minutes=5),
        open_price=200.0,
        high_price=205.0,
        low_price=198.0,
        close_price=203.0,
        volume=1000,
    )

    result = evaluate_snapshot(
        snapshot=snapshot,
        now=now,
        check=DataQualityCheck(max_age=timedelta(minutes=15)),
    )

    assert result.status == DataQualityStatus.PASS
    assert result.blocks_downstream is False


def test_quality_check_fails_for_stale_and_inconsistent_snapshot() -> None:
    now = datetime(2026, 4, 13, 9, 35, 0)
    snapshot = PriceSnapshot(
        symbol="MSFT",
        as_of=now - timedelta(minutes=30),
        open_price=430.0,
        high_price=425.0,
        low_price=428.0,
        close_price=427.0,
        volume=0,
    )

    result = evaluate_snapshot(
        snapshot=snapshot,
        now=now,
        check=DataQualityCheck(max_age=timedelta(minutes=15)),
    )

    assert result.status == DataQualityStatus.FAIL
    assert result.blocks_downstream is True
    assert "snapshot is stale" in result.reasons
    assert "volume is below minimum threshold" in result.reasons


def test_data_agent_moves_passed_check_to_done() -> None:
    registry = AgentRegistry()
    registry.register(AgentProfile(name="DataAgent", role="data"))
    board = InMemoryTaskBoard(registry, ExecutionSafetyPolicy())
    service = DataAgentService(board)

    task = service.create_quality_check_task("NVDA")
    board.transition(task.task_id, TaskStatus.CLAIMED, "DataAgent", "Claiming check.")

    now = datetime(2026, 4, 13, 9, 35, 0)
    snapshot = PriceSnapshot(
        symbol="NVDA",
        as_of=now - timedelta(minutes=2),
        open_price=120.0,
        high_price=123.0,
        low_price=119.0,
        close_price=122.5,
        volume=5000,
    )

    run = service.run_quality_check(
        task_id=task.task_id,
        actor="DataAgent",
        snapshot=snapshot,
        now=now,
        check=DataQualityCheck(max_age=timedelta(minutes=10)),
    )

    assert run.task.status == TaskStatus.DONE
    assert run.result.status == DataQualityStatus.PASS


def test_data_agent_blocks_failed_check() -> None:
    registry = AgentRegistry()
    registry.register(AgentProfile(name="DataAgent", role="data"))
    board = InMemoryTaskBoard(registry, ExecutionSafetyPolicy())
    service = DataAgentService(board)

    task = service.create_quality_check_task("TSLA")
    board.transition(task.task_id, TaskStatus.CLAIMED, "DataAgent", "Claiming check.")

    now = datetime(2026, 4, 13, 9, 35, 0)
    snapshot = PriceSnapshot(
        symbol="TSLA",
        as_of=now - timedelta(minutes=20),
        open_price=250.0,
        high_price=255.0,
        low_price=248.0,
        close_price=252.0,
        volume=100,
    )

    run = service.run_quality_check(
        task_id=task.task_id,
        actor="DataAgent",
        snapshot=snapshot,
        now=now,
        check=DataQualityCheck(max_age=timedelta(minutes=10)),
    )

    assert run.task.status == TaskStatus.BLOCKED
    assert run.result.status == DataQualityStatus.FAIL


def test_data_agent_requires_claimed_task_before_run() -> None:
    registry = AgentRegistry()
    registry.register(AgentProfile(name="DataAgent", role="data"))
    board = InMemoryTaskBoard(registry, ExecutionSafetyPolicy())
    service = DataAgentService(board)

    task = service.create_quality_check_task("AMZN")
    now = datetime(2026, 4, 13, 9, 35, 0)
    snapshot = PriceSnapshot(
        symbol="AMZN",
        as_of=now,
        open_price=180.0,
        high_price=182.0,
        low_price=179.0,
        close_price=181.5,
        volume=2000,
    )

    with pytest.raises(ValueError, match="must be claimed"):
        service.run_quality_check(
            task_id=task.task_id,
            actor="DataAgent",
            snapshot=snapshot,
            now=now,
            check=DataQualityCheck(max_age=timedelta(minutes=10)),
        )
