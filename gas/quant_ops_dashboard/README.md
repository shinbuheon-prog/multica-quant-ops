# GAS Dashboard

이 폴더의 `Code.gs`는 `dashboard-export.json` 파일을 읽어 Google Sheets 대시보드를 갱신하는 Apps Script 예시입니다.

기본 사용 흐름:

1. 로컬에서 `ops/export-dashboard.ps1`를 실행해 `dashboard-export.json`을 생성합니다.
2. 생성된 JSON 파일을 Google Drive에 업로드하거나, Google Drive 동기화 폴더로 바로 출력합니다.
3. 새 Apps Script 프로젝트를 만들고 `Code.gs` 내용을 붙여 넣습니다.
4. 스프레드시트의 `Config` 시트 `B2` 셀에 업로드한 JSON 파일의 Drive 파일 ID를 입력합니다.
5. 시트 메뉴 `Quant Ops -> 대시보드 새로고침`을 실행합니다.

생성되는 시트:

- `Overview`
- `Dashboard`
- `Batch Runs`
- `Incidents`
- `Config`
