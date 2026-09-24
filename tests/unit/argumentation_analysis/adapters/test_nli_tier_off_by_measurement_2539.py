# -*- coding: utf-8 -*-
"""#2539: the NLI fallacy tier is off by default, because it was measured at chance.

With ``MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7``, the tier
reported a fallacy for every text, a fallacy-free control included, at
confidence >= 0.96. Four zero-shot formulations were probed on 65 fallacies
against 20 controls; none separates them (AUC 0.34-0.54). No template or
threshold to calibrate, so the tier stays off unless a caller asks for it, and
then its result says it is uncalibrated.

``test_the_default_adapter_reports_no_control`` is the real-model check the
issue asks for: on ``main`` the default adapter (LLM tiers off) loads the
model and flags every control. Here it no longer runs the tier at all.
"""

from unittest.mock import patch

from argumentation_analysis.adapters.french_fallacy_adapter import (
    FallacyDetection,
    FrenchFallacyAdapter,
    NLIFallacyDetector,
)

# Fallacy-free French sentences written for #2539; none comes from the corpus.
CONTROLS = (
    "Le rapport annuel indique une hausse de 3 % des ventes au deuxième trimestre.",
    "L'eau bout à 100 degrés Celsius au niveau de la mer.",
    "Tous les mammifères respirent de l'air. Les baleines sont des mammifères. "
    "Les baleines respirent donc de l'air.",
    "Le train de 8 h 12 a été supprimé en raison de travaux sur la voie.",
    "La bibliothèque sera fermée pendant les vacances de Noël et rouvrira le 3 janvier.",
    "Comme le magasin ferme à 19 heures et qu'il est 19 h 30, nous ne pourrons "
    "plus y acheter de pain ce soir.",
)


def _without_llm(**kwargs):
    return FrenchFallacyAdapter(
        enable_symbolic=False, enable_llm=False, enable_self_hosted_llm=False, **kwargs
    )


def test_the_nli_tier_is_off_by_default():
    adapter = _without_llm()

    assert "nli" not in adapter.get_available_tiers()


def test_the_default_adapter_reports_no_control():
    adapter = _without_llm()

    results = {text: adapter.detect(text) for text in CONTROLS}
    reported = {
        text: result["detected_fallacies"]
        for text, result in results.items()
        if result["total_fallacies"]
    }

    assert reported == {}


def test_an_explicit_nli_result_says_it_is_uncalibrated():
    adapter = _without_llm(enable_nli=True)
    hit = FallacyDetection("Attaque personnelle", 0.99, "nli")

    with patch.object(
        NLIFallacyDetector, "is_available", return_value=True
    ), patch.object(NLIFallacyDetector, "detect", return_value=[hit]):
        result = adapter.detect(CONTROLS[0])

    assert result["tiers_used"] == ["nli"]
    assert result["tier_warnings"] == {"nli": NLIFallacyDetector.UNCALIBRATED}
    assert "#2539" in result["tier_warnings"]["nli"]


def test_a_result_the_nli_tier_did_not_touch_carries_no_warning():
    adapter = _without_llm(enable_nli=True)

    with patch.object(
        NLIFallacyDetector, "is_available", return_value=True
    ), patch.object(NLIFallacyDetector, "detect", return_value=[]):
        result = adapter.detect(CONTROLS[0])

    assert "tier_warnings" not in result
