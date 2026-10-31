# -*- coding: utf-8 -*-
"""#3297 — a whole-scope superlative needs a measured ranking to stand on.

R1125a (one paid pass, the coordinator's seat) shipped Act II saying
« Ce résultat est décisif : cet appui reste le plus fragile du dispositif. »
— a superlative over the whole argument set with no fragility ranking in the
state, and two paragraphs later the same report gave another unit more
convergent fragility. #3159 had given the writer the measured ranking AND the
rule (« aucun superlatif portant sur « tout le discours » n'a de base ici »);
nothing read the act after the weaving, so the rule could be broken in
silence — #3134's shape: a rule with no instrument.

Witnesses here (born red on main, where neither the module nor the wiring
exists):

- the R1125a sentence itself flags, EVEN with the ranking line present (the
  defect is not "no ranking" but "ranking not carried by the sentence");
- the three licences hold: measured scope (« de l'ensemble évalué »), the
  ranking base quoted in the sentence, a ranked id named together with a
  ranking word — and Act III's P1-first hierarchy (criterion 4 of the reader
  contract REQUIRES a ranking marker there, so the licence is structural,
  not a courtesy);
- « la plus grande partie » is a share, not a rank — excluded by
  construction (anti-pendulum: « le plus » is never banned in general);
- a tail separated from its head by a clause boundary belongs to the next
  sentence — not flagged (measured: 8 of 46 local whole-scope hits);
- leg 2 (dispatch R1126): the head learns « meilleur(e)(s) » / « pire(s) »
  and the tail learns « du propos » — each measured on the stored states
  BEFORE being kept (head: 14 raw forms, 9 die on the no-tail rule, 5 flag,
  0 idiom false positives; tail: 15 occurrences, never once attached, 0
  hits) — and the two idioms the dispatch named stay silent by construction;
- through the REAL builders: the motive lands in ``degraded`` (hence in
  ``restitution_acts_degraded``), the prose is NOT rewritten, and the motif
  is a code literal carrying no ranking marker — the degraded blockquote
  renders inside the act body and must not satisfy criterion 4 on its own
  (a phantom pass is a false pass).

Synthetic vocabularies only — no corpus text, opaque ids only. The R1125a
sentence is quoted as the defect's literal shape; the local corpus does not
contain it (the paid render lives on the coordinator's seat).

No JVM, no network. The LLM is a stub returning pre-woven prose.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_narrative,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_conclusion,
)
from argumentation_analysis.reporting.restitution.act_reader_contract_check import (
    _RANKED_MARKER_RE,
)
from argumentation_analysis.reporting.restitution.whole_scope_superlative_check import (
    check_whole_scope_superlative,
    whole_scope_superlative_note,
    whole_scope_superlative_sentences,
)

# The R1125a sentence, verbatim shape: the defect this issue repairs.
_R1125A = "Ce résultat est décisif : cet appui reste le plus fragile du dispositif."

# The #3159 ranking line as the producer emits it (same builder, 2 of 2 units).
_RANKING_LINE = (
    "Classement qualité (base : 2 unités évaluées sur 2) : arg_2 (7.8), "
    "arg_1 (4.2). C'est le SEUL classement mesuré — aucun superlatif portant "
    "sur « tout le discours » n'a de base ici."
)


# --- the check itself ---------------------------------------------------------


class TestTheDefect:
    """The R1125a shape and what it is NOT."""

    def test_r1125a_flags_with_the_ranking_present(self):
        """The defect is a sentence that does not carry its ranking — the
        ranking line exists in the act and the sentence ignores it."""
        verdict = check_whole_scope_superlative(_R1125A, ranking_line=_RANKING_LINE)
        assert verdict.band == "FAIL", (
            "the R1125a sentence is a whole-scope superlative with no ranking "
            "carried by the sentence — it must flag even when the act's "
            "ranking line exists"
        )
        assert any("#3297" in r for r in verdict.reasons)

    def test_no_ranking_at_all_still_flags(self):
        """Pre-#3159 acts had no ranking line; the claim is still unbacked."""
        assert check_whole_scope_superlative(_R1125A).band == "FAIL"

    def test_plain_superlative_is_silent(self):
        """Anti-pendulum — a superlative whose scope is NOT the whole report
        (« le plus fragile des deux mouvements ») is ordinary prose."""
        body = "Ce résultat est décisif : cet appui reste le plus fragile des deux mouvements."
        assert check_whole_scope_superlative(body).band == "PASS"
        assert whole_scope_superlative_sentences(body) == []

    def test_the_verdict_reasons_never_quote_the_act(self):
        """The verdict names a count and the issue, never the sentence.

        A reason that quoted the act would carry a corpus sentence onto a
        diagnostic surface the sanitizer does not police (#3249), and the
        ``sentence[:120]`` that built it was a coverage-census site the
        root guard read and the registry did not know (#2850). The sentences
        stay reachable through the public collector; the verdict is not the
        place they leave the report.
        """
        verdict = check_whole_scope_superlative(_R1125A, ranking_line=_RANKING_LINE)
        assert verdict.band == "FAIL"
        flagged = whole_scope_superlative_sentences(_R1125A, ranking_line=_RANKING_LINE)
        assert flagged, "the witness needs a flagged sentence to prove anything"
        for reason in verdict.reasons:
            for sentence in flagged:
                assert sentence.strip()[:40] not in reason, (
                    "the verdict quotes the act; the sentence must stay out "
                    "of the reasons (#3249)"
                )
            assert (
                "«" not in reason
            ), "no quote marks in a reason: it carries a count, not prose"


