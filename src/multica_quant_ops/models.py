from dataclasses import dataclass
from enum import Enum


class TaskStatus(str, Enum):
    TODO = "todo"
    CLAIMED = "claimed"
    RUNNING = "running"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"


class TaskKind(str, Enum):
    RESEARCH = "research"
    DATA_CHECK = "data_check"
    SIGNAL = "signal"
    BACKTEST = "backtest"
    PAPER_EXECUTION = "paper_execution"
    LIVE_EXECUTION = "live_execution"


@dataclass(frozen=True)
class AgentProfile:
    name: str
    role: str
    can_execute_live_orders: bool = False


@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    owner: str
    kind: TaskKind = TaskKind.RESEARCH
    status: TaskStatus = TaskStatus.TODO
