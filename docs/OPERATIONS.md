# 운영 가이드

## 목적

이 문서는 현재 V1 표면을 어떻게 운영하는지 설명합니다.

- CLI
- in-process JSON API
- HTTP API server
- daily scheduler

이 프로젝트는 paper-trading 전용이며 live execution path는 지원하지 않습니다.

## 로컬 실행

환경을 활성화하고 먼저 테스트를 실행합니다.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q
```

## CLI 운영

Run the default daily workflow:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli
```

Run a workflow from a request file:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --input examples\sample_request.json
```

Write a JSON report:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --input examples\sample_request.json --json
```

Write an operator-focused incident summary:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli --stale-data --incident-summary
```

## In-process API 운영

Use the in-process API when another Python component needs direct access without HTTP.

```python
from multica_quant_ops.api.service import WorkflowAPI
from multica_quant_ops.cli import build_default_workflow

api = WorkflowAPI(build_default_workflow())
status_code, payload = api.run_daily_workflow(...)
```

## HTTP API 운영

Start the HTTP server:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.api.http
```

Healthcheck:

```powershell
curl http://127.0.0.1:8000/health
```

Daily workflow request:

```powershell
curl -X POST http://127.0.0.1:8000/workflows/daily `
  -H "Content-Type: application/json" `
  --data-binary "@examples/sample_request.json"
```

## Scheduler 운영

Run the scheduler once and write a timestamped report:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.scheduler --input examples\sample_request.json --once
```

Start the daily loop:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.scheduler --input examples\sample_request.json --time 09:30 --timezone America/New_York
```

Write JSON scheduler reports instead of text:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.scheduler --input examples\sample_request.json --once --json
```

스케줄 실행 후 dashboard export와 텔레그램 알림까지 자동으로 이어가려면:

```powershell
$env:PYTHONPATH="src"
$env:TELEGRAM_BOT_TOKEN="your-bot-token"
$env:TELEGRAM_CHAT_ID="your-chat-id"
python -m multica_quant_ops.scheduler `
  --input examples\sample_request.json `
  --time 09:30 `
  --timezone America/New_York `
  --ops-dir ops `
  --dashboard-output ops\dashboard\dashboard-export.json `
  --telegram-notify `
  --telegram-alert-only
```

이 모드는 실행 후 다음을 자동 수행합니다.

- 일일 리포트 저장
- dashboard export 갱신
- alert 조건 충족 시 텔레그램 전송

## 대시보드 export 운영

Google Sheets 대시보드 갱신용 JSON을 생성하려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\export-dashboard.ps1
```

이 명령은 기본적으로 `ops/dashboard/dashboard-export.json`을 생성합니다.

이 파일은 다음 정보를 포함합니다.

- 종목별 최신 상태
- 최근 batch 실행 이력
- 최근 incident summary 목록
- Alpha Vantage 무료 호출량 상태

Apps Script 연동 절차는 `docs/GAS_DASHBOARD.md`를 참고합니다.

## 텔레그램 알림 운영

대시보드 export를 텔레그램으로 요약 전송하려면:

```powershell
$env:TELEGRAM_BOT_TOKEN="your-bot-token"
$env:TELEGRAM_CHAT_ID="your-chat-id"
powershell -ExecutionPolicy Bypass -File .\ops\notify-telegram.ps1
```

먼저 메시지 형식을 확인만 하려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\notify-telegram.ps1 -DryRun
```

현재 텔레그램 연동은 다음을 보냅니다.

- 전체 상태 요약
- 종목별 상태 상위 몇 개
- 최근 incident headline
- Alpha Vantage 사용량

이 채널은 에이전트들의 자유 대화 로그를 보내는 것이 아니라,
`audit 결과와 운영 요약`을 전달하는 채널입니다.

## 당일 티커 준비

Prepare a same-day paper-trading request and research brief from a ticker:

```powershell
$env:ALPHAVANTAGE_API_KEY="your-key"
powershell -ExecutionPolicy Bypass -File .\ops\prepare-same-day-request.ps1 -Ticker AAPL
```

이 흐름은 paper-trading 준비 전용입니다.

- it builds a same-day workflow request from market data
- it produces a research brief with current price and workflow readiness
- it does not create a live-trading instruction
- it tracks daily Alpha Vantage usage and blocks runs beyond the configured free-mode limit

복수 티커를 한 번에 준비하려면:

```powershell
$env:ALPHAVANTAGE_API_KEY="your-key"
powershell -ExecutionPolicy Bypass -File .\ops\prepare-multi-ticker.ps1 -Tickers AAPL,MSFT,TSLA
```

생성 결과:

- 티커별 request JSON
- 티커별 brief JSON
- 티커별 한국어 operator 리포트
- 전체 비교용 `batch-summary.json`
- 운영자가 빠르게 읽을 수 있는 `batch-summary-ko.txt`

## 예상 차단 상태

`data_quality`
- The market snapshot is stale or invalid.

`backtest`
- Promotion criteria were not met.

`paper_execution`
- Execution safety checks blocked the proposal.
- A common reason is running outside the regular US market session.

## Incident summary

The JSON API payload now includes an `incident_summary` object. The CLI can also emit
an incident-focused text summary when the full daily report is too verbose for triage.

## 시간 가정

- Request timestamps are interpreted from the payload as provided.
- Sample-mode CLI timestamps are built for `America/New_York`.
- Paper execution is blocked outside weekday regular hours from `09:30` to `16:00` in `America/New_York`.

## 실행 전 점검

- Confirm the request payload uses the intended symbol and timestamps.
- Confirm market-session timing if paper execution is expected.
- Confirm the report output directory is writable.
- Review blocked-stage and audit-log output before promoting any operational change.

## 인시던트 대응 메모

If a workflow blocks:

1. Check the `blocked_stage`.
2. Review `paper_execution_reason` or data-quality reasons.
3. Re-run with a corrected request payload.
4. Do not bypass the safety policy in source control just to force execution.
