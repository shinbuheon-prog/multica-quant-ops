"""Typed adapter over the Cowork fundamentals pipeline's own output artifacts.

Design decision (docs/FUNDAMENTALS_INTEGRATION.md, Phase 6): this package does
NOT re-implement the LLM-driven scoring pipeline (universe curation, sector
classification, per-ticker rubric scoring in score5_full.py..score8_full.py,
factor/panel/signal/backtest layers in pipeline/s0_universe.py..s7_backtest.py).
That pipeline is ~6,000+ lines carrying hundreds of ticker-specific research
judgment calls accumulated over many sessions (survivorship-bias bookkeeping,
sector reclassifications with cited rationale, IPO/listing-date handling,
non-10-Q filer flags, etc.) and is already regression-tested by its own
verify_pipeline.py (286 checks as of 2026-09-03). Re-deriving those scores a
second time in this repo would create two copies of the same business logic
that must be kept in sync by hand on every ticker addition -- exactly the
kind of drift risk this project avoids elsewhere ("지어내지 않는다").

Instead, this package treats the pipeline's own CSV exports as the single
source of truth and adds:
  - typed, validated loaders for those CSVs (`universe`, `snapshot`)
  - cross-file consistency checks that a hand-edited CSV or a broken sync
    step could violate (`consistency`)

so that multica-quant-ops can consume fundamentals data without trusting an
untyped CSV blindly, while never claiming to independently re-verify a score
the Cowork pipeline produced.
"""
