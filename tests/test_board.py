import pytest

from multica_quant_ops.agents.registry import AgentRegistry
from multica_quant_ops.execution.safety import ExecutionSafetyPolicy
from multica_quant_ops.models import AgentProfile, TaskKind, TaskStatus
from multica_quant_ops.orchestrator.board import InMemoryTaskBoard


def build_board() -> InMemoryTaskBoard:
    registry = AgentRegistry()
    registry.register(AgentProfile(name="DataAgent", role="data"))
    registry.register(AgentProfile(name="OpsAgent", role="ops"))
    return InMemoryTaskBoard(
        agent_registry=registry,
        safety_policy=ExecutionSafetyPolicy(),
    )


def test_registry_rejects_duplicate_agent_names() -> None:
    registry = AgentRegistry()
    registry.register(AgentProfile(name="DataAgent", role="data"))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(AgentProfile(name="DataAgent", role="data"))


def test_board_creates_and_lists_task() -> None:
    board = build_board()

    task = board.create_task(
        title="Validate premarket snapshot",
        owner="DataAgent",
        kind=TaskKind.DATA_CHECK,
    )

    assert task.owner == "DataAgent"
    assert task.status == TaskStatus.TODO
    assert len(board.list_tasks()) == 1


def test_board_can_reassign_task_to_registered_agent() -> None:
    board = build_board()
    task = board.create_task(
        title="Prepare market open summary",
        owner="DataAgent",
        kind=TaskKind.RESEARCH,
    )

    updated = board.assign_owner(task.task_id, "OpsAgent")

    assert updated.owner == "OpsAgent"


def test_board_transition_records_audit_log() -> None:
    board = build_board()
    task = board.create_task(
        title="Validate close prices",
        owner="DataAgent",
        kind=TaskKind.DATA_CHECK,
    )

    updated = board.transition(
        task_id=task.task_id,
        to_status=TaskStatus.CLAIMED,
        actor="DataAgent",
        reason="Starting daily validation.",
    )

    assert updated.status == TaskStatus.CLAIMED
    assert len(board.audit_log()) == 1
    assert board.audit_log()[0].task_title == "Validate close prices"


def test_board_requires_registered_agents_for_assignment_and_transition() -> None:
    board = build_board()
    task = board.create_task(
        title="Generate signal summary",
        owner="DataAgent",
        kind=TaskKind.SIGNAL,
    )

    with pytest.raises(ValueError, match="Unknown agent"):
        board.assign_owner(task.task_id, "SignalAgent")

    with pytest.raises(ValueError, match="Unknown agent"):
        board.transition(
            task_id=task.task_id,
            to_status=TaskStatus.CLAIMED,
            actor="SignalAgent",
            reason="Attempting unregistered transition.",
        )
