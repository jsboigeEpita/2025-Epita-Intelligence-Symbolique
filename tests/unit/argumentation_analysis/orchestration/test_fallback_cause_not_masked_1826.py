"""#1826 — un échec de handler ne doit pas se déguiser en « JVM absente ».

Le stub fail-loud (voulu, #1019/RA-8 #1053) levait un message figé
« JVM/Tweety required. Install JVM... » pour TOUT échec du handler — y
compris une entrée mal formée, avec la JVM qui tourne. La cause réelle
n'était visible qu'à INFO dans un log noyé ; le chemin d'erreur observable
l'avalait. Un lecteur (ou un agent PM, ou un test) concluait « JVM absente »
à tort.

Contrôles par substitution dégénérée : on force le handler à lever une
erreur NON-JVM (``ValueError("bad shape")``) et l'erreur observable doit
porter cette cause — pas l'affirmation environnementale figée. Sweep des
frères : aspic par substitution (2ᵉ chemin ``_invoke_*`` prouvé), social et
eaf au niveau stub (l'appel direct avec ``cause`` porte la cause ; sans
``cause`` le tripwire environnemental reste — le fail-loud de #1019 est
intact, et le message direct de eaf n'était épinglé nulle part).
"""

import pytest

from argumentation_analysis.orchestration import invoke_callables as ic

SAMPLE_TEXT = "Claim one. Claim two. Claim three."


def _boom(*_args, **_kwargs):
    raise ValueError("bad shape")


async def _ranking_with_failing_handler(monkeypatch):
    monkeypatch.setattr(
        "argumentation_analysis.agents.core.logic.ranking_handler.RankingHandler."
        "__init__",
        lambda self: None,
    )
    monkeypatch.setattr(
        "argumentation_analysis.agents.core.logic.ranking_handler.RankingHandler."
        "rank_arguments",
        _boom,
    )
    ctx = {"arguments": ["a", "b"], "attacks": [["a", "b"]]}
    return await ic._invoke_ranking(SAMPLE_TEXT, ctx)


async def _aspic_with_failing_handler(monkeypatch):
    monkeypatch.setattr(
        "argumentation_analysis.agents.core.logic.aspic_handler.ASPICHandler."
        "__init__",
        lambda self: None,
    )
    monkeypatch.setattr(
        "argumentation_analysis.agents.core.logic.aspic_handler.ASPICHandler."
        "analyze_aspic_framework",
        _boom,
    )
    # #1836 : sans règles fournies par l'appelant, _invoke_aspic traverse
    # translate_to_aspic_rules (étape LLM) AVANT le handler stubbé — chaque
    # test fuyait un POST réel vers un hôte LLM et passait par grâce d'un
    # réseau vivant, plus faible que ce que son nom annonce. Les règles de
    # l'appelant ne sont jamais écrasées (contrat documenté) et court-circuitent
    # le translator : 0 egress, le test n'éprouve que la propagation de cause.
    ctx = {
        "arguments": ["a", "b"],
        "defeasible_rules": [
            {"head": "plausible_conclusion_1", "body": ["claim_a"], "name": "def_arg_1"}
        ],
    }
    return await ic._invoke_aspic(SAMPLE_TEXT, ctx)


class TestRankingCauseNotMasked:
    async def test_non_jvm_error_names_its_cause(self, monkeypatch):
        with pytest.raises(RuntimeError) as excinfo:
            await _ranking_with_failing_handler(monkeypatch)
        message = str(excinfo.value)
        assert "bad shape" in message, (
            f"#1826: l'erreur observable doit porter la cause réelle du handler, "
            f"pas un message figé — got: {message!r}"
        )

    async def test_non_jvm_error_does_not_claim_missing_jvm(self, monkeypatch):
        with pytest.raises(RuntimeError) as excinfo:
            await _ranking_with_failing_handler(monkeypatch)
        message = str(excinfo.value)
        assert "JVM/Tweety required" not in message, (
            f"#1826: une erreur d'entrée (bad shape) ne doit pas s'affirmer "
            f"« JVM absente » alors que la JVM tourne — got: {message!r}"
        )


class TestAspicCauseNotMasked:
    async def test_non_jvm_error_names_its_cause(self, monkeypatch):
        with pytest.raises(RuntimeError) as excinfo:
            await _aspic_with_failing_handler(monkeypatch)
        message = str(excinfo.value)
        assert "bad shape" in message, (
            f"#1826: l'erreur observable doit porter la cause réelle du handler, "
            f"pas un message figé — got: {message!r}"
        )

    async def test_non_jvm_error_does_not_claim_missing_jvm(self, monkeypatch):
        with pytest.raises(RuntimeError) as excinfo:
            await _aspic_with_failing_handler(monkeypatch)
        message = str(excinfo.value)
        assert "JVM/Tweety required" not in message, (
            f"#1826: une erreur d'entrée (bad shape) ne doit pas s'affirmer "
            f"« JVM absente » alors que la JVM tourne — got: {message!r}"
        )


class TestStubKeepsEnvironmentalMessageWhenNoCause:
    """Le tripwire direct (cause=None) garde le message environnemental :
    sans exception handler à rapporter, « installe la JVM » reste la bonne
    lecture — le fail-loud de #1019 est intact."""

    def test_direct_stub_call_still_claims_jvm(self):
        with pytest.raises(RuntimeError, match="JVM/Tweety required"):
            ic._python_ranking_fallback(["a"], [], "categorizer")

    def test_eaf_stub_without_cause_still_claims_jvm(self):
        with pytest.raises(RuntimeError, match="JVM/Tweety required"):
            ic._python_eaf_fallback(["a"], [], "grounded", {})


class TestBrothersStubCarriesCause:
    """Sweep frères (#1826) : social et eaf portent la cause quand il y en a
    une — l'échec réel du handler remonte dans l'erreur observable."""

    def test_social_stub_with_cause_names_it(self):
        with pytest.raises(RuntimeError) as excinfo:
            ic._python_social_fallback(["a"], [], {}, {}, cause=ValueError("bad shape"))
        message = str(excinfo.value)
        assert "bad shape" in message, f"got: {message!r}"
        assert "JVM/Tweety required" not in message, f"got: {message!r}"

    def test_eaf_stub_with_cause_names_it(self):
        with pytest.raises(RuntimeError) as excinfo:
            ic._python_eaf_fallback(
                ["a"], [], "grounded", {}, cause=ValueError("bad shape")
            )
        message = str(excinfo.value)
        assert "bad shape" in message, f"got: {message!r}"
        assert "JVM/Tweety required" not in message, f"got: {message!r}"

    def test_aspic_stub_with_cause_names_it(self):
        with pytest.raises(RuntimeError) as excinfo:
            ic._python_aspic_fallback(
                ["a"], [], [], [], {}, cause=ValueError("bad shape")
            )
        message = str(excinfo.value)
        assert "bad shape" in message, f"got: {message!r}"
        assert "JVM/Tweety required" not in message, f"got: {message!r}"
