# 운영 체크리스트

## 목적

이 문서는 실제 운영자가 매일 확인할 항목만 짧게 정리한 체크리스트입니다.

## 장 시작 전

- Python 환경이 활성화되어 있는지 확인
- `ALPHAVANTAGE_API_KEY`가 설정되어 있는지 확인
- Discord를 쓸 경우 `DISCORD_WEBHOOK_URL`이 설정되어 있는지 확인
- 오늘 watchlist 티커가 맞는지 확인
- Alpha Vantage 남은 호출 수를 확인
- Google Sheets `Config` 시트 값이 맞는지 확인

## 단일 티커 실행 전

- 티커가 맞는지 확인
- 실행 목적이 `paper-trading 준비`인지 확인
- live trading으로 오해할 수 있는 문구나 절차가 없는지 확인

실행:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\prepare-same-day-request.ps1 -Ticker AAPL
```

## 복수 티커 실행 전

- batch에 넣을 티커 수가 무료 호출 한도 안에 드는지 확인
- 불필요한 종목이 섞이지 않았는지 확인

실행:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\prepare-multi-ticker.ps1 -Tickers AAPL,MSFT,TSLA
```

## 실행 직후

- `blocked_stage`를 먼저 확인
- 한국어 operator 리포트의 `다음 액션`을 확인
- `batch-summary-ko.txt`를 먼저 읽고 전체 상태를 파악
- 남은 호출 수가 위험 구간인지 확인

## blocked stage별 체크

### `data_quality`

- 스냅샷 시각이 오래되지 않았는지 확인
- 가격/거래량이 비정상적이지 않은지 확인
- 데이터가 정상이면 재실행

### `backtest`

- 오늘은 승격 보류로 판단
- 기준 미달 상태에서 억지 승격하지 않음
- 필요 시 나중에 전략 기준 별도 검토

### `paper_execution`

- 미국 정규장 시간인지 확인
- execution safety 조건을 확인
- 안전 조건이 맞지 않으면 재실행하지 않음

## 대시보드 갱신

실행:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\export-dashboard.ps1
```

그 다음:

- Google Drive에 JSON 반영 확인
- Google Sheets에서 `Quant Ops -> 대시보드 새로고침`
- `Overview`, `Dashboard`, `Incidents` 확인
- 필요하면 `notify-discord.ps1 -AlertOnly`로 운영 채널 알림 전송

## Google Sheets 확인 포인트

### `Overview`

- 표시 종목 수
- 차단 종목 수
- 남은 호출 수
- 현재 상태 필터

### `Dashboard`

- `blocked_only`로 보면 문제 종목만 빠르게 확인 가능
- `ready_only`로 보면 준비 가능한 종목만 확인 가능
- operator 리포트 요약과 헤드라인 확인

### `Incidents`

- `높음` 우선순위부터 확인
- `중간`은 backtest 보류로 해석
- `정보`는 참고용

## 무료 Alpha Vantage 운영 체크

- 오늘 사용량이 `20/25` 이상이면 추가 실행을 줄임
- 남은 호출이 `5` 이하이면 batch 실행을 멈추고 필요한 종목만 수동 확인
- 무료 모드 검증 단계에서는 low-frequency 운영을 유지

## 하지 말아야 할 것

- blocked 상태를 무시하고 live order처럼 해석하지 않기
- safety gate를 끄기 위해 소스를 임의 수정하지 않기
- 무료 호출 한도를 무시하고 대량 batch를 반복하지 않기
- operator 리포트를 개인화 투자 자문으로 해석하지 않기

## 하루 마감 전

- 오늘 batch 결과를 대시보드에 반영했는지 확인
- Discord 알림 채널을 쓴 경우 오늘 blocked 상태가 필요한 사람에게 공유됐는지 확인
- incident가 있었으면 원인과 다음 액션을 메모
- 내일 watchlist 후보를 정리
- 필요하면 premium 전환이 필요한지 usage를 검토
