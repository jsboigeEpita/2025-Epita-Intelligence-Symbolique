"""#1624 — pin the relation between the two state-reading surfaces in restitution.

The restitution reads the shared state through TWO divergent surfaces:

1. PROSE — ``build_act{1,2,3}_evidence(state)`` in the ``act*_plugin`` modules
   reads its axes via ``getattr(state, "<key>")`` / ``state["<key>"]`` and feeds
   the three-act narrative (the conducted prompt).
2. ANNEXE — ``state_adapter._STATE_KEYS`` enumerates the axes the appendix
   attests as "disponible", and ``appendix._provenance_counts`` renders them.

Same state, two reading lists, different keys. Before this guard, a future
divergence (an axis added to one surface but not the other) would pass
silently — the report could attest "disponible" for an axis the conclusion
never mobilised, or omit one it did. This module pins the relation explicitly
so any divergence fails instead of drifting.

The file-disjoint wiring is deliberate (``state_adapter.py`` header, lines 6-8):
the adapter does not import the prose plugins, and the plugins do not import
``_STATE_KEYS``. The two lists are not mutualised — THIS TEST carries the
accord between them (same shape as the #1619 corrective).

Falsifiability — two degenerate substitutions with disjoint kill-sets:

* **Sub A** — remove ``"aspic_results"`` from ``state_adapter._STATE_KEYS``:
  the key sits in the intersection since #1667, so ``prose - annexe`` GAINS it
  and ``test_annexe_prose_relation_is_pinned`` fails (``PROSE_ONLY`` does not
  list it). ``test_ast_prose_matches_baseline`` survives (it does not read
  ``_STATE_KEYS``). Kill-set = {relation, projection} — re-measured after
  #1624 added ``test_every_declared_key_survives_the_projection``, which the
  same substitution also trips. The claim was {relation} alone when written;
  a falsifiability note that is never re-run decays exactly like the guard it
  describes.
* **Sub B** — delete the ``getattr(state, "deanonymized", ...)`` call in
  ``act1_framing_plugin.build_act1_evidence``: the AST extraction loses
  ``deanonymized``, so ``test_ast_prose_matches_baseline`` fails
  (``PROSE_BASELINE`` still contains it). ``test_annexe_prose_relation_is_pinned``
  survives (it compares against the literal, not the AST). Kill-set = {baseline}.

The two substitutions kill different tests, so neither assertion is vacuous.

#1624 closes the annexe side: the appendix now attests the three axes the prose
mobilises and it was silent about, and each rendered dimension declares whether
the conclusion reads it (``appendix._MOBILISATION``). That declaration is a
second claim about the same state, so it gets the same treatment — five more
substitutions, each killing a different set:

* **Sub C** — drop ``"debate_transcripts"`` from ``_STATE_KEYS``: kills the
  relation, the projection guard, and the adapter test (3).
* **Sub D** — declare ``arg_structuree`` a plain ``"prose"`` dimension instead
  of ``"failure_only"``: kills exactly one test, the fourth-case guard. Nothing
  else can see that mislabel, which is why it has its own assertion.
* **Sub E** — declare ``synthese_formelle`` mobilised: kills the
  declaration/AST agreement and the "present but unread" state (2).
* **Sub F** — make ``_mobilisation_notes`` return ``"mobilisée"``
  unconditionally: kills 6, i.e. every assertion about the column's content.
  A constant column is the degenerate case the whole class exists to exclude.
* **Sub G** — remove the ``gouvernance`` row from ``_provenance_counts``: kills
  the declaration/row coverage and the two count assertions (3).
"""

from __future__ import annotations

import ast
import pathlib
from typing import Any, Dict

from argumentation_analysis.reporting.restitution import state_adapter as _sa
from argumentation_analysis.reporting.restitution.appendix import (
    _MOBILISATION,
    _mobilisation_notes,
    _provenance_counts,
    render_appendix,
)
from argumentation_analysis.reporting.restitution.state_adapter import (
    _STATE_KEYS,
    state_to_appendix_mapping,
)


