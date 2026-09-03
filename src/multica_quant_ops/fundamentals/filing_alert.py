"""Loader and notification message builder for the fundamentals pipeline's
filing-detection signal (`filing_alert_latest.json`).

That file is produced by the Cowork pipeline's `s9d_filing_alert.py` (9d
layer): a weekly SEC-filing-detection trigger appends raw sightings to
`filing_alerts.csv`, and s9d_filing_alert.py deduplicates them, keeps only
the latest sighting per ticker, and **auto-clears** any alert once a human
has rescored that ticker on or after the filing date (see that script's
module docstring: "재채점되면 자동으로 사라진다" -- there is nothing for a
person to check off or delete by hand). By the time `filing_alert_latest.json`
exists, that noise-minimization judgment has already been applied -- this
module only loads the already-resolved result and formats it for a Discord/
Telegram notification. It does not re-run the clearing logic.

Same operational open item as fundamentals/universe.py and snapshot.py
(docs/FUNDAMENTALS_INTEGRATION.md, section 9-4): how filing_alert_latest.json
physically lands in this repository is not yet decided.
"""

import json
from csv import DictReader
from dataclasses import dataclass
from datetime import date
from pathlib import Path


class FilingAlertFormatError(ValueError):
    """Raised when filing_alert_latest.json is malformed."""


@dataclass(frozen=True)
class FilingAlert:
    ticker: str
    filed_date: date
    form: str
    reason: str
    detected_on: str


def load_filing_alerts(path: Path) -> dict[str, FilingAlert]:
    """Load the active (not-yet-rescored) filing alerts.

    An absent file is treated the same way s9d_filing_alert.py treats it --
    "no filing has been detected yet" is a normal, empty state, not an
    error -- so this returns `{}` rather than raising.
    """
    if not path.exists():
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FilingAlertFormatError(f"{path} is not valid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise FilingAlertFormatError(f"{path} must contain a JSON object keyed by ticker")

    alerts: dict[str, FilingAlert] = {}
    for ticker, fields in raw.items():
        if not isinstance(fields, dict) or "filed_date" not in fields:
            raise FilingAlertFormatError(f"{path}: entry for {ticker!r} is missing filed_date")
        try:
            filed_date = date.fromisoformat(fields["filed_date"])
        except ValueError as exc:
            raise FilingAlertFormatError(
                f"{path}: entry for {ticker!r} has an unparseable filed_date "
                f"{fields['filed_date']!r}"
            ) from exc
        alerts[ticker] = FilingAlert(
            ticker=ticker,
            filed_date=filed_date,
            form=str(fields.get("form", "")),
            reason=str(fields.get("reason", "")),
            detected_on=str(fields.get("detected_on", "")),
        )
    return alerts


def build_filing_alert_message(alerts: dict[str, FilingAlert]) -> str | None:
    """Build a Discord/Telegram-ready message, or None when there is nothing
    to say.

    Returning None on an empty alert set is deliberate noise-minimization
    (docs/FUNDAMENTALS_INTEGRATION.md section 6: "알림 노이즈 최소화") -- the
    caller should skip sending entirely rather than post a "no alerts" ping,
    matching the project's existing alert_only pattern in discord_notify.py /
    telegram_notify.py.
    """
    if not alerts:
        return None

    lines = [
        "[Quant Ops 공시신호]",
        f"신규 공시 감지 종목 {len(alerts)}개 (아직 재채점 전)",
        "",
    ]
    for ticker in sorted(alerts):
        alert = alerts[ticker]
        row = f"- {ticker}: {alert.form or '공시'} · {alert.filed_date.isoformat()}"
        if alert.reason:
            row += f" · {alert.reason}"
        lines.append(row)

    lines.extend(
        [
            "",
            "참고",
            "- 이 신호는 투자 판단이 아니라 재채점이 필요할 수 있다는 알림입니다.",
            "- 사람이 재채점하면(judgment_scores.csv 갱신) 이 신호는 자동으로 사라집니다.",
        ]
    )
    return "\n".join(lines)


# Kept for callers that already have filing_alerts.csv and want to validate
# its shape without going through s9d_filing_alert.py's dedup/auto-clear
# logic -- e.g. a consistency check that the raw log at least parses.
REQUIRED_LOG_COLUMNS = ("ticker", "filed_date", "form", "accession", "detected_on", "reason")


def validate_filing_alerts_log(path: Path) -> list[str]:
    """Return a list of shape issues with the raw filing_alerts.csv log, or
    an empty list if it parses cleanly. An absent file is not an issue (see
    load_filing_alerts's docstring)."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = DictReader(handle)
        header = reader.fieldnames or []
        missing = set(REQUIRED_LOG_COLUMNS) - set(header)
        if missing:
            return [f"filing_alerts.csv is missing required column(s): {sorted(missing)}"]
        issues = []
        for line_no, row in enumerate(reader, start=2):
            if not row.get("ticker", "").strip():
                issues.append(f"filing_alerts.csv line {line_no}: empty ticker")
            filed_date = row.get("filed_date", "").strip()
            if filed_date:
                try:
                    date.fromisoformat(filed_date)
                except ValueError:
                    issues.append(
                        f"filing_alerts.csv line {line_no}: unparseable filed_date {filed_date!r}"
                    )
        return issues
