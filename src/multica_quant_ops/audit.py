from dataclasses import dataclass

from multica_quant_ops.models import TaskStatus


@dataclass(frozen=True)
class AuditEvent:
    task_title: str
    actor: str
    from_status: TaskStatus
    to_status: TaskStatus
    reason: str
