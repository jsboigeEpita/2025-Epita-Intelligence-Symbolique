"""#1846 — the consistency label must OBSERVE the reasoner, not re-compute it.

``modal_handler.py`` derived ``solver_name`` from a SECOND call to
``_resolve_active_solver_choice()`` — the same instrument that
``_get_active_reasoner()`` already consulted. Label and reasoner were two
reads of one resolver, so they agreed vacuously: a reasoner swapped under the
verdict kept deciding under a stale ``"tweety"`` stamp. The coordinator's
degenerate substitution (replace ``_get_active_reasoner``'s body with the
SPASS reasoner) left **every** ``"tweety" in msg`` assert green — 8 passed,
zero red, on main.

This file pins the fix: the label is derived from ``type(reasoner).__name__``
(the observation) — the substitution below is that degenerate control, made
permanent, and it must stay discriminating.
"""

from types import SimpleNamespace
from unittest import mock

from argumentation_analysis.agents.core.logic import modal_handler as mh_module
from argumentation_analysis.agents.core.logic.modal_handler import ModalHandler
from argumentation_analysis.core.config import ModalSolverChoice


def _make_handler(monkeypatch, reasoner):
    """Real ``ModalHandler`` over a stub initializer — no JVM needed.

    Same shape as the #1759 bounded-signature harness: production path stays
    genuine up to the reasoner call.
    """
    initializer = mock.MagicMock()
    initializer.get_modal_parser.return_value = mock.MagicMock()
    initializer.get_modal_reasoner.return_value = reasoner
    handler = ModalHandler(initializer_instance=initializer)
    # Substitution A (#1846): the reasoner the verdict will actually come
    # from is SPASS-shaped, whatever the resolver says.
    monkeypatch.setattr(handler, "_get_active_reasoner", lambda: reasoner)
    monkeypatch.setattr(
        handler, "_build_contradiction_probe", lambda belief_set: object()
    )
    monkeypatch.setattr(
        mh_module,
        "jpype",
        SimpleNamespace(
            JClass=lambda name: lambda payload: (name, payload),
            JException=type("JException", (Exception,), {}),
        ),
    )
    return handler


class TestLabelObservesTheReasoner:
    """#1846: solver_name is an observation of the reasoner object."""

    def test_swapped_reasoner_moves_the_label_with_it(self, monkeypatch):
        """Né-rouge: a SPASS-shaped reasoner under a TWEETY-resolved route.

        Pre-fix the label re-computed the routing intention (tweety) while
        the substituted reasoner decided — the exact blindness the issue
        measured. Post-fix the label reports what type(reasoner) shows.
        """

        class SubstitutedSPASSReasoner:  # name carries SPASS — observed
            def query(self, belief_set, formula):
                return False  # does not entail contradiction -> consistent

        handler = _make_handler(monkeypatch, SubstitutedSPASSReasoner())
        # Pin the resolver to TWEETY so the two pre-fix reads would agree.
        monkeypatch.setattr(
            handler,
            "_resolve_active_solver_choice",
            lambda: ModalSolverChoice.TWEETY,
        )

        is_consistent, message = handler.is_modal_kb_consistent("[](p => q)")

        assert is_consistent is True
        assert "spass" in message
        assert "tweety" not in message

    def test_tweety_shaped_reasoner_keeps_the_tweety_label(self, monkeypatch):
        """The derivation is not a blanket "always spass": a plain reasoner
        under a plain route still labels tweety — routing unchanged."""

        class PlainReasoner:
            def query(self, belief_set, formula):
                return False

        handler = _make_handler(monkeypatch, PlainReasoner())
        monkeypatch.setattr(
            handler,
            "_resolve_active_solver_choice",
            lambda: ModalSolverChoice.TWEETY,
        )

        is_consistent, message = handler.is_modal_kb_consistent("[](p => q)")

        assert is_consistent is True
        assert "tweety" in message
