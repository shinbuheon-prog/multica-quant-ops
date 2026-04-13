from dataclasses import dataclass
from enum import Enum


class SignalDirection(str, Enum):
    LONG = "long"
    FLAT = "flat"


@dataclass(frozen=True)
class Signal:
    symbol: str
    direction: SignalDirection
    confidence: float
    rationale: str
