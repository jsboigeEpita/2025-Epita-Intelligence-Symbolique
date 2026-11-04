# -*- coding: utf-8 -*-
"""#3389 — a « … » span in the reader's prose is compared with the document.

The v1 panel's cycle 0 measured three defects the report could not see about
itself: an Act III that printed an invitation the document does not carry (one
pronoun changed), an Act II that printed a French translation of an English
document as the document's words, and exact quotes that stayed untranslated in
a French prose. Nothing compared those spans with the text:
``reader_vocabulary_check`` (#3319) catches a pre-computed verdict between
« », and the readability gate treats every span as quoted data and skips it.

The witnesses below are the issue's DoD, one class per ask:

- **one rule, one producer** — the judge's ``document_quote`` check and the
  render's spans are located by the same implementation (``quote_fidelity``),
  which folds case, whitespace and typographic apostrophes and reads ``[…]``
  as a gap;
- **three labels at write time** — ``verbatim`` / ``translation`` /
  ``unverified``, on the writer's own prose, while the document is in memory;
- **the degradation, never the silence** — an ``unverified`` span loses its
  guillemets and reads as the paraphrase it is; the act records the count, and
  the readability gate reports it;
- **no fuzzy matching** — a span the document does not carry is not located by
  approximation, and an exact span passes BYTE-IDENTICAL (the control that
  must stay green on both trees).

Synthetic vocabularies only — no corpus text, opaque ids only.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.acts import RestitutionActs
from argumentation_analysis.reporting.restitution.quote_fidelity import (
    TRANSLATION,
    UNVERIFIED,
    VERBATIM,
    classify_span,
    normalise_for_citation,
    normalised_quote_in,
    occurs_in_document,
    sanitize_act_quotes,
    sanitize_document_quotes,
)
from argumentation_analysis.reporting.restitution.readability_gate import (
    ReadabilityGate,
)

# ---------------------------------------------------------------------------
# Synthetic documents — invented words, no corpus text
# ---------------------------------------------------------------------------

#: French source. The sentences are long enough for the language probe and
#: carry no corpus vocabulary.
_RAW_FR = (
    "Le comité invite les participants à se rendre dans la salle commune avant "
    "midi. Le secrétariat rappelle que les documents préparatoires restent "
    "consultables au bureau. Aucune décision ne sera prise sans quorum."
)

#: The same document, one pronoun changed — the panel's measured defect on a
#: French document. Every other word is the document's.
_ALTERED = (
    "Le comité invite les participants à se rendre vous-mêmes dans la salle "
    "commune avant midi."
)
_EXACT = (
    "Le comité invite les participants à se rendre dans la salle commune avant midi."
)

#: English source — a French render can only print a TRANSLATION of it.
_RAW_EN = (
    "The committee invites the participants to gather in the common room "
    "before noon. The secretariat recalls that the preparatory documents stay "
    "available at the office. No decision will be taken without a quorum."
)
_EXACT_EN = (
    "The committee invites the participants to gather in the common room "
    "before noon."
)
_FRENCH_RENDERING = (
    "Le comité invite les participants à se réunir dans la salle commune avant midi."
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _stub(text: str):
    async def llm_callable(_prompt: str) -> str:
        return text

    return llm_callable


# ---------------------------------------------------------------------------
# Ask 1 — one rule, one producer
# ---------------------------------------------------------------------------


class TestOneRuleOneProducer:
    """The judge's citation rule and the render's are ONE implementation."""

    def test_the_judge_folds_case_and_typographic_apostrophes(self):
        """On main ``is_cited`` was case-SENSITIVE and folded nothing else, so
        the judge and the render could disagree on what "the document says"."""
        import scripts.dataset.judge_panel as jp

        document = "L’assemblée accepte la thèse alpha dans la sémantique préférée."
        # the judge types a straight apostrophe and other capitals, the
        # document carries a curly apostrophe and a lower-case start
        assert jp.is_cited(document, "L'ASSEMBLÉE accepte la thèse alpha")
        assert normalised_quote_in(document, "L'ASSEMBLÉE accepte la thèse alpha")

    def test_the_judge_reads_the_gap_marker_like_the_render(self):
        """``[…]`` is a gap for both — on main the judge's copy had no gap rule."""
        import scripts.dataset.judge_panel as jp

        quote = (
            "Le comité invite les participants […] dans la salle commune avant midi."
        )
        assert jp.is_cited(_RAW_FR, quote)
        assert occurs_in_document(quote, _RAW_FR)

    def test_the_judge_keeps_its_length_floor(self):
        """Control (green on both trees): a word or two is a keyword, not a
        citation — the floor is the JUDGE's rule and it stays."""
        import scripts.dataset.judge_panel as jp

        assert not jp.is_cited(_RAW_FR, "comité")

    def test_the_two_surfaces_agree_on_every_sample(self):
        import scripts.dataset.judge_panel as jp

        samples = [
            (_RAW_FR, _EXACT),
            (_RAW_FR, _ALTERED),
            (_RAW_EN, _EXACT_EN),
            (normalise_for_citation("a  b"), "a b"),
        ]
        for text, quote in samples:
            assert jp.is_cited(text, quote) == normalised_quote_in(text, quote)


