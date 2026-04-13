# Product Requirements

## Product

Multica Quant Ops is an agent teammate platform for operating a US equities quant trading workflow.

Inspired by Multica's agent-as-teammate model, the product assigns operational work to named agents instead of one-off prompts.

## Users

- solo operator managing a quant stack
- small quant team
- engineering + research team operating a shared strategy platform

## Core use cases

1. Assign a research task to an agent.
2. Run scheduled data-quality checks before market open.
3. Generate signals from approved strategies.
4. Backtest changes before promotion.
5. Produce a daily operator report.
6. Keep paper-trading actions visible and reviewable.

## Non-goals for V1

- fully autonomous live trading
- derivatives trading
- multi-broker smart routing
- portfolio optimization across many asset classes

## Success criteria

- agents can complete bounded operational tasks end-to-end
- every task has status, logs, and an audit trail
- data-quality failures block downstream tasks
- signal generation and paper execution are reproducible
