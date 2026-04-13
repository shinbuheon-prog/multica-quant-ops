from multica_quant_ops.models import AgentProfile, Task, TaskStatus


def test_agent_profile_defaults_to_no_live_order_capability() -> None:
    agent = AgentProfile(name="SignalAgent", role="signal")

    assert agent.can_execute_live_orders is False


def test_task_defaults_to_todo_status() -> None:
    task = Task(task_id="task-1", title="Generate premarket report", owner="OpsAgent")

    assert task.status == TaskStatus.TODO
