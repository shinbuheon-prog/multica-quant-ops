from datetime import date
from pathlib import Path

from multica_quant_ops.data.providers.base import MarketQuote
from multica_quant_ops.same_day_batch import main


class BatchFakeProvider:
    def __init__(self) -> None:
        self.last_usage_snapshot = None

    def fetch_quote(self, symbol: str) -> MarketQuote:
        return MarketQuote(
            symbol=symbol,
            latest_trading_day=date(2026, 4, 13),
            open_price=200.0,
            high_price=202.0,
            low_price=199.0,
            price=201.0,
            previous_close=198.5,
            volume=1000,
            change_percent=0.0126,
        )

    def fetch_daily_closes(self, symbol: str, limit: int) -> list[float]:
        closes = [190.0, 192.0, 194.0, 196.0, 198.0, 200.0, 201.0]
        return closes[-limit:]


def test_same_day_batch_writes_operator_reports(monkeypatch) -> None:
    runtime_dir = Path("test-artifacts") / "same-day-batch"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "test-key")
    monkeypatch.setattr(
        "multica_quant_ops.same_day_batch.AlphaVantageMarketDataProvider.build_free_mode",
        lambda **kwargs: BatchFakeProvider(),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "same_day_batch",
            "--tickers",
            "AAPL,MSFT",
            "--quantity",
            "1",
            "--output-dir",
            str(runtime_dir),
            "--usage-file",
            str(runtime_dir / "usage.json"),
        ],
    )

    assert main() == 0
    assert (runtime_dir / "AAPL-operator-report-ko.txt").exists()
    assert (runtime_dir / "MSFT-operator-report-ko.txt").exists()
    assert (runtime_dir / "batch-summary.json").exists()
    assert (runtime_dir / "batch-summary-ko.txt").exists()
