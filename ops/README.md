# Ops Pack

This folder is the operator-facing runtime pack for starting paper-trading workflow operations.

## What It Includes

- `requests/daily-paper-request.json`
- `run-daily.ps1`
- `run-incident-summary.ps1`
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
3. Run `run-daily.ps1` for a manual workflow execution.
4. If triage is needed, run `run-incident-summary.ps1`.
5. If you want recurring execution, run `start-scheduler.ps1`.

## Notes

- Reports are written into `ops/reports/`.
- Incident summaries are written into `ops/incidents/`.
- Update request payload timestamps and prices before a real paper-ops run.
