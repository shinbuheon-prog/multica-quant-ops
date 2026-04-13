# Multica Quant Ops

미국 주식 퀀트 트레이딩 워크플로우를 paper-trading 기준으로 운영하기 위한 에이전트 팀원 플랫폼입니다.

이 프로젝트는 `multica-ai/multica`의 agent teammate 개념을 참고했지만, 현재는 더 좁고 안전한 운영 범위에 집중합니다.

- 코딩 에이전트를 역할이 분명한 팀원으로 둡니다.
- research, signal, backtest, data-quality, operations 태스크를 분리합니다.
- 트레이딩 실행은 강한 safety control 뒤에 둡니다.

## V1 범위

- 리서치와 시그널 생성
- 백테스트와 일일 리포트
- 데이터 품질 점검
- paper trading 전용
- live trading 기능은 사람 승인 전까지 도입하지 않음

## 현재 제공 표면

- 수동 실행용 CLI
- Python 내부 연동용 JSON API
- 로컬 서비스형 연동용 HTTP 서버
- 반복 실행용 스케줄러
- incident summary를 포함한 리포팅

## 목표

- 에이전트를 역할이 분명한 운영 주체로 다룹니다.
- 모든 태스크가 감사 가능하도록 만듭니다.
- 결정적 테스트와 반복 가능한 실행을 우선합니다.
- research와 execution을 분리합니다.
- unsafe action은 기본적으로 불가능하게 둡니다.

## 로컬 실행 준비

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q
```

## 빠른 시작

샘플 일일 워크플로우 실행:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.cli
```

HTTP 서버 실행:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.api.http
```

스케줄러 1회 실행:

```powershell
$env:PYTHONPATH="src"
python -m multica_quant_ops.scheduler --input examples\sample_request.json --once
```

운영용 스크립트 팩 사용:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\run-daily.ps1
```

대시보드 export 생성:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\export-dashboard.ps1
```

티커 기준 same-day paper request 준비:

```powershell
$env:ALPHAVANTAGE_API_KEY="your-key"
powershell -ExecutionPolicy Bypass -File .\ops\prepare-same-day-request.ps1 -Ticker AAPL
```

복수 티커 batch 준비:

```powershell
$env:ALPHAVANTAGE_API_KEY="your-key"
powershell -ExecutionPolicy Bypass -File .\ops\prepare-multi-ticker.ps1 -Tickers AAPL,MSFT,TSLA
```

이 실행은 티커별 JSON/한국어 리포트와 함께 `batch-summary-ko.txt` 운영 요약도 생성합니다.

## 문서

- [Ops Pack](ops/README.md)
- [Changelog](CHANGELOG.md)
- [Release v0.1.0](docs/RELEASE_v0.1.0.md)
- [Alpha Vantage Free Mode](docs/ALPHAVANTAGE_FREE_MODE.md)
- [GAS Dashboard Guide](docs/GAS_DASHBOARD.md)
- [Solution Overview](docs/SOLUTION_OVERVIEW.md)
- [Use Cases](docs/USE_CASES.md)
- [Workflow Guide](docs/WORKFLOWS.md)
- [Product Requirements](docs/PRD.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Safety Policy](docs/SAFETY_POLICY.md)
- [Operations Guide](docs/OPERATIONS.md)
- [Roadmap](docs/ROADMAP.md)
