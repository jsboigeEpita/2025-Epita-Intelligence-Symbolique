"""#3238 — « le vote social-choice » is a code-written English token on the
reader surface.

The R1110c paid pass (issue #3238) showed Act II saying « Le vote
social-choice désigne lui aussi cette réponse comme l'option arrivée en
tête ». The token is not the model's: ``cited_units.governance_origin``
returns ``"le vote social-choice"`` as the origin label of a
``vote_aggregate`` winner (:267), ``render_governance_lead`` grafts it onto
the GOUVERNANCE line of BOTH acts' prompts (act2:1953, act3:3138 — one
shared renderer, R1078), and the writer copies prompt tokens — the #3225
pattern. ``check_reader_vocabulary`` passed the sentence.

Census of the code-written governance lines (the issue's second box —
every literal the renderer and its callees write, verified per constant):

* ``governance_origin`` labels — ``"le vote social-choice"`` (THE defect,
  fixed here); ``"une recommandation de stratégie du modèle"`` ✓ French;
  ``"une médiation de conflit"`` ✓ French; the note
  ``"méthode de vote recommandée par le modèle"`` ✓;
  ``GOVERNANCE_MODEL_WARNING`` ✓ French throughout;
* the « méthode interne « {method} » » interpolations — the producer's
  method value, measured on this seat's 49 stored states:
  ``social_choice`` ×15, ``agent_based`` ×33. DELIBERATE (anti-pendulum:
  the internal method name stays in the state and on the data side of the
  prompt), and both acts' consignes forbid copying it by name
  (act2:2317, act3:3468 : « token snake_case (agent_1, social_choice…) »);
* the robustness band literals (``qualitative_support_band``) and the vote
  tail — French throughout.

So the fix is the label, and the check learns the token class. Both
spellings — the hyphenated label and the snake_case internal name — are
machinery on the reader surface; the vocabulary check FAILs either at
first hit, letter-bounded both sides like the P1/P2/P3 class (#3225).

Population measured on this seat (49 stored states, 144 act bodies): the
token reaches 0 act bodies — the 2 known hits (R1110c Act II and one
campaign state) are on the coordinator's 81-state corpus; this witness
proves the same property locally and the R1110c replay box stays on the
coordinator's seat (#3243 precedent).
"""

from __future__ import annotations

import ast
import glob
import os
from pathlib import Path

import pytest

from argumentation_analysis.reporting.restitution import (
    act2_narrative_plugin,
    act3_conclusion_plugin,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.cited_units import (
    governance_origin,
    render_governance_lead,
)
from argumentation_analysis.reporting.restitution.reader_vocabulary_check import (
    check_reader_vocabulary,
)


def _method_token_re():
    """Lazy: the class does not exist on unrepaired main — each test that
    needs it reddens on its own instead of failing the whole collection."""
    from argumentation_analysis.reporting.restitution.reader_vocabulary_check import (
        _METHOD_TOKEN_RE,
    )

    return _METHOD_TOKEN_RE


# The R1110c Act II sentence (issue #3238) — writer-produced French about
# the vote, no corpus text.
_R1110C_SENTENCE = (
    "Le vote social-choice désigne lui aussi cette réponse comme "
    "l'option arrivée en tête."
)

# The two other origin labels of the same function, verbatim — the census
# asserts they already speak the reader's French.
_LLM_LABEL = "une recommandation de stratégie du modèle"
_MEDIATION_LABEL = "une médiation de conflit"

_STORED_STATES = sorted(
    glob.glob(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "..",
            "..",
            "argumentation_analysis",
            "evaluation",
            "results",
            "campaign_2841_lecture",
            "04_annexes",
            "states",
            "state_full_*.json",
        )
    )
)

_ACT_KEYS = ("act1_framing", "act2_narrative", "act3_conclusion")


def _stored_act_bodies() -> list[tuple[str, str]]:
    """The stored act bodies (file stem, body) — skipped cleanly on CI."""
    import json

    bodies: list[tuple[str, str]] = []
    for path in _STORED_STATES:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for key in _ACT_KEYS:
            value = data.get(key)
            if isinstance(value, str) and value:
                bodies.append((f"{os.path.basename(path)}:{key}", value))
    return bodies


