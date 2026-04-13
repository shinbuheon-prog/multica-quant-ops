# 하루 운영 예시 시나리오

## 목적

이 문서는 실제 운영자가 하루 동안 이 시스템을 어떻게 쓰는지 예시 흐름으로 설명합니다.

가정:

- Alpha Vantage 무료 모드 사용
- watchlist는 `AAPL, MSFT, TSLA`
- 운영 목적은 `paper-trading 준비`
- Google Sheets 대시보드를 함께 사용

## 08:50 KST / 장 시작 전 준비

운영자는 먼저 다음을 확인합니다.

- Python 환경이 활성화되어 있는지
- `ALPHAVANTAGE_API_KEY`가 설정되어 있는지
- 오늘 watchlist가 맞는지
- Google Sheets `Config` 시트 값이 맞는지

이 시점의 목표는 실행 준비이지,
매수/매도 결정을 내리는 것이 아닙니다.

## 09:00 KST / batch 준비 실행

운영자는 batch를 실행합니다.

```powershell
$env:ALPHAVANTAGE_API_KEY="your-key"
powershell -ExecutionPolicy Bypass -File .\ops\prepare-multi-ticker.ps1 -Tickers AAPL,MSFT,TSLA
```

이 실행으로 생성되는 핵심 파일:

- 티커별 operator 리포트
- `batch-summary-ko.txt`
- Alpha Vantage usage tracker

운영자는 먼저 `batch-summary-ko.txt`를 읽습니다.

## 09:02 KST / batch 요약 1차 판단

예를 들어 이런 상황이 나올 수 있습니다.

- `AAPL`: `backtest`
- `MSFT`: `backtest`
- `TSLA`: `backtest`

이 경우 운영자 해석은 다음과 같습니다.

- 시세 수집은 되었음
- 전략 승격 기준은 통과하지 못했음
- 오늘은 강한 실행 후보가 없을 가능성이 큼

즉, 이 단계의 판단은
`바로 실행`이 아니라 `오늘은 관찰 모드`에 가깝습니다.

## 09:05 KST / 단일 티커 상세 확인

운영자는 한 종목을 더 자세히 봅니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\prepare-same-day-request.ps1 -Ticker AAPL
```

여기서 보는 것은 다음입니다.

- `blocked_stage`
- operator 리포트의 `관찰 포인트`
- operator 리포트의 `다음 액션`

예를 들어 `backtest`라면:

- 실행 후보로 올리지 않음
- 전략 기준 검토는 별도 시간에 함
- 오늘 운영에서는 보류

## 09:10 KST / 대시보드 export 생성

운영자는 현재 결과를 대시보드로 보냅니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\export-dashboard.ps1
```

생성 파일:

- `ops/dashboard/dashboard-export.json`

이 파일을 Google Drive에 반영합니다.

## 09:12 KST / Google Sheets 대시보드 확인

운영자는 Google Sheets에서 다음을 봅니다.

### `Overview`

- 표시 종목 수
- 차단 종목 수
- 남은 호출 수

이 숫자로 오늘 운영 강도를 조절합니다.

### `Dashboard`

`dashboard_status_filter = blocked_only`로 두면
차단 종목만 빠르게 볼 수 있습니다.

운영자는 여기서:

- blocked stage
- operator 리포트 요약
- 운영 헤드라인

을 확인합니다.

### `Incidents`

우선순위 `높음`부터 확인합니다.

예:

- `data_quality`
- `paper_execution`

이 둘은 즉시 재검토 대상입니다.

`backtest`는 보통 `중간` 우선순위로 보고,
오늘 전략 승격 보류로 해석합니다.

## 10:00 KST / 추가 실행 여부 판단

운영자는 Alpha Vantage 사용량을 봅니다.

예:

- `21/25`
- 남은 호출 `4`

이 수준이면 대량 batch는 멈추고,
꼭 필요한 종목만 단일 실행으로 확인합니다.

즉, 운영 판단은:

- `대시보드로 상태 확인`
- `무료 호출 한도 관리`
- `문제 종목만 선별 점검`

입니다.

## 15:30 KST / 마감 전 정리

운영자는 다음을 확인합니다.

- 오늘 batch 결과가 대시보드에 반영됐는지
- incident가 있었는지
- 내일 watchlist 후보가 무엇인지
- premium 전환 필요성이 있는지

이 시점에서 남기는 메모 예시:

- `AAPL/MSFT/TSLA 모두 backtest 차단`
- `데이터 품질 문제는 없음`
- `무료 한도 사용량 21/25`
- `내일도 3종목 watchlist 유지`

## 이 시나리오의 핵심

이 시스템의 핵심은
`자동으로 매수/매도 결정을 대신하는 것`이 아닙니다.

핵심은 다음입니다.

- Codex가 운영 체계를 만들고 개선
- Python이 에이전트 팀원 워크플로우를 실행
- operator가 blocked stage와 다음 액션을 빠르게 해석
- Google Sheets가 매일 보는 운영 화면 역할 수행

즉, 운영자는 폴더를 뒤지기보다
`요약 -> 문제 종목 -> 상세 점검` 순서로 일하게 됩니다.