class TestTheLicences:
    """What backs a whole-scope superlative."""

    def test_measured_scope_is_licensed(self):
        """« de l'ensemble évalué » — the #3159 form: the claim names the
        population it ranks, not the whole report."""
        body = "Cet appui demeure le plus fragile de l'ensemble évalué."
        assert whole_scope_superlative_sentences(body, ranking_line=_RANKING_LINE) == []

    def test_ranking_base_quoted_in_the_sentence_is_licensed(self):
        """The sentence carries « 2 unités évaluées sur 2 » — the reader sees
        how thin the base is."""
        body = (
            "Cet appui demeure le plus fragile du dispositif parmi les 2 "
            "unités évaluées sur 2."
        )
        assert whole_scope_superlative_sentences(body, ranking_line=_RANKING_LINE) == []

    def test_ranked_id_with_a_ranking_word_is_licensed(self):
        """Naming a ranked unit together with a ranking word rests the claim
        on the ranking the act shows."""
        body = (
            "Dans le classement qualité, arg_2 demeure le mieux tenu du " "dispositif."
        )
        assert whole_scope_superlative_sentences(body, ranking_line=_RANKING_LINE) == []

    def test_unranked_id_with_a_ranking_word_still_flags(self):
        """A ranking word alone is not a ranking — the unit must be one the
        line actually ranks (arg_9 is not)."""
        body = "Dans le classement qualité, arg_9 demeure le mieux tenu du dispositif."
        hits = whole_scope_superlative_sentences(body, ranking_line=_RANKING_LINE)
        assert len(hits) == 1

    def test_act3_p1_licence(self):
        """Act III's own ranking is the salience hierarchy: a sentence naming
        the unit it ranks first is licensed — criterion 4 of the reader
        contract REQUIRES a ranking marker there."""
        body = "La vulnérabilité décisive est celle de arg_1 : c'est le point le plus fragile du discours."
        assert whole_scope_superlative_sentences(body, licensed_ids=["arg_1"]) == []
        # Without the licence (or naming a non-P1 unit), the same shape flags.
        assert whole_scope_superlative_sentences(body) != []
        assert whole_scope_superlative_sentences(body, licensed_ids=["arg_2"]) != []


class TestExclusionsByConstruction:
    """What is not a ranking at all."""

    def test_quantifier_share_is_excluded(self):
        """« la plus grande partie » states a share, not a rank."""
        body = "La plus grande partie du discours repose sur ce mouvement."
        assert whole_scope_superlative_sentences(body) == []

    def test_clause_detached_tail_is_not_flagged(self):
        """A tail separated from its head by a clause boundary belongs to the
        NEXT sentence (measured: 8 of 46 local hits were exactly this)."""
        body = "Cet appui reste le plus fragile. Le dispositif repose sur lui."
        assert whole_scope_superlative_sentences(body) == []

    def test_quoted_superlative_is_not_the_reports_claim(self):
        """Inside « … » the words are the speaker's, not the report's."""
        body = "Le locuteur soutient que « son plan est le plus solide du discours », ce que rien ne confirme."
        assert whole_scope_superlative_sentences(body) == []

    def test_id_matching_respects_word_boundaries(self):
        """arg_1 is not inside arg_15 — substring matching would license a
        sentence naming a unit the run never ranked."""
        body = "Dans le classement qualité, arg_15 demeure le mieux tenu du dispositif."
        hits = whole_scope_superlative_sentences(body, ranking_line=_RANKING_LINE)
        assert len(hits) == 1


