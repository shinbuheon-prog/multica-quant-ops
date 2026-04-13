from dataclasses import dataclass, field
from uuid import uuid4

from multica_quant_ops.agents.registry import AgentRegistry
from multica_quant_ops.audit import AuditEvent
from multica_quant_ops.execution.safety import ExecutionSafetyPolicy
from multica_quant_ops.models import Task, TaskKind, TaskStatus
from multica_quant_ops.orchestrator.state_machine import transition_task


@dataclass
class InMemoryTaskBoard:
    agent_registry: AgentRegistry
    safety_policy: ExecutionSafetyPolicy
    _tasks: dict[str, Task] = field(default_factory=dict)
    _audit_log: list[AuditEvent] = field(default_factory=list)

    def create_task(self, title: str, owner: str, kind: TaskKind) -> Task:
        self.agent_registry.get(owner)
        task = Task(task_id=str(uuid4()), title=title, owner=owner, kind=kind)
        self._tasks[task.task_id] = task
        return task

    def get_task(self, task_id: str) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError as exc:
            raise ValueError(f"Unknown task: {task_id}") from exc

    def assign_owner(self, task_id: str, owner: str) -> Task:
        self.agent_registry.get(owner)
        task = self.get_task(task_id)
        updated = Task(
            task_id=task.task_id,
            title=task.title,
            owner=owner,
            kind=task.kind,
            status=task.status,
        )
        self._tasks[task_id] = updated
        return updated

    def transition(self, task_id: str, to_status: TaskStatus, actor: str, reason: str) -> Task:
        self.agent_registry.get(actor)
        task = self.get_task(task_id)
        result = transition_task(
            task=task,
            to_status=to_status,
            actor=actor,
            reason=reason,
            safety_policy=self.safety_policy,
        )
        self._tasks[task_id] = result.task
        self._audit_log.append(result.audit_event)
        return result.task

    def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        tasks = list(self._tasks.values())
        if status is not None:
            tasks = [task for task in tasks if task.status == status]
        return sorted(tasks, key=lambda task: (task.owner, task.title, task.task_id))

    def audit_log(self) -> list[AuditEvent]:
        return list(self._audit_log)
