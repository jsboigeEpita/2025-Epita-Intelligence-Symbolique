"""#3229 — the formal synthesis container republishes every phase's output.

``add_formal_synthesis_report`` stores ``phase_results`` verbatim, so the
container carries every formal phase's NL — including the Dung extensions
(the same claim texts pass 4c opacifies under ``dung_frameworks``) and source
quotes under quote-named keys. #1702 froze the gap pending a triage that never
happened; measured on a real state: 634 distinct NL paths and 1 695 strings
survive ``sanitize_state`` under this single container, 686 of them argument
text the scrubber strips one field away.

Reader census (the issue's decision rule, export side): NO script reads
``formal_synthesis_reports[*].phase_results`` from a sanitized export — the
five ``.analysis_kb`` consumers read counts (``identified_arguments``...),
the acts, and ``structured_arg_status``; the live-state readers (restitution,
synthesis) are not the question. Decision: **drop ``phase_results`` from the
export** — the entry keeps its scrubbed ``summary`` and its structural
aggregates (``overall_validity``...). The in-memory field and its writer are
untouched (the live readers keep them).

Born red on the unrepaired module: the canary planted through the real
producer survives under the container.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation.sanitize_state import sanitize_state

# Synthetic strings invented for this witness — they appear in no corpus.
_CANARY = "CANARY_3229 le texte de phase que le sanitiseur doit retirer de l'export"
_CANARY2 = "CANARY_3229_b la citation source rangee sous une cle quote"


@pytest.fixture(autouse=True)
def _synthetic_opaque_salt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the salt the scrubber demands (#1973) — everything here is fabricated."""
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-3229")


def _state_with_one_report() -> UnifiedAnalysisState:
    """One report planted through the real producer, canaries in phase_results.

    Shapes mirror the real writers: the Dung extensions republish claim texts,
    the fallacy axis stores a quote of the source under a quote-named key.
    """
    state = UnifiedAnalysisState("texte synthetique sans valeur de corpus")
    state.add_formal_synthesis_report(
        summary=_CANARY,
        phase_results={
            "dung_extensions": {
                "all_extensions": {
                    "conflict_free": {"extensions": [[_CANARY], [_CANARY2]]},
                }
            },
            "fol": {"message": _CANARY},
            "hierarchical_fallacy": {
                "per_argument_fallacies": [
                    {"problematic_quote": _CANARY2, "fallacy": "ad_hominem"}
                ]
            },
        },
        overall_validity=0.5,
    )
    return state


def _strings(obj: object) -> list[str]:
    found: list[str] = []
    if isinstance(obj, str):
        found.append(obj)
    elif isinstance(obj, dict):
        for key, value in obj.items():
            found.append(str(key))
            found.extend(_strings(value))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            found.extend(_strings(item))
    return found


class TestPhaseResultsIsDroppedFromTheExport:
    def test_no_canary_survives_under_the_container(self) -> None:
        out = sanitize_state(_state_with_one_report().get_state_snapshot())
        reports = out.get("formal_synthesis_reports") or []
        assert reports, (
            "the container itself vanished — the entry must stay (scrubbed "
            "summary + structural aggregates); drop phase_results only"
        )
        assert not any(
            "CANARY_3229" in s for s in _strings(reports)
        ), "a phase_results canary survived the sanitized export"

    def test_the_entry_keeps_summary_and_structural_aggregates(self) -> None:
        """The control: the fix cannot be « drop the report entry »."""
        out = sanitize_state(_state_with_one_report().get_state_snapshot())
        (entry,) = out["formal_synthesis_reports"]
        assert isinstance(entry, dict)
        assert "phase_results" not in entry, "phase_results must be dropped"
        assert (
            entry.get("overall_validity") == 0.5
        ), "a structural aggregate was lost — only phase_results goes"
        assert (
            "summary" not in entry
        ), "the summary keeps its pass-5 drop (scrubbed, as before this fix)"
