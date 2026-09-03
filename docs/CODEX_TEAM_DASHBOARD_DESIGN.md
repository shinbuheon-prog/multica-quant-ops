> **Deprecated (2026-09-03, docs/FUNDAMENTALS_INTEGRATION.md 9-2절/Phase 10).** 실제
> 운영은 이 문서가 설명하는 GAS 대시보드가 아니라 기존 Cowork CSV 기반 시트를 씁니다.
> 이 문서는 저장소 히스토리로만 남깁니다.

# Codex 주식 에이전트 팀원 + GAS 대시보드 설계도

## 목적

이 문서는 `Codex`를 활용해 미국 주식 paper-trading 워크플로우를 운영하고,
그 결과를 `Google Sheets + Apps Script` 대시보드로 관리하는 전체 구조를 한 번에 설명합니다.

대상 독자는 다음과 같습니다.

- Codex로 주식 에이전트 팀원을 운영하려는 사용자
- 로컬 산출물을 스프레드시트에서 한 번에 보고 싶은 운영자
- CLI, API, 스케줄러, GAS가 어떻게 연결되는지 빠르게 이해하고 싶은 사용자

## 한 문장 요약

Codex가 로컬에서 에이전트 팀원 워크플로우를 실행하고, Python이 운영 결과를 파일로 남기며,
그 파일을 다시 `dashboard-export.json`으로 묶어 Google Sheets 대시보드에서 확인하는 구조입니다.

## 전체 구조

```text
Codex / Operator
  -> CLI / same-day / batch / scheduler
  -> agent workflow 실행
  -> ops/runtime, ops/reports, ops/incidents 산출물 생성
  -> dashboard_export.py
  -> ops/dashboard/dashboard-export.json
  -> Google Drive
  -> Google Apps Script
  -> Google Sheets Dashboard
```

## 구성 요소

### 1. Codex

Codex는 이 프로젝트에서 다음 역할을 담당합니다.

- 코드 작성과 수정
- 운영 스크립트 추가
- 테스트와 정적 검사 실행
- same-day / batch / scheduler 워크플로우 실행
- 문서와 운영 절차 정리

즉, Codex는 단순 코드 생성기가 아니라
`에이전트 팀원 운영 체계를 계속 보강하는 엔지니어링 실행자` 역할을 합니다.

### 2. 주식 에이전트 팀원

현재 워크플로우에는 역할이 분리된 에이전트가 있습니다.

- `DataAgent`
  - 시세 스냅샷 품질 확인
  - stale data, 가격 이상, 거래량 이상 탐지

- `SignalAgent`
  - 승인된 전략 기준으로 방향성과 신뢰도 계산

- `BacktestAgent`
  - 승격 기준 충족 여부 판단
  - 기준 미달 시 downstream 차단

- `OpsAgent`
  - paper execution 제안 생성
  - 장 시간, execution safety, kill-switch 조건 점검

이 구조의 핵심은 각 단계가 분리되어 있고,
어느 단계에서 막혔는지가 명확히 드러난다는 점입니다.

### 3. Python 실행 표면

현재 운영 표면은 다음과 같습니다.

- `CLI`
  - 수동 실행과 빠른 확인에 적합

- `same_day`
  - 티커 기준으로 당일 request/brief/operator report 생성

- `same_day_batch`
  - 여러 티커를 한 번에 준비

- `HTTP API`
  - 외부 서비스형 연동용

- `Scheduler`
  - 반복 실행용

- `dashboard_export`
  - 여러 산출물을 대시보드용 JSON으로 통합

## 운영 데이터 흐름

### 1. 실행 입력

입력은 두 갈래입니다.

- 샘플 또는 수동 request JSON
- Alpha Vantage 기반 same-day 시세 입력

same-day 흐름에서는 티커를 주면 Python이 다음을 자동 생성합니다.

- request JSON
- brief JSON
- 한국어 operator 리포트

batch 흐름에서는 위 산출물이 종목별로 만들어지고,
추가로 `batch-summary.json`, `batch-summary-ko.txt`가 생성됩니다.

### 2. 실행 결과 파일

주요 산출물 위치는 다음과 같습니다.

- `ops/runtime/`
  - same-day / batch 산출물
  - usage tracker

- `ops/reports/`
  - 일일 전체 리포트

- `ops/incidents/`
  - incident summary

- `ops/dashboard/`
  - Google Sheets용 `dashboard-export.json`

### 3. 대시보드 통합

`src/multica_quant_ops/dashboard_export.py`가 여러 산출물을 모아
하나의 JSON으로 정리합니다.

포함되는 정보:

- 종목별 최신 상태
- 현재가, 시그널, blocked stage
- operator report 요약
- 최근 batch 실행 이력
- 최근 incident 목록
- Alpha Vantage 사용량과 남은 호출 수

