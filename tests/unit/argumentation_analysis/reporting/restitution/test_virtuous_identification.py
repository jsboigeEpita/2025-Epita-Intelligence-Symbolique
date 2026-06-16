"""Tests for R5 volet-1 virtuous-text identification (spec §5.1).

Deterministic: synthetic definitions, no JVM, no LLM, no real dataset. Pins:
- dual-schema prose extraction (extract_text vs full_text)
- candidate screen (sweet spot + low lexical signal)
- rarity bands (fail-loud on a thin pool)
- privacy HARD: opaque IDs only, no source_name / no prose value in outputs

The candidate list is UNCONFIRMED by design — the DERIVED virtuous flag needs a
pipeline run (spec §5.1). Tests assert that honest caveat is present.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.reporting.restitution.virtuous_identification import (
    VirtuousCandidate,
    VirtuousInventory,
    _extract_prose,
    _opaque_id,
    identify,
    render_inventory_report,
)

# --- synthetic corpus builders --------------------------------------------

# A long, clean (low lexical-signal) prose — repeated benign filler. Density ~0.
_CLEAN_PROSE = (
    "Le comite a examine les donnees disponibles et conclut, "
    "apres deliberation, qu'une approche graduelle est preferable. "
) * 80  # ~6400 chars, no fallacy lexical markers


def _src_a(extracts):
    """Schema A source: extract_text prose."""
    return {"extracts": [{"extract_text": t} for t in extracts]}


def _src_b(extracts):
    """Schema B source: full_text prose."""
    return {"extracts": [{"full_text": t} for t in extracts]}


def _high_signal_prose(n_chars: int = 4000) -> str:
    # pack the imperative + generalisation markers densely
    base = "Tous les experts affirment que nous devons agir. "
    reps = max(1, n_chars // len(base))
    return base * reps


# --- prose extraction -----------------------------------------------------


class TestProseExtraction:
    def test_schema_a_extract_text(self):
        assert _extract_prose({"extract_text": "hello"}) == "hello"

    def test_schema_b_full_text(self):
        assert _extract_prose({"full_text": "world"}) == "world"

    def test_schema_a_preferred_over_full_text(self):
        # extract_text is primary for schema A
        ex = {"extract_text": "a", "full_text": "b"}
        assert _extract_prose(ex) == "a"

    def test_metadata_only_returns_none(self):
        assert _extract_prose({"extract_name": "x", "start_marker": "m"}) is None

    def test_blank_string_treated_as_absent(self):
        assert _extract_prose({"extract_text": "   "}) is None


# --- candidate screen -----------------------------------------------------


class TestCandidateScreen:
    def test_clean_sweet_spot_text_is_candidate(self):
        defs = [_src_a([_CLEAN_PROSE])]  # ~6400 chars, density 0
        inv = identify(defs)
        assert inv.candidate_count == 1
        c = inv.candidates[0]
        assert c.opaque_id == "src_0_ext_0"
        assert c.signal_total == 0
        assert c.signal_density == 0.0

    def test_too_short_excluded(self):
        defs = [_src_a(["court " * 50])]  # ~300 chars
        inv = identify(defs)
        assert inv.candidate_count == 0
        assert inv.excluded_too_short == 1

    def test_too_long_excluded(self):
        defs = [_src_a(["x" * 60000])]  # 60k > 50k ceiling
        inv = identify(defs)
        assert inv.candidate_count == 0
        assert inv.excluded_too_long == 1

    def test_high_signal_excluded(self):
        defs = [_src_a([_high_signal_prose(4000)])]  # dense fallacy lexicon
        inv = identify(defs)
        assert inv.candidate_count == 0
        assert inv.excluded_high_signal == 1

    def test_schema_b_full_text_candidate(self):
        defs = [_src_b([_CLEAN_PROSE])]
        inv = identify(defs)
        assert inv.candidate_count == 1
        assert inv.candidates[0].opaque_id == "src_0_ext_0"

    def test_candidates_ordered_lowest_density_first(self):
        # one clean (density 0), one with a single weak marker (density >0 but <=0.2)
        # — exactly ONE lexical hit keeps density under the candidate ceiling.
        defs = [
            _src_a([_CLEAN_PROSE]),
            _src_a([_CLEAN_PROSE + " Un passage cite un expert. "]),
        ]
        inv = identify(defs)
        assert inv.candidate_count == 2
        assert inv.candidates[0].signal_density <= inv.candidates[1].signal_density
        assert inv.candidates[1].signal_total == 1  # exactly one marker


# --- rarity ---------------------------------------------------------------


class TestRarity:
    def test_thin_pool(self):
        inv = VirtuousInventory(
            total_sources=1,
            total_extracts=2,
            text_extracts=2,
            metadata_only_extracts=0,
            candidates=[VirtuousCandidate("src_0_ext_0", 3000, 0, 0.0)],
        )
        assert inv.rarity == "THIN"

    def test_scarce_pool(self):
        cands = [VirtuousCandidate(f"src_{i}_ext_0", 3000, 0, 0.0) for i in range(4)]
        inv = VirtuousInventory(1, 4, 4, 0, candidates=cands)
        assert inv.rarity == "SCARCE"

    def test_adequate_pool(self):
        cands = [VirtuousCandidate(f"src_{i}_ext_0", 3000, 0, 0.0) for i in range(6)]
        inv = VirtuousInventory(1, 6, 6, 0, candidates=cands)
        assert inv.rarity == "ADEQUATE"

    def test_empty_pool_is_thin_fail_loud(self):
        # no candidate => THIN (the gap is reported, not padded) — anti-pendule
        inv = VirtuousInventory(1, 5, 5, 0)
        assert inv.rarity == "THIN"
        assert inv.candidate_count == 0


# --- composition metrics --------------------------------------------------


class TestComposition:
    def test_counts_and_brackets(self):
        defs = [
            _src_a([_CLEAN_PROSE]),  # sweet spot
            _src_a(["x" * 100]),  # tiny
            _src_a(["metadata_only"]),  # no — this has text; use real metadata
            {"extracts": [{"extract_name": "m"}]},  # metadata-only (no text)
        ]
        inv = identify(defs)
        assert inv.total_sources == 4
        assert inv.total_extracts == 4
        assert inv.text_extracts == 3
        assert inv.metadata_only_extracts == 1
        assert inv.candidate_count == 1
        assert inv.size_brackets.get("no_text") == 1

    def test_multiple_sources_indexing(self):
        defs = [_src_a([_CLEAN_PROSE]), _src_b([_CLEAN_PROSE])]
        inv = identify(defs)
        ids = {c.opaque_id for c in inv.candidates}
        assert ids == {"src_0_ext_0", "src_1_ext_0"}


# --- privacy HARD ---------------------------------------------------------


class TestPrivacy:
    def test_report_has_no_source_name(self):
        defs = [
            {
                "source_name": "SECRET_SOURCE_DO_NOT_LEAK",
                "extracts": [{"extract_text": _CLEAN_PROSE}],
            }
        ]
        inv = identify(defs)
        report = render_inventory_report(inv)
        assert "SECRET_SOURCE_DO_NOT_LEAK" not in report
        assert "source_name" not in report

    def test_report_has_no_prose_value(self):
        marker = "UNIQUEPROSEMARKER_NEVER_IN_REPORT"
        defs = [_src_a([_CLEAN_PROSE + marker])]
        inv = identify(defs)
        report = render_inventory_report(inv)
        assert marker not in report

    def test_opaque_id_format(self):
        assert _opaque_id(3, 7) == "src_3_ext_7"

    def test_report_states_unconfirmed_caveat(self):
        # the honest caveat (candidates unconfirmed, pipeline needed) must be present
        defs = [_src_a([_CLEAN_PROSE])]
        report = render_inventory_report(identify(defs))
        assert "pipeline" in report.lower()
        assert "unconfirmed" in report.lower() or "not assert" in report.lower()
