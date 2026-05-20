"""Tests for Track EE substance metrics in the #592 benchmark harness (#641).

The #592 benchmark previously scored *vocabulary* (does the word "Dung" appear?)
rather than *computation* (was a Dung framework actually built?). A strong 0-shot
LLM name-drops formal methods and scores equal. These tests cover the new metrics
that measure unfakeable substance: convergence depth and computed artifacts, plus
the fix for the cross-text section-heading false-positive.
"""

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "scripts"
    / "scda_deepsynthesis_vs_baseline.py"
)


@pytest.fixture(scope="module")
def bench():
    spec = importlib.util.spec_from_file_location("scda_bench_ee", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# A pipeline-style report: concrete computed artifacts + convergent verdicts.
PIPELINE_LIKE = """
## 5. Dialectical Structure (Dung)
**Framework**: conversational_dung (32 arguments, 26 attacks)
**Attack relations:**
- `fallacy_Post hoc` -> `arg_1`
- `fallacy_Straw man` -> `arg_2`
**Grounded extension**: `arg_10`, `arg_11`, `arg_12`
The grounded extension contains 27 argument(s): arg_10, arg_11, arg_12.

## 6. Belief Revision Trace
4 beliefs contracted (4 -> 0).
ASPIC framework built: 7 strict, 9 defeasible, 11 surviving, 5 defeated.

## Convergent Verdicts (cross-method agreement)
**Verdict convergent sur arg_1** : 5 methodes independantes concourent a le signaler.
**Verdict convergent sur arg_2** : 3 methodes independantes concourent a le signaler.
"""

# A 0-shot-style report: describes frameworks abstractly, computes nothing.
BASELINE_LIKE = """
## Analyse rhetorique
Cadre ASPIC+/Dung : les arguments sont attaquables par rebuttal, undermining,
undercutting. Encadrement argumentatif (Dung) : on pourrait formaliser quelques
arguments en logique propositionnelle ou ASPIC+ pour montrer ou les attaques
s'appliquent. Aucune extension calculee n'est fournie ici.
"""


class TestConvergenceDepth:
    def test_counts_verdicts_and_max(self, bench):
        conv = bench.count_convergence_depth(PIPELINE_LIKE)
        assert conv["verdict_count"] == 2
        assert conv["max_convergence"] == 5
        assert conv["total_method_signals"] == 8

    def test_zero_for_namedrop_baseline(self, bench):
        conv = bench.count_convergence_depth(BASELINE_LIKE)
        assert conv["verdict_count"] == 0
        assert conv["max_convergence"] == 0

    def test_accent_insensitive(self, bench):
        text = "**Verdict convergent sur arg_3** : 4 méthodes indépendantes."
        conv = bench.count_convergence_depth(text)
        assert conv["verdict_count"] == 1
        assert conv["max_convergence"] == 4


class TestComputedArtifacts:
    def test_pipeline_has_all_artifacts(self, bench):
        art = bench.detect_computed_artifacts(PIPELINE_LIKE)
        assert "grounded_extension_members" in art
        assert art["attack_edge_list"] >= 2
        assert "inconsistency_measures" in art
        assert art["jtms_retraction_count"] == 4

    def test_baseline_namedrop_has_none(self, bench):
        art = bench.detect_computed_artifacts(BASELINE_LIKE)
        # Describing Dung/ASPIC abstractly yields no concrete computed artifact.
        assert art == {}

    def test_grounded_phrase_without_members_not_counted(self, bench):
        # The mere phrase "grounded extension" must not count without a member set.
        text = "We could compute the grounded extension to see what survives."
        art = bench.detect_computed_artifacts(text)
        assert "grounded_extension_members" not in art


class TestCrossTextFalsePositiveFix:
    def test_empty_section_negation_is_false(self, bench):
        text = "## 8. Cross-Text Rhetorical Parallels\n\n_No cross-text parallels in this run (single-corpus analysis)._"
        assert bench.detect_cross_text_parallels(text) is False

    def test_heading_alone_is_false(self, bench):
        text = "## 8. Cross-Text Rhetorical Parallels\n\n(section present, no content)"
        assert bench.detect_cross_text_parallels(text) is False

    def test_populated_content_is_true(self, bench):
        text = "Ce motif récurrent apparaît aussi ailleurs ; comparaison avec un autre corpus."
        assert bench.detect_cross_text_parallels(text) is True


class TestVerdictRubricIntegration:
    def test_analyze_report_exposes_new_dimensions(self, bench):
        analysis = bench.analyze_report(PIPELINE_LIKE)
        assert analysis["convergence"]["verdict_count"] == 2
        assert "jtms_retraction_count" in analysis["computed_artifacts"]

    def test_baseline_analysis_lacks_substance(self, bench):
        analysis = bench.analyze_report(BASELINE_LIKE)
        assert analysis["convergence"]["verdict_count"] == 0
        assert analysis["computed_artifacts"] == {}
