from datetime import date

from multica_quant_ops.fundamentals.consistency import check_snapshot_against_universe
from multica_quant_ops.fundamentals.snapshot import FundamentalsRow
from multica_quant_ops.fundamentals.universe import UniverseEntry


def _universe_entry(ticker: str, sector: str = "soft", exit_date: date | None = None) -> UniverseEntry:
    return UniverseEntry(
        ticker=ticker,
        name=ticker,
        sector=sector,
        cik="0000000000",
        fye_month=12,
        watch_added=date(2026, 8, 26),
        list_date=None,
        exit_date=exit_date,
        status="active",
        fin_first=None,
        fin_last=None,
        fin_quarters=0,
        px_first=None,
        px_last=None,
        px_obs=0,
        px_source="",
        periodic_filer=True,
        note="",
    )


def _snapshot_row(
    ticker: str,
    sector: str = "soft",
    investment_score: float | None = 7.5,
    confidence: float | None = 0.9,
    health_grade: str = "B",
    verdict: str = "중립 상단",
    attractiveness_grade: str = "A",
) -> FundamentalsRow:
    return FundamentalsRow(
        ticker=ticker,
        name=ticker,
        sector=sector,
        basket="basket",
        reference_close_price=100.0,
        price_date=date(2026, 8, 28),
        verdict=verdict,
        investment_score=investment_score,
        attractiveness_grade=attractiveness_grade,
        holding_horizon="장기보유형",
        health_grade=health_grade,
        key_multiples="",
        filing_alert="",
        weekly_watch="",
        recent_change="",
        prediction_check="",
        latest_opinion="",
        confidence=confidence,
        price_observations=1000,
        financial_age_days=10,
        price_basis_note="",
        latest_filing_date=None,
        health_score=75.0,
        cost_bp=1.0,
        watch_start=date(2026, 8, 26),
        scored_date=date(2026, 8, 26),
        google_symbol=ticker,
    )


def test_clean_snapshot_has_no_issues() -> None:
    universe = [_universe_entry("AAPL")]
    snapshot = [_snapshot_row("AAPL")]

    assert check_snapshot_against_universe(snapshot, universe) == []


def test_snapshot_ticker_missing_from_universe_is_flagged() -> None:
    issues = check_snapshot_against_universe([_snapshot_row("GHOST")], [])

    assert any("GHOST" in issue and "missing from universe.csv" in issue for issue in issues)


def test_active_universe_ticker_missing_from_snapshot_is_flagged() -> None:
    issues = check_snapshot_against_universe([], [_universe_entry("AAPL")])

    assert any("AAPL" in issue and "missing from sheet_export.csv" in issue for issue in issues)


def test_exited_universe_ticker_not_required_in_snapshot() -> None:
    universe = [_universe_entry("OLD", exit_date=date(2026, 9, 1))]

    assert check_snapshot_against_universe([], universe) == []


def test_sector_mismatch_is_flagged() -> None:
    universe = [_universe_entry("AAPL", sector="soft")]
    snapshot = [_snapshot_row("AAPL", sector="heal")]

    issues = check_snapshot_against_universe(snapshot, universe)

    assert any("sector mismatch" in issue for issue in issues)


def test_investment_score_out_of_range_is_flagged() -> None:
    universe = [_universe_entry("AAPL")]
    snapshot = [_snapshot_row("AAPL", investment_score=15.0)]

    issues = check_snapshot_against_universe(snapshot, universe)

    assert any("investment_score" in issue for issue in issues)


def test_confidence_out_of_range_is_flagged() -> None:
    universe = [_universe_entry("AAPL")]
    snapshot = [_snapshot_row("AAPL", confidence=1.5)]

    issues = check_snapshot_against_universe(snapshot, universe)

    assert any("confidence" in issue for issue in issues)


def test_unrecognized_health_grade_is_flagged() -> None:
    universe = [_universe_entry("AAPL")]
    snapshot = [_snapshot_row("AAPL", health_grade="Z")]

    issues = check_snapshot_against_universe(snapshot, universe)

    assert any("health_grade" in issue for issue in issues)


def test_unrecognized_verdict_is_flagged() -> None:
    universe = [_universe_entry("AAPL")]
    snapshot = [_snapshot_row("AAPL", verdict="모름")]

    issues = check_snapshot_against_universe(snapshot, universe)

    assert any("verdict" in issue for issue in issues)


def test_unscored_ticker_with_blank_fields_is_clean() -> None:
    universe = [_universe_entry("MUFG")]
    snapshot = [
        _snapshot_row(
            "MUFG",
            investment_score=None,
            confidence=None,
            health_grade="",
            verdict="미채점",
            attractiveness_grade="평가불가",
        )
    ]

    assert check_snapshot_against_universe(snapshot, universe) == []