def _full_state() -> Dict[str, Any]:
    """A projection where every declared dimension carries something.

    Synthetic atoms only (privacy HARD — no corpus tokens). Shapes match what the
    writers produce, not what is convenient: ``fol_analysis_results`` is the list
    of per-theory dicts the #1290 reader expects, ``structured_arg_status`` the
    per-capability ledger.
    """
    return {
        "identified_arguments": {"a1": {}},
        "identified_fallacies": {"f1": {}},
        "counter_arguments": [{"strategy": "distinction"}],
        "argument_quality_scores": {"a1": 0.7},
        "fol_analysis_results": [{"consistent": True, "message": "ok"}],
        "propositional_analysis_results": [{"consistent": True}],
        "modal_analysis_results": [{"consistent": True}],
        "dung_frameworks": {"dung_1": {"name": "dung_arbitration"}},
        "aspic_results": [{"id": "aspic_1", "extensions": [["a"]]}],
        "belief_revision_results": [{"method": "dalal"}],
        "bipolar_results": [{"supports": [["a", "b"]]}],
        "debate_transcripts": [{"turns": []}, {"turns": []}],
        "governance_decisions": [{"method": "borda"}],
        "structured_arg_status": {
            "aspic_plus_reasoning": {
                "capability": "aspic_plus_reasoning",
                "status": "evaluated",
                "degraded": False,
                "reason": "",
                "extension_count": 1,
            }
        },
        "narrative_synthesis": "synthèse",
        "final_conclusion": "conclusion",
        "formal_synthesis_reports": [{"axis": "fol"}],
        "workflow_results": {"deep_synthesis_value_gates": {"VG1": True}},
    }


# The prose modules live alongside state_adapter in the same package — locate
# them via the package path rather than counting parents from this test file.
_BASE = pathlib.Path(_sa.__file__).resolve().parent
_PROSE_MODULES = (
    "act1_framing_plugin.py",
    "act2_narrative_plugin.py",
    "act3_conclusion_plugin.py",
    # #1911 — the global-projection helper is a prose module: it reads state to
    # feed the acts' conducted prompts, so its ``getattr(state, ...)`` calls
    # belong to the prose reading surface the sweep measures.
    "global_projection.py",
    # #1914 — the specialist-role classifier is a prose module of the same
    # family: it reads state to feed the acts' citation hierarchy.
    "specialist_roles.py",
)


def _prose_keys_read_from_state() -> set[str]:
    """Conservative superset of state keys read by the three prose modules.

    Walks every ``getattr(state, "<key>")`` and ``state["<key>"]`` across the
    act-plugin modules. These modules contain only prose code, so every state
    access in them is on the prose reading surface — including accesses inside
    the helpers that ``build_act{1,2,3}_evidence`` delegates to (e.g.
    ``_derive_genre``, ``detect_virtuous_mode``).
    """
    keys: set[str] = set()
    for mod in _PROSE_MODULES:
        tree = ast.parse((_BASE / mod).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "getattr"
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "state"
                and isinstance(node.args[1], ast.Constant)
            ):
                keys.add(node.args[1].value)
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == "state"
                and isinstance(node.slice, ast.Constant)
            ):
                keys.add(node.slice.value)
    return keys


# The state keys the three act modules read off ``state`` to build their
# evidence (the PROSE surface). AST-derived conservative superset of the
# transitive accesses made by ``build_act{1,2,3}_evidence`` and its delegates.
#
# Note: ``structured_arg_status`` IS read by the prose (act3 conclusion,
# ``build_act3_evidence`` → the honest-absence ledger at l.685), so it is NOT
# annexe-only despite living in ``_STATE_KEYS`` — it sits in the intersection.
#
# ``aspic_results`` and ``bipolar_results`` joined in #1667, and the move is the
# measurable outcome of that issue rather than bookkeeping. Until then the ONLY
# path from a structured-argumentation axis to the conclusion was
# ``structured_arg_status``, whose collector opens on ``degraded=True``: the
# prose had a vocabulary for the axis that FAILED and none for the axis that
# SUCCEEDED. ``aspic_results`` therefore leaves ANNEXE_ONLY for the
# intersection — the appendix attested "disponible" for an axis the conclusion
# had no way to mobilise, which is precisely the divergence this module exists
# to keep visible.
PROSE_BASELINE = frozenset(
    {
        "argument_quality_scores",
        "aspic_results",
        "belief_revision_results",
        "bipolar_results",
        "counter_arguments",
        "deanonymized",
        "debate_transcripts",
        "dung_frameworks",
        "fol_analysis_results",
        "governance_decisions",
        "identified_arguments",
        "identified_fallacies",
        "modal_analysis_results",
        "propositional_analysis_results",
        "source_metadata",
        "stakes_and_stakeholders",
        "structured_arg_status",
        # #1911 — ``global_projection.py`` reads the bag that carries the
        # deep-synthesis value gates; the key left ANNEXE_ONLY for the
        # intersection. The ``synthese_globale`` appendix row attests the
        # channel, while the bag itself keeps no count row of its own.
        "workflow_results",
    }
)

