# 솔루션 개요

## 이 프로젝트가 하는 일

Multica Quant Ops는 미국 주식 퀀트 워크플로우를 엄격한 safety boundary 안에서 운영하기 위한 agent teammate 플랫폼입니다.

The current V1 implementation is intentionally narrow:

- validate market data quality
- generate a signal from an approved strategy
- run a backtest gate
- prepare a paper-trading proposal
- produce operator-facing reports and incident summaries

현재는 live trading을 지원하지 않습니다.

## 해결하려는 문제

Quant research and operations often degrade into ad hoc scripts, manual checks, and fragile handoffs.

This project introduces a more explicit operating model:

- each step is owned by a named agent role
- task states are auditable
- blocked conditions stop downstream actions
- execution stays paper-only and safety-constrained

## 핵심 설계 원칙

- Keep research, backtest, and execution concerns separate.
- Make task transitions visible and reviewable.
- Prefer deterministic local execution over hidden automation.
- Default to blocked behavior when safety checks fail.
- Treat execution as high risk even in paper-trading mode.

## 현재 시스템 표면

`CLI`
- Fastest way to run the workflow manually.

`In-process JSON API`
- Best for Python integrations that do not need HTTP.

`HTTP server`
- Thin standard-library wrapper over the JSON API.

`Scheduler`
- Daily execution loop that writes timestamped reports.

## End-to-End 워크플로우

1. `DataAgent` validates snapshot freshness and basic data integrity.
2. `SignalAgent` generates a candidate signal only if data quality passes.
3. `BacktestAgent` evaluates promotion criteria.
4. `OpsAgent` prepares a paper-trading proposal only if the backtest passes and execution safety gates are satisfied.
5. Reporting builds:
   - a full daily report
   - a structured JSON payload
   - an incident summary when triage is needed

## Safety 모델

The key execution gates are:

- no live execution support in V1
- no downstream workflow after failed data quality
- no paper execution after failed backtest
- no paper execution outside regular US market session
- kill-switch support in the execution layer

## 운영자 관점 결과

The workflow ends in one of two broad states:

`successful run`
- signal and backtest are recorded
- a paper order proposal is created

`blocked run`
- blocked stage is explicit
- reason is carried into reports
- incident summary provides recommended next actions

## 추천 읽기 순서

1. [Product Requirements](PRD.md)
2. [Architecture](ARCHITECTURE.md)
3. [Safety Policy](SAFETY_POLICY.md)
4. [Use Cases](USE_CASES.md)
5. [Workflow Guide](WORKFLOWS.md)
6. [Operations Guide](OPERATIONS.md)
