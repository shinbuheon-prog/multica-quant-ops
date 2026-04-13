from dataclasses import dataclass
from datetime import datetime

from multica_quant_ops.agents.backtest_agent import BacktestAgentService
from multica_quant_ops.agents.data_agent import DataAgentService
from multica_quant_ops.agents.ops_agent import OpsAgentService
from multica_quant_ops.agents.signal_agent import SignalAgentService
from multica_quant_ops.backtest.engine import BacktestCriteria, BacktestResult
from multica_quant_ops.data.quality import DataQualityCheck, DataQualityResult, PriceSnapshot
from multica_quant_ops.execution.paper import PaperOrderProposal
from multica_quant_ops.models import TaskStatus
from multica_quant_ops.strategies.signals import Signal


@dataclass(frozen=True)
class DailyWorkflowRequest:
    symbol: str
    snapshot: PriceSnapshot
    now: datetime
    quality_check: DataQualityCheck
    signal_prices: list[float]
    backtest_prices: list[float]
    backtest_criteria: BacktestCriteria
    quantity: int = 1


@dataclass(frozen=True)
class DailyWorkflowResult:
    data_quality_result: DataQualityResult
    signal: Signal | None
    backtest_result: BacktestResult | None
    paper_order: PaperOrderProposal | None
    blocked_stage: str | None


class DailyWorkflowService:
    def __init__(
        self,
        data_agent: DataAgentService,
        signal_agent: SignalAgentService,
        backtest_agent: BacktestAgentService,
        ops_agent: OpsAgentService,
    ) -> None:
        self.data_agent = data_agent
        self.signal_agent = signal_agent
        self.backtest_agent = backtest_agent
        self.ops_agent = ops_agent

    def run(self, request: DailyWorkflowRequest) -> DailyWorkflowResult:
        data_task = self.data_agent.create_quality_check_task(request.symbol)
        self.data_agent.board.transition(
            data_task.task_id,
            TaskStatus.CLAIMED,
            "DataAgent",
            "Claiming daily data quality task.",
        )
        data_run = self.data_agent.run_quality_check(
            task_id=data_task.task_id,
            actor="DataAgent",
            snapshot=request.snapshot,
            now=request.now,
            check=request.quality_check,
        )
        if data_run.result.blocks_downstream:
            return DailyWorkflowResult(
                data_quality_result=data_run.result,
                signal=None,
                backtest_result=None,
                paper_order=None,
                blocked_stage="data_quality",
            )

        signal_task = self.signal_agent.create_signal_task(request.symbol)
        self.signal_agent.board.transition(
            signal_task.task_id,
            TaskStatus.CLAIMED,
            "SignalAgent",
            "Claiming daily signal task.",
        )
        signal_run = self.signal_agent.run_signal_task(
            task_id=signal_task.task_id,
            actor="SignalAgent",
            symbol=request.symbol,
            prices=request.signal_prices,
            data_quality=data_run.result,
        )

        backtest_task = self.backtest_agent.create_backtest_task(request.symbol)
        self.backtest_agent.board.transition(
            backtest_task.task_id,
            TaskStatus.CLAIMED,
            "BacktestAgent",
            "Claiming daily backtest task.",
        )
        backtest_run = self.backtest_agent.run_backtest_task(
            task_id=backtest_task.task_id,
            actor="BacktestAgent",
            symbol=request.symbol,
            prices=request.backtest_prices,
            criteria=request.backtest_criteria,
        )
        if not backtest_run.result.approved_for_paper_trading:
            return DailyWorkflowResult(
                data_quality_result=data_run.result,
                signal=signal_run.signal,
                backtest_result=backtest_run.result,
                paper_order=None,
                blocked_stage="backtest",
            )

        paper_task = self.ops_agent.create_paper_execution_task(request.symbol)
        self.ops_agent.board.transition(
            paper_task.task_id,
            TaskStatus.CLAIMED,
            "OpsAgent",
            "Claiming daily paper execution task.",
        )
        paper_run = self.ops_agent.run_paper_execution_task(
            task_id=paper_task.task_id,
            actor="OpsAgent",
            signal=signal_run.signal,
            data_quality=data_run.result,
            backtest_result=backtest_run.result,
            quantity=request.quantity,
        )

        return DailyWorkflowResult(
            data_quality_result=data_run.result,
            signal=signal_run.signal,
            backtest_result=backtest_run.result,
            paper_order=paper_run.proposal,
            blocked_stage=None,
        )