class TestLeg2Dictionary:
    """The leg-2 extensions, measured before being kept (dispatch R1126).

    Born red on the leg-1 module: the meilleur/pire heads and the « du
    propos » tail are not in its dictionary, so the three flagging witnesses
    below passed silently there. The measured corpus numbers live in the
    module docstring; the witnesses here are synthetic shapes of the same
    families, never corpus text.
    """

    def test_meilleur_head_flags(self):
        """« la meilleure arme du dispositif » — the R1125a shape in the
        meilleur form: whole-report scope, no ranking carried by the
        sentence. Flags even with the ranking line present."""
        body = (
            "Ce résultat est net : cette attaque reste la meilleure arme du dispositif."
        )
        assert (
            check_whole_scope_superlative(body, ranking_line=_RANKING_LINE).band
            == "FAIL"
        )
        assert (
            len(whole_scope_superlative_sentences(body, ranking_line=_RANKING_LINE))
            == 1
        )

    def test_pire_head_flags(self):
        """« le pire point du discours » — the same shape on the pire side."""
        body = "Cette faiblesse demeure le pire point du discours."
        assert check_whole_scope_superlative(body).band == "FAIL"

    def test_du_propos_tail_flags(self):
        """« le plus solide du propos » — the baseline head with the leg-2
        tail: the scope is the whole report, and no licence names it."""
        body = "Ce mouvement demeure le plus solide du propos."
        assert check_whole_scope_superlative(body).band == "FAIL"

    def test_le_meilleur_moyen_is_not_a_ranking(self):
        """The idiom the dispatch named: « le meilleur moyen » states a
        method, not a rank over the report — no whole-scope tail attaches,
        so it stays silent (measured: 9 of 14 raw meilleur/pire heads die
        exactly here)."""
        body = "Le meilleur moyen d'exposer la thèse reste la comparaison continue."
        assert whole_scope_superlative_sentences(body) == []

    def test_le_pire_des_cas_is_excluded_by_construction(self):
        """The second named idiom: « le pire des cas » — the noun after the
        head is « cas », a quantifier, exactly like « la plus grande
        partie ». A share-scenario, never a ranking."""
        body = "Le pire des cas de figure reste une objection laissée sans réponse."
        assert whole_scope_superlative_sentences(body) == []

    def test_meilleur_head_keeps_the_licences(self):
        """The extension rides the same licences as « le plus » — the #3159
        measured scope licenses a meilleur superlative that names the
        population it ranks."""
        body = "Cette attaque demeure la meilleure arme de l'ensemble évalué."
        assert whole_scope_superlative_sentences(body, ranking_line=_RANKING_LINE) == []


# --- through the real builders ------------------------------------------------


def _state(**fields: object) -> SimpleNamespace:
    """Lightweight state stub with the acts' relevant fields."""
    base = dict(
        identified_arguments={},
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
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _scored_state() -> SimpleNamespace:
    """Two identified units, both quality-scored → the #3159 ranking exists."""
    return _state(
        identified_arguments={
            "arg_1": "Un mouvement défendu par un raisonnement causal étayé.",
            "arg_2": "Une revendication appuyée sur une comparaison continue.",
        },
        argument_quality_scores={
            "arg_1": {"overall": 4.2, "scores": {"pertinence": 3.0, "clarte": 5.0}},
            "arg_2": {"overall": 7.8, "scores": {"pertinence": 8.0, "clarte": 7.5}},
        },
    )


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestActTwoWiring:
    """The motive reaches ``degraded``; the prose is never rewritten."""

    def test_motive_recorded_and_prose_kept(self):
        """The stub LLM weaves the R1125a sentence; the real builder must (a)
        record the motive in ``degraded`` — hence in
        ``restitution_acts_degraded`` via the state round-trip — and (b) keep
        the sentence: the repair reports, it does not rewrite (no silent
        rewrite is part of the DoD)."""
        woven = (
            "Premier mouvement : le raisonnement causal tient et porte le "
            "récit. " + _R1125A + " Le jugement du lecteur reste entier."
        )

        async def llm_callable(prompt: str) -> str:  # pragma: no cover - stub
            return woven

        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm_callable))
        assert "act2_whole_scope_superlative" in result.degraded, (
            "the whole-scope superlative motive must reach the act's "
            "degraded map (hence restitution_acts_degraded)"
        )
        assert _R1125A in result.narrative, (
            "the prose is NOT rewritten — the reader sees the claim and the "
            "report carries the reason it is unbacked"
        )

    def test_clean_weave_records_no_motive(self):
        woven = (
            "Premier mouvement : le raisonnement causal tient. "
            "Cet appui demeure le plus solide de l'ensemble évalué."
        )

        async def llm_callable(prompt: str) -> str:  # pragma: no cover - stub
            return woven

        result = _run(build_act2_narrative(_scored_state(), llm_callable=llm_callable))
        assert "act2_whole_scope_superlative" not in result.degraded


