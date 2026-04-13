from dataclasses import dataclass

from multica_quant_ops.backtest.engine import BacktestResult
from multica_quant_ops.data.quality import DataQualityResult
from multica_quant_ops.execution.safety import ExecutionSafetyPolicy
from multica_quant_ops.strategies.signals import Signal, SignalDirection


@dataclass(frozen=True)
class PaperOrderProposal:
    symbol: str
    side: str
    quantity: int
    rationale: str


def build_paper_order_proposal(
    signal: Signal,
    data_quality: DataQualityResult,
    backtest_result: BacktestResult,
    safety_policy: ExecutionSafetyPolicy,
    quantity: int = 1,
) -> PaperOrderProposal:
    safety_policy.assert_paper_execution_enabled()

    if data_quality.blocks_downstream:
        raise ValueError("Paper execution is blocked by failed data quality checks.")
    if not backtest_result.approved_for_paper_trading:
        raise ValueError("Paper execution is blocked by failed backtest criteria.")
    if signal.direction != SignalDirection.LONG:
        raise ValueError("Paper execution only supports LONG entry proposals in V1.")
    if quantity <= 0:
        raise ValueError("Quantity must be positive.")

    return PaperOrderProposal(
        symbol=signal.symbol,
        side="buy",
        quantity=quantity,
        rationale=signal.rationale,
    )
