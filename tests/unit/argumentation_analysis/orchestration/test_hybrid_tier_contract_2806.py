# -*- coding: utf-8 -*-
"""#2806: the hybrid tier reads the adapter's real ``detected_fallacies``.

``_invoke_hybrid_fallacy`` used to read ``fallacies``/``detections``, keys
``FrenchFallacyAdapter.detect()`` never produces, so ``fallacy_tier="hybrid"``
answered 0 on every input and ``"full"`` merged an empty hybrid half.

These tests build the real adapter (symbolic rules only, no network) on
synthetic sentences written to match its spaCy rules.
"""

import pytest

AD_HOMINEM = "Pierre est malhonnête, donc son argument est faux."
NEUTRAL = "Le train part à huit heures et arrive à midi."


@pytest.fixture(scope="module")
def symbolic_tier():
    from argumentation_analysis.adapters.french_fallacy_adapter import (
        SymbolicFallacyDetector,
    )

    detector = SymbolicFallacyDetector()
    if not detector.is_available():
        pytest.skip("no spaCy French model: the symbolic tier cannot run")
    return detector


async def test_hybrid_tier_returns_what_the_adapter_detects(symbolic_tier):
    from argumentation_analysis.adapters.french_fallacy_adapter import (
        FrenchFallacyAdapter,
    )
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_hybrid_fallacy,
    )

    adapter = FrenchFallacyAdapter(
        enable_symbolic=True,
        enable_nli=False,
        enable_llm=False,
        enable_self_hosted_llm=False,
        enable_camembert=False,
    )
    expected = adapter.detect(AD_HOMINEM)["detected_fallacies"]
    assert "Attaque personnelle (Ad Hominem)" in expected

    result = await _invoke_hybrid_fallacy(AD_HOMINEM, {})

    assert result["extraction_method"] == "hybrid_neural_symbolic"
    by_type = {f["fallacy_type"]: f for f in result["fallacies"]}
    assert set(by_type) == set(expected)
    found = by_type["Attaque personnelle (Ad Hominem)"]
    wanted = expected["Attaque personnelle (Ad Hominem)"]
    assert found["confidence"] == wanted["confidence"]
    assert found["taxonomy_pk"] == wanted["taxonomy_pk"]
    assert found["source_tier"] == "symbolic"
    assert found["description"]


async def test_hybrid_tier_reports_zero_only_when_it_ran(symbolic_tier):
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_hybrid_fallacy,
    )

    result = await _invoke_hybrid_fallacy(NEUTRAL, {})

    assert result["extraction_method"] == "hybrid_neural_symbolic"
    assert result["fallacies"] == []


async def test_hybrid_tier_without_a_runnable_tier_is_unavailable(monkeypatch):
    from argumentation_analysis.adapters import french_fallacy_adapter
    from argumentation_analysis.orchestration.invoke_callables import (
        _invoke_hybrid_fallacy,
    )

    monkeypatch.setattr(
        french_fallacy_adapter.SymbolicFallacyDetector,
        "is_available",
        lambda self: False,
    )

    result = await _invoke_hybrid_fallacy(AD_HOMINEM, {})

    assert result["fallacies"] == []
    assert result["extraction_method"] == "unavailable"
    assert "spaCy" in result["error"]


async def test_full_tier_carries_the_hybrid_detections(symbolic_tier, monkeypatch):
    from argumentation_analysis.orchestration import invoke_callables

    async def _llm_unavailable(text, context):
        raise RuntimeError("FALLACY_DETECTION_UNAVAILABLE: test double, no key")

    monkeypatch.setattr(
        invoke_callables, "_invoke_hierarchical_fallacy", _llm_unavailable
    )

    result = await invoke_callables._invoke_full_fallacy(AD_HOMINEM, {})

    assert result["llm_count"] == 0
    assert result["hybrid_count"] >= 1
    assert "Attaque personnelle (Ad Hominem)" in {
        f["fallacy_type"] for f in result["fallacies"]
    }
