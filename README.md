# Multica Quant Ops

Agent teammate platform for operating a US equities quant trading system.

This project is inspired by `multica-ai/multica`, but focused on a narrower operating model:

- turn coding agents into named teammates
- assign research, signal, backtest, data-quality, and operations tasks
- keep trading execution behind strict safety controls

## Version 1 scope

- Research and signal generation
- Backtesting and daily reporting
- Data pipeline health checks
- Paper trading only
- Human approval required before any live-trading capability is introduced

## Project goals

- Treat agents as operators with explicit roles
- Make every task auditable
- Prefer deterministic tests and repeatable runs
- Separate research from execution
- Make unsafe actions impossible by default

## Initial structure

- `docs/PRD.md`: product definition
- `docs/ARCHITECTURE.md`: system design
- `docs/SAFETY_POLICY.md`: financial and operational guardrails
- `docs/ROADMAP.md`: implementation phases
- `AGENTS.md`: project instructions for Codex
- `src/`: application code
- `tests/`: test suite

## Next step

Run Codex inside this folder and start from Phase 0 in `docs/ROADMAP.md`.

## Local setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q
```

## CLI demo

Run the sample daily workflow:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli
```

Trigger a blocked data-quality run:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --stale-data
```

Trigger a blocked backtest run:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --weak-backtest
```

Trigger a blocked paper-execution run outside the regular US market session:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --outside-session
```

Run from a JSON request file:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --input examples\sample_request.json
```

Save the report to a file:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --input examples\sample_request.json --output reports\daily-report.txt
```

Emit a machine-readable JSON report with task and audit details:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --json
```

Time assumptions:

- sample-mode timestamps are interpreted in `America/New_York`
- paper execution is blocked outside regular US market hours (`09:30` to `16:00`, weekdays)

## JSON API surface

The project includes a small in-process JSON API layer for integrations and future HTTP wrapping.

```python
from multica_quant_ops.api.service import WorkflowAPI
from multica_quant_ops.cli import build_default_workflow

api = WorkflowAPI(build_default_workflow())
status_code, payload = api.healthcheck()
workflow_status, workflow_payload = api.run_daily_workflow({...})
```

## HTTP server

Run the built-in HTTP wrapper:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.api.http
```

Available endpoints:

- `GET /health`
- `POST /workflows/daily`
