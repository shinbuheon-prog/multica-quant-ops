# Multica Quant Ops Instructions

## Mission

Build an agent-operated platform for US equities quant research and paper-trading operations.

## Operating constraints

- Do not add live order execution by default.
- Treat broker writes, credential handling, and money movement as high-risk operations.
- Prefer simulation, backtesting, and read-only market data integrations first.
- Every behavior change must come with tests or a clear explanation of why tests are blocked.

## Working style

- Read the relevant files before editing.
- Prefer small, reviewable changes.
- Keep agent orchestration logic separate from trading strategy logic.
- Keep research, backtest, and execution modules isolated.
- Avoid introducing hidden automation that can place or modify real orders.

## Verification

- Test command: `pytest -q`
- Lint command: `ruff check .`
- Type check command: `mypy src`
- Build command: `python -m compileall src`

Run the smallest relevant checks first. If behavior changes, add or update tests.

## Done when

- The requested behavior works.
- Relevant tests were added or updated.
- Relevant checks were run and reported.
- The change respects `docs/SAFETY_POLICY.md`.

## Review rules

- Follow `code_review.md`.
- For trading or broker-related changes, explicitly review failure modes and kill-switch behavior.
