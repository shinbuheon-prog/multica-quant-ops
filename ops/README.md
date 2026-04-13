# Ops Pack

This folder is the operator-facing runtime pack for starting paper-trading workflow operations.

## What It Includes

- `requests/daily-paper-request.json`
- `run-daily.ps1`
- `run-incident-summary.ps1`
- `prepare-same-day-request.ps1`
- `show-alpha-vantage-usage.ps1`
- `start-http-api.ps1`
- `start-scheduler.ps1`

## Operating Mode

This project remains paper-trading only.

- no live broker connectivity
- no live order placement
- no automatic bypass of execution safety gates

## Typical Start Sequence

1. Activate the Python environment.
2. Review `requests/daily-paper-request.json`.
3. For same-day preparation, run `prepare-same-day-request.ps1 -Ticker AAPL`.
4. Run `run-daily.ps1` for a manual workflow execution.
5. If triage is needed, run `run-incident-summary.ps1`.
6. If you want recurring execution, run `start-scheduler.ps1`.

## Notes

- Reports are written into `ops/reports/`.
- Incident summaries are written into `ops/incidents/`.
- Same-day generated request and brief files are written into `ops/runtime/`.
- Alpha Vantage usage counts are tracked in `ops/runtime/alpha-vantage-usage.json`.
- Update request payload timestamps and prices before a real paper-ops run.
- `prepare-same-day-request.ps1` requires `ALPHAVANTAGE_API_KEY`.
- Per Alpha Vantage's official docs, quote freshness depends on your plan. Default quote behavior is not realtime unless you have the required entitlement.
