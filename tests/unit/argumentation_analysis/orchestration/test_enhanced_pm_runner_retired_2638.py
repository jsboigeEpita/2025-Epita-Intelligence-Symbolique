"""#2638: the enhanced PM analysis runner stays retired.

The module was deliberately deleted by ``d2fef7b4`` (2025-07-12, "remove
obsolete analysis runners" — DRIFT_REGISTER ORC-4: superseded by
``UnifiedPipeline``, won't restore), then accidentally resurrected by
``f4e39b02`` (2025-10-30, a WIP manual-conflict-resolution commit that
re-added 638 lines a branch still carried). For its whole second life it had
zero production callers, a ``DeprecationWarning`` in its constructor, and a
setup path broken at ``ExtractAgent.setup_agent_components`` — a method its
class had lost on 2025-07-01 (``9a9a620fd``, SK-API migration, removed it from
``ExtractAgent``), so the resurrected runner called an API unanswered for four
months, hidden by #2536's ``MagicMock`` doubles (#2638).

This tombstone reddens if a merge or conflict resolution brings the module
back: a deletion lost to a concurrent branch must surface as a review
decision, not slip in silently.
"""

import importlib.util


def test_the_module_is_gone():
    spec = importlib.util.find_spec(
        "argumentation_analysis.orchestration.enhanced_pm_analysis_runner"
    )
    assert spec is None, (
        "enhanced_pm_analysis_runner est de retour : il avait été retiré "
        "(d2fef7b4, confirmé #2638) — une résurrection doit passer par une "
        "décision review, pas par une résolution de conflit silencieuse"
    )


def test_no_test_still_certifies_its_agent_setup():
    """La double #2536 (MagicMock certifiant une méthode absente) ne revient
    pas avec le module : le fichier témoin est retiré avec lui."""
    from pathlib import Path

    repo = Path(__file__).resolve().parents[4]
    retired_witness = (
        repo
        / "tests"
        / "unit"
        / "argumentation_analysis"
        / "orchestration"
        / "test_enhanced_pm_agent_setup_2536.py"
    )
    message = "le témoin #2536 teste l'orchestrateur retiré — il doit partir avec lui"
    assert not retired_witness.exists(), message
