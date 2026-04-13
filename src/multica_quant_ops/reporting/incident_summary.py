from dataclasses import dataclass

from multica_quant_ops.audit import AuditEvent
from multica_quant_ops.orchestrator.daily_workflow import DailyWorkflowRequest, DailyWorkflowResult


@dataclass(frozen=True)
class IncidentSummary:
    is_incident: bool
    stage: str | None
    headline: str
    details: list[str]
    recommended_actions: list[str]


def build_incident_summary(
    request: DailyWorkflowRequest,
    result: DailyWorkflowResult,
    audit_log: list[AuditEvent],
) -> IncidentSummary:
    if result.blocked_stage is None:
        return IncidentSummary(
            is_incident=False,
            stage=None,
            headline=f"No incident for {request.symbol}.",
            details=["The daily workflow completed without a blocked stage."],
            recommended_actions=["Review the report and audit log as part of normal operations."],
        )

    details = [f"Workflow blocked at stage: {result.blocked_stage}."]
    recommended_actions = ["Review the audit log before retrying the workflow."]

    if result.blocked_stage == "data_quality":
        if result.data_quality_result.reasons:
            details.append(
                "Data-quality reasons: " + ", ".join(result.data_quality_result.reasons) + "."
            )
        recommended_actions.extend(
            [
                "Refresh or correct the market snapshot.",
                "Re-run the workflow only after the data-quality checks pass.",
            ]
        )
    elif result.blocked_stage == "backtest":
        details.append("Backtest promotion criteria were not met.")
        if result.backtest_result is not None:
            details.append(
                "Backtest metrics: "
                f"return={result.backtest_result.total_return:.4f}, "
                f"win_rate={result.backtest_result.win_rate:.4f}."
            )
        recommended_actions.extend(
            [
                "Inspect the backtest assumptions and thresholds.",
                "Do not promote the strategy until the criteria pass.",
            ]
        )
    elif result.blocked_stage == "paper_execution":
        if result.paper_execution_reason is not None:
            details.append(result.paper_execution_reason)
        recommended_actions.extend(
            [
                "Confirm market-session timing and execution safety settings.",
                "Re-run only after the paper-execution gate is expected to pass.",
            ]
        )

    if audit_log:
        last_event = audit_log[-1]
        details.append(
            f"Last audit event: {last_event.actor} moved '{last_event.task_title}' "
            f"to {last_event.to_status.value}."
        )

    return IncidentSummary(
        is_incident=True,
        stage=result.blocked_stage,
        headline=f"Incident detected for {request.symbol}: {result.blocked_stage}.",
        details=details,
        recommended_actions=recommended_actions,
    )


def render_incident_summary(summary: IncidentSummary) -> str:
    lines = [summary.headline]
    if summary.stage is not None:
        lines.append(f"Stage: {summary.stage}")

    lines.extend(summary.details)
    lines.append("Recommended actions:")
    lines.extend(f"- {action}" for action in summary.recommended_actions)
    return "\n".join(lines)
