# Use Cases

## Solo Quant Operator

### Daily pre-market review

Use the scheduler or CLI to validate a prepared request payload before the market session.

Useful surfaces:

- scheduler for routine execution
- CLI for manual replay
- incident summary for quick triage

Typical value:

- stale or malformed data is caught before paper execution is considered
- backtest criteria stay explicit instead of implicit

### Manual strategy check

Run a request file through the CLI or JSON API after changing signal or backtest assumptions.

Useful surfaces:

- CLI with text output for quick reading
- CLI with `--json` for structured inspection

Typical value:

- strategy changes can be inspected without introducing live execution behavior

## Small Quant Team

### Shared operational review

Use the HTTP server as a shared internal surface and archive JSON reports or incident summaries.

Useful surfaces:

- HTTP API for integration
- JSON payloads for downstream tooling
- issue and PR templates for collaboration

Typical value:

- everyone reviews the same blocked stage, audit log, and incident output
- operational decisions become easier to trace

### Change validation before merge

Use the CLI, API, and tests during development. Review PRs with the safety checklist.

Useful surfaces:

- PR template
- bug and feature templates
- deterministic tests and local reports

Typical value:

- behavioral regressions are easier to catch before they affect operations

## Integration Developer

### Python integration without HTTP

Use the in-process `WorkflowAPI` when the caller already runs inside Python and does not need a server boundary.

Useful surfaces:

- `WorkflowAPI.healthcheck()`
- `WorkflowAPI.run_daily_workflow(payload)`

Typical value:

- no extra deployment surface
- structured payloads with incident summary included

### Internal service integration over HTTP

Use the built-in HTTP wrapper when another service needs request/response interaction.

Useful surfaces:

- `GET /health`
- `POST /workflows/daily`

Typical value:

- easy local integration path
- same workflow and safety behavior as CLI and in-process API

## Operator Response Scenarios

### Data-quality failure

What happens:

- workflow blocks at `data_quality`
- no signal, backtest, or paper order is produced

How to use the system:

- inspect data-quality reasons
- read incident summary
- refresh the payload and rerun

### Backtest failure

What happens:

- workflow blocks at `backtest`
- signal may exist, but paper execution does not proceed

How to use the system:

- inspect return and win-rate thresholds
- compare request assumptions with intended strategy behavior

### Paper-execution failure

What happens:

- workflow blocks at `paper_execution`
- common reason is outside-session execution

How to use the system:

- check market-session timing
- review execution safety settings
- rerun only when the safety condition should pass
