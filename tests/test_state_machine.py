import pytest

from multica_quant_ops.execution.safety import ExecutionSafetyPolicy
from multica_quant_ops.models import Task, TaskKind, TaskStatus
from multica_quant_ops.orchestrator.state_machine import transition_task


def test_valid_transition_creates_audit_event() -> None:
    task = Task(
        task_id="task-1",
        title="Premarket data check",
        owner="DataAgent",
        kind=TaskKind.DATA_CHECK,
    )

    result = transition_task(
        task=task,
        to_status=TaskStatus.CLAIMED,
        actor="DataAgent",
        reason="Taking ownership of scheduled check.",
    )

    assert result.task.status == TaskStatus.CLAIMED
    assert result.audit_event.from_status == TaskStatus.TODO
    assert result.audit_event.to_status == TaskStatus.CLAIMED


def test_invalid_transition_is_rejected() -> None:
    task = Task(
        task_id="task-2",
        title="Backtest strategy",
        owner="BacktestAgent",
        kind=TaskKind.BACKTEST,
    )

    with pytest.raises(ValueError, match="Invalid task transition"):
        transition_task(
            task=task,
            to_status=TaskStatus.DONE,
            actor="BacktestAgent",
            reason="Skipping required work.",
        )


def test_kill_switch_blocks_execution_tasks_from_running() -> None:
    task = Task(
        task_id="task-3",
        title="Place simulated rebalance orders",
        owner="OpsAgent",
        kind=TaskKind.PAPER_EXECUTION,
        status=TaskStatus.CLAIMED,
    )
    policy = ExecutionSafetyPolicy(kill_switch_enabled=True)

    with pytest.raises(ValueError, match="kill switch"):
        transition_task(
            task=task,
            to_status=TaskStatus.RUNNING,
            actor="OpsAgent",
            reason="Starting execution window.",
            safety_policy=policy,
        )


def test_live_execution_is_rejected_even_without_kill_switch() -> None:
    task = Task(
        task_id="task-4",
        title="Submit live order",
        owner="OpsAgent",
        kind=TaskKind.LIVE_EXECUTION,
        status=TaskStatus.CLAIMED,
    )
    policy = ExecutionSafetyPolicy()

    with pytest.raises(ValueError, match="not allowed in V1"):
        transition_task(
            task=task,
            to_status=TaskStatus.RUNNING,
            actor="OpsAgent",
            reason="Attempting live execution.",
            safety_policy=policy,
        )
