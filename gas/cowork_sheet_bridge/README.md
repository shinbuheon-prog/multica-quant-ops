# Cowork sheet <- GitHub bridge (reference code)

이 폴더는 Phase 10(`docs/FUNDAMENTALS_INTEGRATION.md` "9-4절"과 같은 성격의 미해결
운영 질문)의 결과물입니다: 기존 Cowork CSV 기반 시트("지표 시트"/"통합대시보드")가
Drive 업로드를 거치지 않고 이 저장소의 산출물을 직접 읽도록 연결하는 코드입니다.
파일이 두 개입니다:

- `github_price_source.gs` — GitHub Actions 산출물(`ops/prices/daily_prices.csv`,
  Phase 5의 Stooq 일일 가격 갱신)을 **추가 소스**로 읽어 실시간 조회 실패 시
  대체값으로 쓴다. 기존 가격 로직을 건드리지 않는 부가 티어.
- `github_sheet_export_source.gs` — 지표 시트 본체(`sheet_export.csv`, 투자점수·
  건전성등급 등 27개 열 전부)를 Drive 대신 GitHub raw에서 직접 읽어 **통째로
  대체**한다. 2026-09-04, "매번 Drive에 CSV를 수동/트리거로 올려야 하는 게
  번거롭다"는 사용자 질문에서 시작됐다 — `build_drive_manifest.py`가 설명하는
  "Drive MCP는 에이전트 세션에서만 쓸 수 있어 업로드가 주간 트리거에 묶인다"는
  제약을 이 경로에서는 아예 없앤다(Apps Script가 스스로 GitHub에서 당겨오므로).

## 왜 별도 폴더인가

`gas/quant_ops_dashboard/`(폐기됨, 9-2절 참고)와 이름이 비슷하지만 완전히 다른
대상입니다:

- `gas/quant_ops_dashboard/` — multica-quant-ops의 paper-trading 운영 대시보드
  (Overview/Dashboard/Batch Runs/Incidents). **폐기됨.**
- `gas/cowork_sheet_bridge/` — 사용자가 실제로 매일 보는 Cowork 펀더멘털 시트("지표
  시트")에 붙이는 **추가 함수**. 그 시트의 본체 Apps Script(Cowork 세션의
  `/home/claude/gas/Code.gs`, 2,100줄 넘는 실사용 프로덕션 코드)는 이 저장소에 없고
  사용자의 Google 계정에만 있습니다.

## 왜 자동으로 배포하지 않는가

이 저장소의 git push는 사람이 PR을 보고 머지하는 검토 단계가 있습니다. Apps Script는
저장하는 순간 실사용 시트에 바로 적용되고, 이 세션은 Apps Script 실행을 테스트할 방법이
없습니다. 그래서 이 코드는 **직접 붙여넣기 전 사용자 검토용 참고 코드**로 둡니다 —
`git bundle` 워크플로와 같은 이유로, 검증 안 된 변경을 실사용 파일에 조용히 밀어넣지
않습니다.

## 공통 준비: public/private 확인

두 파일 다 같은 전제를 씁니다 — 저장소가 public인지 private인지 먼저 확인하세요.
private이면 각 파일의 `..._CONFIG.REQUIRES_AUTH`를 `true`로 바꾸고, Apps Script
프로젝트의 Script Properties에 read-only "Contents" 권한만 있는 GitHub PAT을
`GITHUB_PAT` 키로 저장하세요(두 파일이 같은 키를 공유합니다). **PAT을 코드에 직접
적지 마세요.**

## A. `github_price_source.gs` 적용 방법 (가격 부가 티어)

1. 위 public/private 준비를 마칩니다.
2. `github_price_source.gs`의 두 함수(`fetchGithubDailyPrices_`,
   `resolvePriceWithGithubTier_`)를 기존 Cowork 시트의 Apps Script 프로젝트에
   새 파일로 추가하세요(기존 `resolvePrice_` 등은 건드리지 않습니다 -- 이 함수들은
   그 옆에 추가하는 것입니다).
