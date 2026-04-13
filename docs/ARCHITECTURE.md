# Architecture

## Guiding idea

Borrow the Multica concept of agents as teammates, but reduce the initial technical surface area.

V1 uses a Python-first architecture:

- orchestration layer for tasks and agents
- market data adapters in read-only mode
- strategy engine for signal generation
- backtest service
- paper-trading executor
- reporting and audit logging

## Proposed modules

- `src/multica_quant_ops/orchestrator/`
- `src/multica_quant_ops/agents/`
- `src/multica_quant_ops/api/`
- `src/multica_quant_ops/data/`
- `src/multica_quant_ops/strategies/`
- `src/multica_quant_ops/backtest/`
- `src/multica_quant_ops/execution/`
- `src/multica_quant_ops/reporting/`
- `src/multica_quant_ops/risk/`

## Initial runtime model

- `ResearchAgent`: investigates strategy ideas and code tasks
- `DataAgent`: validates market data freshness and completeness
- `SignalAgent`: computes candidate signals
- `BacktestAgent`: runs evaluation jobs
- `OpsAgent`: prepares reports and incident summaries

## Safety boundaries

- read-only market data first
- paper broker adapter only in V1
- live trading adapter excluded by default
- hard kill switch in execution layer
- operator approval required to promote risky capabilities
