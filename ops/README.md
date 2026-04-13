# Ops Pack

이 폴더는 paper-trading 운영을 시작할 때 바로 사용할 수 있는 operator 실행 팩입니다.

## 포함 파일

- `requests/daily-paper-request.json`
- `run-daily.ps1`
- `run-incident-summary.ps1`
- `bootstrap-session.ps1`
- `prepare-same-day-request.ps1`
- `prepare-multi-ticker.ps1`
- `export-dashboard.ps1`
- `notify-telegram.ps1`
- `show-status.ps1`
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
2. 새 탭이나 재부팅 후에는 `bootstrap-session.ps1`와 `show-status.ps1`를 먼저 실행합니다.
3. Review `requests/daily-paper-request.json`.
4. For same-day preparation, run `prepare-same-day-request.ps1 -Ticker AAPL`.
5. 여러 종목을 함께 준비하려면 `prepare-multi-ticker.ps1 -Tickers AAPL,MSFT,TSLA`를 실행합니다.
6. `run-daily.ps1`로 수동 워크플로우를 실행합니다.
7. triage가 필요하면 `run-incident-summary.ps1`를 실행합니다.
8. 반복 실행이 필요하면 `start-scheduler.ps1`를 실행합니다.
9. 스프레드시트 현황판을 갱신하려면 `export-dashboard.ps1`를 실행합니다.
10. 텔레그램 알림을 보내려면 `notify-telegram.ps1`를 실행합니다.

## 참고

- Reports are written into `ops/reports/`.
- Incident summaries are written into `ops/incidents/`.
- Same-day generated request and brief files are written into `ops/runtime/`.
- Same-day 단일/배치 실행은 한국어 operator 리포트 텍스트도 함께 생성합니다.
- 배치 실행은 `ops/runtime/<timestamp>/batch-summary-ko.txt` 형식의 운영 요약을 남깁니다.
- 대시보드 export는 기본적으로 `ops/dashboard/dashboard-export.json`에 생성됩니다.
- 텔레그램 알림은 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 환경변수를 사용합니다.
- `start-scheduler.ps1`는 스케줄 실행 후 dashboard export와 텔레그램 알림까지 자동으로 이어집니다.
- Alpha Vantage usage counts are tracked in `ops/runtime/alpha-vantage-usage.json`.
- Update request payload timestamps and prices before a real paper-ops run.
- `prepare-same-day-request.ps1` requires `ALPHAVANTAGE_API_KEY`.
- Per Alpha Vantage's official docs, quote freshness depends on your plan. Default quote behavior is not realtime unless you have the required entitlement.
