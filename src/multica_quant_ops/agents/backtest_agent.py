from dataclasses import dataclass

from multica_quant_ops.backtest.engine import BacktestCriteria, BacktestResult, run_backtest
from multica_quant_ops.models import Task, TaskKind, TaskStatus
from multica_quant_ops.orchestrator.board import InMemoryTaskBoard
from multica_quant_ops.strategies.base import SignalStrategy


@dataclass(frozen=True)
class BacktestRun:
    task: Task
    result: BacktestResult


class BacktestAgentService:
    def __init__(self, board: InMemoryTaskBoard, strategy: SignalStrategy) -> None:
        self.board = board
        self.strategy = strategy

    def create_backtest_task(self, symbol: str, owner: str = "BacktestAgent") -> Task:
        return self.board.create_task(
            title=f"Backtest strategy for {symbol}",
            owner=owner,
            kind=TaskKind.BACKTEST,
        )

    def run_backtest_task(
        self,
        task_id: str,
        actor: str,
        symbol: str,
        prices: list[float],
        criteria: BacktestCriteria,
    ) -> BacktestRun:
        task = self.board.get_task(task_id)
        if task.kind != TaskKind.BACKTEST:
            raise ValueError("Task is not a backtest task.")
        if task.status != TaskStatus.CLAIMED:
            raise ValueError("Backtest tasks must be claimed before execution.")

        self.board.transition(
            task_id=task_id,
            to_status=TaskStatus.RUNNING,
            actor=actor,
            reason="Starting backtest run.",
        )
        result = run_backtest(self.strategy, symbol=symbol, prices=prices, criteria=criteria)
        next_status = TaskStatus.DONE if result.approved_for_paper_trading else TaskStatus.BLOCKED
        reason = (
            "Backtest passed promotion criteria."
            if next_status == TaskStatus.DONE
            else "Backtest failed promotion criteria."
        )
        updated_task = self.board.transition(
            task_id=task_id,
            to_status=next_status,
            actor=actor,
            reason=reason,
        )
        return BacktestRun(task=updated_task, result=result)
