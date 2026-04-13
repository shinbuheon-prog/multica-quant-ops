import pytest

from multica_quant_ops.agents.backtest_agent import BacktestAgentService
from multica_quant_ops.agents.registry import AgentRegistry
from multica_quant_ops.backtest.engine import BacktestCriteria, run_backtest
from multica_quant_ops.execution.safety import ExecutionSafetyPolicy
from multica_quant_ops.models import AgentProfile, TaskStatus
from multica_quant_ops.orchestrator.board import InMemoryTaskBoard
from multica_quant_ops.strategies.momentum import SimpleMomentumStrategy


def build_backtest_board() -> InMemoryTaskBoard:
    registry = AgentRegistry()
    registry.register(AgentProfile(name="BacktestAgent", role="backtest"))
    return InMemoryTaskBoard(registry, ExecutionSafetyPolicy())


def test_backtest_engine_approves_positive_series() -> None:
    result = run_backtest(
        strategy=SimpleMomentumStrategy(),
        symbol="AAPL",
        prices=[100.0, 101.0, 103.0, 104.0, 106.0],
        criteria=BacktestCriteria(min_total_return=0.01, min_win_rate=0.5),
    )

    assert result.approved_for_paper_trading is True
    assert result.total_return > 0


def test_backtest_engine_rejects_weak_series() -> None:
    result = run_backtest(
        strategy=SimpleMomentumStrategy(),
        symbol="AAPL",
        prices=[100.0, 99.0, 98.0, 97.0, 96.0],
        criteria=BacktestCriteria(min_total_return=0.01, min_win_rate=0.5),
    )

    assert result.approved_for_paper_trading is False


def test_backtest_agent_marks_task_done_when_criteria_pass() -> None:
    board = build_backtest_board()
    service = BacktestAgentService(board, SimpleMomentumStrategy())
    task = service.create_backtest_task("AAPL")
    board.transition(task.task_id, TaskStatus.CLAIMED, "BacktestAgent", "Claiming backtest.")

    run = service.run_backtest_task(
        task_id=task.task_id,
        actor="BacktestAgent",
        symbol="AAPL",
        prices=[100.0, 101.0, 103.0, 104.0, 106.0],
        criteria=BacktestCriteria(min_total_return=0.01, min_win_rate=0.5),
    )

    assert run.task.status == TaskStatus.DONE
    assert run.result.approved_for_paper_trading is True


def test_backtest_agent_blocks_task_when_criteria_fail() -> None:
    board = build_backtest_board()
    service = BacktestAgentService(board, SimpleMomentumStrategy())
    task = service.create_backtest_task("AAPL")
    board.transition(task.task_id, TaskStatus.CLAIMED, "BacktestAgent", "Claiming backtest.")

    run = service.run_backtest_task(
        task_id=task.task_id,
        actor="BacktestAgent",
        symbol="AAPL",
        prices=[100.0, 99.5, 99.0, 98.5, 98.0],
        criteria=BacktestCriteria(min_total_return=0.01, min_win_rate=0.5),
    )

    assert run.task.status == TaskStatus.BLOCKED
    assert run.result.approved_for_paper_trading is False


def test_backtest_agent_requires_claimed_task() -> None:
    board = build_backtest_board()
    service = BacktestAgentService(board, SimpleMomentumStrategy())
    task = service.create_backtest_task("AAPL")

    with pytest.raises(ValueError, match="must be claimed"):
        service.run_backtest_task(
            task_id=task.task_id,
            actor="BacktestAgent",
            symbol="AAPL",
            prices=[100.0, 101.0, 103.0],
            criteria=BacktestCriteria(min_total_return=0.01, min_win_rate=0.5),
        )
