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
