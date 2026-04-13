from multica_quant_ops.orchestrator.daily_workflow import DailyWorkflowRequest, DailyWorkflowResult


def build_daily_report(request: DailyWorkflowRequest, result: DailyWorkflowResult) -> str:
    lines = [
        f"Daily Workflow Report: {request.symbol}",
        f"Blocked stage: {result.blocked_stage or 'none'}",
        f"Data quality: {result.data_quality_result.status.value}",
    ]

    if result.data_quality_result.reasons:
        lines.append(f"Data quality reasons: {', '.join(result.data_quality_result.reasons)}")

    if result.signal is not None:
        lines.append(
            f"Signal: {result.signal.direction.value} "
            f"(confidence={result.signal.confidence:.4f})"
        )
        lines.append(f"Signal rationale: {result.signal.rationale}")
    else:
        lines.append("Signal: not produced")

    if result.backtest_result is not None:
        lines.append(
            "Backtest: "
            f"return={result.backtest_result.total_return:.4f}, "
            f"win_rate={result.backtest_result.win_rate:.4f}, "
            f"approved={str(result.backtest_result.approved_for_paper_trading).lower()}"
        )
    else:
        lines.append("Backtest: not run")

    if result.paper_order is not None:
        lines.append(
            f"Paper order: {result.paper_order.side} "
            f"{result.paper_order.quantity} {result.paper_order.symbol}"
        )
        lines.append(f"Paper order rationale: {result.paper_order.rationale}")
    else:
        lines.append("Paper order: not created")
        if result.paper_execution_reason is not None:
            lines.append(f"Paper execution reason: {result.paper_execution_reason}")

    return "\n".join(lines)
