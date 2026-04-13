# Release v0.1.0

## Summary

`v0.1.0` is the first end-to-end release of Multica Quant Ops.

This release establishes the core V1 operating model:

- deterministic local workflow execution
- explicit agent roles
- auditable task transitions
- paper-trading-only execution path
- operator-facing daily and incident reporting

## Included In This Release

### Workflow engine

- data-quality validation
- signal generation
- backtest gating
- paper-order proposal generation

### Runtime surfaces

- CLI
- in-process JSON API
- HTTP API server
- scheduler

### Safety and reporting

- execution kill-switch support
- regular US market-session gate
- incident summary generation
- audit log output

### Documentation and collaboration

- solution overview
- use cases
- workflow guide
- operations guide
- GitHub issue and PR templates

## Typical Ways To Use v0.1.0

### Manual operator run

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --input examples\sample_request.json
```

### Structured automation run

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --input examples\sample_request.json --json
```

### HTTP mode

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.api.http
```

### Scheduled mode

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.scheduler --input examples\sample_request.json --once
```

## Safety Position

This release does not support live trading.

It is suitable for:

- workflow prototyping
- operator runbooks
- paper-trading process design
- integration experiments around safe execution boundaries

It is not suitable for:

- broker-connected live order placement
- autonomous deployment into a real-money trading path

## Verification

This release was verified with:

- `python -m pytest -q`
- `python -m ruff check .`
- `python -m mypy src`
