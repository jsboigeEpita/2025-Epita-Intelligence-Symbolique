# -*- coding: utf-8 -*-
"""#3307 — the grounded synthesis designates, it does not print ids.

R1127a (paid pass, `doc_A`): the spectacular synthesis prose printed bare
ids outside its ``[artifact:…]`` anchors — ``fallacy_N`` 13, ``ca_N`` 13,
``arg_N`` 27. The ``fallacy_N``/``ca_N`` spike was later measured as
variance (1 pass in 31, attribution to #3303 withdrawn); the bare
``arg_N`` is chronic (0 to 20). What stands: the prompt's rule 5 read
« Identifiants opaques uniquement (Speaker_A, arg_1) » — naming ``arg_1``
as the example ORDERED the machine key into the prose (#3296's defect
class, surviving here because #3303 repaired ``OPAQUE_ID_DIRECTIVE``, not
this prompt), and no check read this prose.

Witnesses, born red on ``b5f515b86``:

- what the writer is TOLD: rule 5 designates a unit, a fallacy or a
  counter by what it says or a reader label, names the machine keys as
  anchor-only, and the old id-ordering clause is gone;
- the anchor channel keeps its ids (positive control: rule 1's verbatim
  citation example still teaches the key);
- VG-5 counts the three classes OUTSIDE anchors — a bare ``fallacy_3``
  fails it while VG-1..VG-4 stay green (isolated failure); the same key
  inside its anchor passes; VG-1's arithmetic is unchanged on the same
  text (the DoD's control, recomputed independently).

Synthetic stubs only — opaque ids, synthetic citation keys, no corpus
text. No JVM, no network, no LLM.
"""

from __future__ import annotations

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)

#: The #3259 shape: four required French sections, every judgement anchored.
#: This is the writer behaving — it passes every gate.
_CLEAN_STUB = """## Motifs transversaux
Le même geste d'esquive revient sur plusieurs cibles [artifact:identified_arguments.arg_1] et franchit les familles de sophismes [artifact:identified_fallacies.f1].

## Évaluation de la stratégie rhétorique
La pression tient lieu de preuve : le locuteur déplace l'enjeu [artifact:counter_arguments.c1] et l'extension admise ne le soutient pas [artifact:dung_frameworks.dung_1].

## Vulnérabilités structurelles
Les croyances rétractées affaiblissent la chaîne [artifact:jtms_beliefs.b1] ; la convergence formelle fait défaut [artifact:propositional_analysis_results.p1].

## Synthèse interprétative
Sous l'examen multi-méthodes, le discours tient par l'autorité, non par la preuve [artifact:identified_arguments.arg_2] [artifact:identified_fallacies.f2]."""

#: The R1127a defect in one sentence: the machine key printed to the reader
#: next to its own anchor (the anchor is right, the designation is missing).
_BARE_FALLACY_STUB = _CLEAN_STUB.replace(
    "Le même geste d'esquive revient sur plusieurs cibles",
    "La dérision repérée sous la clé fallacy_3 revient sur plusieurs cibles",
)


class TestWhatTheWriterIsTold:
    """Rule 5 — the designation the writer receives (#3307's source repair)."""

    def test_rule_5_designates_it_does_not_order_the_key(self):
        """The measured hole was the absence of a designation: rule 5 must
        tell the writer HOW to designate a unit, a fallacy or a counter
        (by what it says / a reader label), and name the machine keys as
        anchor-only — never again teach `arg_1` as a designation example."""
        prompt = DeepSynthesisAgent.GROUNDED_SYNTHESIS_PROMPT
        # The old clause ORDERED the id into the prose — gone.
        assert "Identifiants opaques uniquement" not in prompt
        # A designation for the three classes exists...
        assert "un argument, un sophisme ou un contre-argument" in prompt
        # ...by what the unit says or a reader label...
        assert "ce qu'il dit" in prompt
        # ...and the machine keys are named as living only in the anchor.
        assert "(arg_1, fallacy_3, ca_2)" in prompt
        assert "La clé ne vit" in prompt and "que dans la citation" in prompt

    def test_the_anchor_channel_keeps_its_ids(self):
        """Positive control — the id still reaches the prompt as DATA: rule
        1 keeps teaching the verbatim citation key, which VG-1 counts."""
        prompt = DeepSynthesisAgent.GROUNDED_SYNTHESIS_PROMPT
        assert "[artifact:identified_fallacies.f1]" in prompt


