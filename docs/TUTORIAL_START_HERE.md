# 튜토리얼: Codex 주식 에이전트 팀원 시작하기

## 이 문서의 목표

이 문서는 처음 이 프로젝트를 잡는 사용자가
`Codex -> same-day 실행 -> batch 실행 -> 대시보드 반영`까지 한 번에 따라 하도록 돕는 빠른 시작 튜토리얼입니다.

결과적으로 다음 상태를 만드는 것이 목표입니다.

- 티커 기준 당일 준비 리포트 생성
- 복수 티커 batch 요약 생성
- `dashboard-export.json` 생성
- Google Sheets에서 운영 현황 확인

## 1. 로컬 환경 준비

프로젝트 루트에서 다음을 실행합니다.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q
```

정상이라면 테스트가 통과합니다.

새 PowerShell 탭이나 재부팅 후에는 아래 재진입 스크립트를 먼저 써도 됩니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\bootstrap-session.ps1
powershell -ExecutionPolicy Bypass -File .\ops\show-status.ps1
```

## 2. Alpha Vantage 키 설정

무료 모드 기준으로 먼저 시작합니다.

```powershell
$env:ALPHAVANTAGE_API_KEY="your-key"
```

무료 모드에서는 호출 수가 작기 때문에
처음에는 티커 수를 적게 유지하는 것이 좋습니다.

## 3. 단일 티커 same-day 준비

예를 들어 `AAPL`로 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\prepare-same-day-request.ps1 -Ticker AAPL
```

이 실행이 끝나면 `ops/runtime/` 아래에 다음이 생깁니다.

- request JSON
- brief JSON
- 한국어 operator 리포트
- Alpha Vantage usage tracker

여기서 먼저 확인할 것은 두 가지입니다.

- `blocked_stage`
- 한국어 operator 리포트의 `다음 액션`

## 4. 복수 티커 batch 준비

다음으로 여러 종목을 함께 준비합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\prepare-multi-ticker.ps1 -Tickers AAPL,MSFT,TSLA
```

이 실행이 끝나면 `ops/runtime/batch-<timestamp>/` 아래에 다음이 생깁니다.

- 티커별 request JSON
- 티커별 brief JSON
- 티커별 한국어 operator 리포트
- `batch-summary.json`
- `batch-summary-ko.txt`

처음에는 `batch-summary-ko.txt`부터 보는 것이 가장 편합니다.

## 5. 대시보드 export 생성

이제 여러 산출물을 Google Sheets에서 보기 위해 export를 만듭니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\export-dashboard.ps1
```

결과 파일:

- `ops/dashboard/dashboard-export.json`

이 파일에는 다음이 합쳐져 있습니다.

- 종목별 최신 상태
- batch 실행 요약
- incident 목록
- Alpha Vantage 사용량

## 6. Google Drive에 반영

두 방법 중 하나를 사용합니다.

1. `dashboard-export.json`을 Google Drive에 수동 업로드
2. Google Drive Desktop 동기화 폴더를 export 위치로 사용

실제로는 2번이 더 편합니다.

## 7. Google Sheets + Apps Script 연결

1. Google Sheets에서 새 스프레드시트를 만듭니다.
2. `확장 프로그램 -> Apps Script`로 이동합니다.
3. `gas/quant_ops_dashboard/Code.gs` 내용을 붙여 넣습니다.
4. 저장 후 시트로 돌아옵니다.
5. `Config` 시트 `B2`에 Drive 파일 ID를 넣습니다.
6. 메뉴 `Quant Ops -> 대시보드 새로고침`을 실행합니다.

## 8. Config 시트 기본 추천값

처음에는 다음처럼 두는 것이 좋습니다.

- `watchlist_tickers` = `AAPL,MSFT,TSLA`
- `dashboard_status_filter` = `all`
- `dashboard_max_rows` = `10`
- `batch_runs_max_rows` = `10`
- `incidents_max_rows` = `10`

문제가 있는 종목만 빠르게 보려면:

- `dashboard_status_filter` = `blocked_only`

## 9. 무엇을 보면 되는가

처음 운영자는 다음 순서로 보면 됩니다.

1. `Overview`
   - 오늘 종목 수
   - 차단 종목 수
   - 남은 API 호출 수
2. `Dashboard`
   - 종목별 blocked stage
   - operator 리포트 요약
3. `Incidents`
   - 우선순위
   - 헤드라인
4. `Batch Runs`
   - 최근 batch가 전체적으로 어땠는지

## 10. 첫 운영에서 자주 보는 상황

### `backtest`

가장 흔한 차단입니다.

의미:
- 시세는 읽었지만 승격 기준을 못 넘음

운영자 행동:
- 오늘은 관찰 위주로 둠
- 전략 기준을 억지로 완화하지 않음

### `data_quality`

의미:
- 스냅샷이 오래됐거나 값이 이상함

운영자 행동:
- 다시 시세를 확인하고 재실행

### `paper_execution`

의미:
- 장 시간 또는 실행 safety에 걸림

운영자 행동:
- 세션 시간부터 확인

## 11. 매일 반복할 최소 루틴

1. same-day 또는 batch 실행
2. operator 리포트 확인
3. `export-dashboard.ps1` 실행
4. Google Sheets 새로고침
5. blocked 종목만 점검

## 12. 다음에 읽을 문서

- [운영 체크리스트](OPERATIONS_CHECKLIST.md)
- [Codex Team + Dashboard Design](CODEX_TEAM_DASHBOARD_DESIGN.md)
- [GAS Dashboard Guide](GAS_DASHBOARD.md)