# ---------------------------------------------------------------------------
# Ask 2 — three labels, at write time
# ---------------------------------------------------------------------------


class TestTheThreeLabels:
    def test_a_verbatim_span_is_verbatim(self):
        assert classify_span(_EXACT, _RAW_FR) == VERBATIM

    def test_a_changed_pronoun_is_unverified(self):
        """The panel's measured defect: Act III's « » carried words the
        document does not contain."""
        assert classify_span(_ALTERED, _RAW_FR) == UNVERIFIED

    def test_a_french_rendering_of_an_english_document_is_a_translation(self):
        assert classify_span(_FRENCH_RENDERING, _RAW_EN) == TRANSLATION

    def test_an_unproven_language_never_licenses_a_translation(self):
        """Anti-#1019: a probe that cannot answer proves nothing, so a span it
        cannot compare is unverified, not a translation."""
        assert classify_span(_FRENCH_RENDERING, _RAW_EN, lang="unknown") == UNVERIFIED


# ---------------------------------------------------------------------------
# R1141 rework — the language belongs to the document that was read
# ---------------------------------------------------------------------------


#: A shared 2 000-character head carrying none of the detector's function
#: words, so the probe's verdict comes from what each document adds after it —
#: the corpus's shape: extracts cut from one source, headers that repeat.
_NEUTRAL_HEAD = ("qwvk zrn mpxl btf gjd wzs " * 100)[:2000]
_LONG_FR = _NEUTRAL_HEAD + (
    "Le comité invite les participants à se rendre dans la salle commune avant "
    "midi. Le secrétariat rappelle que les documents préparatoires restent "
    "consultables au bureau de la délégation. Aucune décision ne sera prise "
    "sans quorum. La presidente de la séance précise que les échanges restent "
    "limités aux points inscrits pour l'ordre du jour de la session."
) * 2
_LONG_EN = _NEUTRAL_HEAD + (
    "The committee invites the participants to gather in the common room "
    "before noon. The secretariat recalls that the preparatory documents stay "
    "available at the office of the delegation. No decision will be taken "
    "without a quorum. The chairperson states that the exchanges remain "
    "limited to the items listed on the agenda of the session."
) * 2


class TestLanguageBelongsToTheDocument:
    """R1141: two documents sharing their head must not share a language.

    The first cut cached the detected language under the first 2 000
    characters — a prefix slice, and a collision: the second of two documents
    cut from one source inherited the first's language, and its non-verbatim
    spans were labelled translations of a language it is not written in.
    """

    def test_same_head_different_documents_different_languages(self):
        from argumentation_analysis.reporting.restitution.quote_fidelity import (
            document_language,
        )

        first = document_language(_LONG_FR)
        second = document_language(_LONG_EN)
        assert (first, second) == ("fr", "en")

    def test_the_second_documents_render_is_not_read_in_the_firsts_language(self):
        """The harm behind the collision: with the French twin read first, the
        English document's render would be counted unverified (its language
        read as French) instead of the translation it is."""
        assert classify_span(_FRENCH_RENDERING, _LONG_FR) == UNVERIFIED
        assert classify_span(_FRENCH_RENDERING, _LONG_EN) == TRANSLATION


# ---------------------------------------------------------------------------
# Ask 3+4 — the policy and the degradation
# ---------------------------------------------------------------------------


