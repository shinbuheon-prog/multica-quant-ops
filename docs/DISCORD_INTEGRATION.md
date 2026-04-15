# 디스코드 연동 가이드

## 목적

이 문서는 운영 결과를 Discord 채널로 받아보는 방법을 정리합니다.
현재 구조에서는 텔레그램 대체안으로 `Discord Incoming Webhook`을 쓰는 방식이 가장 단순합니다.

## 왜 웹훅이 맞는가

현재 프로젝트는 자유 대화형 봇보다 `운영 상태 요약 알림`이 중심입니다.
그래서 별도 봇 명령 처리보다, 채널에 요약 메시지를 바로 보내는 웹훅 방식이 더 가볍고 운영에 맞습니다.

현재 보내는 정보:

- 전체 상태 요약
- 준비 완료 종목 수 / 차단 종목 수
- Alpha Vantage 사용량
- 종목별 최근 상태 일부
- 최근 audit 이벤트 요약
- 최근 incident headline

즉, Discord는 지금 구조에서 `대화형 봇`이 아니라 `운영 알림 채널` 역할입니다.

## 필요한 환경변수

```powershell
$env:DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

한 번 Windows `User` 환경변수로 저장해 두면, `ops/notify-discord.ps1`는 새 PowerShell 탭에서도 그 값을 자동으로 읽습니다.

## Discord Webhook 만들기

1. 알림을 받을 Discord 서버의 채널 설정 열기
2. `Integrations`
3. `Webhooks`
4. 새 Webhook 생성
5. 생성된 URL 복사

그 URL 전체가 `DISCORD_WEBHOOK_URL`입니다.

## 실행 순서

먼저 대시보드 export를 만듭니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\export-dashboard.ps1
```

그 다음 Discord 전송:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\notify-discord.ps1
```

메시지 미리보기만 보려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\notify-discord.ps1 -DryRun
```

문제가 있을 때만 보내려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\notify-discord.ps1 -AlertOnly
```

남은 호출 경고 기준을 바꾸려면:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\notify-discord.ps1 -AlertOnly -LowCallsThreshold 3
```

## 전송 실패 시 점검

- `DISCORD_WEBHOOK_URL is required`
  - 환경변수가 아직 없거나 현재 세션에 로드되지 않았습니다.
- `Discord webhook URL was rejected`
  - Webhook URL이 잘못됐거나 삭제된 Webhook입니다.
- `Discord rejected the payload`
  - 요청 본문이 잘못됐습니다. 현재 코드 기준에선 드문 경우입니다.
- `connection was refused`
  - 현재 PC 또는 네트워크에서 `discord.com`으로 나가는 HTTPS 연결이 막힌 상태입니다.
- `host could not be resolved`
  - DNS 또는 프록시 설정 문제일 가능성이 큽니다.
- `timed out`
  - Discord API 응답이 제시간에 오지 않았습니다.

운영 중에는 먼저 `-DryRun`으로 메시지 형식을 보고, 실제 전송을 다시 시도하는 흐름이 가장 안전합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\notify-discord.ps1 -DryRun -AlertOnly
```

## 추천 활용 방식

### 1. 텔레그램 대체 채널

텔레그램 API가 네트워크 정책에 막히는 환경이면 Discord Webhook을 대체 채널로 쓰기 좋습니다.

### 2. 팀 채널 공유

Google Sheets는 상세 확인용, Discord는 상태 공유용으로 나누면 운영이 단순해집니다.

### 3. blocked only 알림

평소에는 조용히 두고, blocked stage가 생길 때만 채널에 보내는 구성이 실용적입니다.
