import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


_BATCH_NAME_RE = re.compile(r"^batch-(\d{8}-\d{6})$")
_SINGLE_BRIEF_RE = re.compile(r"^([A-Z0-9._-]+)-brief-(\d{8}-\d{6})\.json$")
_INCIDENT_FILE_RE = re.compile(r"^incident-summary-(\d{8}-\d{6})\.txt$")
_DAILY_REPORT_RE = re.compile(r"^daily-report-(\d{8}-\d{6})\.txt$")


def _parse_compact_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d-%H%M%S")


def _format_timestamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").lstrip("\ufeff").strip()


def _read_text_excerpt(path: Path, max_lines: int = 4) -> str:
    lines = [line.lstrip("\ufeff").strip() for line in _read_text(path).splitlines() if line.strip()]
    return " ".join(lines[:max_lines])


def _serialize_path(path: Path | None) -> str | None:
    return str(path) if path is not None else None


def _build_dashboard_row(
    brief_payload: dict[str, Any],
    generated_at: datetime,
    brief_path: Path,
    request_path: Path | None,
    report_path: Path | None,
    source_label: str,
) -> dict[str, Any]:
    brief = brief_payload["brief"]
    workflow = brief_payload["workflow"]
    incident_summary = workflow["incident_summary"]
    request = workflow["request"]
    report_excerpt = _read_text_excerpt(report_path) if report_path is not None and report_path.exists() else ""
    return {
        "symbol": brief["symbol"],
        "generated_at": _format_timestamp(generated_at),
        "source": source_label,
        "request_now": request["now"],
        "snapshot_as_of": request["snapshot"]["as_of"],
        "current_price": brief["current_price"],
        "change_percent": brief["change_percent"],
        "signal_direction": brief["signal_direction"],
        "signal_confidence": brief["signal_confidence"],
        "paper_execution_ready": brief["paper_execution_ready"],
        "blocked_stage": brief["blocked_stage"],
        "incident_headline": brief["incident_headline"],
        "recommended_actions": incident_summary["recommended_actions"],
        "incident_details": incident_summary["details"],
        "remaining_calls": brief["alpha_vantage_remaining_calls"],
        "used_calls": brief["alpha_vantage_used_calls"],
        "daily_limit": brief["alpha_vantage_daily_limit"],
        "brief_path": str(brief_path),
        "request_path": _serialize_path(request_path),
        "report_path": _serialize_path(report_path),
        "report_excerpt": report_excerpt,
    }


