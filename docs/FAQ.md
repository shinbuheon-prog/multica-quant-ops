# FAQ

## 이 시스템은 실거래를 하나요?

아니요. 현재는 `paper-trading 준비`와 운영 관제까지만 지원합니다.
live trading은 설계상 비활성 상태입니다.

## Codex는 여기서 무슨 역할을 하나요?

Codex는 코드 수정, 운영 스크립트 작성, 테스트 실행, 문서 정리, 워크플로우 실행을 담당합니다.
즉, 운영 체계를 실제로 만들고 다듬는 엔지니어링 실행자 역할입니다.

## 에이전트 팀원은 어떤 순서로 움직이나요?

기본 순서는 다음과 같습니다.

1. `DataAgent`
2. `SignalAgent`
3. `BacktestAgent`
4. `OpsAgent`

앞 단계에서 막히면 다음 단계로 내려가지 않습니다.

## `blocked_stage`는 왜 중요한가요?

이 값이 운영 판단의 출발점이기 때문입니다.

- `data_quality`: 데이터 문제
- `backtest`: 승격 기준 미달
- `paper_execution`: 장 시간 또는 실행 safety 문제

운영자는 먼저 이 값을 보고 다음 행동을 정합니다.

## `backtest`가 나오면 매수하면 안 되는 건가요?

이 시스템 기준에서는 `승격 보류`입니다.
즉, 실행 후보로 올리지 않는 것이 기본 해석입니다.

## `paper_execution`이 나오면 무슨 뜻인가요?

주로 미국 정규장 시간 밖이거나 execution safety 조건에 걸렸다는 뜻입니다.
먼저 세션 시간과 안전 조건을 다시 확인해야 합니다.

## Alpha Vantage 무료 키로 팀 운영이 가능한가요?

작은 규모의 저빈도 운영 검증은 가능합니다.
하지만 일일 호출 수가 작기 때문에 많은 티커를 반복 실행하는 운영에는 빠르게 한계가 옵니다.

## 그래서 무료 모드에서 무엇을 조심해야 하나요?

- 티커 수를 적게 유지
- batch를 과하게 반복하지 않기
- 남은 호출 수를 대시보드에서 같이 확인
- `20/25` 이상이면 추가 실행 줄이기

## 왜 Google Sheets 대시보드를 붙였나요?

운영자가 매번 `ops/runtime/` 아래 파일을 직접 열어보는 불편을 줄이기 위해서입니다.
대시보드는 결과를 요약해서 빠르게 보게 하는 역할입니다.

## GAS가 거래 판단도 대신하나요?

아니요. GAS는 실행 엔진이 아니라 보기 계층입니다.

- Python: 실행과 판단
- GAS: 정리와 표시

## 텔레그램 연동을 붙이면 에이전트들이 나눈 대화도 보이나요?

지금 구조에서는 아닙니다.
현재 시스템이 남기는 것은 `자유 대화 로그`가 아니라 다음과 같은 운영 결과입니다.

- task 상태 변화
- audit log
- blocked stage
- incident summary
- operator 리포트

즉, 텔레그램은 `에이전트들이 무엇을 했고 어떤 결과를 냈는지`는 보여주지만,
사람처럼 주고받은 채팅 대화를 재생하는 구조는 아닙니다.

## `dashboard-export.json`은 왜 필요한가요?

여러 파일을 Google Sheets가 바로 읽기 어렵기 때문에,
Python이 이를 한 번에 읽기 좋은 형태로 묶어 주는 중간 산출물입니다.

## Google Sheets에서 어떤 탭부터 봐야 하나요?

추천 순서는 다음입니다.

1. `Overview`
2. `Dashboard`
3. `Incidents`
4. `Batch Runs`

## `watchlist_tickers`는 언제 쓰나요?

전체 종목이 아니라 특정 감시 대상만 보려 할 때 씁니다.
예: `AAPL,MSFT,TSLA`

## `dashboard_status_filter`는 언제 쓰나요?

빠르게 상태를 좁혀 보고 싶을 때 씁니다.

- `all`
- `ready_only`
- `blocked_only`

## 운영자가 가장 먼저 읽어야 하는 파일은 무엇인가요?

단일 실행이면 한국어 operator 리포트,
배치 실행이면 `batch-summary-ko.txt`입니다.

## 어떤 문서부터 읽으면 되나요?

처음 시작:
- [Start Here Tutorial](TUTORIAL_START_HERE.md)

매일 운영:
- [Operations Checklist](OPERATIONS_CHECKLIST.md)

전체 구조 이해:
- [Codex Team + Dashboard Design](CODEX_TEAM_DASHBOARD_DESIGN.md)

대시보드 설정:
- [GAS Dashboard Guide](GAS_DASHBOARD.md)
