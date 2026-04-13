# GAS 대시보드 가이드

## 목적

이 문서는 `ops/` 산출물을 Google Sheets에서 바로 확인하기 위한 대시보드 흐름을 설명합니다.

핵심 아이디어는 단순합니다.

- 로컬 Python이 `dashboard-export.json`을 생성합니다.
- Google Apps Script가 이 JSON을 읽어 스프레드시트 시트를 갱신합니다.
- 운영자는 폴더를 직접 열지 않고도 종목 상태와 인시던트를 한 화면에서 확인합니다.

## 포함 요소

- Python export 생성기: `src/multica_quant_ops/dashboard_export.py`
- PowerShell wrapper: `ops/export-dashboard.ps1`
- Apps Script 예시: `gas/quant_ops_dashboard/Code.gs`

## 권장 시트 구성

- `Overview`: 오늘 종목 수, 차단 수, Alpha Vantage 호출 수
- `Dashboard`: 종목별 현재가, 시그널, blocked stage, 운영 헤드라인
- `Batch Runs`: 최근 batch 실행 이력
- `Incidents`: 최근 incident summary 목록
- `Config`: Google Drive 파일 ID, 마지막 새로고침 시각, watchlist/표시 옵션

## 로컬 export 생성

기본 경로로 export 생성:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\export-dashboard.ps1
```

특정 경로로 export 생성:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\export-dashboard.ps1 `
  -OutputPath "C:\path\to\dashboard-export.json"
```

기본 출력 경로는 `ops/dashboard/dashboard-export.json`입니다.

## Google Drive 연결 방식

다음 두 방식 중 하나를 추천합니다.

1. 생성된 `dashboard-export.json` 파일을 Google Drive에 수동 업로드
2. Google Drive Desktop 동기화 폴더를 `-OutputPath`로 직접 지정

실무상으로는 두 번째가 더 편합니다. export를 덮어쓰기만 하면 GAS가 같은 파일 ID를 계속 읽을 수 있기 때문입니다.

## Apps Script 설정

1. Google Sheets에서 새 스프레드시트를 만듭니다.
2. `확장 프로그램 -> Apps Script`로 이동합니다.
3. `gas/quant_ops_dashboard/Code.gs` 내용을 붙여 넣습니다.
4. 저장 후 스프레드시트로 돌아갑니다.
5. `Config` 시트의 `B2` 셀에 `dashboard-export.json`의 Google Drive 파일 ID를 입력합니다.
6. 상단 메뉴 `Quant Ops -> 대시보드 새로고침`을 실행합니다.

초기 렌더링 후 색상이나 표가 흐트러졌다면 `Quant Ops -> 서식 다시 적용`을 실행하면 됩니다.

## Config 시트 옵션

기본 키는 다음과 같습니다.

- `dashboard_export_file_id`: Google Drive JSON 파일 ID
- `last_refresh_at`: 마지막 새로고침 시각
- `watchlist_tickers`: 쉼표 구분 감시 티커 목록
- `dashboard_max_rows`: Dashboard 시트 최대 표시 행 수
- `batch_runs_max_rows`: Batch Runs 시트 최대 표시 행 수
- `incidents_max_rows`: Incidents 시트 최대 표시 행 수

예시:

- `watchlist_tickers` = `AAPL,MSFT,TSLA`
- `dashboard_max_rows` = `10`

`watchlist_tickers`를 비워 두면 export에 들어 있는 전체 종목을 표시합니다.

## 대시보드에 보이는 내용

`Overview`
- export 생성 시각
- 표시 종목 수
- 준비 완료 종목 수
- 차단 종목 수
- 전체 종목 수
- Alpha Vantage 사용량과 남은 호출 수
- 준비 상태 요약 차트

`Dashboard`
- 티커
- 생성 시각
- 현재가
- 시그널 방향과 신뢰도
- 페이퍼 실행 준비 여부
- 차단 단계
- 운영 헤드라인
- 남은 API 호출 수
- 한국어 operator 리포트 요약
- 상태별 행 강조 색상
  - 준비 가능: 연녹색
  - 차단 발생: 연적색
  - 남은 호출 5 이하: 연노랑

`Batch Runs`
- batch 이름
- 생성 시각
- 종목 수
- 준비 완료 수
- 차단 수
- 운영 요약
- 차단 수 기준 행 강조 색상

`Incidents`
- 최근 incident summary 파일의 헤드라인
- 세부 요약
- 원본 파일 경로

## 운영 루틴 추천

1. 당일 same-day 또는 batch 실행
2. `ops/export-dashboard.ps1` 실행
3. 필요하면 `Config` 시트에서 watchlist와 최대 행 수 조정
4. Google Sheets에서 `대시보드 새로고침`
5. `Dashboard`와 `Incidents` 시트 확인

## 주의 사항

- 이 대시보드는 live trading 도구가 아니라 paper-trading 운영 관제용입니다.
- Alpha Vantage 무료 모드를 쓰는 경우, 대시보드에도 남은 호출 수를 같이 확인해야 합니다.
- Google Apps Script는 로컬 파일을 직접 읽지 못합니다. 반드시 Google Drive에 올라간 JSON 파일을 읽도록 구성해야 합니다.
