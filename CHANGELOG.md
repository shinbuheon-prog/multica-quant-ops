# Changelog

## v0.1.0

Initial public release of Multica Quant Ops.

### Added

- agent-oriented daily workflow for data quality, signal generation, backtesting, and paper execution
- audit-friendly task orchestration and task state transitions
- CLI for text, JSON, and incident-summary output
- in-process JSON API for direct Python integration
- standard-library HTTP API server
- daily scheduler entry point for recurring report generation
- operator incident summary reporting
- market-session execution guardrails for paper execution
- operations, design, workflow, and use-case documentation
- GitHub issue and pull request templates

### Safety

- no live trading support in V1
- data-quality failures block downstream work
- backtest failures block paper execution
- paper execution is blocked outside the regular US market session

### Verification

- `python -m pytest -q`
- `python -m ruff check .`
- `python -m mypy src`
