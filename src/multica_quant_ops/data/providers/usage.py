import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class ProviderUsageSnapshot:
    date: str
    used_calls: int
    daily_limit: int

    @property
    def remaining_calls(self) -> int:
        return max(0, self.daily_limit - self.used_calls)


class DailyCallLimitExceededError(ValueError):
    pass


class FileBackedUsageTracker:
    def __init__(self, path: Path, daily_limit: int) -> None:
        self.path = path
        self.daily_limit = daily_limit

    def snapshot(self, now: datetime) -> ProviderUsageSnapshot:
        payload = self._load()
        current_date = now.date().isoformat()
        used_calls = int(payload.get(current_date, 0))
        return ProviderUsageSnapshot(
            date=current_date,
            used_calls=used_calls,
            daily_limit=self.daily_limit,
        )

    def reserve_call(self, now: datetime) -> ProviderUsageSnapshot:
        payload = self._load()
        current_date = now.date().isoformat()
        used_calls = int(payload.get(current_date, 0))
        if used_calls >= self.daily_limit:
            raise DailyCallLimitExceededError(
                f"Alpha Vantage free-mode daily limit reached for {current_date}: "
                f"{used_calls}/{self.daily_limit} calls used."
            )

        payload[current_date] = used_calls + 1
        self._save(payload)
        return ProviderUsageSnapshot(
            date=current_date,
            used_calls=used_calls + 1,
            daily_limit=self.daily_limit,
        )

    def _load(self) -> dict[str, int]:
        if not self.path.exists():
            return {}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Provider usage tracker file is malformed.")
        return {str(key): int(value) for key, value in payload.items()}

    def _save(self, payload: dict[str, int]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
