"""#2338 — un verdict FOL est propagé tel que calculé, jamais fabriqué.

Le contrat a été mesuré sur l'adaptateur
``first_order_logic_agent_adapter.FOLLogicAgent``, retiré par #2432 (aucun
consommateur hors tests, quatre classes qui fabriquaient). Il suit ici l'agent
que la production construit, ``fol_logic_agent.FOLLogicAgent``
(``logic_factory``, ``logic_service`` de l'API web, pipeline unifié) :
``execute_query`` rend ``Tuple[Optional[bool], str]`` — ``True`` entaillé,
``False`` refusé, ``None`` non calculé, avec un message qui dit pourquoi.

Mesuré sur cet agent au moment du déplacement (``main`` ``748e1ad0``) : le tuple
du bridge est bien lu et l'absence de bridge rend ``None``, mais
- une exception du bridge devenait ``False``, un refus que personne n'a calculé
  (le pipeline unifié l'affiche « Not Entailed ») ;
- ``derive_conclusions`` rendait ``True, "Inferences simulated"`` : ``TweetyBridge``
  n'expose aucune dérivation d'inférences, donc ce ``True`` sortait à chaque
  appel, bridge présent ou non ;
- ``consistency_check`` sur un bridge qui lève devenait ``False`` (incohérent).

Construction sans JVM : l'agent reçoit un bridge factice par son constructeur
(``tweety_bridge=``). Le factice n'expose que des méthodes du vrai
``TweetyBridge`` (``fol_handler``, ``check_consistency``) : une doublure plus
riche que l'objet réel certifierait un chemin mort en production.
"""

import pytest

from argumentation_analysis.agents.core.logic.belief_set import FirstOrderBeliefSet
from argumentation_analysis.agents.core.logic.fol_handler import FOLHandler
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


class _FakeFolHandler:
    """Rend le tuple que ``FOLHandler.execute_fol_query`` rend réellement
    (``(entailed, message)``), ou lève."""

    def __init__(self, result=None, raises: BaseException | None = None):
        self._result = result
        self._raises = raises
        self.calls: list[tuple] = []

    def execute_fol_query(self, belief_set, query):
        self.calls.append((belief_set, query))
        if self._raises is not None:
            raise self._raises
        return self._result


class _FakeBridge:
    def __init__(self, result=None, raises: BaseException | None = None):
        self.fol_handler = _FakeFolHandler(result=result, raises=raises)
        self._raises = raises

    def check_consistency(self, belief_set, logic_type):
        if self._raises is not None:
            raise self._raises
        return True, "consistent"


def test_the_double_is_no_richer_than_the_real_bridge():
    public = {n for n in vars(_FakeBridge) if not n.startswith("_")}
    public |= {"fol_handler"}
    assert public <= set(dir(TweetyBridge))
    handler = {n for n in vars(_FakeFolHandler) if not n.startswith("_")}
    assert handler <= set(dir(FOLHandler))


_BELIEF_SET = FirstOrderBeliefSet(content="forall X: (P(X) => Q(X))")


@pytest.fixture
def agent_with(mock_kernel_with_llm):
    def _build(bridge):
        return FOLLogicAgent(kernel=mock_kernel_with_llm, tweety_bridge=bridge)

    return _build


class TestRealVerdictIsPropagated:
    async def test_entailed_true_from_the_bridge_is_returned_true(self, agent_with):
        bridge = _FakeBridge(result=(True, "Query ACCEPTED (entailed)"))

        entailed, message = await agent_with(bridge).execute_query(_BELIEF_SET, "P(a)")

        assert entailed is True
        assert "ACCEPTED" in message
        assert bridge.fol_handler.calls == [(_BELIEF_SET.content, "P(a)")]

    async def test_entailed_false_from_the_bridge_is_returned_false(self, agent_with):
        bridge = _FakeBridge(result=(False, "Query REJECTED"))

        entailed, message = await agent_with(bridge).execute_query(_BELIEF_SET, "P(a)")

        assert entailed is False
        assert "REJECTED" in message


class TestDegradationIsNamedAndNeverFabricates:
    async def test_bridge_exception_yields_none_not_a_refusal(self, agent_with):
        """Rouge avant #2432 : l'exception rendait ``False``."""
        agent = agent_with(_FakeBridge(raises=RuntimeError("JVM morte")))

        verdict, message = await agent.execute_query(_BELIEF_SET, "P(a)")

        assert verdict is None, (
            "une panne de bridge ne calcule AUCUN verdict — rendre False est un "
            f"refus fabriqué ; reçu {verdict!r}"
        )
        assert "NON CALCULÉ" in message
        assert "RuntimeError" in message, "la dégradation doit nommer la cause"

    async def test_no_bridge_at_all_yields_none_with_a_named_degradation(
        self, agent_with
    ):
        verdict, message = await agent_with(None).execute_query(_BELIEF_SET, "P(a)")

        assert verdict is None
        assert "bridge" in message.lower()

    @pytest.mark.parametrize(
        "bridge",
        [None, _FakeBridge(result=(True, "ok"))],
        ids=["no_bridge", "bridge_without_derivation"],
    )
    async def test_derive_conclusions_computes_nothing_so_claims_nothing(
        self, agent_with, bridge
    ):
        """Rouge avant #2432 : ``True, "Inferences simulated"`` à chaque appel."""
        verdict, message = await agent_with(bridge).execute_query(
            _BELIEF_SET, "derive_conclusions"
        )

        assert verdict is None
        assert "NON CALCULÉE" in message

    async def test_consistency_failure_is_not_an_inconsistency(self, agent_with):
        """Rouge avant #2432 : l'exception rendait ``False`` (incohérent)."""
        agent = agent_with(_FakeBridge(raises=ValueError("boom")))

        verdict, message = await agent.execute_query(_BELIEF_SET, "consistency_check")

        assert verdict is None
        assert "ValueError" in message

    async def test_tri_state_is_respected(self, agent_with):
        """Le contrat déclaré est Optional[bool] : None ≠ False ≠ True."""
        results = {
            name: (await agent_with(bridge).execute_query(_BELIEF_SET, "q"))[0]
            for name, bridge in {
                "entailed": _FakeBridge(result=(True, "ok")),
                "refused": _FakeBridge(result=(False, "no")),
                "not_computed": _FakeBridge(raises=RuntimeError("down")),
            }.items()
        }
        assert results == {"entailed": True, "refused": False, "not_computed": None}


async def test_interpretation_does_not_read_an_uncomputed_derivation_as_a_negative(
    mock_kernel_with_llm,
):
    agent = FOLLogicAgent(kernel=mock_kernel_with_llm)

    text = await agent.interpret_results(
        "Donc il faut agir.",
        _BELIEF_SET,
        ["derive_conclusions"],
        [(None, "not computed")],
    )

    assert "non calculée" in text
    assert "Aucune conclusion dérivable" not in text
