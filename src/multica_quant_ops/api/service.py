from dataclasses import fields, is_dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from multica_quant_ops.backtest.engine import BacktestCriteria
from multica_quant_ops.data.quality import DataQualityCheck, PriceSnapshot
from multica_quant_ops.orchestrator.board import InMemoryTaskBoard
from multica_quant_ops.orchestrator.daily_workflow import DailyWorkflowRequest, DailyWorkflowService


def build_request_from_payload(payload: dict[str, Any]) -> DailyWorkflowRequest:
    snapshot_payload = payload["snapshot"]
    quality_payload = payload["quality_check"]
    backtest_payload = payload["backtest_criteria"]
    return DailyWorkflowRequest(
        symbol=payload["symbol"],
        snapshot=PriceSnapshot(
            symbol=snapshot_payload["symbol"],
            as_of=datetime.fromisoformat(snapshot_payload["as_of"]),
            open_price=snapshot_payload["open_price"],
            high_price=snapshot_payload["high_price"],
            low_price=snapshot_payload["low_price"],
            close_price=snapshot_payload["close_price"],
            volume=snapshot_payload["volume"],
        ),
        now=datetime.fromisoformat(payload["now"]),
        quality_check=DataQualityCheck(
            max_age=timedelta(minutes=quality_payload["max_age_minutes"]),
            min_price=quality_payload.get("min_price", 0.01),
            min_volume=quality_payload.get("min_volume", 1),
        ),
        signal_prices=payload["signal_prices"],
        backtest_prices=payload["backtest_prices"],
        backtest_criteria=BacktestCriteria(
            min_total_return=backtest_payload["min_total_return"],
            min_win_rate=backtest_payload["min_win_rate"],
        ),
        quantity=payload.get("quantity", 1),
    )


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {
            field.name: to_jsonable(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, timedelta):
        return int(value.total_seconds() / 60)
    if isinstance(value, Enum):
        return value.value
    return value


def build_workflow_payload(
    request: DailyWorkflowRequest,
    result: Any,
    board: InMemoryTaskBoard,
) -> dict[str, Any]:
    return {
        "request": to_jsonable(request),
        "result": to_jsonable(result),
        "tasks": to_jsonable(board.list_tasks()),
        "audit_log": to_jsonable(board.audit_log()),
    }


class WorkflowAPI:
    def __init__(self, workflow: DailyWorkflowService) -> None:
        self.workflow = workflow

    def healthcheck(self) -> tuple[int, dict[str, Any]]:
        return 200, {"status": "ok", "service": "multica-quant-ops"}

    def run_daily_workflow(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        try:
            request = build_request_from_payload(payload)
        except (KeyError, TypeError, ValueError) as exc:
            return 400, {"error": f"Invalid request payload: {exc}"}

        result = self.workflow.run(request)
        return 200, build_workflow_payload(request, result, self.workflow.data_agent.board)
