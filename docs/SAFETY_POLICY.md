# Safety Policy

This project touches a high-risk financial domain. Safety defaults are part of the product.

## Hard rules

- No live trading support in V1.
- No automatic broker writes without explicit human approval.
- No storage of real broker credentials in source-controlled files.
- No strategy promotion without backtest evidence and operator review.
- No downstream execution when data-quality checks fail.

## Operational controls

- kill switch for all execution jobs
- paper-trading mode default
- regular US market-session gate for paper execution
- audit log for every task state transition
- approval step before any execution-mode change

## Engineering rules

- strategy code must be testable without network access
- market sessions and timezone assumptions must be explicit
- external integrations must be wrapped behind interfaces