def _collect_batch_rows(runtime_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dashboard_rows: list[dict[str, Any]] = []
    batch_runs: list[dict[str, Any]] = []

    for batch_dir in sorted(runtime_dir.glob("batch-*")):
        if not batch_dir.is_dir():
            continue
        match = _BATCH_NAME_RE.match(batch_dir.name)
        if match is None:
            continue
        generated_at = _parse_compact_timestamp(match.group(1))
        per_batch_rows: list[dict[str, Any]] = []
        for brief_path in sorted(batch_dir.glob("*-brief.json")):
            brief_payload = _read_json(brief_path)
            symbol = str(brief_payload["brief"]["symbol"])
            request_path = batch_dir / f"{symbol}-request.json"
            report_path = batch_dir / f"{symbol}-operator-report-ko.txt"
            per_batch_rows.append(
                _build_dashboard_row(
                    brief_payload=brief_payload,
                    generated_at=generated_at,
                    brief_path=brief_path,
                    request_path=request_path if request_path.exists() else None,
                    report_path=report_path if report_path.exists() else None,
                    source_label=batch_dir.name,
                )
            )

        if not per_batch_rows:
            continue

        dashboard_rows.extend(per_batch_rows)
        ready_count = sum(1 for row in per_batch_rows if row["paper_execution_ready"])
        blocked_count = sum(1 for row in per_batch_rows if row["blocked_stage"] is not None)
        summary_path = batch_dir / "batch-summary.json"
        summary_report_path = batch_dir / "batch-summary-ko.txt"
        batch_runs.append(
            {
                "batch_name": batch_dir.name,
                "generated_at": _format_timestamp(generated_at),
                "ticker_count": len(per_batch_rows),
                "ready_count": ready_count,
                "blocked_count": blocked_count,
                "summary_path": _serialize_path(summary_path if summary_path.exists() else None),
                "summary_report_path": _serialize_path(
                    summary_report_path if summary_report_path.exists() else None
                ),
                "summary_report_excerpt": (
                    _read_text_excerpt(summary_report_path, max_lines=6)
                    if summary_report_path.exists()
                    else ""
                ),
            }
        )

    batch_runs.sort(key=lambda item: str(item["generated_at"]), reverse=True)
    return dashboard_rows, batch_runs


def _collect_single_rows(runtime_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for brief_path in sorted(runtime_dir.glob("*-brief-*.json")):
        match = _SINGLE_BRIEF_RE.match(brief_path.name)
        if match is None:
            continue
        symbol = match.group(1)
        generated_at = _parse_compact_timestamp(match.group(2))
        brief_payload = _read_json(brief_path)
        request_path = runtime_dir / f"{symbol}-request-{match.group(2)}.json"
        report_path = runtime_dir / f"{symbol}-operator-report-ko-{match.group(2)}.txt"
        rows.append(
            _build_dashboard_row(
                brief_payload=brief_payload,
                generated_at=generated_at,
                brief_path=brief_path,
                request_path=request_path if request_path.exists() else None,
                report_path=report_path if report_path.exists() else None,
                source_label="single-run",
            )
        )

    return rows


def _latest_rows_by_symbol(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = str(row["symbol"])
        previous = latest.get(symbol)
        if previous is None or str(row["generated_at"]) > str(previous["generated_at"]):
            latest[symbol] = row
    return sorted(latest.values(), key=lambda item: str(item["symbol"]))


def _collect_usage(runtime_dir: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    usage_path = runtime_dir / "alpha-vantage-usage.json"
    used_calls = None
    usage_date = None
    if usage_path.exists():
        usage_payload = _read_json(usage_path)
        if usage_payload:
            usage_date = max(usage_payload)
            used_calls = usage_payload[usage_date]

    daily_limit = next((row["daily_limit"] for row in rows if row["daily_limit"] is not None), None)
    remaining_calls = (
        daily_limit - used_calls
        if isinstance(daily_limit, int) and isinstance(used_calls, int)
        else None
    )
    return {
        "usage_path": _serialize_path(usage_path if usage_path.exists() else None),
        "usage_date": usage_date,
        "used_calls": used_calls,
        "daily_limit": daily_limit,
        "remaining_calls": remaining_calls,
    }


def _collect_incidents(incidents_dir: Path, limit: int = 10) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(incidents_dir.glob("incident-summary-*.txt"), reverse=True):
        match = _INCIDENT_FILE_RE.match(path.name)
        if match is None:
            continue
        lines = [line.lstrip("\ufeff").strip() for line in _read_text(path).splitlines() if line.strip()]
        items.append(
            {
                "generated_at": _format_timestamp(_parse_compact_timestamp(match.group(1))),
                "headline": lines[0] if lines else "",
                "details_excerpt": " ".join(lines[1:4]),
                "path": str(path),
            }
        )
        if len(items) >= limit:
            break
    return items


def _collect_latest_daily_report(reports_dir: Path) -> dict[str, Any]:
    latest_path: Path | None = None
    latest_timestamp: datetime | None = None
    for path in reports_dir.glob("daily-report-*.txt"):
        match = _DAILY_REPORT_RE.match(path.name)
        if match is None:
            continue
        timestamp = _parse_compact_timestamp(match.group(1))
        if latest_timestamp is None or timestamp > latest_timestamp:
            latest_timestamp = timestamp
            latest_path = path

    if latest_path is None or latest_timestamp is None:
        return {"path": None, "generated_at": None, "headline": None}

    lines = [line.lstrip("\ufeff").strip() for line in _read_text(latest_path).splitlines() if line.strip()]
    return {
        "path": str(latest_path),
        "generated_at": _format_timestamp(latest_timestamp),
        "headline": lines[0] if lines else "",
    }


def build_dashboard_export(ops_dir: Path) -> dict[str, Any]:
    runtime_dir = ops_dir / "runtime"
    incidents_dir = ops_dir / "incidents"
    reports_dir = ops_dir / "reports"

    batch_rows, batch_runs = _collect_batch_rows(runtime_dir)
    single_rows = _collect_single_rows(runtime_dir)
    dashboard_rows = _latest_rows_by_symbol(batch_rows + single_rows)
    usage = _collect_usage(runtime_dir, dashboard_rows)
    incidents = _collect_incidents(incidents_dir)
    latest_daily_report = _collect_latest_daily_report(reports_dir)

    ready_count = sum(1 for row in dashboard_rows if row["paper_execution_ready"])
    blocked_count = sum(1 for row in dashboard_rows if row["blocked_stage"] is not None)
    latest_generated_at = (
        max(str(row["generated_at"]) for row in dashboard_rows)
        if dashboard_rows
        else None
    )

    return {
        "generated_at": _format_timestamp(datetime.now()),
        "overview": {
            "total_tickers": len(dashboard_rows),
            "ready_tickers": ready_count,
            "blocked_tickers": blocked_count,
            "latest_market_snapshot": latest_generated_at,
            "alpha_vantage_used_calls": usage["used_calls"],
            "alpha_vantage_daily_limit": usage["daily_limit"],
            "alpha_vantage_remaining_calls": usage["remaining_calls"],
            "alpha_vantage_usage_date": usage["usage_date"],
            "alpha_vantage_usage_path": usage["usage_path"],
            "latest_daily_report_path": latest_daily_report["path"],
            "latest_daily_report_generated_at": latest_daily_report["generated_at"],
            "latest_daily_report_headline": latest_daily_report["headline"],
        },
        "dashboard": dashboard_rows,
        "batch_runs": batch_runs,
        "incidents": incidents,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a JSON payload for the spreadsheet dashboard."
    )
    parser.add_argument(
        "--ops-dir",
        default="ops",
        help="Path to the ops directory that contains runtime, reports, and incidents.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write the dashboard export JSON file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ops_dir = Path(args.ops_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_dashboard_export(ops_dir)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Dashboard export written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
