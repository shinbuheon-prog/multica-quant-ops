# Multica Quant Ops

Agent teammate platform for operating a US equities quant trading system.

This project is inspired by `multica-ai/multica`, but focused on a narrower operating model:

- turn coding agents into named teammates
- assign research, signal, backtest, data-quality, and operations tasks
- keep trading execution behind strict safety controls

## V1 scope

- Research and signal generation
- Backtesting and daily reporting
- Data pipeline health checks
- Paper trading only
- Human approval required before any live-trading capability is introduced

## Current surfaces

- CLI for manual runs
- JSON API for in-process integrations
- HTTP server for local service-style access
- scheduler for recurring daily runs
- reporting with incident summary output

## Project goals

- Treat agents as operators with explicit roles
- Make every task auditable
- Prefer deterministic tests and repeatable runs
- Separate research from execution
- Make unsafe actions impossible by default

## Local setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q
```

## Quick start

Run the sample daily workflow:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli
```

Run the HTTP server:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.api.http
```

Run the scheduler once:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.scheduler --input examples\sample_request.json --once
```

## Docs

- [Changelog](CHANGELOG.md)
- [Release v0.1.0](docs/RELEASE_v0.1.0.md)
- [Solution Overview](docs/SOLUTION_OVERVIEW.md)
- [Use Cases](docs/USE_CASES.md)
- [Workflow Guide](docs/WORKFLOWS.md)
- [Product Requirements](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Safety Policy](docs/SAFETY_POLICY.md)
- [Operations Guide](docs/OPERATIONS.md)
- [Roadmap](docs/ROADMAP.md)
