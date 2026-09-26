# -*- coding: utf-8 -*-
"""#2526: one fallacy detector behind ``/api/fallacies`` and ``/api/analyze``.

Both routes call ``_invoke_hierarchical_fallacy``, the pipeline's own detector.
Here a stand-in takes its place: it records the tier it was asked for and
returns the shapes the real one returns. Those shapes were measured on
``f80f65ad3``: a detection, a key-less run (raises
``FALLACY_DETECTION_UNAVAILABLE``), and a failed LLM call (returns
``{"error": ..., "fallacies": []}``, #2540).

What is checked: an empty list is an answer only when the detector ran and
found nothing. Every run that did not happen is a 503, and every failed run a
502. Neither is ever a 200.
"""

import csv
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import fallacy_detection
from api.endpoints import router as api_router
from api.errors import install_error_handlers
from api.frontend_endpoints import frontend_router
from argumentation_analysis.orchestration import invoke_callables

TU_QUOQUE = "Tu dis que fumer est dangereux, mais tu fumes toi-même, donc tu as tort."

# An item as the llm tier returns it (measured, explanation shortened).
DETECTED = {
    "fallacy_type": "Tu quoque",
    "taxonomy_pk": "1362",
    "taxonomy_path": "7.3.1.1",
    "explanation": "On écarte la critique en invoquant l'incohérence de son auteur.",
    "problematic_quote": "tu fumes toi-même",
    "confidence": 0.9,
    "navigation_trace": ["1361", "1362"],
    "family": "Obstruction",
    "depth": 4,
}
DOUBTFUL = {**DETECTED, "fallacy_type": "Projection mentale", "taxonomy_pk": "52"}
DOUBTFUL["confidence"] = 0.4
DOUBTFUL["family"] = "Insuffisance"


