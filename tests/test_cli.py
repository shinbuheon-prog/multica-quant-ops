import subprocess
import sys
from pathlib import Path


def test_cli_success_report() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "multica_quant_ops.cli"],
        check=True,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src"},
    )

    assert "Blocked stage: none" in result.stdout
    assert "Paper order: buy 2 AAPL" in result.stdout


def test_cli_stale_data_report() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "multica_quant_ops.cli", "--stale-data"],
        check=True,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src"},
    )

    assert "Blocked stage: data_quality" in result.stdout
    assert "Paper order: not created" in result.stdout


def test_cli_can_load_input_file_and_write_output() -> None:
    runtime_dir = Path("test-artifacts")
    runtime_dir.mkdir(exist_ok=True)
    input_path = runtime_dir / "request.json"
    output_path = runtime_dir / "report.txt"
    input_path.write_text(
        """
{
  "symbol": "AAPL",
  "now": "2026-04-13T09:35:00",
  "snapshot": {
    "symbol": "AAPL",
    "as_of": "2026-04-13T09:34:00",
    "open_price": 200.0,
    "high_price": 202.0,
    "low_price": 199.0,
    "close_price": 201.0,
    "volume": 1000
  },
  "quality_check": {
    "max_age_minutes": 5
  },
  "signal_prices": [100.0, 101.0, 103.0],
  "backtest_prices": [100.0, 101.0, 103.0, 104.0, 106.0],
  "backtest_criteria": {
    "min_total_return": 0.01,
    "min_win_rate": 0.5
  },
  "quantity": 2
}
""".strip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "multica_quant_ops.cli",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "src"},
    )

    assert "Report written to" in result.stdout
    assert "Paper order: buy 2 AAPL" in output_path.read_text(encoding="utf-8")