3. Apps Script 편집기에서 `fetchGithubDailyPrices_`를 한 번 단독 실행해 로그
   (`Logger.log`)를 확인하세요. `ops/tickers.txt`가 아직 비어 있으면(5단계 문서
   참고) 빈 맵이 정상입니다.
4. 검증되면, 가격을 쓰는 지점(`refreshPrices()`/`computeValuation()` 등)에서
   기존 `resolvePrice_(live, csv, csvDate)` 호출을 `resolvePriceWithGithubTier_(live,
   githubMap[ticker], csv, csvDate)`로 바꾸는 걸 검토하세요. 이 저장소는 이 교체를
   대신 해주지 않습니다 -- 실사용 시트를 건드리는 마지막 단계는 사용자 판단입니다.

**우선순위**: `실시간 조회 > GitHub Actions 일일 갱신 > 파이프라인 CSV(sheet_export.csv
기준종가)` 순으로 가격을 고릅니다. GitHub 쪽 데이터가 있어도 `stale=true`(Stooq 실패로
이전 값을 그대로 들고 온 경우)면 파이프라인 CSV보다 우선하지 않습니다 -- `stale` 플래그의
의미는 `docs/FUNDAMENTALS_INTEGRATION.md` 5-4절과 `refresh_daily_prices.py`의 모듈
문서를 참고하세요.

## B. `github_sheet_export_source.gs` 적용 방법 (지표 시트 전체 대체)

1. 위 public/private 준비를 마칩니다.
2. 이 저장소의 `ops/fundamentals/sheet_export.csv`가 최신인지 먼저 확인하세요 —
   이 다리는 저장소에 있는 파일을 그대로 읽으므로, 저장소가 오래되면 시트도 오래된
   채로 새로고침됩니다. Cowork 세션 쪽엔 `/home/claude/sync_sheet_export_to_repo.sh`가
   있어 파이프라인이 만든 최신 `sheet_export.csv`를 이 저장소 클론에 복사하고 git
   diff를 보여줍니다(커밋·push는 안 합니다 -- 그 VM엔 push 자격증명이 없어서, 항상
   그래왔듯 Windows 터미널에서 pull → 확인 → 커밋 → push 하시면 됩니다).
3. `github_sheet_export_source.gs`의 두 함수(`fetchGithubSheetExportCsv_`,
   `refreshMetricsFromGithub`)를 기존 Cowork 시트의 Apps Script 프로젝트에 새 파일로
   추가하세요(기존 `refreshMetrics()` 등은 건드리지 않습니다 -- A와 같은 원칙).
4. Apps Script 편집기에서 `refreshMetricsFromGithub`를 한 번 단독 실행하고, 지표
   시트와 메타 정보("지표 파일" 행이 GitHub raw URL로 바뀌었는지)를 확인하세요.
5. 검증되면 아래 중 하나를 선택하세요(이 저장소는 선택을 대신 해주지 않습니다):
   - **완전 교체**: 메뉴/트리거가 부르던 `refreshMetrics()` 호출을
     `refreshMetricsFromGithub()`로 바꾼다. Drive 업로드·`drive_manifest.json`의
     `sheet_export.csv` 항목이 더는 필요 없어진다(`watchlist_priceonly.csv`는 그대로
     Drive 경로를 씁니다 -- 이 다리는 지표 시트 하나만 다룹니다).
   - **시간 트리거 병행**: 기존 `refreshMetrics()`는 그대로 두고,
     `refreshMetricsFromGithub()`를 별도 시간 기반 트리거(예: 매일 새벽)로 등록해
     "Cowork 세션이 며칠 안 열려도 최소 저장소에 올라간 최신본으로는 갱신되는" 안전망으로
     쓴다.

## 남는 제약

실제 스코어링(SEC 리서치·건전성 등급 산출 등) 자체는 여전히 Cowork 세션에서만 도는
로직입니다. 이 다리가 없애는 건 "계산된 CSV를 시트까지 옮기는" 배송 단계뿐입니다 —
"계산"까지 완전 무인화하려면 그 로직을 GitHub Actions 쪽으로 옮기는 별도 작업이
필요합니다(Scout/Doctor 에이전트 코드화는 이미 있어 방향은 잡혀 있습니다).