class TestVG5CountsOutsideAnchors:
    """VG-5 — the check that reads this prose (#2980's class, extended)."""

    def test_a_bare_fallacy_key_fails_vg5_and_only_vg5(self):
        """The R1127a shape: a bare `fallacy_3` next to clean prose. VG-5
        fails with the count; VG-1..VG-4 stay green — the failure is
        isolated to the designation defect."""
        gates = DeepSynthesisAgent.validate_value_gates(_BARE_FALLACY_STUB, 4)
        vg5 = gates["vg5_reader_designation"]
        assert vg5["pass"] is False
        assert vg5["bare_machine_ids"] == 1
        assert vg5["by_class"] == {"arg": 0, "fallacy": 1, "ca": 0}
        for earlier in (
            "vg1_citation_density",
            "vg2_state_guard",
            "vg3_no_boilerplate",
            "vg4_transversal_insight",
        ):
            assert gates[earlier]["pass"] is True, earlier
        assert gates["all_pass"] is False

    def test_the_clean_prose_passes_vg5(self):
        """The writer behaving: zero bare key, all gates green."""
        gates = DeepSynthesisAgent.validate_value_gates(_CLEAN_STUB, 4)
        assert gates["vg5_reader_designation"]["pass"] is True
        assert gates["vg5_reader_designation"]["bare_machine_ids"] == 0
        assert gates["all_pass"] is True

    def test_the_key_inside_its_anchor_never_counts(self):
        """The anchor is the data channel: the SAME key inside
        `[artifact:identified_fallacies.fallacy_3]` must not count — only
        its bare copy outside does (stripped vs unstripped)."""
        anchored = (
            "## Motifs transversaux\n"
            "L'esquive la plus nette est la dérision "
            "[artifact:identified_fallacies.fallacy_3], qui revient.\n\n"
            "## Évaluation de la stratégie rhétorique\n"
            "La pression tient lieu de preuve "
            "[artifact:identified_arguments.arg_1].\n\n"
            "## Vulnérabilités structurelles\n"
            "L'extension admise ne soutient pas le geste "
            "[artifact:dung_frameworks.dung_1].\n\n"
            "## Synthèse interprétative\n"
            "Le discours tient par l'autorité [artifact:jtms_beliefs.b1]."
        )
        gates = DeepSynthesisAgent.validate_value_gates(anchored, 4)
        assert gates["vg5_reader_designation"]["pass"] is True

    def test_the_three_classes_each_count(self):
        """arg_N, fallacy_N and ca_N are the three chronic classes — each
        bare occurrence counts, by class."""
        body = _CLEAN_STUB.replace(
            "Le même geste d'esquive revient sur plusieurs cibles",
            "Le geste repéré en arg_7 comme en fallacy_3 et en ca_2 revient",
        )
        gates = DeepSynthesisAgent.validate_value_gates(body, 4)
        vg5 = gates["vg5_reader_designation"]
        assert vg5["pass"] is False
        assert vg5["by_class"] == {"arg": 1, "fallacy": 1, "ca": 1}

    def test_vg1_is_unchanged_on_the_same_text(self):
        """The DoD's control: VG-1's arithmetic is untouched by VG-5 —
        recomputed independently from the same specification
        (>= 1 citation per 200 words, distinct fields counted)."""
        gates = DeepSynthesisAgent.validate_value_gates(_BARE_FALLACY_STUB, 4)
        vg1 = gates["vg1_citation_density"]
        citations = DeepSynthesisAgent.CITATION_RE.findall(_BARE_FALLACY_STUB)
        words = len(_BARE_FALLACY_STUB.split())
        assert vg1["citations"] == len(citations)
        assert vg1["words"] == words
        assert vg1["required_citations"] == max(1, words // 200)
        assert vg1["distinct_fields_cited"] == sorted({field for field, _ in citations})
        assert vg1["pass"] is (len(citations) >= max(1, words // 200))
