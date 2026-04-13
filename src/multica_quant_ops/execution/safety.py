from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

from multica_quant_ops.models import TaskKind


@dataclass(frozen=True)
class ExecutionSafetyPolicy:
    paper_execution_enabled: bool = True
    kill_switch_enabled: bool = False
    live_execution_enabled: bool = False
    enforce_regular_market_session: bool = True
    market_timezone: str = "America/New_York"
    regular_session_start: time = time(hour=9, minute=30)
    regular_session_end: time = time(hour=16, minute=0)

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

    def normalize_market_time(self, at: datetime) -> datetime:
        market_zone = ZoneInfo(self.market_timezone)
        if at.tzinfo is None:
            return at.replace(tzinfo=market_zone)
        return at.astimezone(market_zone)

    def is_regular_market_session(self, at: datetime) -> bool:
        market_time = self.normalize_market_time(at)
        if market_time.weekday() >= 5:
            return False

        current_time = market_time.time()
        return self.regular_session_start <= current_time < self.regular_session_end

    def assert_paper_execution_allowed(self, at: datetime) -> None:
        self.assert_paper_execution_enabled()
        if self.enforce_regular_market_session and not self.is_regular_market_session(at):
            raise ValueError("Paper execution is blocked outside the regular US market session.")
