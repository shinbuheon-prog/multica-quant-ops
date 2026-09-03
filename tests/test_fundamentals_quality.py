from datetime import datetime

import pytest

from multica_quant_ops.data.quality import (
    DataQualityStatus,
    FundamentalsQualityCheck,
    FundamentalsSnapshot,
    evaluate_equity_rollforward,
    evaluate_fundamentals_change,
)


def _snapshot(symbol: str, metric: str, period_end: str, value: float) -> FundamentalsSnapshot:
    return FundamentalsSnapshot(
        symbol=symbol, metric=metric, period_end=datetime.fromisoformat(period_end), value=value
    )


def test_small_change_passes() -> None:
    previous = _snapshot("MSFT", "revenue", "2026-03-31", 60_000_000_000)
    current = _snapshot("MSFT", "revenue", "2026-06-30", 63_000_000_000)  # +5%

    result = evaluate_fundamentals_change(current, previous, FundamentalsQualityCheck())

    assert result.status == DataQualityStatus.PASS
    assert result.blocks_downstream is False
    assert result.relative_change == pytest.approx(0.05)


def test_large_jump_beyond_threshold_fails() -> None:
    previous = _snapshot("XYZ", "total_assets", "2026-03-31", 10_000_000_000)
    current = _snapshot("XYZ", "total_assets", "2026-06-30", 14_000_000_000)  # +40%

    result = evaluate_fundamentals_change(
        current, previous, FundamentalsQualityCheck(max_relative_change=0.25)
    )

    assert result.status == DataQualityStatus.FAIL
    assert result.blocks_downstream is True
    assert "total_assets" in result.reasons[0]
    assert result.relative_change == pytest.approx(0.40)


def test_sign_flip_always_flags_regardless_of_threshold() -> None:
    previous = _snapshot("ABC", "net_income", "2026-03-31", 500_000_000)
    current = _snapshot("ABC", "net_income", "2026-06-30", -100_000_000)

    result = evaluate_fundamentals_change(
        current, previous, FundamentalsQualityCheck(max_relative_change=100.0)
    )

    assert result.status == DataQualityStatus.FAIL
    assert "flipped sign" in result.reasons[0]


def test_zero_base_with_new_nonzero_value_is_flagged_for_manual_review() -> None:
    previous = _snapshot("NEWCO", "goodwill", "2026-03-31", 0.0)
    current = _snapshot("NEWCO", "goodwill", "2026-06-30", 2_000_000_000)

    result = evaluate_fundamentals_change(current, previous, FundamentalsQualityCheck())

    assert result.status == DataQualityStatus.FAIL
    assert "no prior-period base" in result.reasons[0]


def test_mismatched_symbol_or_metric_raises() -> None:
    previous = _snapshot("AAA", "revenue", "2026-03-31", 100.0)
    current = _snapshot("BBB", "revenue", "2026-06-30", 110.0)

    with pytest.raises(ValueError):
        evaluate_fundamentals_change(current, previous, FundamentalsQualityCheck())


def test_out_of_order_periods_raise() -> None:
    earlier = _snapshot("AAA", "revenue", "2026-03-31", 100.0)
    later = _snapshot("AAA", "revenue", "2026-06-30", 110.0)

    with pytest.raises(ValueError):
        evaluate_fundamentals_change(current=earlier, previous=later, check=FundamentalsQualityCheck())


def test_equity_rollforward_reconciles_within_tolerance() -> None:
    result = evaluate_equity_rollforward(
        symbol="MSFT",
        beginning_equity=250_000_000_000,
        net_income=25_000_000_000,
        other_comprehensive_income=-500_000_000,
        buybacks=6_000_000_000,
        dividends=5_000_000_000,
        ending_equity=263_400_000_000,
    )

    assert result.status == DataQualityStatus.PASS
    assert result.blocks_downstream is False


def test_equity_rollforward_flags_unreconciled_gap() -> None:
    """Synthetic reconstruction of the shape of the GOOGL 2026-06-30 finding
    (docs/FUNDAMENTALS_INTEGRATION.md, sections 1 and 3): reported ending
    equity left a large unexplained gap even after crediting a one-time
    gain on top of ordinary net income.

    These figures are illustrative, not the real filed GOOGL numbers -- the
    point of this test is to pin the *behavior* (an unreconciled roll-forward
    gets flagged, with the gap size reported) as a regression guard, not to
    assert a specific historical figure this project never independently
    re-verified end to end.
    """
    beginning_equity = 550_000_000_000
    ordinary_net_income = 30_000_000_000
    one_time_gain = 98_000_000_000
    net_income = ordinary_net_income + one_time_gain
    reported_ending_equity = 640_480_000_000
    # expected ~= 550B + 128B = 678B; reported is 640.48B -> ~37.5B short,
    # i.e. the same order of magnitude as the originally-flagged gap.

    result = evaluate_equity_rollforward(
        symbol="GOOGL",
        beginning_equity=beginning_equity,
        net_income=net_income,
        ending_equity=reported_ending_equity,
        tolerance_relative=0.03,
    )

    assert result.status == DataQualityStatus.FAIL
    assert result.blocks_downstream is True
    assert "does not reconcile" in result.reasons[0]
    assert result.relative_change is not None
    assert result.relative_change < 0  # reported equity fell short of the roll-forward
