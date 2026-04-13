from typing import Any


def render_korean_prep_report(brief: Any) -> str:
    lines = [
        f"[운영 브리프] {brief.symbol}",
        f"- 현재가: {brief.current_price:.2f}",
        f"- 전일 종가: {brief.previous_close:.2f}",
        f"- 당일 변동률: {brief.change_percent * 100:.2f}%",
        f"- 장중 고가/저가: {brief.session_high:.2f} / {brief.session_low:.2f}",
        f"- 시그널: {brief.signal_direction} (신뢰도 {brief.signal_confidence:.4f})",
        f"- 페이퍼 실행 가능 여부: {'가능' if brief.paper_execution_ready else '불가'}",
        f"- 차단 단계: {brief.blocked_stage or '없음'}",
        f"- 인시던트 헤드라인: {brief.incident_headline}",
    ]
    if brief.alpha_vantage_used_calls is not None:
        lines.append(
            "- Alpha Vantage 사용량: "
            f"{brief.alpha_vantage_used_calls}/{brief.alpha_vantage_daily_limit} "
            f"(남은 호출 {brief.alpha_vantage_remaining_calls})"
        )
    lines.append(
        "- 참고: 이 결과는 실거래 지시가 아니라 "
        "당일 paper-trading 준비와 운영자 검토를 위한 리서치 브리프입니다."
    )
    return "\n".join(lines)