## Google Sheets + GAS 역할

Google Apps Script는 로컬 Python 실행을 대신하지 않습니다.
대신 `운영 현황을 보기 좋게 재구성하는 뷰 계층` 역할을 합니다.

역할은 다음과 같습니다.

- Google Drive의 `dashboard-export.json` 읽기
- 시트 탭 자동 갱신
- 상태별 색상 적용
- `Overview` 차트 생성
- watchlist, 상태 필터, 최대 행 수 같은 표시 옵션 적용

즉, 구조적으로는:

- Python = 실행/판단/산출물 생성
- GAS = 가시화/필터링/운영자 UX

## 시트 설계

### `Overview`

요약 지표를 보여줍니다.

- 표시 종목 수
- 준비 완료 종목 수
- 차단 종목 수
- 전체 종목 수
- 현재 상태 필터
- Alpha Vantage 사용량과 남은 호출 수

### `Dashboard`

종목별 운영 메인 화면입니다.

- 티커
- 현재가
- 시그널
- 페이퍼 실행 준비 여부
- 차단 단계
- 운영 헤드라인
- 남은 호출 수
- 한국어 operator 리포트 요약

### `Batch Runs`

최근 batch 실행 이력을 모아 봅니다.

- batch 이름
- 생성 시각
- 준비 완료 수
- 차단 수
- 운영 요약

### `Incidents`

최근 문제 상황을 우선순위와 함께 봅니다.

- 우선순위
- 헤드라인
- 세부 요약
- 원본 경로

### `Config`

표시 제어용 시트입니다.

- `dashboard_export_file_id`
- `watchlist_tickers`
- `dashboard_status_filter`
- `dashboard_max_rows`
- `batch_runs_max_rows`
- `incidents_max_rows`

## 운영 루틴

추천 운영 루틴은 다음과 같습니다.

1. 장 시작 전 또는 장중에 same-day / batch 실행
2. 필요 시 incident summary 확인
3. `ops/export-dashboard.ps1` 실행
4. JSON 파일을 Google Drive에 반영
5. Google Sheets에서 `대시보드 새로고침`
6. `Dashboard`, `Incidents`, `Batch Runs` 확인

이렇게 하면 운영자가 매번 폴더를 열어 파일을 찾지 않아도 됩니다.

## Alpha Vantage 무료 모드와의 관계

무료 모드에서는 호출 수가 매우 제한적이므로
대시보드에 usage 상태를 반드시 포함해야 합니다.

현재 설계에서는 다음을 함께 노출합니다.

- 오늘 사용량
- 일일 한도
- 남은 호출 수

따라서 운영자는
`종목 상태`와 `API 소모 상태`를 한 화면에서 같이 볼 수 있습니다.

## 왜 이 구조가 실무적으로 유용한가

이 구조의 장점은 세 가지입니다.

### 1. 실행과 표시를 분리

Python 워크플로우와 GAS 대시보드를 분리했기 때문에,
실행 로직을 건드리지 않고도 운영 화면을 개선할 수 있습니다.

### 2. 파일 기반이라 추적 가능

중간 산출물이 파일로 남기 때문에,
문제가 생겨도 어느 시점에 어떤 결과가 나왔는지 추적하기 쉽습니다.

### 3. 점진적 고도화가 가능

현재는 paper-trading 관제 수준이지만,
나중에는 다음으로 확장할 수 있습니다.

- 더 정교한 watchlist 뷰
- Slack/이메일 알림
- Google Sheets 버튼 기반 새로고침
- premium market data 전환
- 운영 지표 누적 추세 차트

## 현재 한계

현재 설계에는 분명한 한계도 있습니다.

- live trading은 지원하지 않음
- Google Apps Script는 로컬 파일을 직접 읽지 못함
- Google Drive 파일 반영 단계가 필요함
- Apps Script는 보기/정리용이지 거래 판단 엔진이 아님
- 무료 Alpha Vantage는 팀 운영 규모가 커지면 금방 한도에 걸릴 수 있음

## 추천 읽기 순서

1. [Solution Overview](SOLUTION_OVERVIEW.md)
2. [Workflow Guide](WORKFLOWS.md)
3. [Operations Guide](OPERATIONS.md)
4. [GAS Dashboard Guide](GAS_DASHBOARD.md)
5. [Alpha Vantage Free Mode](ALPHAVANTAGE_FREE_MODE.md)

## 결론

이 프로젝트의 운영 설계는 다음 한 줄로 정리할 수 있습니다.

`Codex가 에이전트 팀원 워크플로우를 실행하고, Python이 결과를 파일로 남기며, GAS 대시보드가 그 결과를 운영자가 즉시 판단할 수 있는 화면으로 재구성한다.`
