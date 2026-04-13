from dataclasses import dataclass

from multica_quant_ops.audit import AuditEvent
from multica_quant_ops.execution.safety import ExecutionSafetyPolicy
from multica_quant_ops.models import Task, TaskStatus


ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.TODO: {TaskStatus.CLAIMED},
    TaskStatus.CLAIMED: {TaskStatus.RUNNING, TaskStatus.BLOCKED},
    TaskStatus.RUNNING: {TaskStatus.BLOCKED, TaskStatus.DONE, TaskStatus.FAILED},
    TaskStatus.BLOCKED: {TaskStatus.CLAIMED, TaskStatus.FAILED},
    TaskStatus.DONE: set(),
    TaskStatus.FAILED: set(),
}


@dataclass(frozen=True)
class TransitionResult:
    task: Task
    audit_event: AuditEvent


def transition_task(
    task: Task,
    to_status: TaskStatus,
    actor: str,
    reason: str,
    safety_policy: ExecutionSafetyPolicy | None = None,
) -> TransitionResult:
    allowed = ALLOWED_TRANSITIONS[task.status]
    if to_status not in allowed:
        raise ValueError(f"Invalid task transition: {task.status} -> {to_status}")

    if safety_policy is not None and to_status == TaskStatus.RUNNING:
        safety_policy.assert_task_allowed(task.kind)

    updated_task = Task(
        task_id=task.task_id,
        title=task.title,
        owner=task.owner,
        kind=task.kind,
        status=to_status,
    )
    audit_event = AuditEvent(
        task_title=task.title,
        actor=actor,
        from_status=task.status,
        to_status=to_status,
        reason=reason,
    )
    return TransitionResult(task=updated_task, audit_event=audit_event)