class TestActThreeWiring:
    """The P1 licence through the real builder."""

    @staticmethod
    def _state_with_p1() -> SimpleNamespace:
        """A state whose salience ranks arg_1 first (weight 1) — the same
        shape the plugin's own tests use for a broad run."""
        return _state(
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
                        "L'argument attaque la personne plutôt que la thèse."
                    ),
                },
            },
            argument_quality_scores={
                "arg_1": {"overall": 4.2, "scores": {"pertinence": 3.0, "clarte": 5.0}},
                "arg_2": {"overall": 7.8, "scores": {"pertinence": 8.0, "clarte": 7.5}},
            },
            counter_arguments=[
                {
                    "target_arg_id": "arg_1",
                    "strategy": "contre-exemple",
                    "counter_content": (
                        "On peut attaquer la thèse sans attaquer la personne."
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
            propositional_analysis_results=[
                {"satisfiable": True},
                {"satisfiable": False},
            ],
        )

    def test_p1_named_superlative_is_licensed_end_to_end(self):
        """The woven sentence names the unit the salience ranks first —
        criterion 4 needs a ranking marker in Act III and this is the one
        the report itself measured. No motive."""
        woven = (
            "La vulnérabilité décisive est celle de arg_1 : c'est le point le "
            "plus fragile du discours."
        )

        async def llm_callable(prompt: str) -> str:  # pragma: no cover - stub
            return woven

        result = _run(
            build_act3_conclusion(self._state_with_p1(), llm_callable=llm_callable)
        )
        assert "le plus fragile du discours" in result.narrative, (
            "the licensed sentence must survive to the reader (the claim gate "
            "does not remove it — it names a unit, not an axis)"
        )
        assert "act3_whole_scope_superlative" not in result.degraded

    def test_unbacked_superlative_records_the_motive(self):
        woven = (
            "La forme demeure le plus fort du discours, et le lecteur le voit "
            "dès l'ouverture."
        )

        async def llm_callable(prompt: str) -> str:  # pragma: no cover - stub
            return woven

        result = _run(
            build_act3_conclusion(self._state_with_p1(), llm_callable=llm_callable)
        )
        assert "act3_whole_scope_superlative" in result.degraded
        assert woven.split(",")[0] in result.narrative, "no silent rewrite"


class TestTheMotifIsACodeLiteral:
    """The degraded motif must not quote prose nor fake a ranking marker."""

    def test_motif_carries_no_quote_and_no_ranking_marker(self):
        """Two guards in one: (a) ``restitution_acts_degraded`` is tolerated
        by the sanitizer as a closed producer vocabulary (#3249) — quoting
        the act would carry corpus text into it; (b) the motif renders as a
        blockquote INSIDE the act body, so a « le plus » or « classement »
        in it would satisfy criterion 4's marker regex without the act
        carrying a real ranking — a phantom pass."""
        note = whole_scope_superlative_note(_R1125A, act_label="Acte II")
        assert note
        assert "fragile" not in note, "the motif must not quote the prose"
        assert "«" not in note and "»" not in note
        assert _RANKED_MARKER_RE.search(note) is None, (
            "the degraded motif renders inside the act body — it must not "
            "carry a criterion-4 ranking marker on its own"
        )

    def test_licensed_sentence_still_carries_the_criterion4_marker(self):
        """Criterion 4 intact: the licensed P1 sentence — the one the check
        lets stand — is itself a ranking marker for the reader contract."""
        licensed = (
            "La vulnérabilité décisive est celle de arg_1 : c'est le point le "
            "plus fragile du discours."
        )
        assert _RANKED_MARKER_RE.search(licensed) is not None
        assert whole_scope_superlative_sentences(licensed, licensed_ids=["arg_1"]) == []
