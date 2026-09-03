from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class DataQualityStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True)
class PriceSnapshot:
    symbol: str
    as_of: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int


@dataclass(frozen=True)
class DataQualityCheck:
    max_age: timedelta
    min_price: float = 0.01
    min_volume: int = 1


@dataclass(frozen=True)
class DataQualityResult:
    symbol: str
    status: DataQualityStatus
    reasons: tuple[str, ...]

    @property
    def blocks_downstream(self) -> bool:
        return self.status == DataQualityStatus.FAIL


def evaluate_snapshot(
    snapshot: PriceSnapshot,
    now: datetime,
    check: DataQualityCheck,
) -> DataQualityResult:
    reasons: list[str] = []
    age = now - snapshot.as_of

    if age > check.max_age:
        reasons.append("snapshot is stale")
    if snapshot.volume < check.min_volume:
        reasons.append("volume is below minimum threshold")
    if min(snapshot.open_price, snapshot.high_price, snapshot.low_price, snapshot.close_price) < check.min_price:
        reasons.append("price is below minimum threshold")
    if snapshot.high_price < snapshot.low_price:
        reasons.append("high price is lower than low price")
    if snapshot.open_price > snapshot.high_price or snapshot.open_price < snapshot.low_price:
        reasons.append("open price is outside low/high range")
    if snapshot.close_price > snapshot.high_price or snapshot.close_price < snapshot.low_price:
        reasons.append("close price is outside low/high range")

    status = DataQualityStatus.FAIL if reasons else DataQualityStatus.PASS
    return DataQualityResult(symbol=snapshot.symbol, status=status, reasons=tuple(reasons))


# ---------------------------------------------------------------------------
# Fundamentals-level magnitude anomaly detection
#
# Everything above this line only ever looked at OHLCV price snapshots. It
# has no way to catch a balance-sheet or income-statement figure that jumps
# an implausible amount quarter over quarter -- exactly the kind of thing
# the Cowork fundamentals pipeline caught by hand for GOOGL's 2026-06-30
# total-equity figure (see docs/FUNDAMENTALS_INTEGRATION.md, sections 1 and
# 3). These checks port that manual habit into a deterministic, testable
# rule so it runs automatically for every ticker instead of depending on
# someone noticing.
#
# Neither check below claims to explain *why* a figure looks wrong -- that
# still needs a human (or a Scout-agent research pass) reading the primary
# source. The point is only to flag "look at this" reliably, per this
# project's "지어내지 않는다" principle: never silently accept an
# unreconciled number.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FundamentalsSnapshot:
    symbol: str
    metric: str
    period_end: datetime
    value: float


@dataclass(frozen=True)
class FundamentalsQualityCheck:
    max_relative_change: float = 0.25
    """Flag a period-over-period change larger than this fraction (0.25 = 25%)."""

    min_relative_change_for_flag: float = 0.0
    """Below this fraction, a change is never flagged even if `max_relative_change`
    would otherwise be exceeded due to a tiny base value blowing up the ratio."""


@dataclass(frozen=True)
class FundamentalsQualityResult:
    symbol: str
    metric: str
    status: DataQualityStatus
    reasons: tuple[str, ...]
    relative_change: float | None = None

    @property
    def blocks_downstream(self) -> bool:
        return self.status == DataQualityStatus.FAIL


def evaluate_fundamentals_change(
    current: FundamentalsSnapshot,
    previous: FundamentalsSnapshot,
    check: FundamentalsQualityCheck,
) -> FundamentalsQualityResult:
    """Flag an implausible period-over-period jump in a single fundamentals metric.

    This is deliberately generic (any metric, any two periods) rather than
    hard-coded to equity, so the same function covers revenue, net income,
    total assets, etc. Sign flips (profit to loss, positive to negative
    equity) are always flagged regardless of the relative-change threshold,
    since a percentage change across a sign flip is not meaningful.
    """
    if current.symbol != previous.symbol or current.metric != previous.metric:
        raise ValueError("evaluate_fundamentals_change requires the same symbol and metric.")
    if previous.period_end >= current.period_end:
        raise ValueError("`previous` must precede `current`.")

    reasons: list[str] = []
    relative_change: float | None = None

    sign_flip = (current.value > 0 > previous.value) or (current.value < 0 < previous.value)
    if sign_flip:
        reasons.append(
            f"{current.metric} flipped sign between periods "
            f"({previous.value:,.2f} -> {current.value:,.2f})"
        )
    elif previous.value == 0:
        if current.value != 0:
            reasons.append(
                f"{current.metric} moved from 0 to {current.value:,.2f}; "
                "no prior-period base to compare against, review manually"
            )
    else:
        relative_change = (current.value - previous.value) / abs(previous.value)
        if (
            abs(relative_change) >= check.min_relative_change_for_flag
            and abs(relative_change) > check.max_relative_change
        ):
            reasons.append(
                f"{current.metric} changed {relative_change:+.1%} period-over-period "
                f"({previous.value:,.2f} -> {current.value:,.2f}), exceeding the "
                f"{check.max_relative_change:.0%} threshold"
            )

    status = DataQualityStatus.FAIL if reasons else DataQualityStatus.PASS
    return FundamentalsQualityResult(
        symbol=current.symbol,
        metric=current.metric,
        status=status,
        reasons=tuple(reasons),
        relative_change=relative_change,
    )


def evaluate_equity_rollforward(
    symbol: str,
    beginning_equity: float,
    net_income: float,
    ending_equity: float,
    other_comprehensive_income: float = 0.0,
    buybacks: float = 0.0,
    dividends: float = 0.0,
    other_equity_adjustments: float = 0.0,
    tolerance_relative: float = 0.03,
) -> FundamentalsQualityResult:
    """Reconcile ending equity against the standard roll-forward identity.

    expected_ending = beginning + net_income + OCI - buybacks - dividends
                       + other_adjustments (issuances, stock comp, etc.)

    `tolerance_relative` is expressed as a fraction of beginning equity, to
    absorb normal rounding and minor adjustments not modeled above (stock
    compensation, small M&A effects). This is the automated counterpart to
    the manual reconciliation that flagged GOOGL's 2026-06-30 total-equity
    figure as unexplained by ~$50-67B even under generous assumptions.
    """
    expected_ending = (
        beginning_equity
        + net_income
        + other_comprehensive_income
        - buybacks
        - dividends
        + other_equity_adjustments
    )
    gap = ending_equity - expected_ending
    tolerance = abs(beginning_equity) * tolerance_relative

    reasons: list[str] = []
    if abs(gap) > tolerance:
        reasons.append(
            f"equity roll-forward does not reconcile: expected ending equity "
            f"{expected_ending:,.2f}, reported {ending_equity:,.2f} "
            f"(unexplained gap {gap:+,.2f}, tolerance ±{tolerance:,.2f})"
        )

    status = DataQualityStatus.FAIL if reasons else DataQualityStatus.PASS
    return FundamentalsQualityResult(
        symbol=symbol,
        metric="total_equity_rollforward",
        status=status,
        reasons=tuple(reasons),
        relative_change=(gap / abs(beginning_equity)) if beginning_equity else None,
    )