class _Detector:
    """Stands in for ``_invoke_hierarchical_fallacy``; records each call."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    async def __call__(self, text, context):
        self.calls.append((text, dict(context)))
        if self.error is not None:
            raise self.error
        return self.result


@pytest.fixture
def detector(monkeypatch):
    def install(result=None, error=None):
        stand_in = _Detector(result, error)
        monkeypatch.setattr(invoke_callables, "_invoke_hierarchical_fallacy", stand_in)
        return stand_in

    return install


@pytest.fixture
def client():
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(api_router, prefix="/api")
    app.include_router(frontend_router, prefix="/api")
    # /api/analyze parses prose with the markers component (#2562); the
    # AspicParser stand-in below only serves formal ASPIC+ input.
    context = Mock()
    context.jvm_initialized = True
    kb = Mock()
    kb.getArguments.return_value = ["premise1", "conclusion1"]
    context.tweety_classes = {"AspicParser": Mock()}
    context.tweety_classes["AspicParser"].parseBeliefBase.return_value = kb
    app.state.project_context = context
    with TestClient(app) as test_client:
        yield test_client


def _taxonomy_row(pk):
    with open(fallacy_detection.TAXONOMY_PATH, encoding="utf-8") as handle:
        return next(row for row in csv.DictReader(handle) if row["PK"] == pk)


# ---- /api/fallacies ----


def test_a_detection_carries_what_the_detector_and_the_taxonomy_say(client, detector):
    stand_in = detector(
        {
            "fallacies": [DETECTED],
            "extraction_method": "widenet_only_no_perarg_args",
            "degraded": True,
            "last_error": "per-argument fallacy lift skipped (no extractable arguments)",
        }
    )

    response = client.post("/api/fallacies", json={"text": TU_QUOQUE})

    assert response.status_code == 200, response.text
    body = response.json()
    assert stand_in.calls == [(TU_QUOQUE, {"fallacy_tier": "llm"})]
    row = _taxonomy_row("1362")
    assert body["fallacies"] == [
        {
            "name": "Tu quoque",
            "confidence": 0.9,
            "taxonomy_pk": "1362",
            "family": "Obstruction",
            "description": row["desc_fr"],
            "example": row["example_fr"],
            "explanation": DETECTED["explanation"],
            "quote": "tu fumes toi-même",
        }
    ]
    assert row["desc_fr"] and row["example_fr"]
    assert body["fallacy_count"] == 1
    assert body["below_threshold"] == 0
    assert body["tier"] == "llm"
    assert body["method"] == "widenet_only_no_perarg_args"
    # The detector's own degradation reaches the client, in its words.
    assert body["degraded"] is True
    assert body["degradation_reason"].startswith("per-argument fallacy lift skipped")


def test_the_tier_and_the_threshold_come_from_the_request(client, detector):
    stand_in = detector(
        {"fallacies": [DETECTED, DOUBTFUL], "extraction_method": "taxonomy_lexical"}
    )

    response = client.post(
        "/api/fallacies",
        json={
            "text": TU_QUOQUE,
            "options": {"tier": "taxonomy", "min_confidence": 0.5},
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert stand_in.calls[0][1] == {"fallacy_tier": "taxonomy"}
    assert [f["name"] for f in body["fallacies"]] == ["Tu quoque"]
    assert body["fallacy_count"] == 1
    assert body["below_threshold"] == 1


def test_none_found_is_an_empty_list(client, detector):
    detector({"fallacies": [], "extraction_method": "widenet+perarg_union"})

    response = client.post("/api/fallacies", json={"text": "Il pleut depuis mardi."})

    assert response.status_code == 200, response.text
    assert response.json()["fallacies"] == []
    assert response.json()["fallacy_count"] == 0


def test_no_key_is_a_503_with_the_detectors_reason(client, detector):
    reason = (
        "FALLACY_DETECTION_UNAVAILABLE: tier=llm, reason=OPENAI_API_KEY is set to "
        "an empty string (#2281)."
    )
    detector(error=RuntimeError(reason))

    response = client.post("/api/fallacies", json={"text": TU_QUOQUE})

    assert response.status_code == 503, response.text
    assert response.json()["error_code"] == "service_unavailable"
    assert response.json()["detail"] == reason


@pytest.mark.parametrize(
    "result",
    [
        # _invoke_taxonomy_only_fallacy / _invoke_hybrid_fallacy when they cannot run
        {"fallacies": [], "extraction_method": "unavailable", "error": "No module"},
        # the llm tier without its taxonomy file
        {"fallacies": [], "exploration_method": "skipped", "reason": "no taxonomy"},
    ],
    ids=["tier-unavailable", "taxonomy-missing"],
)
def test_a_tier_that_did_not_run_is_a_503(client, detector, result):
    detector(result)

    response = client.post("/api/fallacies", json={"text": TU_QUOQUE})

    assert response.status_code == 503, response.text
    assert "FALLACY_DETECTION_UNAVAILABLE" in response.json()["detail"]


def test_a_failed_llm_call_is_a_502_not_an_empty_list(client, detector):
    """What the invoker raises when no LLM run answered (#2540)."""
    detector(
        error=invoke_callables.FallacyDetectionFailed(
            "FALLACY_DETECTION_FAILED: tier=llm, reason=service failed to "
            "complete the prompt: Connection error."
        )
    )

    response = client.post("/api/fallacies", json={"text": TU_QUOQUE})

    assert response.status_code == 502, response.text
    assert response.json()["error_code"] == "upstream_error"
    assert "Connection error." in response.json()["detail"]


def test_an_option_the_detector_does_not_take_is_refused(client, detector):
    """The frontend used to send ``severity_threshold`` and ``fallacy_types``."""
    stand_in = detector({"fallacies": []})

    response = client.post(
        "/api/fallacies",
        json={"text": TU_QUOQUE, "options": {"severity_threshold": 0.3}},
    )

    assert response.status_code == 422
    assert stand_in.calls == []


# ---- /api/analyze ----


def test_analyze_without_detection_does_not_claim_a_fallacy_count(client, detector):
    stand_in = detector(error=AssertionError("the detector must not run"))

    response = client.post("/api/analyze", json={"text": TU_QUOQUE})

    assert response.status_code == 200, response.text
    results = response.json()["results"]
    assert stand_in.calls == []
    for absent in (
        "fallacies",
        "fallacy_count",
        "fallacy_detection",
        "overall_quality",
    ):
        assert absent not in results, absent
    # #2562 : la structure vient du parseur de marqueurs (le prose ne passe
    # plus par le AspicParser) — prémisse = ce qui précède « donc ». #2682 :
    # la conclusion part du marqueur ; elle rendait la phrase entière,
    # prémisse comprise, et la prémisse gardait sa virgule.
    assert results["argument_structure"] == {
        "premises": ["Tu dis que fumer est dangereux, mais tu fumes toi-même"],
        "conclusion": "donc tu as tort",
    }


def test_analyze_with_detection_runs_the_same_detector(client, detector):
    stand_in = detector(
        {"fallacies": [DETECTED], "extraction_method": "taxonomy_lexical"}
    )

    response = client.post(
        "/api/analyze",
        json={
            "text": TU_QUOQUE,
            "options": {"detect_fallacies": True, "fallacy_tier": "taxonomy"},
        },
    )

    assert response.status_code == 200, response.text
    results = response.json()["results"]
    assert stand_in.calls == [(TU_QUOQUE, {"fallacy_tier": "taxonomy"})]
    assert [f["name"] for f in results["fallacies"]] == ["Tu quoque"]
    assert results["fallacy_count"] == 1
    assert results["fallacy_detection"]["tier"] == "taxonomy"
    assert results["metadata"]["components_used"] == [
        "ArgumentParser_marqueurs_francais",
        "hierarchical_fallacy:taxonomy",
    ]


def test_analyze_fails_when_the_requested_detection_cannot_run(client, detector):
    detector(error=RuntimeError("FALLACY_DETECTION_UNAVAILABLE: tier=llm, reason=x"))

    response = client.post(
        "/api/analyze", json={"text": TU_QUOQUE, "options": {"detect_fallacies": True}}
    )

    assert response.status_code == 503, response.text
