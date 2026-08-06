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
  ``annexe - prose`` loses that key, so ``test_annexe_prose_relation_is_pinned``
  fails (``ANNEXE_ONLY`` still contains it). ``test_ast_prose_matches_baseline``
  survives (it does not read ``_STATE_KEYS``). Kill-set = {relation}.
* **Sub B** — delete the ``getattr(state, "deanonymized", ...)`` call in
  ``act1_framing_plugin.build_act1_evidence``: the AST extraction loses
  ``deanonymized``, so ``test_ast_prose_matches_baseline`` fails
  (``PROSE_BASELINE`` still contains it). ``test_annexe_prose_relation_is_pinned``
  survives (it compares against the literal, not the AST). Kill-set = {baseline}.

The two substitutions kill different tests, so neither assertion is vacuous.
"""

from __future__ import annotations

import ast
import pathlib

from argumentation_analysis.reporting.restitution import state_adapter as _sa
from argumentation_analysis.reporting.restitution.state_adapter import _STATE_KEYS

# The prose modules live alongside state_adapter in the same package — locate
# them via the package path rather than counting parents from this test file.
_BASE = pathlib.Path(_sa.__file__).resolve().parent
_PROSE_MODULES = (
    "act1_framing_plugin.py",
    "act2_narrative_plugin.py",
    "act3_conclusion_plugin.py",
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
PROSE_BASELINE = frozenset(
    {
        "argument_quality_scores",
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
        "aspic_results",
        "final_conclusion",
        "formal_synthesis_reports",
        "narrative_synthesis",
        "workflow_results",
    }
)

# Axes the PROSE reads that the ANNEXE never attests — mobilised by the
# conclusion but invisible to the appendix provenance table.
PROSE_ONLY = frozenset(
    {
        "deanonymized",
        "debate_transcripts",
        "governance_decisions",
    }
)


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