# Axes the ANNEXE attests (``state_adapter._STATE_KEYS``) that the PROSE never
# reads — declared "disponible" in the appendix table but absent from the
# conclusion's conducted prompt.
#
# ``narrative_synthesis`` joined this set in #1620. It used to sit in the
# intersection: ``build_act3_evidence`` read it — and reduced it to a boolean
# (``narrative_synthesis_available``) that no code ever consumed. Measured on
# three real artifacts, the Acte III prose asserts nothing about a narrative
# synthesis even where the state carries a 5053-char one, so the read guarded
# no claim and was removed. The appendix still attests it, which is why the key
# lands here rather than disappearing: it is genuinely "attested but not
# mobilised" — the exact divergence this module exists to keep visible.
#
# ``final_conclusion`` joined in the same change, from the other direction: it
# was never projected at all, so the appendix could not see the synthesis the
# conversational voie writes. It is carried now (``_STATE_KEYS``) and the prose
# still does not read it — annexe-only by construction, not by attrition.
ANNEXE_ONLY = frozenset(
    {
        "final_conclusion",
        "formal_synthesis_reports",
        "narrative_synthesis",
        # ``workflow_results`` left this set in #1911: the global projection
        # (a prose module) reads the bag for the deep-synthesis value gates,
        # moving the key to the intersection (PROSE_BASELINE ∩ _STATE_KEYS).
    }
)

# Axes the PROSE reads that the ANNEXE never attests — mobilised by the
# conclusion but invisible to the appendix provenance table.
#
# This set held four keys until #1624 closed the annexe side. ``bipolar_results``
# (which had joined the prose in #1667), ``debate_transcripts`` and
# ``governance_decisions`` are now carried by ``_STATE_KEYS`` and rendered by
# the appendix: a report whose conclusion leans on the deliberation and on the
# governance vote no longer omits both from its own coverage table.
#
# ``deanonymized`` stays, and stays deliberately. It is on the prose surface
# (all three acts read it) but it is a rendering flag — are entity names printed
# in clear? — not an analytical dimension, so "disponible / mobilisée" has no
# meaning for it. The justification lives at its site in ``state_adapter.py``.
PROSE_ONLY = frozenset({"deanonymized"})


def test_ast_prose_matches_baseline() -> None:
    """The AST extraction of prose state reads equals the declared baseline.

    Catches both directions: a new ``getattr(state, X)`` in a prose module
    without a baseline update, or a stale baseline entry the prose no longer
    reads.
    """
    assert _prose_keys_read_from_state() == PROSE_BASELINE


def test_annexe_prose_relation_is_pinned() -> None:
    """The annexe/prose divergence is exactly ANNEXE_ONLY / PROSE_ONLY.

    If a future change adds an axis to one surface without the other, the
    set difference shifts and this assertion fails — the divergence becomes a
    deliberate update to these two frozensets, not a silent drift.
    """
    annexe = set(_STATE_KEYS)
    prose = set(PROSE_BASELINE)
    assert annexe - prose == ANNEXE_ONLY
    assert prose - annexe == PROSE_ONLY


class TestMobilisationDeclarationMatchesTheProse:
    """#1624 item 2 — the appendix declares mobilisation; the prose decides it.

    ``appendix._MOBILISATION`` is a literal written at the appendix's own site
    (the two surfaces stay file-disjoint on purpose). These tests are what makes
    that literal answerable to reality instead of being a second, independent
    claim about the same state.
    """

    def test_dimensions_declared_mobilised_are_read_by_the_prose(self) -> None:
        prose = _prose_keys_read_from_state()
        offenders = {
            dim: [k for k in keys if k not in prose]
            for dim, (keys, kind, _site) in _MOBILISATION.items()
            if kind in ("prose", "failure_only")
        }
        offenders = {dim: missing for dim, missing in offenders.items() if missing}
        assert offenders == {}, (
            "these dimensions claim the conclusion reads them, but no act module "
            f"reads the key: {offenders}"
        )

    def test_dimensions_declared_unmobilised_are_absent_from_the_prose(self) -> None:
        # The other direction, and the one that decays silently: an axis wired
        # into the prose later would keep its "non mobilisée" cell and the
        # appendix would under-claim — the mirror of the over-claim #1624 opened
        # on. Understating is less harmful, not harmless.
        prose = _prose_keys_read_from_state()
        wrongly_silent = {
            dim: [k for k in keys if k in prose]
            for dim, (keys, kind, _site) in _MOBILISATION.items()
            if kind == "none"
        }
        wrongly_silent = {d: k for d, k in wrongly_silent.items() if k}
        assert wrongly_silent == {}

    def test_every_declared_key_survives_the_projection(self) -> None:
        # The #1620 trap, documented in ``appendix.py``: the appendix receives a
        # PROJECTION of the state, not the state. A dimension whose key is not in
        # ``_STATE_KEYS`` reads ``None`` in production however correct its
        # declaration is — inert, while passing any unit test built on a raw
        # dict. That is exactly how the first cut of the #1620 fix shipped green
        # and dead.
        carried = set(_STATE_KEYS)
        dropped = {
            dim: [k for k in keys if k not in carried]
            for dim, (keys, _kind, _site) in _MOBILISATION.items()
        }
        dropped = {d: k for d, k in dropped.items() if k}
        assert dropped == {}

    def test_declaration_covers_exactly_the_rendered_rows(self) -> None:
        # No row without a declaration (it would render "non déclarée"), and no
        # declaration without a row (a dead entry drifts out of sight).
        rendered = set(_provenance_counts(_full_state()))
        assert rendered == set(_MOBILISATION)


