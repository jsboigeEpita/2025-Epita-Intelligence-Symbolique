"""Tests for the pipeline agent API routes.

Validates:
- Quality evaluation endpoint
- Counter-argument generation endpoint
- Debate endpoint
- Governance simulation endpoint
- Full analysis endpoint
- Error handling (500 on pipeline failure)
- Input validation (min text length)
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from argumentation_analysis.orchestration.workflow_dsl import PhaseResult, PhaseStatus


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


# Sample state snapshots returned by mocked pipeline
QUALITY_SNAPSHOT = {
    "quality_scores": {
        "arg_0_main_claim": {
            "clarity": 0.8,
            "coherence": 0.7,
            "relevance": 0.9,
        },
        "arg_1_supporting": {
            "clarity": 0.6,
            "coherence": 0.8,
            "relevance": 0.7,
        },
    },
}

COUNTER_ARG_SNAPSHOT = {
    "counter_argument_parsed": {"claims": ["claim1"], "premises": ["p1"]},
    "counter_argument_strategy": {"recommended": "reductio"},
    "llm_counter_arguments": [
        {
            "target": "claim1",
            "strategy": "counter-example",
            "counter": "But consider X...",
        },
        {
            "target": "claim1",
            "strategy": "distinction",
            "text": "The distinction is...",
        },
    ],
}

# Shape mirrors the real writer (state_writers._write_debate_to_state +
# shared_state.add_debate_transcript): debate_transcripts is a LIST of
# {id, topic, exchanges: [{point, rebuttal, scheme?, ...}], winner}. The
# previous mock encoded the reader's own broken dict shape — the test was
# validating the reader against itself (#2135 finding 1).
DEBATE_SNAPSHOT = {
    "debate_transcripts": [
        {
            "id": "debate_0",
            "topic": "Democracy is the best form of government for modern societies.",
            "exchanges": [
                {
                    "point": "The data shows growth",
                    "rebuttal": "But the sample is biased",
                    "scheme": "Argument from Example",
                    "scheme_key": "example",
                    "critical_question": "Is the example representative?",
                }
            ],
            "winner": "Agent A",
        }
    ],
}

GOVERNANCE_SNAPSHOT = {
    "governance_decisions": {
        "majority": {
            "winner": "proposal_A",
            "scores": {"proposal_A": 3.0, "proposal_B": 1.0},
        },
        "borda": {
            "winner": "proposal_A",
            "scores": {"proposal_A": 5.0, "proposal_B": 2.0},
        },
        "consensus_score": 0.75,
        "summary": "Strong consensus for proposal A",
    },
}


def _completed(name, capability):
    return PhaseResult(
        phase_name=name, status=PhaseStatus.COMPLETED, capability=capability
    )


def _mock_pipeline_result(capability, snapshot):
    """An async mock of a run where extraction and *capability* completed.

    #2767: the endpoints read the phase status, so the double carries the
    phase results the real ``_run_pipeline_phase`` returns.
    """
    mock = AsyncMock()
    mock.return_value = {
        "phase_results": {
            "extract": _completed("extract", "fact_extraction"),
            capability: _completed(capability, capability),
        },
        "snapshot": snapshot,
    }
    return mock


# ──── Quality Endpoint ────


class TestQualityEndpoint:
    def test_quality_success(self, client):
        with patch(
            "api.agent_routes._run_pipeline_phase",
            _mock_pipeline_result("argument_quality", QUALITY_SNAPSHOT),
        ):
            resp = client.post(
                "/api/v1/agents/quality",
                json={
                    "text": "This is a substantial argument about policy reform and its implications."
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["scores"]) == 2
        assert data["scores"][0]["argument"] == "arg_0_main_claim"
        assert data["scores"][0]["scores"]["clarity"] == 0.8
        assert "aggregate" in data
        assert data["aggregate"]["clarity"] == 0.7  # avg of 0.8 and 0.6
        assert data["duration_seconds"] >= 0

    def test_quality_empty_scores(self, client):
        with patch(
            "api.agent_routes._run_pipeline_phase",
            _mock_pipeline_result("argument_quality", {"quality_scores": {}}),
        ):
            resp = client.post(
                "/api/v1/agents/quality",
                json={"text": "Short but valid argument text for testing."},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["scores"] == []
        assert data["aggregate"] == {}

    def test_quality_pipeline_error(self, client):
        mock = AsyncMock(side_effect=RuntimeError("LLM timeout"))
        with patch("api.agent_routes._run_pipeline_phase", mock):
            resp = client.post(
                "/api/v1/agents/quality",
                json={
                    "text": "This argument should trigger a pipeline error during quality evaluation."
                },
            )
        assert resp.status_code == 500
        assert "LLM timeout" in resp.json()["detail"]

    def test_quality_text_too_short(self, client):
        resp = client.post(
            "/api/v1/agents/quality",
            json={"text": "short"},
        )
        assert resp.status_code == 422  # validation error


# ──── Counter-Argument Endpoint ────


class TestCounterArgumentEndpoint:
    def test_counter_args_success(self, client):
        with patch(
            "api.agent_routes._run_pipeline_phase",
            _mock_pipeline_result("counter_argument_generation", COUNTER_ARG_SNAPSHOT),
        ):
            resp = client.post(
                "/api/v1/agents/counter-arguments",
                json={
                    "text": "We should ban all fossil fuels immediately to save the planet."
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["llm_counter_arguments"]) == 2
        assert data["llm_counter_arguments"][0]["strategy"] == "counter-example"
        assert data["llm_counter_arguments"][1]["counter"] == "The distinction is..."
        assert data["parsed"]["claims"] == ["claim1"]

    def test_counter_args_string_format(self, client):
        """Test backward compatibility with string counter-arguments."""
        with patch(
            "api.agent_routes._run_pipeline_phase",
            _mock_pipeline_result(
                "counter_argument_generation",
                {"llm_counter_arguments": ["Simple counter 1", "Simple counter 2"]},
            ),
        ):
            resp = client.post(
                "/api/v1/agents/counter-arguments",
                json={
                    "text": "Nuclear energy is the safest form of power generation available."
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["llm_counter_arguments"]) == 2
        assert data["llm_counter_arguments"][0]["counter"] == "Simple counter 1"

    def test_counter_args_single_string(self, client):
        """Test backward compatibility with single string counter-argument."""
        with patch(
            "api.agent_routes._run_pipeline_phase",
            _mock_pipeline_result(
                "counter_argument_generation",
                {"llm_counter_arguments": "A single counter-argument in legacy format"},
            ),
        ):
            resp = client.post(
                "/api/v1/agents/counter-arguments",
                json={
                    "text": "The earth is getting warmer due to human activity and industrial pollution."
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["llm_counter_arguments"]) == 1


# ──── Debate Endpoint ────


class TestDebateEndpoint:
    def test_debate_success(self, client):
        with patch(
            "api.agent_routes._run_pipeline_phase",
            _mock_pipeline_result("adversarial_debate", DEBATE_SNAPSHOT),
        ):
            resp = client.post(
                "/api/v1/agents/debate",
                json={
                    "text": "Democracy is the best form of government for modern societies."
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["winner"] == "Agent A"
        assert len(data["key_exchanges"]) == 1
        assert data["key_exchanges"][0]["agent_a_point"] == "The data shows growth"
        assert (
            data["key_exchanges"][0]["agent_b_rebuttal"] == "But the sample is biased"
        )

    def test_debate_uses_the_last_transcript_when_several(self, client):
        several = {
            "debate_transcripts": [
                {
                    "id": "debate_0",
                    "topic": "first run",
                    "exchanges": [{"point": "old point", "rebuttal": "old rebuttal"}],
                    "winner": "Agent B",
                },
                DEBATE_SNAPSHOT["debate_transcripts"][0],
            ]
        }
        with patch(
            "api.agent_routes._run_pipeline_phase",
            _mock_pipeline_result("adversarial_debate", several),
        ):
            resp = client.post(
                "/api/v1/agents/debate",
                json={"text": "Democracy debate text long enough to pass validation."},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["winner"] == "Agent A"
        assert data["key_exchanges"][0]["agent_a_point"] == "The data shows growth"

    def test_debate_transcript_none_winner_is_empty_string(self, client):
        none_winner = {
            "debate_transcripts": [
                {
                    "id": "debate_0",
                    "topic": "t",
                    "exchanges": [{"point": "p", "rebuttal": "r"}],
                    "winner": None,
                }
            ]
        }
        with patch(
            "api.agent_routes._run_pipeline_phase",
            _mock_pipeline_result("adversarial_debate", none_winner),
        ):
            resp = client.post(
                "/api/v1/agents/debate",
                json={"text": "Democracy debate text long enough to pass validation."},
            )
        assert resp.status_code == 200
        assert resp.json()["winner"] == ""

    def test_debate_empty(self, client):
        with patch(
            "api.agent_routes._run_pipeline_phase",
            _mock_pipeline_result("adversarial_debate", {"debate_transcripts": []}),
        ):
            resp = client.post(
                "/api/v1/agents/debate",
                json={
                    "text": "A minimal text that produces an empty debate result for testing."
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["winner"] == ""
        assert data["key_exchanges"] == []


# ──── Governance Endpoint ────


class TestGovernanceEndpoint:
    def test_governance_success(self, client):
        with patch(
            "api.agent_routes._run_pipeline_phase",
            _mock_pipeline_result("governance_simulation", GOVERNANCE_SNAPSHOT),
        ):
            resp = client.post(
                "/api/v1/agents/governance",
                json={
                    "text": "We should allocate more budget to education than to military spending."
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["decisions"]) == 2
        assert data["decisions"][0]["method"] == "majority"
        assert data["decisions"][0]["winner"] == "proposal_A"
        assert data["consensus_score"] == 0.75
        assert data["summary"] == "Strong consensus for proposal A"

    def test_governance_pipeline_error(self, client):
        mock = AsyncMock(side_effect=RuntimeError("Governance simulation failed"))
        with patch("api.agent_routes._run_pipeline_phase", mock):
            resp = client.post(
                "/api/v1/agents/governance",
                json={
                    "text": "A text that should trigger an error in the governance pipeline."
                },
            )
        assert resp.status_code == 500
        assert "Governance simulation failed" in resp.json()["detail"]


# ──── Full Analysis Endpoint ────


class TestFullAnalysisEndpoint:
    def test_full_analysis_success(self, client):
        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(
            return_value={"extract": _completed("extract", "fact_extraction")}
        )

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.setup_registry",
            return_value=MagicMock(),
        ), patch(
            "argumentation_analysis.orchestration.workflow_dsl.WorkflowExecutor",
            return_value=mock_executor,
        ), patch(
            "argumentation_analysis.evaluation.run_iteration._build_iteration_workflow",
            return_value=MagicMock(),
        ), patch(
            "argumentation_analysis.orchestration.unified_pipeline.CAPABILITY_STATE_WRITERS",
            {"fact_extraction": None},
        ):
            resp = client.post(
                "/api/v1/agents/full-analysis",
                json={
                    "text": "A comprehensive text for full pipeline analysis and testing."
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "fields_populated" in data
        assert "duration_seconds" in data
        assert data["degraded"] is False
        assert data["failed_phases"] == {}


# ──── Input Validation ────


class TestInputValidation:
    def test_max_text_parameter(self, client):
        """Test that max_text parameter is accepted."""
        with patch(
            "api.agent_routes._run_pipeline_phase",
            _mock_pipeline_result("argument_quality", {"quality_scores": {}}),
        ):
            resp = client.post(
                "/api/v1/agents/quality",
                json={"text": "A" * 200, "max_text": 100},
            )
        assert resp.status_code == 200


# ──── #2767: a failed phase is not an answer ────

ENDPOINTS = [
    ("/api/v1/agents/quality", "argument_quality"),
    ("/api/v1/agents/counter-arguments", "counter_argument_generation"),
    ("/api/v1/agents/debate", "adversarial_debate"),
    ("/api/v1/agents/governance", "governance_simulation"),
]
TEXT = {"text": "A synthetic argument long enough for the endpoint."}


def _phase(name, capability, status, error=None, output=None, terminal=False):
    result = PhaseResult(
        phase_name=name,
        status=status,
        capability=capability,
        error=error,
        output=output,
    )
    result.terminal = terminal
    return result


def _fake_run(phases):
    """Patch the executor the real ``_run_pipeline_phase`` builds.

    It returns *phases* and writes nothing to the state, so the snapshot the
    endpoint reads stays empty.
    """
    executor = MagicMock()
    executor.execute = AsyncMock(return_value=phases)
    return [
        patch(
            "argumentation_analysis.orchestration.unified_pipeline.setup_registry",
            return_value=MagicMock(),
        ),
        patch(
            "argumentation_analysis.orchestration.workflow_dsl.WorkflowExecutor",
            return_value=executor,
        ),
    ]


def _post(client, path, phases):
    patches = _fake_run(phases)
    for p in patches:
        p.start()
    try:
        return client.post(path, json=TEXT)
    finally:
        for p in reversed(patches):
            p.stop()


class TestFailedPhaseIsNotSuccess2767:
    @pytest.mark.parametrize("path,capability", ENDPOINTS)
    def test_failed_capability_is_a_named_upstream_error(
        self, client, path, capability
    ):
        resp = _post(
            client,
            path,
            {
                "extract": _phase("extract", "fact_extraction", PhaseStatus.COMPLETED),
                capability: _phase(
                    capability,
                    capability,
                    PhaseStatus.FAILED,
                    error="synthetic provider failure",
                ),
            },
        )
        assert resp.status_code == 502
        body = resp.json()
        assert body["error_code"] == "upstream_error"
        assert capability in body["detail"]
        assert "synthetic provider failure" in body["detail"]
        assert body["context"]["phases"][capability] == "failed"

    @pytest.mark.parametrize("path,capability", ENDPOINTS)
    def test_failed_extraction_names_the_phase_that_failed(
        self, client, path, capability
    ):
        resp = _post(
            client,
            path,
            {
                "extract": _phase(
                    "extract",
                    "fact_extraction",
                    PhaseStatus.FAILED,
                    error="synthetic extraction failure",
                ),
                capability: _phase(capability, capability, PhaseStatus.SKIPPED),
            },
        )
        assert resp.status_code == 502
        detail = resp.json()["detail"]
        assert "fact_extraction" in detail
        assert "synthetic extraction failure" in detail

    @pytest.mark.parametrize("path,capability", ENDPOINTS)
    def test_non_argumentative_text_is_unanalyzable(self, client, path, capability):
        resp = _post(
            client,
            path,
            {
                "extract": _phase(
                    "extract",
                    "fact_extraction",
                    PhaseStatus.COMPLETED,
                    output={"extraction_status": "non_argumentative"},
                    terminal=True,
                ),
                capability: _phase(capability, capability, PhaseStatus.SKIPPED),
            },
        )
        assert resp.status_code == 422
        assert resp.json()["error_code"] == "unanalyzable_input"

    @pytest.mark.parametrize("path,capability", ENDPOINTS)
    def test_completed_capability_keeps_its_valid_empty_answer(
        self, client, path, capability
    ):
        resp = _post(
            client,
            path,
            {
                "extract": _phase("extract", "fact_extraction", PhaseStatus.COMPLETED),
                capability: _phase(capability, capability, PhaseStatus.COMPLETED),
            },
        )
        assert resp.status_code == 200

    def test_full_analysis_names_its_failed_phases(self, client):
        with patch(
            "argumentation_analysis.evaluation.run_iteration._build_iteration_workflow",
            return_value=MagicMock(),
        ):
            resp = _post(
                client,
                "/api/v1/agents/full-analysis",
                {
                    "extract": _phase(
                        "extract", "fact_extraction", PhaseStatus.COMPLETED
                    ),
                    "quality": _phase(
                        "quality",
                        "argument_quality",
                        PhaseStatus.FAILED,
                        error="synthetic quality failure",
                    ),
                    "debate": _phase(
                        "debate", "adversarial_debate", PhaseStatus.SKIPPED
                    ),
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["degraded"] is True
        assert data["failed_phases"] == {
            "quality": "failed: synthetic quality failure",
            "debate": "skipped",
        }

    def test_full_analysis_with_nothing_completed_is_an_upstream_error(self, client):
        with patch(
            "argumentation_analysis.evaluation.run_iteration._build_iteration_workflow",
            return_value=MagicMock(),
        ):
            resp = _post(
                client,
                "/api/v1/agents/full-analysis",
                {
                    "extract": _phase(
                        "extract",
                        "fact_extraction",
                        PhaseStatus.FAILED,
                        error="synthetic extraction failure",
                    ),
                    "quality": _phase(
                        "quality", "argument_quality", PhaseStatus.SKIPPED
                    ),
                },
            )
        assert resp.status_code == 502
        assert "synthetic extraction failure" in resp.json()["detail"]