class TestTheVoteOriginLabelSpeaksTheReadersFrench:
    def test_the_label_names_the_vote_in_reader_terms(self) -> None:
        """Born red: main returns « le vote social-choice » (:267)."""
        _warning, origin, _note, kind = governance_origin("vote_aggregate")
        assert kind == "vote"
        assert origin == "le vote de la délibération"

    def test_the_shared_lead_carries_no_hyphenated_english(self) -> None:
        """The one renderer both acts graft — fixing it fixes both prompts
        (the R1110c base was 1 + 1 hyphenated tokens)."""
        _warning, lead = render_governance_lead(
            "social_choice",
            "option_a",
            "le texte synthétique de l'unité retenue",
            "vote_aggregate",
        )
        assert "social-choice" not in lead
        # Anti-pendulum: the vote itself stays spoken, as the deliberation's
        # choice — never hidden.
        assert "vote" in lead.lower()

    def test_both_acts_route_through_the_one_renderer(self) -> None:
        """The census's structural half: act2 AND act3 call the shared
        renderer — one label, both prompts, no drift."""

        def _calls_render(module: object) -> bool:
            tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8-sig"))
            return any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "render_governance_lead"
                for node in ast.walk(tree)
            )

        assert _calls_render(act2_narrative_plugin)
        assert _calls_render(act3_conclusion_plugin)

    def test_the_two_other_origin_labels_are_checked_the_same_way(self) -> None:
        """The census's remaining labels: French, no hyphenated English."""
        for provenance, expected in (
            ("llm_resolution", _LLM_LABEL),
            ("conflict_resolution", _MEDIATION_LABEL),
        ):
            _warning, origin, _note, _kind = governance_origin(provenance)
            assert origin == expected
            assert not _method_token_re().search(origin)


class TestTheCheckKnowsTheTokenClass:
    def test_the_r1110c_act2_sentence_flags(self) -> None:
        """Born red: check_reader_vocabulary passes the sentence on main."""
        verdict = check_reader_vocabulary(_R1110C_SENTENCE)
        assert verdict.band == "FAIL"
        assert any("social-choice" in r for r in verdict.reasons)

    def test_the_snake_case_form_flags_too(self) -> None:
        verdict = check_reader_vocabulary(
            "La méthode social_choice a retenu l'option arrivée en tête."
        )
        assert verdict.band == "FAIL"

    def test_the_fixed_sentence_passes(self) -> None:
        """The repaired surface reads clean — the reader keeps the vote."""
        verdict = check_reader_vocabulary(
            "Le vote de la délibération désigne cette réponse comme "
            "l'option arrivée en tête."
        )
        assert verdict.band == "PASS"

    def test_french_social_and_choix_do_not_flag(self) -> None:
        """False-positive control: the French words that share letters."""
        verdict = check_reader_vocabulary(
            "Le climat social du pays pèse sur le choix des mots, dit " "l'orateur."
        )
        assert verdict.band == "PASS"

    def test_reinserted_label_is_caught_by_the_check(self) -> None:
        """Mutation (DoD 3): putting the label back — the writer copying
        the old origin label — reddens here and in the class tests."""
        _warning, lead = render_governance_lead(
            "social_choice",
            "option_a",
            "le texte synthétique",
            "vote_aggregate",
        )
        reverted = lead.replace("le vote de la délibération", "le vote social-choice")
        assert "social-choice" in reverted, "the mutation did not take"
        assert check_reader_vocabulary(reverted).band == "FAIL"


class TestTheHierarchyInstructionNamesTheP1Role:
    """The #3225 held edit (this PR's second commit): the Act III hierarchy
    instruction hands the writer the French role BESIDE the label — the
    same gesture as « l'identifiant interne… décris-le par son RÔLE ». The
    P1/P2/P3 vocabulary class catches the copies; this witness pins the
    prompt side that removes the temptation. Born red on the pre-edit
    prompt (« les P1 d'abord », no role named)."""

    def test_both_instruction_sites_carry_the_french_role(self) -> None:
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            build_act3_evidence,
            build_act3_prompt,
        )

        state = UnifiedAnalysisState("texte synthétique sans valeur de corpus")
        prompt = build_act3_prompt(build_act3_evidence(state))
        # The HIÉRARCHIE instruction — the ordering site.
        assert "les P1 (points décisifs) d'abord" in prompt
        # The QUESTION instruction — the verdict-derivation site.
        assert "(les points décisifs, P1, d'abord)" in prompt


@pytest.mark.skipif(not _STORED_STATES, reason="no stored states on this seat")
class TestTheStoredActBodies:
    def test_every_carrier_is_flagged(self) -> None:
        """Population form of the no-false-positive measurement: a stored
        act body carrying the token MUST be flagged, never passed. On this
        seat's 144 bodies the carrier count is 0 (the 2 known hits live on
        the coordinator's corpus) — a carrier that appears later is a real
        defect and this witness must hold."""
        carriers = 0
        for _name, body in _stored_act_bodies():
            if _method_token_re().search(body):
                carriers += 1
                assert check_reader_vocabulary(body).band == "FAIL", _name
        # The measurement this test encodes (2026-10-25, 49 states):
        assert carriers == 0
