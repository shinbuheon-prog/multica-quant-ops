# Ops Pack

이 폴더는 paper-trading 운영을 시작할 때 바로 사용할 수 있는 operator 실행 팩입니다.

## 포함 파일

- `requests/daily-paper-request.json`
- `run-daily.ps1`
- `run-incident-summary.ps1`
- `prepare-same-day-request.ps1`
- `prepare-multi-ticker.ps1`
- `show-alpha-vantage-usage.ps1`
- `start-http-api.ps1`
- `start-scheduler.ps1`

## 운영 모드

이 프로젝트는 현재도 paper-trading 전용입니다.

- no live broker connectivity
- no live order placement
- no automatic bypass of execution safety gates

## 추천 시작 순서

1. Activate the Python environment.
2. Review `requests/daily-paper-request.json`.
3. For same-day preparation, run `prepare-same-day-request.ps1 -Ticker AAPL`.
4. 여러 종목을 함께 준비하려면 `prepare-multi-ticker.ps1 -Tickers AAPL,MSFT,TSLA`를 실행합니다.
5. `run-daily.ps1`로 수동 워크플로우를 실행합니다.
6. triage가 필요하면 `run-incident-summary.ps1`를 실행합니다.
7. 반복 실행이 필요하면 `start-scheduler.ps1`를 실행합니다.

## 참고

- Reports are written into `ops/reports/`.
- Incident summaries are written into `ops/incidents/`.
- Same-day generated request and brief files are written into `ops/runtime/`.
- Alpha Vantage usage counts are tracked in `ops/runtime/alpha-vantage-usage.json`.
- Update request payload timestamps and prices before a real paper-ops run.
- `prepare-same-day-request.ps1` requires `ALPHAVANTAGE_API_KEY`.
- Per Alpha Vantage's official docs, quote freshness depends on your plan. Default quote behavior is not realtime unless you have the required entitlement.
