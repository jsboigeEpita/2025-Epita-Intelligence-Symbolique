"""#1986 — encompassment axis detector: mechanics + dev-corpus coherence.

What these tests prove (and what they deliberately do NOT):

- The three-state contract (#1977): ``None`` (could-not-evaluate) is
  produced by unparseable output / undecidable criteria / too-short text,
  and NEVER collapses into ``False``.
- The firing rule is deterministic in code: the LLM judges criteria, the
  verdict is computed — a stub returning a fixed rubric drives it.
- The dev corpus annotations (the hand-authored master) satisfy the
  published rule — a mutated annotation must redden the coherence check.

What they do NOT prove: that a real LLM applies the rubric well. That is
the validation pass over the dev corpus (results under gitignored
``argumentation_analysis/evaluation/results/``), reported on the PR by
opaque reference only.
"""

import json
from pathlib import Path

import pytest

from argumentation_analysis.evaluation.encompassment import (
    EncompassmentError,
    EncompassmentVerdict,
    assess_encompassment,
    verdict_from_criteria,
)

pytestmark = pytest.mark.no_jvm_session

CORPUS_PATH = (
    Path(__file__).resolve().parents[3]
    / "fixtures"
    / "encompassment"
    / "dev_corpus_1986.json"
)


def _load_corpus() -> dict:
    with open(CORPUS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _rubric(c1, c2, c3, c4, wrap_fences=False) -> str:
    body = (
        '{"c1": %s, "c2": %s, "c3": %s, "c4": %s, '
        '"q1": "soldats de la légion", "q2": "nous sommes un seul corps", '
        '"q3": "les hordes du nord", "q4": "fini pour toujours", '
        '"note": "adresse de masse complète"}'
    ) % (
        json.dumps(c1),
        json.dumps(c2),
        json.dumps(c3),
        json.dumps(c4),
    )
    if wrap_fences:
        return "Voici mon évaluation :\n```json\n" + body + "\n```\nMerci."
    return body


def _jdump(v):
    return "null" if v is None else ("true" if v else "false")


# ---------------------------------------------------------------------------
# Firing rule — the deterministic core
# ---------------------------------------------------------------------------


class TestFiringRule:
    def test_full_form_fires(self):
        assert verdict_from_criteria({"c1": True, "c2": True, "c3": True, "c4": True})

    def test_closure_only_shape_fires_without_enemy(self):
        """The closure-only shape (C3 refused, C4 held) MUST fire — the
        disjunction is what keeps a text that absorbs its audience without
        naming an enemy from being a negative defined by construction.

        NB: this shape is NOT an empirical description of witness
        ``20a53f0c``. The held-out measurement reads that witness with C3
        true 3/3 and C4 false 2/3 — it fires through the OTHER disjunct.
        The item calibrates the branch; it does not portray the witness."""
        assert verdict_from_criteria({"c1": True, "c2": True, "c3": False, "c4": True})

    def test_closure_disjunct_either_side(self):
        assert verdict_from_criteria({"c1": True, "c2": True, "c3": True, "c4": False})

    def test_no_closure_rejected(self):
        assert (
            verdict_from_criteria({"c1": True, "c2": True, "c3": False, "c4": False})
            is False
        )

    def test_constitutive_pair_required(self):
        for c3, c4 in [(True, True), (True, False), (False, True)]:
            assert (
                verdict_from_criteria({"c1": False, "c2": True, "c3": c3, "c4": c4})
                is False
            )
            assert (
                verdict_from_criteria({"c1": True, "c2": False, "c3": c3, "c4": c4})
                is False
            )

    def test_undecidable_constitutive_criterion_is_none(self):
        assert (
            verdict_from_criteria({"c1": None, "c2": True, "c3": True, "c4": True})
            is None
        )
        assert (
            verdict_from_criteria({"c1": True, "c2": None, "c3": True, "c4": True})
            is None
        )

    def test_both_closures_undecidable_is_none(self):
        """Even with the constitutive pair decided, an undecidable closure
        disjunct is None — not a fabricated negative."""
        assert (
            verdict_from_criteria({"c1": True, "c2": True, "c3": None, "c4": None})
            is None
        )

    def test_one_decided_closure_rescues_the_disjunct(self):
        assert (
            verdict_from_criteria({"c1": True, "c2": True, "c3": None, "c4": False})
            is False
        )
        assert verdict_from_criteria({"c1": True, "c2": True, "c3": None, "c4": True})


# ---------------------------------------------------------------------------
# assess_encompassment mechanics (stub LLM — FB-29/38 injectable pattern)
# ---------------------------------------------------------------------------


class TestAssessMechanics:
    def test_stub_positive_rubric_fires(self):
        v = assess_encompassment(
            "Un texte assez long pour porter les quatre critères.",
            lambda p: _rubric(True, True, True, True),
        )
        assert v.state is True
        assert v.fired
        assert v.criteria == {"c1": True, "c2": True, "c3": True, "c4": True}
        assert "hordes" in v.evidence["q3"]

    def test_stub_negative_rubric_rejects(self):
        v = assess_encompassment(
            "Un texte assez long pour porter les quatre critères.",
            lambda p: _rubric(False, False, False, False),
        )
        assert v.state is False
        assert not v.fired

    def test_witness_shape_rubric_fires(self):
        v = assess_encompassment(
            "Un texte assez long pour porter les quatre critères.",
            lambda p: _rubric(True, True, False, True),
        )
        assert v.state is True

    def test_fenced_json_is_parsed(self):
        v = assess_encompassment(
            "Un texte assez long pour porter les quatre critères.",
            lambda p: _rubric(True, True, True, False, wrap_fences=True),
        )
        assert v.state is True

    def test_unparseable_output_is_none_not_false(self):
        v = assess_encompassment(
            "Un texte assez long pour porter les quatre critères.",
            lambda p: "Je pense que ce texte est très oratoire !",
        )
        assert v.state is None
        assert "unparseable" in v.reason

    def test_missing_criterion_key_is_none(self):
        v = assess_encompassment(
            "Un texte assez long pour porter les quatre critères.",
            lambda p: '{"c1": true, "c2": true, "q1": "..."}',
        )
        assert v.state is None
        assert "missing criterion" in v.reason

    def test_wrong_typed_criterion_is_none(self):
        v = assess_encompassment(
            "Un texte assez long pour porter les quatre critères.",
            lambda p: '{"c1": "oui", "c2": true, "c3": true, "c4": true}',
        )
        assert v.state is None
        assert "must be true/false/null" in v.reason

    def test_null_criterion_yields_none_with_names(self):
        v = assess_encompassment(
            "Un texte assez long pour porter les quatre critères.",
            lambda p: _rubric(None, None, None, None),
        )
        assert v.state is None
        assert "c1" in v.reason and "c2" in v.reason

    def test_empty_text_is_none(self):
        v = assess_encompassment("   ", lambda p: _rubric(True, True, True, True))
        assert v.state is None
        assert "too short" in v.reason

    def test_no_llm_raises_fail_loud(self):
        with pytest.raises(EncompassmentError, match="no LLM callable"):
            assess_encompassment("Un texte assez long.", None)

    def test_prompt_carries_the_text_and_the_anti_lexical_rule(self):
        seen = {}

        def spy(prompt: str) -> str:
            seen["prompt"] = prompt
            return _rubric(True, True, True, True)

        assess_encompassment("Le texte soumis à la sonde du prompt.", spy)
        assert "Le texte soumis" in seen["prompt"]
        assert "STRUCTURE" in seen["prompt"]
        assert "sans la structure ne vaut pas true" in seen["prompt"]


# ---------------------------------------------------------------------------
# Dev corpus — integrity, coherence with the rule, mutation control
# ---------------------------------------------------------------------------


class TestDevCorpus:
    def test_corpus_loads_with_expected_shape(self):
        data = _load_corpus()
        items = data["items"]
        assert (
            10 <= len(items) <= 20
        ), f"#1986 DoD: dev corpus must hold 10-20 items, got {len(items)}"
        ids = [it["id"] for it in items]
        assert len(set(ids)) == len(ids), "duplicate ids in dev corpus"
        for it in items:
            assert it["text"] and isinstance(it["text"], str)
            assert it["expected"] in (True, False, None)
            assert set(it["criteria"]) == {"c1", "c2", "c3", "c4"}

    def test_corpus_has_both_firing_shapes_and_the_witness_mirror(self):
        data = _load_corpus()
        by_cat = [it["category"] for it in data["items"]]
        assert by_cat.count("positif_plein") >= 3
        assert (
            by_cat.count("positif_sans_extrusion") >= 2
        ), "the closure-only shape (fires without C3) must be represented"
        assert any(
            it["expected"] is None for it in data["items"]
        ), "the None boundary needs a live calibration item"
        assert any(
            it["category"] == "negatif_nous_deliberatif" for it in data["items"]
        ), "the anti-lexical control (nous without structure) must be present"

    def test_annotations_satisfy_the_published_rule(self):
        """The master annotations ARE the rule applied — any divergence is a
        spec or an annotation bug."""
        data = _load_corpus()
        for it in data["items"]:
            computed = verdict_from_criteria(it["criteria"])
            assert computed == it["expected"], (
                f"dev item {it['id']!r}: annotated expected={it['expected']} "
                f"but the published rule computes {computed} from its own "
                f"criteria {it['criteria']}"
            )

    def test_mutation_of_an_annotation_reddens_the_coherence_check(self):
        """Negative control for the check above: flipping one annotation
        MUST be caught — proves the coherence test can fail."""
        data = _load_corpus()
        victim = next(it for it in data["items"] if it["category"] == "positif_plein")
        mutated = dict(victim)
        mutated["criteria"] = dict(victim["criteria"], c2=False)
        computed = verdict_from_criteria(mutated["criteria"])
        assert (
            computed != mutated["expected"]
        ), "mutation invisible to the rule — coherence control is vacuous"

    def test_stub_returns_the_master_rubric_end_to_end(self):
        """Mechanical round-trip: a stub that answers with each item's OWN
        annotation drives the detector to exactly the annotated verdict.
        Proves the plumbing corpus→prompt→parse→rule; says nothing about a
        real LLM's judgment."""
        data = _load_corpus()
        for it in data["items"]:
            expected_rubric = (
                '{"c1": %s, "c2": %s, "c3": %s, "c4": %s, '
                '"q1": "", "q2": "", "q3": "", "q4": "", "note": "stub"}'
            ) % (
                _jdump(it["criteria"]["c1"]),
                _jdump(it["criteria"]["c2"]),
                _jdump(it["criteria"]["c3"]),
                _jdump(it["criteria"]["c4"]),
            )
            v = assess_encompassment(it["text"], lambda p: expected_rubric)
            assert v.state == it["expected"], (
                f"item {it['id']!r}: stub master-rubric gave {v.state}, "
                f"annotated {it['expected']}"
            )
