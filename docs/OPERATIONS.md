# Operations Guide

## Purpose

This guide explains how to operate the current V1 surfaces:

- CLI
- in-process JSON API
- HTTP API server
- daily scheduler

The project remains paper-trading only. No live execution path is supported.

## Local workflow

Activate the environment and run the test suite first:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q
```

## CLI operations

Run the default daily workflow:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli
```

Run a workflow from a request file:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --input examples\sample_request.json
```

Write a JSON report:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --input examples\sample_request.json --json
```

Write an operator-focused incident summary:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --stale-data --incident-summary
```

## In-process API operations

Use the in-process API when another Python component needs direct access without HTTP.

```python
from multica_quant_ops.api.service import WorkflowAPI
from multica_quant_ops.cli import build_default_workflow

api = WorkflowAPI(build_default_workflow())
status_code, payload = api.run_daily_workflow(...)
```

## HTTP API operations

Start the HTTP server:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.api.http
```

Healthcheck:

```powershell
curl http://127.0.0.1:8000/health
```

Daily workflow request:

```powershell
curl -X POST http://127.0.0.1:8000/workflows/daily `
  -H "Content-Type: application/json" `
  --data-binary "@examples/sample_request.json"
```

## Scheduler operations

Run the scheduler once and write a timestamped report:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.scheduler --input examples\sample_request.json --once
```

Start the daily loop:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.scheduler --input examples\sample_request.json --time 09:30 --timezone America/New_York
```

Write JSON scheduler reports instead of text:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.scheduler --input examples\sample_request.json --once --json
```

## Same-day ticker preparation

Prepare a same-day paper-trading request and research brief from a ticker:

```powershell
$env:ALPHAVANTAGE_API_KEY="your-key"
powershell -ExecutionPolicy Bypass -File .\ops\prepare-same-day-request.ps1 -Ticker AAPL
```

This flow is intended for paper-trading preparation only.

- it builds a same-day workflow request from market data
- it produces a research brief with current price and workflow readiness
- it does not create a live-trading instruction

## Expected blocked states

`data_quality`
- The market snapshot is stale or invalid.

`backtest`
- Promotion criteria were not met.

`paper_execution`
- Execution safety checks blocked the proposal.
- A common reason is running outside the regular US market session.

## Incident summary

The JSON API payload now includes an `incident_summary` object. The CLI can also emit
an incident-focused text summary when the full daily report is too verbose for triage.

## Time assumptions

- Request timestamps are interpreted from the payload as provided.
- Sample-mode CLI timestamps are built for `America/New_York`.
- Paper execution is blocked outside weekday regular hours from `09:30` to `16:00` in `America/New_York`.

## Operator checks before running

- Confirm the request payload uses the intended symbol and timestamps.
- Confirm market-session timing if paper execution is expected.
- Confirm the report output directory is writable.
- Review blocked-stage and audit-log output before promoting any operational change.

## Incident notes

If a workflow blocks:

1. Check the `blocked_stage`.
2. Review `paper_execution_reason` or data-quality reasons.
3. Re-run with a corrected request payload.
4. Do not bypass the safety policy in source control just to force execution.
