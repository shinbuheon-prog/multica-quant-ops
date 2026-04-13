from dataclasses import dataclass
from datetime import datetime

from multica_quant_ops.data.quality import (
    DataQualityCheck,
    DataQualityResult,
    PriceSnapshot,
    evaluate_snapshot,
)
from multica_quant_ops.models import Task, TaskKind, TaskStatus
from multica_quant_ops.orchestrator.board import InMemoryTaskBoard


@dataclass(frozen=True)
class DataCheckRun:
    task: Task
    result: DataQualityResult


class DataAgentService:
    def __init__(self, board: InMemoryTaskBoard) -> None:
        self.board = board

    def create_quality_check_task(self, symbol: str, owner: str = "DataAgent") -> Task:
        return self.board.create_task(
            title=f"Validate market data for {symbol}",
            owner=owner,
            kind=TaskKind.DATA_CHECK,
        )

    def run_quality_check(
        self,
        task_id: str,
        actor: str,
        snapshot: PriceSnapshot,
        now: datetime,
        check: DataQualityCheck,
    ) -> DataCheckRun:
        task = self.board.get_task(task_id)
        if task.kind != TaskKind.DATA_CHECK:
            raise ValueError("Task is not a data quality check.")
        if task.status != TaskStatus.CLAIMED:
            raise ValueError("Data quality checks must be claimed before execution.")

        self.board.transition(
            task_id=task_id,
            to_status=TaskStatus.RUNNING,
            actor=actor,
            reason="Starting data quality check.",
        )
        result = evaluate_snapshot(snapshot=snapshot, now=now, check=check)
        next_status = TaskStatus.DONE if not result.blocks_downstream else TaskStatus.BLOCKED
        reason = "Data quality passed." if next_status == TaskStatus.DONE else "Data quality failed."
        updated_task = self.board.transition(
            task_id=task_id,
            to_status=next_status,
            actor=actor,
            reason=reason,
        )
        return DataCheckRun(task=updated_task, result=result)
