"""#2338 — l'adaptateur FOL propage le verdict réel et ne fabrique plus ACCEPTED.

Deux défauts mesurés dans ``execute_query`` (``first_order_logic_agent_adapter.py``) :

1. ``"ACCEPTED" in result`` sur un **tuple** ``(entailed: bool, message: str)`` est
   un test d'appartenance d'ÉLÉMENT : aucun élément du tuple n'étant la chaîne
   ``"ACCEPTED"``, ``is_accepted`` vaut toujours ``False`` — **tout verdict
   Tweety réel était inversé** en REJECTED.
2. Sur exception (ou bridge absent), le mode dégradé renvoyait ``True`` avec
   ``"Mode dégradé."`` — un verdict ACCEPTED **fabriqué** (anti-théâtre #1019).

Le contrat déclaré de la méthode est ``Tuple[Optional[bool], str]`` : le tri-état
est déjà dans la signature. Ces tests l'épinglent.

Construction sans JVM : l'objet est bâti par ``__new__`` et ses trois attributs
utilisés par ``execute_query`` sont posés à la main. Le sujet est la DÉCISION de
la méthode sur le tuple rendu par le bridge, pas le cycle de vie de l'adaptateur
(qui instancie TweetyBridge et peut charger la JVM) — un test unitaire qui
démarre une JVM pour trois assertions est un test qui ne tourne pas en CI.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[6]))

from argumentation_analysis.agents.core.logic.first_order_logic_agent_adapter import (
    FOLLogicAgent,
)


class _FakeBridge:
    """Bridge FOL factice : rend le tuple que TweetyBridge rend réellement
    (``fol_handler.execute_fol_query`` → ``(entailed, message)``), ou lève."""

    def __init__(self, result=None, raises: BaseException | None = None):
        self._result = result
        self._raises = raises
        self.calls: list[tuple] = []

    def execute_fol_query(self, belief_set, query):
        self.calls.append((belief_set, query))
        if self._raises is not None:
            raise self._raises
        return self._result


class _BeliefSet:
    content = "forall X: (P(X) => Q(X))"


def _adapter(bridge) -> FOLLogicAgent:
    adapter = FOLLogicAgent.__new__(FOLLogicAgent)
    adapter.name = "FOLLogicAgent"
    adapter.logic_type = "FOL"
    import logging

    adapter.logger = logging.getLogger("test.fol.adapter")
    adapter._sk_agent = None
    adapter._tweety_bridge = bridge
    return adapter


class TestRealVerdictIsPropagated:
    def test_entailed_true_from_the_bridge_is_returned_true(self):
        """Born-red du défaut 1 : le tuple ``(True, msg)`` rendait False."""
        adapter = _adapter(_FakeBridge(result=(True, "Query ACCEPTED (entailed)")))

        entailed, message = adapter.execute_query(_BeliefSet(), "P(a)")

        assert entailed is True, (
            "un verdict d'entalement True rendu par le bridge doit être propagé "
            f"tel quel — reçu {entailed!r} (message: {message!r})"
        )
        assert "ACCEPTED" in message

    def test_entailed_false_from_the_bridge_is_returned_false(self):
        """Contrôle : un refus réel reste un refus (vert avant et après).

        Le message n'est PAS asserté ici : pré-fix, ``execute_query`` rend le
        tuple lui-même à la place du message, et un ``"REJECTED" in message``
        sur un tuple est un test d'appartenance qui échoue — on mesurerait le
        bug du harnais, pas le contrat. Le passage du message est asserté sur
        le cas True (born-red), où le même défaut se voit."""
        adapter = _adapter(_FakeBridge(result=(False, "Query REJECTED")))

        entailed, _message = adapter.execute_query(_BeliefSet(), "P(a)")

        assert entailed is False


class TestDegradationIsNamedAndNeverFabricates:
    def test_bridge_exception_yields_none_not_a_fabricated_accepted(self):
        """Born-red du défaut 2 : l'exception rendait (True, '…ACCEPTED…')."""
        adapter = _adapter(_FakeBridge(raises=RuntimeError("JVM morte")))

        verdict, message = adapter.execute_query(_BeliefSet(), "P(a)")

        assert verdict is None, (
            "une panne de bridge ne calcule AUCUN verdict — rendre True est un "
            f"verdict fabriqué, rendre False est un verdict inversé ; reçu {verdict!r}"
        )
        assert "NON CALCULÉ" in message or "non calculé" in message
        assert "RuntimeError" in message, "la dégradation doit nommer la cause"

    def test_no_bridge_at_all_yields_none_with_a_named_degradation(self):
        adapter = _adapter(None)

        verdict, message = adapter.execute_query(_BeliefSet(), "P(a)")

        assert verdict is None
        assert "bridge" in message.lower()

    def test_tri_state_is_respected(self):
        """Le contrat déclaré est Optional[bool] : None ≠ False ≠ True."""
        results = {
            "entailed": _adapter(_FakeBridge(result=(True, "ok"))).execute_query(
                _BeliefSet(), "q"
            )[0],
            "refused": _adapter(_FakeBridge(result=(False, "no"))).execute_query(
                _BeliefSet(), "q"
            )[0],
            "not_computed": _adapter(None).execute_query(_BeliefSet(), "q")[0],
        }
        assert results == {"entailed": True, "refused": False, "not_computed": None}


class TestDegradationIsNotAnException:
    def test_degradation_does_not_raise(self):
        """La dégradation est un ÉTAT rendu, pas une exception qui remonte."""
        adapter = _adapter(_FakeBridge(raises=ValueError("boom")))
        verdict, _ = adapter.execute_query(_BeliefSet(), "P(a)")
        assert verdict is None  # aucune exception levée jusqu'ici == comportement voulu
