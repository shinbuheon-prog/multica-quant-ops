# Cowork sheet <- GitHub price bridge (reference code)

이 폴더는 Phase 10(`docs/FUNDAMENTALS_INTEGRATION.md` "9-4절"과 같은 성격의 미해결
운영 질문)의 결과물입니다: 기존 Cowork CSV 기반 시트("지표 시트"/"통합대시보드")가
이 저장소의 GitHub Actions 산출물(`ops/prices/daily_prices.csv`, Phase 5의 Stooq
일일 가격 갱신)을 추가 소스로 읽도록 연결하는 코드입니다.

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

## 적용 방법

1. 이 저장소가 public인지 private인지 확인하세요. private이면 `github_price_source.gs`의
   `GITHUB_PRICE_CSV_CONFIG.REQUIRES_AUTH`를 `true`로 바꾸고, Apps Script 프로젝트의
   Script Properties에 read-only "Contents" 권한만 있는 GitHub PAT을 `GITHUB_PAT`
   키로 저장하세요. **PAT을 코드에 직접 적지 마세요.**
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

## 우선순위

`실시간 조회 > GitHub Actions 일일 갱신 > 파이프라인 CSV(sheet_export.csv 기준종가)`
순으로 가격을 고릅니다. GitHub 쪽 데이터가 있어도 `stale=true`(Stooq 실패로 이전 값을
그대로 들고 온 경우)면 파이프라인 CSV보다 우선하지 않습니다 -- `stale` 플래그의 의미는
`docs/FUNDAMENTALS_INTEGRATION.md` 5-4절과 `refresh_daily_prices.py`의 모듈 문서를
참고하세요.

## GitHub ��ǥ ��Ʈ �긮��

`github_sheet_export_source.gs`�� ���� �긮�� �����
`ops/fundamentals/sheet_export.csv` ��ü�� �����ϴ� ���� �ڵ��Դϴ�. ���� Cowork
��Ʈ�� Apps Script ������Ʈ�� ���� ���Ϸ� �߰��ϼ���. ������� ��ú��� ��ũ��Ʈ��
�ڵ����� ��ü�ϰų� ���������� �ʽ��ϴ�.

1. `GITHUB_SHEET_EXPORT_CONFIG.RAW_URL`�� �ֽ� `sheet_export.csv`�� �Խ��ϴ�
   �귣ġ�� ����Ű���� Ȯ���ϼ���.
2. private ����Ҷ�� `REQUIRES_AUTH`�� `true`�� �ٲٰ�, read-only GitHub
   ��ū�� Script Properties�� `GITHUB_PAT`�� �����ϼ���. ��ū�� �ҽ� �ڵ忡 ����
   ���� ������.
3. `refreshMetricsFromGithub()`�� �� �� ���� ������ �� ��ǥ ��Ʈ�� ���� �α׸�
   Ȯ���ϼ���. ������ ���� ���� �޴��� �ð� ��� Ʈ���ſ� �����ϼ���.
4. GitHub�� `ops/fundamentals/sheet_export.csv`�� �ֽ� ���·� �����ϼ���. ��
   �긮���� ���������� push�� ������ ���� ��, export pipeline ��ü�� ����������
   �ʽ��ϴ�.

�������⳪ ������ �����ϸ� ���� ��ǥ ��Ʈ�� ����� ���� ������ �ߴ��մϴ�. ����
�Ͻ����� GitHub ��ֳ� ���� ���а� �߻��ص� ���� ��Ʈ ������ �״�� �����˴ϴ�.