class TestTheDegradation:
    def test_an_unverified_span_loses_its_guillemets_and_keeps_its_words(self):
        """Born red on main: the span stayed between « », so the reader read a
        paraphrase as the document's words."""
        prose = f"Le locuteur écrit : « {_ALTERED} » puis il conclut."
        audit = sanitize_document_quotes(prose, _RAW_FR)
        assert audit.unverified == 1
        assert audit.text == f"Le locuteur écrit : {_ALTERED} puis il conclut."
        assert "«" not in audit.text

    def test_a_translation_printed_as_the_documents_words_is_degraded(self):
        """Ask 3: a translation is never printed between « » on its own — the
        original goes between « », and it is not mechanically recoverable from
        the rendering, so the rendering becomes a paraphrase."""
        prose = f"L'auteur écrit : « {_FRENCH_RENDERING} »"
        audit = sanitize_document_quotes(prose, _RAW_EN)
        assert audit.translation == 1
        assert audit.text == f"L'auteur écrit : {_FRENCH_RENDERING}"
        assert "(trad." not in audit.text

    def test_an_exact_span_passes_byte_identical(self):
        """Control (green on both trees): a correct render is not touched."""
        prose = f"Le locuteur écrit : « {_EXACT} » puis il conclut."
        audit = sanitize_document_quotes(prose, _RAW_FR)
        assert audit.verbatim == 1
        assert audit.degraded == 0
        assert audit.text == prose

    def test_an_exact_foreign_quote_is_counted_as_untranslated(self):
        """Ask 3's other half: the original stays between « », and the fact
        that a French reader gets no rendering is COUNTED, not glossed over."""
        prose = f"L'auteur écrit : « {_EXACT_EN} »"
        audit = sanitize_document_quotes(prose, _RAW_EN)
        assert audit.verbatim == 1
        assert audit.untranslated == 1
        assert audit.text == prose  # exact quotes are never rewritten

    def test_a_rendering_beside_the_original_is_not_counted(self):
        prose = f"L'auteur écrit : « {_EXACT_EN} » (trad. : {_FRENCH_RENDERING})"
        audit = sanitize_document_quotes(prose, _RAW_EN)
        assert audit.verbatim == 1
        assert audit.untranslated == 0

    def test_a_missing_document_is_not_a_reason_to_strip_anything(self):
        """Anti-#1019: without the text nothing can be proven, so the prose is
        returned untouched with zero counts — never degraded on suspicion."""
        prose = f"« {_ALTERED} »"
        audit = sanitize_document_quotes(prose, "")
        assert audit.text == prose
        assert audit.spans == 0 and audit.degraded == 0

    def test_a_prose_without_span_is_untouched(self):
        prose = "Le locuteur écrit une paraphrase sans guillemets."
        audit = sanitize_act_quotes(prose, SimpleNamespace(raw_text=_RAW_FR), "Acte I")[
            0
        ]
        assert audit == prose

    def test_the_motif_carries_counts_and_never_a_span(self):
        """Privacy: the record may travel to the appendix, the document's words
        may not (#3249, #3389's privacy paragraph)."""
        prose = f"« {_ALTERED} »"
        text, motif = sanitize_act_quotes(
            prose, SimpleNamespace(raw_text=_RAW_FR), "Acte III"
        )
        assert "1 citation(s)" in motif
        assert "Acte III" in motif
        assert "comité" not in motif
        assert "vous-mêmes" not in motif
        assert "vous-mêmes" in text  # the words stay, the guillemets go


# ---------------------------------------------------------------------------
# Gaps — ``[…]`` is an elision, never a wildcard
# ---------------------------------------------------------------------------


class TestGaps:
    def test_a_gap_matches_across_the_elision(self):
        assert occurs_in_document(
            "Le comité invite […] la salle commune avant midi.", _RAW_FR
        )

    def test_a_gap_never_reorders_the_fragments(self):
        """The fragments must occur IN ORDER — a gap is not a licence to
        reassemble the document."""
        assert not occurs_in_document("la salle commune […] Le comité invite", _RAW_FR)

    def test_a_gap_only_span_is_not_a_citation(self):
        assert not occurs_in_document("[…]", _RAW_FR)


# ---------------------------------------------------------------------------
# The three acts use the seam, and the gate reports the count
# ---------------------------------------------------------------------------


