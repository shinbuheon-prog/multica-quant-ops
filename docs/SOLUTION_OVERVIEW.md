# Solution Overview

## What This Project Is

Multica Quant Ops is an agent teammate platform for operating a US equities quant workflow with strict safety boundaries.

The current V1 implementation is intentionally narrow:

- validate market data quality
- generate a signal from an approved strategy
- run a backtest gate
- prepare a paper-trading proposal
- produce operator-facing reports and incident summaries

It does not support live trading.

## Problem It Solves

Quant research and operations often degrade into ad hoc scripts, manual checks, and fragile handoffs.

This project introduces a more explicit operating model:

- each step is owned by a named agent role
- task states are auditable
- blocked conditions stop downstream actions
- execution stays paper-only and safety-constrained

## Core Design Principles

- Keep research, backtest, and execution concerns separate.
- Make task transitions visible and reviewable.
- Prefer deterministic local execution over hidden automation.
- Default to blocked behavior when safety checks fail.
- Treat execution as high risk even in paper-trading mode.

## Current System Surfaces

`CLI`
- Fastest way to run the workflow manually.

`In-process JSON API`
- Best for Python integrations that do not need HTTP.

`HTTP server`
- Thin standard-library wrapper over the JSON API.

`Scheduler`
- Daily execution loop that writes timestamped reports.

## End-to-End Workflow

1. `DataAgent` validates snapshot freshness and basic data integrity.
2. `SignalAgent` generates a candidate signal only if data quality passes.
3. `BacktestAgent` evaluates promotion criteria.
4. `OpsAgent` prepares a paper-trading proposal only if the backtest passes and execution safety gates are satisfied.
5. Reporting builds:
   - a full daily report
   - a structured JSON payload
   - an incident summary when triage is needed

## Safety Model

The key execution gates are:

- no live execution support in V1
- no downstream workflow after failed data quality
- no paper execution after failed backtest
- no paper execution outside regular US market session
- kill-switch support in the execution layer

## Operator Outcomes

The workflow ends in one of two broad states:

`successful run`
- signal and backtest are recorded
- a paper order proposal is created

`blocked run`
- blocked stage is explicit
- reason is carried into reports
- incident summary provides recommended next actions

## Recommended Reading Order

1. [Product Requirements](PRD.md)
2. [Architecture](ARCHITECTURE.md)
3. [Safety Policy](SAFETY_POLICY.md)
4. [Use Cases](USE_CASES.md)
5. [Workflow Guide](WORKFLOWS.md)
6. [Operations Guide](OPERATIONS.md)
