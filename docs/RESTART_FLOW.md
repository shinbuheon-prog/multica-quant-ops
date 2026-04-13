# 재시작 / 새 PowerShell 탭 복귀 가이드

## 목적

이 문서는 PC 재부팅, 새 PowerShell 탭, 새 Codex 세션 이후에도
빠르게 작업 상태로 복귀하는 절차를 정리합니다.

핵심 원칙은 간단합니다.

- 세션 상태는 믿지 않음
- 작업 상태는 파일, Git, 문서에 남김
- 새 탭에서는 항상 같은 bootstrap 절차로 재진입

## 가장 추천하는 복귀 순서

### 1. 프로젝트 폴더로 이동

```powershell
cd "C:\Users\shin.buheon\Desktop\Codex 활용\projects\multica-quant-ops"
```

### 2. 세션 bootstrap 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\bootstrap-session.ps1
```

이 스크립트는 다음을 합니다.

- 프로젝트 루트 이동
- `.venv` 활성화
- `PYTHONPATH=src` 설정
- 핵심 환경변수 설정 여부 확인
- 최소 검증 테스트 실행

빠르게만 복귀하려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\bootstrap-session.ps1 -SkipTests
```

### 3. 현재 상태 요약 확인

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\show-status.ps1
```

이 스크립트는 다음을 보여줍니다.

- `git status`
- 최근 runtime 파일
- 최근 report / incident 파일
- 최신 dashboard export 일부
- 환경변수 설정 여부

## 언제 기존 PowerShell 탭을 유지해야 하나

다음 상황이 아니라면 굳이 유지할 필요는 없습니다.

- 긴 실행이 아직 끝나지 않음
- 중간 산출물을 직접 콘솔에서 관찰 중
- 잠깐 후 동일 탭에서 즉시 이어갈 계획

그 외에는:

- 커밋
- 산출물 저장
- 대시보드 export 반영

후 새 탭에서 다시 시작하는 편이 더 안정적입니다.

## 왜 새 탭 복귀 방식이 더 좋은가

이 프로젝트에서 중요한 것은 `콘솔 메모리`가 아니라 다음입니다.

- Git 커밋
- `ops/runtime/`
- `ops/reports/`
- `ops/incidents/`
- `ops/dashboard/dashboard-export.json`
- Google Sheets 대시보드
- 문서와 체크리스트

즉, 작업 맥락은 이미 파일과 저장소에 남아 있으므로
세션을 오래 끌고 가는 것보다 재진입 절차를 짧게 만드는 편이 효율적입니다.

## 추천 복귀 흐름

### 운영자 모드

1. `bootstrap-session.ps1`
2. `show-status.ps1`
3. 필요하면 same-day / batch 실행
4. `export-dashboard.ps1`
5. Google Sheets 확인

### Codex 작업 모드

1. `bootstrap-session.ps1`
2. `show-status.ps1`
3. `README`, 튜토리얼, 체크리스트 확인
4. `git log --oneline -5` 또는 `git status` 확인
5. 이어서 코드/문서 작업

## 함께 보면 좋은 문서

- [Start Here Tutorial](TUTORIAL_START_HERE.md)
- [Operations Checklist](OPERATIONS_CHECKLIST.md)
- [Daily Scenario Example](DAILY_SCENARIO_EXAMPLE.md)
- [Codex Team + Dashboard Design](CODEX_TEAM_DASHBOARD_DESIGN.md)
