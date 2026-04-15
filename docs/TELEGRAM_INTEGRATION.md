# 텔레그램 연동 가이드

## 목적

이 문서는 운영 결과를 텔레그램으로 받아보는 방법과,
현재 구조에서 텔레그램이 무엇을 보여주고 무엇을 보여주지 않는지 설명합니다.

## 현재 텔레그램이 하는 일

텔레그램은 운영 요약 채널입니다.

현재 보내는 정보:

- 전체 상태 요약
- 준비 완료 종목 수 / 차단 종목 수
- Alpha Vantage 사용량
- 종목별 상태 일부
- 종목별 최근 audit 이벤트 요약
- 최근 incident headline

즉, 운영자는 텔레그램에서
`오늘 상태가 어떤가`, `문제 종목이 있는가`, `무료 호출이 얼마나 남았는가`
를 빠르게 확인할 수 있습니다.

## 현재 텔레그램이 하지 않는 일

현재 텔레그램은 다음을 하지 않습니다.

- 실거래 지시 전송
- 브로커 주문 실행
- 에이전트 자유 대화 로그 재생
- 장문의 전체 리포트 원문 전달

## 왜 대화 로그가 아닌가

이 시스템은 `에이전트 간 채팅`을 중심으로 설계된 것이 아니라,
`task transition + audit + result` 구조로 설계되어 있습니다.

따라서 지금 확인 가능한 것은 다음입니다.

- `DataAgent`가 품질 점검을 했는지
- `SignalAgent`가 시그널을 만들었는지
- `BacktestAgent`가 승격을 막았는지
- `OpsAgent`가 paper execution을 만들었는지

이 정보는 audit와 incident, operator report에 담깁니다.

즉, 지금 텔레그램은 `자유 대화 재생`이 아니라
`누가 어떤 task를 마지막으로 처리했고 어떤 상태에서 멈췄는지`를 요약해서 보여주는 구조입니다.

## 필요한 환경변수

```powershell
$env:TELEGRAM_BOT_TOKEN="your-bot-token"
$env:TELEGRAM_CHAT_ID="your-chat-id"
```

한 번 Windows `User` 환경변수로 저장해 두면, `ops/notify-telegram.ps1`는 새 PowerShell 탭에서도 그 값을 자동으로 읽습니다.

## 실행 순서

먼저 대시보드 export를 만듭니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\export-dashboard.ps1
```

그 다음 텔레그램 전송:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\notify-telegram.ps1
```

메시지 미리보기만 보려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\notify-telegram.ps1 -DryRun
```

문제가 있을 때만 보내려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\notify-telegram.ps1 -AlertOnly
```

남은 호출 경고 기준을 바꾸려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\notify-telegram.ps1 -AlertOnly -LowCallsThreshold 3
```

## 전송 실패 시 점검

텔레그램 전송이 실패하면 메시지 원인을 먼저 구분해서 보시면 됩니다.

- `Telegram bot token was rejected`
  - `TELEGRAM_BOT_TOKEN` 값이 잘못됐거나 재발급 후 예전 토큰을 쓰는 상태입니다.
- `Check TELEGRAM_CHAT_ID`
  - `TELEGRAM_CHAT_ID`가 잘못됐거나, 봇이 아직 해당 채팅방과 대화를 시작하지 않았습니다.
- `connection was refused`
  - 현재 PC 또는 네트워크에서 `api.telegram.org`로 나가는 HTTPS 연결이 막힌 상태입니다.
  - 회사 보안 정책, 방화벽, 프록시, 보안 소프트웨어를 먼저 확인하는 쪽이 맞습니다.
- `host could not be resolved`
  - DNS 또는 프록시 설정 문제일 가능성이 큽니다.
- `timed out`
  - 텔레그램 API 응답이 제시간에 오지 않았습니다. 잠시 후 다시 시도하거나 네트워크 상태를 확인합니다.

운영 중에는 먼저 메시지 형식이 정상인지 `-DryRun`으로 확인한 뒤, 실제 전송을 다시 시도하는 흐름이 가장 안전합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\notify-telegram.ps1 -DryRun -AlertOnly
```

## 추천 운영 방식

### 1. batch 실행 후 요약 전송

가장 먼저 추천하는 방식입니다.

흐름:

1. batch 실행
2. dashboard export 생성
3. 텔레그램 요약 전송
4. 자세한 확인은 Google Sheets에서 수행

### 2. blocked only 감시용 사용

장중에 문제가 생겼는지만 빠르게 보려는 경우 적합합니다.

### 3. 무료 호출 감시

남은 호출 수가 적을 때 경고용 채널로 쓰기 좋습니다.

## 앞으로 확장 가능한 방향

나중에는 다음도 가능합니다.

- `blocked_stage`가 있으면 즉시 전송
- `paper_execution`만 높은 우선순위 알림
- batch 결과를 오전/오후 정기 전송
- Google Sheets 링크 포함
- incident별 추천 액션 더 자세히 포함
- `/status`, `/blocked`, `/usage` 같은 텔레그램 봇 명령형 인터페이스
