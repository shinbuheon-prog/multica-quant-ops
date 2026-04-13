from dataclasses import dataclass

from multica_quant_ops.models import TaskKind


@dataclass(frozen=True)
class ExecutionSafetyPolicy:
    paper_execution_enabled: bool = True
    kill_switch_enabled: bool = False
    live_execution_enabled: bool = False

    def assert_task_allowed(self, task_kind: TaskKind) -> None:
        if self.kill_switch_enabled and task_kind in {
            TaskKind.PAPER_EXECUTION,
            TaskKind.LIVE_EXECUTION,
        }:
            raise ValueError("Execution is blocked by kill switch.")

        if task_kind == TaskKind.PAPER_EXECUTION and not self.paper_execution_enabled:
            raise ValueError("Paper execution is disabled.")

        if task_kind == TaskKind.LIVE_EXECUTION:
            raise ValueError("Live execution is not allowed in V1.")

    def assert_paper_execution_enabled(self) -> None:
        self.assert_task_allowed(TaskKind.PAPER_EXECUTION)
