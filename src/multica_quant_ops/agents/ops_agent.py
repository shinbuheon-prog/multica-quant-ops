from dataclasses import dataclass

from multica_quant_ops.backtest.engine import BacktestResult
from multica_quant_ops.data.quality import DataQualityResult
from multica_quant_ops.execution.paper import PaperOrderProposal, build_paper_order_proposal
from multica_quant_ops.execution.safety import ExecutionSafetyPolicy
from multica_quant_ops.models import Task, TaskKind, TaskStatus
from multica_quant_ops.orchestrator.board import InMemoryTaskBoard
from multica_quant_ops.strategies.signals import Signal


@dataclass(frozen=True)
class PaperExecutionRun:
    task: Task
    proposal: PaperOrderProposal


class OpsAgentService:
    def __init__(self, board: InMemoryTaskBoard, safety_policy: ExecutionSafetyPolicy) -> None:
        self.board = board
        self.safety_policy = safety_policy

    def create_paper_execution_task(self, symbol: str, owner: str = "OpsAgent") -> Task:
        return self.board.create_task(
            title=f"Prepare paper order for {symbol}",
            owner=owner,
            kind=TaskKind.PAPER_EXECUTION,
        )

    def run_paper_execution_task(
        self,
        task_id: str,
        actor: str,
        signal: Signal,
        data_quality: DataQualityResult,
        backtest_result: BacktestResult,
        quantity: int = 1,
    ) -> PaperExecutionRun:
        task = self.board.get_task(task_id)
        if task.kind != TaskKind.PAPER_EXECUTION:
            raise ValueError("Task is not a paper execution task.")
        if task.status != TaskStatus.CLAIMED:
            raise ValueError("Paper execution tasks must be claimed before execution.")

        self.board.transition(
            task_id=task_id,
            to_status=TaskStatus.RUNNING,
            actor=actor,
            reason="Starting paper execution gate.",
        )
        proposal = build_paper_order_proposal(
            signal=signal,
            data_quality=data_quality,
            backtest_result=backtest_result,
            safety_policy=self.safety_policy,
            quantity=quantity,
        )
        updated_task = self.board.transition(
            task_id=task_id,
            to_status=TaskStatus.DONE,
            actor=actor,
            reason="Paper execution proposal created.",
        )
        return PaperExecutionRun(task=updated_task, proposal=proposal)
