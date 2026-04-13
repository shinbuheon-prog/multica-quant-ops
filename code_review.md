# Code Review Guide

## Correctness

- Does the change solve the requested problem?
- Are data gaps, stale data, and time-window edge cases handled?
- Are async jobs and retries safe?

## Trading risk

- Can this change place, modify, or cancel real orders?
- Is paper-trading mode preserved?
- Is there an approval gate for risky actions?
- Is there a clear kill switch?

## Testing

- Was a regression or behavior test added?
- Are tests deterministic?
- Are time and market-calendar assumptions explicit?

## Maintainability

- Is orchestration separate from strategy logic?
- Is there unnecessary coupling to one broker or data vendor?
- Are audit logs and operator-visible states preserved?
