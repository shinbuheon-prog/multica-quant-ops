# Alpha Vantage Free Mode

## Goal

Use Alpha Vantage's free tier to validate workflow usefulness before upgrading to a premium plan.

This mode is appropriate for:

- local development
- manual paper-trading preparation
- low-frequency ticker checks

It is not appropriate for:

- high-frequency automation
- many-ticker monitoring
- assuming guaranteed realtime US equity data

## How This Repository Uses Free Mode

The same-day ticker preparation flow uses:

- one quote request to build the request
- one daily time-series request to build signal and backtest inputs
- one quote request to generate the final paper-trading prep brief

That means a single same-day preparation run typically consumes about `3` Alpha Vantage calls.

## Daily Limit Guard

This repository includes:

- a file-backed request counter
- a daily limit guard

The guard blocks new calls once the configured daily limit is reached.

Default free-mode limit:

- `25` calls per day

The tracker file is written to:

- `ops/runtime/alpha-vantage-usage.json`

## Operator Workflow

1. Set `ALPHAVANTAGE_API_KEY`.
2. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\prepare-same-day-request.ps1 -Ticker AAPL
```

3. Review the generated brief JSON.
4. Check the usage tracker:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\show-alpha-vantage-usage.ps1
```

## When To Upgrade

Upgrade from free mode when one or more of these become true:

- operators need more than a handful of ticker preparations per day
- scheduler or HTTP automation should run routinely
- delayed or entitlement-limited quote behavior becomes operationally limiting
- the workflow has proven useful enough to justify cleaner market-data guarantees

## Safety Notes

- This mode still feeds a paper-trading preparation workflow only.
- Generated outputs are not live-trading instructions.
- Operators should check quote freshness and plan entitlements before treating the output as same-session ready.