def _act_state(**fields) -> SimpleNamespace:
    """The Acte I shape: metadata, stakes, coverage, and the raw text."""
    base = dict(
        act1_framing="",
        act2_narrative="",
        act3_conclusion="",
        source_metadata={"genre": "discours politique"},
        stakes_and_stakeholders={
            "stakes": [{"stake_type": "décision", "description": f"point {i}"}]
            for i in range(3)
        },
        stakeholders=[],
        identified_arguments={"arg_1": "Une revendication défendue par un exemple."},
        identified_fallacies={},
        analysis_coverage={},
        reading_window_status=None,
        raw_text=_RAW_FR,
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _act2_state(**fields) -> SimpleNamespace:
    base = dict(
        identified_arguments={
            "arg_1": "Une revendication défendue par un raisonnement causal étayé.",
        },
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
        raw_text=_RAW_FR,
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _act3_state(**fields) -> SimpleNamespace:
    """The Acte III non-triviality gates need five axes, so the state is rich."""
    base = dict(
        identified_arguments={
            "arg_1": "Le locuteur disqualifie l'adversaire par une attaque personnelle.",
            "arg_2": "Une revendication défendue par un raisonnement causal étayé.",
        },
        identified_fallacies={
            "fl_1": {
                "target_argument_id": "arg_1",
                "family": "ad hominem",
                "type": "ad hominem circonstanciel",
                "taxonomy_path": "racine > sophismes de pertinence > ad hominem",
                "justification": (
                    "L'argument attaque la personne plutôt que la thèse, ce qui "
                    "détache la conclusion des motifs."
                ),
            }
        },
        argument_quality_scores={
            "arg_1": {"overall": 4.2, "scores": {"pertinence": 3.0, "clarte": 5.0}},
            "arg_2": {"overall": 7.8, "scores": {"pertinence": 8.0, "coherence": 7.5}},
        },
        counter_arguments=[
            {
                "target_arg_id": "arg_1",
                "strategy": "contre-exemple",
                "counter_content": (
                    "On peut attaquer la thèse sans attaquer la personne, ce qui "
                    "montre que le procès personnel est superflu."
                ),
            }
        ],
        dung_frameworks={
            "fw_1": {
                "name": "verification_grounded",
                "arguments": ["arg_1", "arg_2"],
                "attacks": [["arg_2", "arg_1"]],
                "extensions": {"all_members": ["arg_2"]},
                "semantics": "grounded",
            }
        },
        propositional_analysis_results=[{"satisfiable": True}, {"satisfiable": False}],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
        raw_text=_RAW_FR,
    )
    base.update(fields)
    return SimpleNamespace(**base)


class TestTheActsUseTheSeam:
    def test_act_one_degrades_a_span_the_document_does_not_carry(self):
        """Born red on main: the act kept the guillemets and filed nothing."""
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            build_act1_framing,
        )

        woven = (
            "### Le texte\n\n"
            f"Le locuteur écrit : « {_ALTERED} » puis il conclut.\n\n"
            "### Les enjeux\n\nCe qui se joue est une décision collective."
        )
        result = _run(build_act1_framing(_act_state(), llm_callable=_stub(woven)))
        assert "«" not in result.narrative
        assert _ALTERED in result.narrative
        motif = result.degraded.get("act1_quote_fidelity", "")
        assert "1 citation(s)" in motif and "Acte I" in motif

    def test_act_one_leaves_an_exact_quote_byte_identical(self):
        """Control (green on both trees): the correct act is not rewritten."""
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            build_act1_framing,
        )

        woven = (
            "### Le texte\n\n"
            f"Le locuteur écrit : « {_EXACT} » puis il conclut.\n\n"
            "### Les enjeux\n\nCe qui se joue est une décision collective."
        )
        result = _run(build_act1_framing(_act_state(), llm_callable=_stub(woven)))
        assert f"« {_EXACT} »" in result.narrative
        assert "act1_quote_fidelity" not in result.degraded

    def test_act_two_degrades_a_span_the_document_does_not_carry(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_narrative,
        )

        woven = f"Le récit cite : « {_ALTERED} » et poursuit son mouvement."
        result = _run(build_act2_narrative(_act2_state(), llm_callable=_stub(woven)))
        assert "«" not in result.narrative.split("**Bornes")[0]
        assert "act2_quote_fidelity" in result.degraded

    def test_act_three_degrades_a_span_the_document_does_not_carry(self):
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            build_act3_conclusion,
        )

        woven = (
            "Le propos se conclut sur une invitation, et l'acte la cite : "
            f"« {_ALTERED} »."
        )
        result = _run(build_act3_conclusion(_act3_state(), llm_callable=_stub(woven)))
        assert result.status == "woven", result.degraded
        assert "«" not in result.narrative.split("**Bornes")[0]
        motif = result.degraded.get("act3_quote_fidelity", "")
        assert "1 citation(s)" in motif and "Acte III" in motif


class TestTheGateReportsTheCount:
    def test_the_quote_motif_reaches_the_gate_verdict(self):
        """Ask 4: the readability gate reports that count — the acts file the
        motive in ``degraded``, which ``check_acts`` reads for the act."""
        motif = (
            "Acte I : « … » comparés au document à l'écriture — 0/1 fidèle(s) ; "
            "1 citation(s) retirée(s) des guillemets (0 traduction(s) de la "
            "langue source, 1 non retrouvée(s) dans le document) — elles se "
            "lisent désormais comme des paraphrases (#3389)."
        )
        acts = RestitutionActs(
            act1_framing="Un acte lisible, sans énumération ni identifiant brut.",
            act2_narrative="Un second acte lisible, en prose continue.",
            act3_conclusion="Un troisième acte lisible, qui conclut.",
            degraded={"act1_framing": motif},
        )
        verdict = ReadabilityGate().check_acts(acts)
        assert any(
            "1 citation(s) retirée(s) des guillemets" in r for r in verdict.reasons
        ), verdict.reasons
