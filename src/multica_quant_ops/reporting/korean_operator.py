from typing import Any


def _format_signal_label(direction: str) -> str:
    labels = {
        "long": "상승",
        "short": "하락",
        "flat": "중립",
        "none": "없음",
    }
    return labels.get(direction, direction)


def _format_next_action(brief: Any) -> str:
    if brief.paper_execution_ready:
        return (
            "페이퍼 주문 후보가 생성된 상태입니다. 주문 전 수량, 세션 시간, "
            "데이터 신선도를 다시 확인하세요."
        )
    if brief.blocked_stage == "data_quality":
        return "시세 데이터 시각과 거래량을 다시 확인한 뒤 요청을 재생성하세요."
    if brief.blocked_stage == "backtest":
        return "백테스트 기준을 충족하지 못했습니다. 오늘은 관찰 위주로 유지하세요."
    if brief.blocked_stage == "paper_execution":
        return "장 시간과 실행 안전 조건을 먼저 점검한 뒤 다시 실행하세요."
    return "리포트를 검토하고 필요 시 추가 티커 비교 또는 재실행을 진행하세요."


def render_korean_prep_report(brief: Any) -> str:
    readiness = "가능" if brief.paper_execution_ready else "보류"
    blocked_stage = brief.blocked_stage or "없음"
    lines = [
        f"[당일 준비 리포트] {brief.symbol}",
        "",
        "관찰 포인트",
        f"- 현재가: {brief.current_price:.2f}",
        f"- 전일 종가: {brief.previous_close:.2f}",
        f"- 당일 변동률: {brief.change_percent * 100:.2f}%",
        f"- 장중 고가/저가: {brief.session_high:.2f} / {brief.session_low:.2f}",
        f"- 시그널 방향: {_format_signal_label(brief.signal_direction)}",
        f"- 시그널 신뢰도: {brief.signal_confidence:.4f}",
        "",
        "판단 상태",
        f"- 페이퍼 실행 준비: {readiness}",
        f"- 차단 단계: {blocked_stage}",
        f"- 운영 헤드라인: {brief.incident_headline}",
    ]
    if brief.alpha_vantage_used_calls is not None:
        lines.append(
            "- Alpha Vantage 사용량: "
            f"{brief.alpha_vantage_used_calls}/{brief.alpha_vantage_daily_limit} "
            f"(남은 호출 {brief.alpha_vantage_remaining_calls})"
        )
    lines.extend(
        [
            "",
            "다음 액션",
            f"- {_format_next_action(brief)}",
            "- 이 결과는 실거래 지시가 아니라 당일 paper-trading 준비와 운영자 검토를 위한 리서치 브리프입니다.",
        ]
    )
    return "\n".join(lines)


def render_korean_batch_summary(items: list[dict[str, object]]) -> str:
    ready_count = sum(1 for item in items if item.get("paper_execution_ready"))
    blocked_items = [item for item in items if item.get("blocked_stage")]

    lines = [
        "[멀티 티커 운영 요약]",
        f"- 준비 완료 종목: {ready_count} / {len(items)}",
        f"- 차단 발생 종목: {len(blocked_items)}",
        "",
        "종목별 상태",
    ]

    for item in items:
        ticker = str(item["ticker"])
        direction = _format_signal_label(str(item["signal_direction"]))
        current_price_value = item["current_price"]
        current_price = (
            float(current_price_value)
            if isinstance(current_price_value, int | float)
            else 0.0
        )
        blocked_stage = item.get("blocked_stage") or "없음"
        readiness = "가능" if item.get("paper_execution_ready") else "보류"
        remaining_calls = item.get("remaining_calls")
        usage_text = f", 남은 호출 {remaining_calls}" if remaining_calls is not None else ""
        lines.append(
            f"- {ticker}: 현재가 {current_price:.2f}, 시그널 {direction}, "
            f"페이퍼 실행 {readiness}, 차단 단계 {blocked_stage}{usage_text}"
        )

    lines.extend(
        [
            "",
            "운영 메모",
            "- 보류 종목은 차단 단계와 데이터 시각을 먼저 검토하세요.",
            "- 무료 Alpha Vantage 한도는 batch 실행 중 빠르게 소모되므로 남은 호출 수를 함께 확인하세요.",
            "- 이 요약은 실거래 지시가 아니라 당일 paper-trading 준비용 운영 메모입니다.",
        ]
    )
    return "\n".join(lines)
