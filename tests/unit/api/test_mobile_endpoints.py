"""Tests for the mobile API endpoints.

Validates:
- POST /api/mobile/analyze — argument analysis
- POST /api/mobile/fallacies — fallacy detection
- POST /api/mobile/validate — logical validation
- POST /api/mobile/chat — chat assistant
- Input validation (text too short)
- Error handling with specific assertions (no broad try/except masking)
- Response contracts match TypeScript frontend types

Fixes #848: Tests use specific assertions and fail on real bugs.
Fixes #846: Tests verify create_llm_service is called with service_id.
Fixes #847: Tests verify Toulmin fields are serialized as strings.

#2541: ``/analyze`` runs the real ``run_unified_analysis`` on a registry whose
three ``light`` phases are stand-ins returning their producers' shapes; the
executor, the state writers and the state the route reads are the pipeline's
own, so a key the pipeline does not produce turns a test red. ``/fallacies``
runs ``detect_fallacies`` with a stand-in for ``_invoke_hierarchical_fallacy``
returning the shapes ``test_fallacy_detection_2526`` measured. A run that did
not happen is a non-2xx answer carrying the ``api/errors`` envelope.

Note: These tests construct a standalone FastAPI app with just the mobile
router (avoids torch DLL crash from api.main import chain on Windows).
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.errors import install_error_handlers
from api.mobile_endpoints import EXTRACTION_UNAVAILABLE, mobile_router
from argumentation_analysis.core.capability_registry import CapabilityRegistry
from argumentation_analysis.orchestration import invoke_callables, unified_pipeline


@pytest.fixture
def app():
    """Create a minimal FastAPI app with just the mobile router."""
    _app = FastAPI()
    install_error_handlers(_app)
    _app.include_router(mobile_router, prefix="/api")
    return _app


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


TEXT = (
    "Il faut réduire la vitesse en ville, car les accidents graves diminuent "
    "quand on roule moins vite. Les piétons y gagnent aussi."
)
FIRST = {
    "text": "Réduire la vitesse diminue les accidents graves",
    "source_quote": "les accidents graves diminuent quand on roule moins vite",
}
SECOND = {
    "text": "Les piétons profitent d'une vitesse réduite",
    "source_quote": "Les piétons y gagnent aussi",
}


def _extraction(arguments, status="ok"):
    """What ``_invoke_fact_extraction`` returns: the keys of its LLM path."""
    return {
        "arguments": arguments,
        "claims": [],
        "fallacies": [],
        "summary": "",
        "claim_count": 0,
        "argument_count": len(arguments),
        "source_length": len(TEXT),
        "extraction_method": "llm" if status == "ok" else "heuristic",
        "extraction_status": status,
    }


# What ``_invoke_quality_evaluator`` returns: per-argument scores keyed by the
# 1-based ``arg_N`` of the extraction's list. Fractions: 1.4/2 and 1.2/3.
QUALITY = {
    "per_argument_scores": {
        "arg_1": {
            "scores_par_vertu": {"clarte": 0.8, "pertinence": 0.6},
            "note_finale": 1.4,
        },
        "arg_2": {
            "scores_par_vertu": {"clarte": 0.5, "pertinence": 0.5, "exhaustivite": 0.2},
            "note_finale": 1.2,
        },
    }
}


@pytest.fixture
def pipeline(monkeypatch):
    """The real ``run_unified_analysis`` on stand-in ``light`` phases."""

    def install(extraction, quality=None):
        calls = []

        def stand_in(capability, output):
            async def invoke(text, context):
                calls.append(capability)
                return output

            return invoke

        registry = CapabilityRegistry()
        for capability, output in [
            ("fact_extraction", extraction),
            ("argument_quality", quality or {}),
            ("counter_argument_generation", {}),
        ]:
            registry.register_agent(
                name=f"stand_in_{capability}",
                agent_class=type(f"StandIn_{capability}", (), {}),
                capabilities=[capability],
                invoke=stand_in(capability, output),
            )
        monkeypatch.setattr(unified_pipeline, "setup_registry", lambda: registry)
        return calls

    return install


def _quoted(argument):
    """The description ``_write_fact_extraction_to_state`` stores."""
    return f'{argument["text"]} [quote: "{argument["source_quote"]}"]'


# ──── Analyze Endpoint ────


class TestMobileAnalyze:
    def test_the_arguments_are_the_ones_the_pipeline_writes_to_its_state(
        self, client, pipeline
    ):
        calls = pipeline(_extraction([FIRST, SECOND]), QUALITY)

        resp = client.post("/api/mobile/analyze", json={"text": TEXT})

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert calls == [
            "fact_extraction",
            "argument_quality",
            "counter_argument_generation",
        ]
        assert data["text"] == TEXT
        assert [
            (a["id"], a["text"], a["premises"], a["conclusion"])
            for a in data["arguments"]
        ] == [
            ("arg_1", _quoted(FIRST), [], ""),
            ("arg_2", _quoted(SECOND), [], ""),
        ]
        assert data["overall_quality"] == pytest.approx((1.4 / 2 + 1.2 / 3) / 2)

    def test_an_argument_the_quality_phase_did_not_measure_is_not_a_zero(
        self, client, pipeline
    ):
        only_first = {
            "per_argument_scores": {"arg_1": QUALITY["per_argument_scores"]["arg_1"]}
        }
        pipeline(_extraction([FIRST, SECOND]), only_first)

        data = client.post("/api/mobile/analyze", json={"text": TEXT}).json()

        assert len(data["arguments"]) == 2
        assert data["overall_quality"] == pytest.approx(0.7)

    def test_a_quality_phase_that_measured_nothing_leaves_the_quality_null(
        self, client, pipeline
    ):
        pipeline(_extraction([FIRST, SECOND]))

        resp = client.post("/api/mobile/analyze", json={"text": TEXT})

        assert resp.status_code == 200, resp.text
        assert resp.json()["overall_quality"] is None

    def test_an_extraction_that_found_no_argument_is_the_non_argumentative_stop(
        self, client, pipeline
    ):
        # #1909: the executor classifies a successful zero-argument extraction
        # as non-argumentative and stops there; the quality phase never runs.
        calls = pipeline(_extraction([]), QUALITY)

        resp = client.post("/api/mobile/analyze", json={"text": TEXT})

        assert resp.status_code == 422, resp.text
        assert resp.json()["context"]["status"] == "non_argumentative"
        assert calls == ["fact_extraction"]

    def test_no_llm_client_is_a_503(self, client, pipeline):
        pipeline(_extraction([], status=EXTRACTION_UNAVAILABLE))

        resp = client.post("/api/mobile/analyze", json={"text": TEXT})

        assert resp.status_code == 503, resp.text
        body = resp.json()
        assert body["error_code"] == "service_unavailable"
        assert body["context"]["reason"] == EXTRACTION_UNAVAILABLE

    async def test_the_503_status_is_the_one_the_extraction_reports_without_a_client(
        self, monkeypatch
    ):
        monkeypatch.setattr(invoke_callables, "_get_openai_client", lambda: (None, ""))

        result = await invoke_callables._invoke_fact_extraction(TEXT, {})

        assert result["extraction_status"] == EXTRACTION_UNAVAILABLE
        assert result["arguments"] == []

    def test_a_failed_extraction_is_a_502(self, client, pipeline):
        status = "failed:llm_call_error(attempt=3,type=APIError,msg=boom)"
        pipeline(_extraction([], status=status))

        resp = client.post("/api/mobile/analyze", json={"text": TEXT})

        assert resp.status_code == 502, resp.text
        assert resp.json()["error_code"] == "upstream_error"
        assert resp.json()["context"]["reason"] == status

    def test_a_non_argumentative_text_is_a_422(self, client, pipeline):
        pipeline(_extraction([], status="non_argumentative"))

        resp = client.post("/api/mobile/analyze", json={"text": TEXT})

        assert resp.status_code == 422, resp.text
        assert resp.json()["error_code"] == "unanalyzable_input"

    def test_a_pipeline_that_raises_is_a_502(self, client, monkeypatch):
        monkeypatch.setattr(
            unified_pipeline,
            "run_unified_analysis",
            AsyncMock(side_effect=RuntimeError("Pipeline down")),
        )

        resp = client.post(
            "/api/mobile/analyze",
            json={"text": "Test fallback when pipeline fails"},
        )

        assert resp.status_code == 502, resp.text
        body = resp.json()
        assert body["error_code"] == "upstream_error"
        assert "Pipeline down" in body["detail"]

    def test_analyze_validation_short_text(self, client):
        resp = client.post("/api/mobile/analyze", json={"text": "hi"})
        assert resp.status_code == 422  # text too short (min 5)


# ──── Fallacies Endpoint ────

TU_QUOQUE = "Tu dis que fumer est dangereux, mais tu fumes toi-même, donc tu as tort."
# An item as the llm tier returns it (the shape test_fallacy_detection_2526 measured).
DETECTED = {
    "fallacy_type": "Tu quoque",
    "taxonomy_pk": "1362",
    "explanation": "On écarte la critique en invoquant l'incohérence de son auteur.",
    "problematic_quote": "tu fumes toi-même",
    "confidence": 0.9,
    "family": "Obstruction",
}


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


class TestMobileFallacies:
    def test_the_fallacies_are_the_detectors_with_its_confidence(
        self, client, detector, monkeypatch
    ):
        whole_run = AsyncMock()
        monkeypatch.setattr(unified_pipeline, "run_unified_analysis", whole_run)
        doubtful = {**DETECTED, "fallacy_type": "Projection mentale", "confidence": 0.4}
        del doubtful["problematic_quote"]
        stand_in = detector(
            {"fallacies": [DETECTED, doubtful], "extraction_method": "llm"}
        )

        resp = client.post("/api/mobile/fallacies", json={"text": TU_QUOQUE})

        assert resp.status_code == 200, resp.text
        assert stand_in.calls == [(TU_QUOQUE, {"fallacy_tier": "llm"})]
        whole_run.assert_not_awaited()
        start = TU_QUOQUE.index("tu fumes toi-même")
        assert resp.json()["fallacies"] == [
            {
                "type": "Tu quoque",
                "confidence": 0.9,
                "span": [start, start + len("tu fumes toi-même")],
                "explanation": DETECTED["explanation"],
            },
            {
                "type": "Projection mentale",
                "confidence": 0.4,
                "span": [0, 0],
                "explanation": DETECTED["explanation"],
            },
        ]

    def test_a_quote_absent_from_the_text_has_no_span(self, client, detector):
        elsewhere = {**DETECTED, "problematic_quote": "une phrase qui n'y est pas"}
        detector({"fallacies": [elsewhere], "extraction_method": "llm"})

        resp = client.post("/api/mobile/fallacies", json={"text": TU_QUOQUE})

        assert resp.json()["fallacies"][0]["span"] == [0, 0]

    def test_a_detector_that_found_nothing_answers_an_empty_list(
        self, client, detector
    ):
        detector({"fallacies": [], "extraction_method": "llm"})

        resp = client.post("/api/mobile/fallacies", json={"text": TU_QUOQUE})

        assert resp.status_code == 200, resp.text
        assert resp.json()["fallacies"] == []

    def test_no_detector_is_a_503(self, client, detector):
        detector(error=RuntimeError("FALLACY_DETECTION_UNAVAILABLE: no LLM key"))

        resp = client.post("/api/mobile/fallacies", json={"text": TU_QUOQUE})

        assert resp.status_code == 503, resp.text
        assert resp.json()["error_code"] == "service_unavailable"

    def test_a_failed_detector_is_a_502(self, client, detector):
        # Replaces the #848 test that asserted a 200 with an empty list here.
        detector(error=ValueError("Pipeline error"))

        resp = client.post(
            "/api/mobile/fallacies",
            json={"text": "Test fallacy detection failure handling"},
        )

        assert resp.status_code == 502, resp.text
        body = resp.json()
        assert body["error_code"] == "upstream_error"
        assert "Pipeline error" in body["detail"]


# ──── Validate Endpoint ────


class TestMobileValidate:
    def test_validate_short_text_rejected(self, client):
        resp = client.post("/api/mobile/validate", json={"text": "hi"})
        assert resp.status_code == 422

    @patch(
        "argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer.SemanticArgumentAnalyzer.run"
    )
    def test_validate_toulmin_fields_are_strings(self, mock_run, client):
        """Validate endpoint must return Toulmin fields as strings (#847)."""
        from argumentation_analysis.core.models.toulmin_model import (
            ToulminAnalysisResult,
            ToulminComponent,
        )

        mock_run.return_value = ToulminAnalysisResult(
            claim=ToulminComponent(text="The road is wet", confidence_score=0.9, source_sentences=[0]),
            data=[
                ToulminComponent(text="It rains", confidence_score=0.8, source_sentences=[0]),
                ToulminComponent(text="Rain causes wetness", confidence_score=0.7, source_sentences=[0]),
            ],
            warrant=ToulminComponent(text="Rain causes wet roads", confidence_score=0.85, source_sentences=[0]),
            qualifier=ToulminComponent(text="certainly", confidence_score=0.9, source_sentences=[0]),
        )

        resp = client.post(
            "/api/mobile/validate",
            json={"text": "If it rains then the road is wet. It rains. Therefore the road is wet."},
        )
        assert resp.status_code == 200
        data = resp.json()
        form = data["formalization"]

        # #847: all fields must be strings per mobile contract
        assert isinstance(form["conclusion"], str), f"conclusion should be str, got {type(form['conclusion'])}"
        assert form["conclusion"] == "The road is wet"
        assert isinstance(form["rule"], str), f"rule should be str, got {type(form['rule'])}"
        assert form["rule"] == "Rain causes wet roads"
        assert isinstance(data["explanation"], str), f"explanation should be str, got {type(data['explanation'])}"
        assert data["explanation"] == "certainly"
        # Premises must be a list of strings
        assert isinstance(form["premises"], list)
        for p in form["premises"]:
            assert isinstance(p, str), f"premise should be str, got {type(p)}: {p}"
        assert form["premises"] == ["It rains", "Rain causes wetness"]

    @patch(
        "argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer.SemanticArgumentAnalyzer.run",
        side_effect=RuntimeError("Analyzer error"),
    )
    def test_validate_handles_failure(self, mock_run, client):
        resp = client.post(
            "/api/mobile/validate",
            json={"text": "Test validation failure handling."},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Specific: valid should be False on failure
        assert data["valid"] is False


# ──── Chat Endpoint ────


class TestMobileChat:
    def test_chat_empty_message_rejected(self, client):
        resp = client.post("/api/mobile/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_chat_missing_message(self, client):
        resp = client.post("/api/mobile/chat", json={})
        assert resp.status_code == 422

    @patch("argumentation_analysis.core.llm_service.create_llm_service")
    def test_chat_calls_create_llm_service_with_service_id(self, mock_create, client):
        """create_llm_service must be called with service_id parameter (#846)."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="A fallacy is a flaw in reasoning.")
        mock_create.return_value = mock_llm

        resp = client.post(
            "/api/mobile/chat",
            json={"message": "What is a logical fallacy?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "timestamp" in data
        # #846: verify create_llm_service was called with service_id
        mock_create.assert_called_once_with(service_id="mobile_chat")

    @patch("argumentation_analysis.core.llm_service.create_llm_service", return_value=None)
    @patch("argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis")
    def test_chat_fallback_when_llm_unavailable(self, mock_pipeline, mock_create, client):
        """When LLM service is None, falls back to pipeline."""
        mock_pipeline.return_value = {
            "summary": "Analysis result from pipeline fallback",
        }
        resp = client.post(
            "/api/mobile/chat",
            json={"message": "Tell me about fallacies"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert len(data["message"]) > 0


# ──── Response Contract ────


class TestResponseContract:
    """Verify response shapes match the mobile app's TypeScript types."""

    def test_analyze_response_shape(self, client, pipeline):
        pipeline(_extraction([FIRST]), QUALITY)
        data = client.post("/api/mobile/analyze", json={"text": TEXT}).json()

        # Specific type assertions
        assert isinstance(data["text"], str)
        assert isinstance(data["arguments"], list)
        assert isinstance(data["overall_quality"], (int, float))
        arg = data["arguments"][0]
        assert isinstance(arg["id"], str)
        assert isinstance(arg["text"], str)

    def test_fallacy_response_shape(self, client, detector):
        detector({"fallacies": [DETECTED], "extraction_method": "llm"})
        data = client.post("/api/mobile/fallacies", json={"text": TU_QUOQUE}).json()

        # Specific type assertions
        assert isinstance(data["text"], str)
        assert isinstance(data["fallacies"], list)
        assert isinstance(data["execution_time"], (int, float))
        f = data["fallacies"][0]
        assert isinstance(f["type"], str)
        assert isinstance(f["confidence"], (int, float))
        assert isinstance(f["explanation"], str)
        assert [type(i) for i in f["span"]] == [int, int]
