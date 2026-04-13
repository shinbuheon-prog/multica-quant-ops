from dataclasses import dataclass

from multica_quant_ops.data.quality import DataQualityResult
from multica_quant_ops.models import Task, TaskKind, TaskStatus
from multica_quant_ops.orchestrator.board import InMemoryTaskBoard
from multica_quant_ops.strategies.base import SignalStrategy
from multica_quant_ops.strategies.signals import Signal


@dataclass(frozen=True)
class SignalRun:
    task: Task
    signal: Signal


class SignalAgentService:
    def __init__(self, board: InMemoryTaskBoard, strategy: SignalStrategy) -> None:
        self.board = board
        self.strategy = strategy

    def create_signal_task(self, symbol: str, owner: str = "SignalAgent") -> Task:
        return self.board.create_task(
            title=f"Generate signal for {symbol}",
            owner=owner,
            kind=TaskKind.SIGNAL,
        )

    def run_signal_task(
        self,
        task_id: str,
        actor: str,
        symbol: str,
        prices: list[float],
        data_quality: DataQualityResult,
    ) -> SignalRun:
        task = self.board.get_task(task_id)
        if task.kind != TaskKind.SIGNAL:
            raise ValueError("Task is not a signal generation task.")
        if task.status != TaskStatus.CLAIMED:
            raise ValueError("Signal tasks must be claimed before execution.")
        if data_quality.blocks_downstream:
            raise ValueError("Signal generation is blocked by failed data quality checks.")

        self.board.transition(
            task_id=task_id,
            to_status=TaskStatus.RUNNING,
            actor=actor,
            reason="Starting signal generation.",
        )
        signal = self.strategy.generate_signal(symbol=symbol, prices=prices)
        updated_task = self.board.transition(
            task_id=task_id,
            to_status=TaskStatus.DONE,
            actor=actor,
            reason="Signal generation completed.",
        )
        return SignalRun(task=updated_task, signal=signal)
