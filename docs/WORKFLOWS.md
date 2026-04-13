# Workflow Guide

## Common Request Shape

All main surfaces share the same request payload shape.

```json
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
```

## Manual CLI Workflow

Run a normal workflow:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --input examples\sample_request.json
```

Use when:

- one operator wants immediate feedback
- text output is easier to scan than JSON

## Structured JSON Workflow

Run the same workflow and capture machine-readable output:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --input examples\sample_request.json --json
```

The JSON output includes:

- `request`
- `result`
- `incident_summary`
- `tasks`
- `audit_log`

## Incident Triage Workflow

Force a blocked run and emit only the incident summary:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --stale-data --incident-summary
```

Use when:

- the operator wants the shortest useful failure summary
- the full daily report is too verbose for first-pass triage

## HTTP Workflow

Start the server:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.api.http
```

Then call:

```powershell
curl -X POST http://127.0.0.1:8000/workflows/daily `
  -H "Content-Type: application/json" `
  --data-binary "@examples/sample_request.json"
```

Use when:

- another process or service needs the workflow over HTTP
- structured integration matters more than direct Python access

## Scheduled Workflow

Run once immediately:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.scheduler --input examples\sample_request.json --once
```

Run daily:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.scheduler --input examples\sample_request.json --time 09:30 --timezone America/New_York
```

Use when:

- the same request shape should be executed on a fixed cadence
- reports need to be persisted with timestamps

## Choosing The Right Surface

`CLI`
- best for local manual execution

`CLI --json`
- best for local automation and quick structured output

`CLI --incident-summary`
- best for operator triage

`WorkflowAPI`
- best for Python-to-Python integration

`HTTP server`
- best for service-style integration

`Scheduler`
- best for recurring daily runs with saved reports