class TestTheThreeStatesAreDistinguishable:
    """#1624 item 2 — absent / present-and-mobilised / present-not-mobilised."""

    def test_absent_dimension_claims_nothing_about_mobilisation(self) -> None:
        notes = _mobilisation_notes({})
        assert set(notes.values()) == {"—"}

    def test_present_and_mobilised_names_the_act(self) -> None:
        notes = _mobilisation_notes(_full_state())
        assert notes["axe_dung"].startswith("mobilisée")
        assert "acte" in notes["axe_dung"].lower()

    def test_present_but_not_mobilised_says_so(self) -> None:
        notes = _mobilisation_notes(_full_state())
        assert "non mobilisée" in notes["synthese_formelle"]
        assert "non mobilisée" in notes["synthese_narrative"]

    def test_failure_only_is_not_rendered_as_plain_mobilisation(self) -> None:
        # The fourth case: ``structured_arg_status`` reaches the conclusion
        # through the absence collector alone, which opens on ``degraded``. A run
        # where the axis WORKS is mute; a run where it degrades gains a sentence.
        # Rendering that as plain "mobilisée" would read backwards.
        notes = _mobilisation_notes(_full_state())
        assert "seulement si l'axe échoue" in notes["arg_structuree"]
        assert notes["arg_structuree"] != notes["axe_dung"]

    def test_the_three_states_coexist_in_one_render(self) -> None:
        # Not three separate reads of three separate states: one state, three
        # cells. A table whose column is constant would satisfy every assertion
        # above taken alone.
        state = _full_state()
        del state["formal_synthesis_reports"]  # → absent
        notes = _mobilisation_notes(state)
        assert notes["synthese_formelle"] == "—"  # absent
        assert "non mobilisée" in notes["synthese_narrative"]  # present, unread
        assert notes["axe_dung"].startswith("mobilisée")  # present, read
        assert (
            len(
                {
                    notes["synthese_formelle"],
                    notes["synthese_narrative"],
                    notes["axe_dung"],
                }
            )
            == 3
        )


class TestTheNewlyAttestedAxesReachTheTable:
    """#1624 item 3 — the axes the prose mobilises are named by the annexe."""

    def test_deliberation_and_governance_are_counted(self) -> None:
        counts = _provenance_counts(_full_state())
        assert counts["deliberation"] == 2
        assert counts["gouvernance"] == 1

    def test_bipolar_axis_is_attested(self) -> None:
        counts = _provenance_counts(_full_state())
        assert counts["axe_bipolaire"] == "disponible"
        assert _provenance_counts({})["axe_bipolaire"] == "indisponible"

    def test_the_adapter_carries_them_off_a_real_state_object(self) -> None:
        # The projection hop, on an object rather than a dict — ``_STATE_KEYS``
        # is read via ``getattr`` in production.
        class _S:
            debate_transcripts = [{"turns": []}]
            governance_decisions = [{"method": "borda"}]
            bipolar_results = [{"supports": [["a", "b"]]}]

        mapping = state_to_appendix_mapping(_S())
        assert set(mapping) == {
            "debate_transcripts",
            "governance_decisions",
            "bipolar_results",
        }

    def test_rendered_table_carries_the_third_column(self) -> None:
        out = render_appendix(_full_state())
        assert "| Dimension | Valeur | Mobilisation |" in out
        assert "| deliberation | 2 |" in out
        assert "| gouvernance | 1 |" in out
        assert "non mobilisée" in out

    def test_added_rows_carry_counts_not_content(self) -> None:
        # Privacy HARD: the deliberation and governance containers hold turns and
        # ballots; the table must expose their cardinality and nothing else.
        state = _full_state()
        state["debate_transcripts"] = [{"turns": ["CANARY_TOKEN"]}]
        state["governance_decisions"] = [{"rationale": "CANARY_TOKEN"}]
        out = render_appendix(state)
        assert "CANARY_TOKEN" not in out
        assert "| deliberation | 1 |" in out
