#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests for web API models (request/response) and services (ValidationService, FallacyService).

Covers:
- Request model validation (AnalysisRequest, ValidationRequest, FallacyRequest, FrameworkRequest, etc.)
- Response model creation and serialization (FallacyDetection, ArgumentStructure, AnalysisResponse, etc.)
- ValidationService heuristic analysis with mocked LogicService
- FallacyService pattern-based detection with mocked analyzers
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from pydantic import ValidationError

# --- Request Models ---
from argumentation_analysis.services.web_api.models.request_models import (
    AnalysisOptions,
    AnalysisRequest,
    ValidationRequest,
    FallacyOptions,
    FallacyRequest,
    Argument,
    FrameworkOptions,
    FrameworkRequest,
    FrameworkAnalysisRequest,
    LogicBeliefSetRequest,
    LogicQueryRequest,
)

# --- Response Models ---
from argumentation_analysis.services.web_api.models.response_models import (
    FallacyDetection,
    ArgumentStructure,
    AnalysisResponse,
    ValidationResult,
    ValidationResponse,
    FallacyResponse,
    ErrorResponse,
    SuccessResponse,
    ArgumentNode,
    Extension,
    FrameworkVisualization,
    FrameworkResponse,
    LogicQueryResult,
)


# ============================================================================
# Request Models
# ============================================================================


class TestAnalysisOptions:
    """Tests for AnalysisOptions default values and validation."""

    def test_default_values(self):
        """All defaults should be True/0.5."""
        opts = AnalysisOptions()
        assert opts.detect_fallacies is True
        assert opts.analyze_structure is True
        assert opts.evaluate_coherence is True
        assert opts.include_context is True
        assert opts.severity_threshold == 0.5

    def test_custom_values(self):
        opts = AnalysisOptions(
            detect_fallacies=False,
            analyze_structure=False,
            severity_threshold=0.8,
        )
        assert opts.detect_fallacies is False
        assert opts.analyze_structure is False
        assert opts.severity_threshold == 0.8

    def test_severity_threshold_bounds(self):
        """severity_threshold must be in [0.0, 1.0]."""
        with pytest.raises(ValidationError):
            AnalysisOptions(severity_threshold=-0.1)
        with pytest.raises(ValidationError):
            AnalysisOptions(severity_threshold=1.1)

    def test_severity_threshold_edge_values(self):
        """Edge values 0.0 and 1.0 should be accepted."""
        opts_zero = AnalysisOptions(severity_threshold=0.0)
        assert opts_zero.severity_threshold == 0.0
        opts_one = AnalysisOptions(severity_threshold=1.0)
        assert opts_one.severity_threshold == 1.0


class TestAnalysisRequestModel:
    """Tests for AnalysisRequest validation."""

    def test_valid_text(self):
        req = AnalysisRequest(text="This is a valid argument.")
        assert req.text == "This is a valid argument."
        assert req.options is not None  # default_factory creates AnalysisOptions

    def test_text_gets_stripped(self):
        req = AnalysisRequest(text="  padded text  ")
        assert req.text == "padded text"

    def test_empty_text_raises(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(text="")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError):
            AnalysisRequest(text="   ")

    def test_custom_options(self):
        opts = AnalysisOptions(detect_fallacies=False, severity_threshold=0.9)
        req = AnalysisRequest(text="Some text", options=opts)
        assert req.options.detect_fallacies is False
        assert req.options.severity_threshold == 0.9

    def test_none_options_uses_default(self):
        """When options is explicitly None, it should still allow creation (default_factory)."""
        req = AnalysisRequest(text="Valid", options=None)
        assert req.options is None


class TestValidationRequestModel:
    """Tests for ValidationRequest validation."""

    def test_valid_request(self):
        req = ValidationRequest(
            premises=["All men are mortal", "Socrates is a man"],
            conclusion="Socrates is mortal",
        )
        assert len(req.premises) == 2
        assert req.conclusion == "Socrates is mortal"
        assert req.argument_type == "deductive"  # default

    def test_premises_get_stripped(self):
        req = ValidationRequest(
            premises=["  premise one  ", "  premise two  "],
            conclusion="conclusion",
        )
        assert req.premises == ["premise one", "premise two"]

    def test_premises_empty_strings_filtered(self):
        """Empty strings in premises list should be filtered out."""
        req = ValidationRequest(
            premises=["valid premise", "", "  "],
            conclusion="conclusion",
        )
        assert req.premises == ["valid premise"]

    def test_empty_premises_list_raises(self):
        with pytest.raises(ValidationError):
            ValidationRequest(premises=[], conclusion="conclusion")

    def test_all_empty_premises_raises(self):
        """If all premises are empty/whitespace, validation should fail."""
        with pytest.raises(ValidationError):
            ValidationRequest(premises=["", "  ", ""], conclusion="conclusion")

    def test_empty_conclusion_raises(self):
        with pytest.raises(ValidationError):
            ValidationRequest(premises=["a premise"], conclusion="")

    def test_whitespace_conclusion_raises(self):
        with pytest.raises(ValidationError):
            ValidationRequest(premises=["a premise"], conclusion="   ")

    def test_conclusion_gets_stripped(self):
        req = ValidationRequest(
            premises=["premise"],
            conclusion="  the conclusion  ",
        )
        assert req.conclusion == "the conclusion"

    def test_valid_argument_types(self):
        for arg_type in ["deductive", "inductive", "abductive"]:
            req = ValidationRequest(
                premises=["p1"],
                conclusion="c1",
                argument_type=arg_type,
            )
            assert req.argument_type == arg_type

    def test_invalid_argument_type_raises(self):
        with pytest.raises(ValidationError):
            ValidationRequest(
                premises=["p1"],
                conclusion="c1",
                argument_type="invalid_type",
            )

    def test_none_argument_type_accepted(self):
        req = ValidationRequest(
            premises=["p1"],
            conclusion="c1",
            argument_type=None,
        )
        assert req.argument_type is None


class TestFallacyRequestModel:
    """Tests for FallacyRequest and FallacyOptions."""

    def test_valid_fallacy_request(self):
        req = FallacyRequest(text="This is a fallacious argument")
        assert req.text == "This is a fallacious argument"
        assert req.options is not None
        assert req.options.severity_threshold == 0.5

    def test_text_stripped(self):
        req = FallacyRequest(text="  text with spaces  ")
        assert req.text == "text with spaces"

    def test_empty_text_raises(self):
        with pytest.raises(ValidationError):
            FallacyRequest(text="")

    def test_whitespace_text_raises(self):
        with pytest.raises(ValidationError):
            FallacyRequest(text="   ")

    def test_fallacy_options_defaults(self):
        opts = FallacyOptions()
        assert opts.severity_threshold == 0.5
        assert opts.include_context is True
        assert opts.max_fallacies == 10
        assert opts.categories is None
        assert opts.use_enhanced is True
        assert opts.use_contextual is True
        assert opts.use_patterns is True

    def test_fallacy_options_max_fallacies_bounds(self):
        with pytest.raises(ValidationError):
            FallacyOptions(max_fallacies=0)  # ge=1
        with pytest.raises(ValidationError):
            FallacyOptions(max_fallacies=51)  # le=50

    def test_fallacy_options_custom(self):
        opts = FallacyOptions(
            severity_threshold=0.3,
            max_fallacies=20,
            categories=["formal", "informal"],
            use_enhanced=False,
        )
        assert opts.severity_threshold == 0.3
        assert opts.max_fallacies == 20
        assert opts.categories == ["formal", "informal"]
        assert opts.use_enhanced is False


class TestFrameworkRequestModel:
    """Tests for Argument, FrameworkOptions, and FrameworkRequest."""

    def test_valid_argument(self):
        arg = Argument(id="a1", content="First argument")
        assert arg.id == "a1"
        assert arg.content == "First argument"
        assert arg.attacks == []
        assert arg.supports == []

    def test_argument_id_stripped(self):
        arg = Argument(id="  a1  ", content="content")
        assert arg.id == "a1"

    def test_argument_empty_id_raises(self):
        with pytest.raises(ValidationError):
            Argument(id="", content="content")

    def test_argument_empty_content_raises(self):
        with pytest.raises(ValidationError):
            Argument(id="a1", content="")

    def test_framework_options_defaults(self):
        opts = FrameworkOptions()
        assert opts.compute_extensions is True
        assert opts.semantics == "preferred"
        assert opts.include_visualization is True
        assert opts.max_arguments == 100

    def test_framework_options_invalid_semantics(self):
        with pytest.raises(ValidationError):
            FrameworkOptions(semantics="invalid")

    def test_framework_options_valid_semantics(self):
        for sem in ["grounded", "complete", "preferred", "stable", "semi-stable"]:
            opts = FrameworkOptions(semantics=sem)
            assert opts.semantics == sem

    def test_framework_request_valid(self):
        args = [
            Argument(id="a1", content="Arg 1", attacks=["a2"]),
            Argument(id="a2", content="Arg 2"),
        ]
        req = FrameworkRequest(arguments=args)
        assert len(req.arguments) == 2

    def test_framework_request_empty_raises(self):
        with pytest.raises(ValidationError):
            FrameworkRequest(arguments=[])

    def test_framework_request_duplicate_ids_raises(self):
        args = [
            Argument(id="a1", content="Arg 1"),
            Argument(id="a1", content="Arg 2"),
        ]
        with pytest.raises(ValidationError, match="uniques"):
            FrameworkRequest(arguments=args)

    def test_framework_request_invalid_attack_ref_raises(self):
        args = [
            Argument(id="a1", content="Arg 1", attacks=["nonexistent"]),
        ]
        with pytest.raises(ValidationError, match="non trouvé"):
            FrameworkRequest(arguments=args)

    def test_framework_request_invalid_support_ref_raises(self):
        args = [
            Argument(id="a1", content="Arg 1", supports=["nonexistent"]),
        ]
        with pytest.raises(ValidationError, match="non trouvé"):
            FrameworkRequest(arguments=args)

    def test_framework_analysis_request(self):
        req = FrameworkAnalysisRequest(
            arguments=["a1", "a2", "a3"],
            attacks=[["a1", "a2"], ["a2", "a3"]],
        )
        assert len(req.arguments) == 3
        assert len(req.attacks) == 2


class TestLogicRequestModels:
    """Tests for LogicBeliefSetRequest and LogicQueryRequest."""

    def test_logic_belief_set_request_valid(self):
        req = LogicBeliefSetRequest(
            text="All dogs are animals",
            logic_type="first_order",
        )
        assert req.text == "All dogs are animals"
        assert req.logic_type == "first_order"

    def test_logic_belief_set_invalid_type(self):
        with pytest.raises(ValidationError):
            LogicBeliefSetRequest(text="some text", logic_type="fuzzy")

    def test_logic_belief_set_empty_text_raises(self):
        with pytest.raises(ValidationError):
            LogicBeliefSetRequest(text="", logic_type="propositional")

    def test_logic_query_request_valid(self):
        req = LogicQueryRequest(
            belief_set_id="bs-123",
            query="forall X: dog(X) => animal(X)",
            logic_type="first_order",
        )
        assert req.belief_set_id == "bs-123"
        assert req.logic_type == "first_order"

    def test_logic_query_invalid_logic_type(self):
        with pytest.raises(ValidationError):
            LogicQueryRequest(
                belief_set_id="bs-1",
                query="p => q",
                logic_type="invalid",
            )

    def test_logic_query_empty_query_raises(self):
        with pytest.raises(ValidationError):
            LogicQueryRequest(
                belief_set_id="bs-1",
                query="",
                logic_type="propositional",
            )


# ============================================================================
# Response Models
# ============================================================================


class TestResponseModels:
    """Tests for response model creation and serialization."""

    def test_fallacy_detection_creation(self):
        fd = FallacyDetection(
            type="ad_hominem",
            name="Ad Hominem",
            description="Attack on the person",
            severity=0.8,
            confidence=0.9,
        )
        assert fd.type == "ad_hominem"
        assert fd.severity == 0.8
        assert fd.confidence == 0.9
        assert fd.location is None
        assert fd.context is None
        assert fd.explanation is None

    def test_fallacy_detection_with_optional_fields(self):
        fd = FallacyDetection(
            type="straw_man",
            name="Straw Man",
            description="Misrepresenting the argument",
            severity=0.7,
            confidence=0.85,
            location={"start": 10, "end": 50},
            context="some surrounding text",
            explanation="The argument was distorted",
        )
        assert fd.location == {"start": 10, "end": 50}
        assert fd.context == "some surrounding text"

    def test_fallacy_detection_severity_bounds(self):
        with pytest.raises(ValidationError):
            FallacyDetection(
                type="x", name="x", description="x",
                severity=1.5, confidence=0.5,
            )
        with pytest.raises(ValidationError):
            FallacyDetection(
                type="x", name="x", description="x",
                severity=0.5, confidence=-0.1,
            )

    def test_argument_structure_defaults(self):
        struct = ArgumentStructure()
        assert struct.premises == []
        assert struct.conclusion == ""
        assert struct.argument_type == "unknown"
        assert struct.strength == 0.0
        assert struct.coherence == 0.0

    def test_argument_structure_custom(self):
        struct = ArgumentStructure(
            premises=["P1", "P2"],
            conclusion="C",
            argument_type="deductive",
            strength=0.9,
            coherence=0.8,
        )
        assert len(struct.premises) == 2
        assert struct.strength == 0.9

    def test_analysis_response_creation(self):
        resp = AnalysisResponse(
            success=True,
            text_analyzed="Some text",
            overall_quality=0.75,
            coherence_score=0.8,
            fallacy_count=2,
        )
        assert resp.success is True
        assert resp.text_analyzed == "Some text"
        assert resp.overall_quality == 0.75
        assert resp.fallacy_count == 2
        assert isinstance(resp.analysis_timestamp, datetime)

    def test_validation_result_creation(self):
        result = ValidationResult(
            is_valid=True,
            validity_score=0.85,
            soundness_score=0.7,
        )
        assert result.is_valid is True
        assert result.validity_score == 0.85
        assert result.soundness_score == 0.7
        assert result.issues == []
        assert result.suggestions == []

    def test_validation_response_creation(self):
        result = ValidationResult(
            is_valid=True,
            validity_score=0.9,
            soundness_score=0.8,
        )
        resp = ValidationResponse(
            success=True,
            premises=["P1"],
            conclusion="C1",
            argument_type="deductive",
            result=result,
        )
        assert resp.success is True
        assert resp.premises == ["P1"]
        assert resp.result.validity_score == 0.9

    def test_fallacy_response_creation(self):
        resp = FallacyResponse(
            success=True,
            text_analyzed="test text",
            fallacy_count=0,
        )
        assert resp.success is True
        assert resp.fallacies == []
        assert resp.fallacy_count == 0
        assert isinstance(resp.detection_timestamp, datetime)

    def test_error_response_creation(self):
        err = ErrorResponse(
            error="ValidationError",
            message="Invalid input",
            status_code=400,
        )
        assert err.error == "ValidationError"
        assert err.message == "Invalid input"
        assert err.status_code == 400
        assert isinstance(err.timestamp, datetime)
        assert err.details is None

    def test_error_response_with_details(self):
        err = ErrorResponse(
            error="ServerError",
            message="Something went wrong",
            status_code=500,
            details={"trace": "stack trace here"},
        )
        assert err.details == {"trace": "stack trace here"}

    def test_success_response_defaults(self):
        resp = SuccessResponse()
        assert resp.message == "Operation successful"
        assert resp.data is None
        assert resp.status_code == 200
        assert isinstance(resp.timestamp, datetime)

    def test_success_response_custom(self):
        resp = SuccessResponse(
            message="Created",
            data={"id": 42},
            status_code=201,
        )
        assert resp.message == "Created"
        assert resp.data == {"id": 42}
        assert resp.status_code == 201

    def test_argument_node_creation(self):
        node = ArgumentNode(id="a1", content="My argument")
        assert node.id == "a1"
        assert node.status == "undecided"
        assert node.attacks == []
        assert node.attacked_by == []

    def test_extension_creation(self):
        ext = Extension(
            type="preferred",
            arguments=["a1", "a3"],
            is_preferred=True,
        )
        assert ext.type == "preferred"
        assert ext.arguments == ["a1", "a3"]
        assert ext.is_preferred is True
        assert ext.is_complete is False

    def test_framework_response_creation(self):
        resp = FrameworkResponse(
            success=True,
            semantics_used="preferred",
            argument_count=3,
            attack_count=2,
        )
        assert resp.success is True
        assert resp.semantics_used == "preferred"
        assert resp.arguments == []
        assert resp.extensions == []

    def test_logic_query_result(self):
        qr = LogicQueryResult(
            query="p => q",
            result=True,
            formatted_result="True",
            explanation="Modus ponens applied",
        )
        assert qr.result is True
        assert qr.explanation == "Modus ponens applied"

    def test_response_model_serialization(self):
        """Models should serialize to dict without errors."""
        resp = SuccessResponse(message="ok", data={"key": "value"})
        d = resp.model_dump()
        assert d["message"] == "ok"
        assert d["data"] == {"key": "value"}
        assert "timestamp" in d

    def test_error_response_serialization(self):
        err = ErrorResponse(error="E", message="M", status_code=422)
        d = err.model_dump()
        assert d["error"] == "E"
        assert d["status_code"] == 422


# ============================================================================
# ValidationService
# ============================================================================


class TestValidationService:
    """Tests for ValidationService with mocked LogicService."""

    @pytest.fixture
    def mock_logic_service(self):
        """Create a mock LogicService."""
        service = MagicMock()
        service.is_healthy.return_value = True
        return service

    @pytest.fixture
    def validation_service(self, mock_logic_service):
        """Create a ValidationService instance with mocked dependencies."""
        from argumentation_analysis.services.web_api.services.validation_service import (
            ValidationService,
        )
        return ValidationService(logic_service=mock_logic_service)

    def test_init(self, validation_service):
        """Service should initialize properly."""
        assert validation_service.is_initialized is True
        assert validation_service.logical_connectors is not None
        assert validation_service.premise_indicators is not None

    def test_is_healthy_when_all_ok(self, validation_service, mock_logic_service):
        """is_healthy should return True when both self and logic_service are healthy."""
        mock_logic_service.is_healthy.return_value = True
        assert validation_service.is_healthy() is True

    def test_is_healthy_logic_service_down(self, validation_service, mock_logic_service):
        """is_healthy returns False when logic_service is unhealthy."""
        mock_logic_service.is_healthy.return_value = False
        assert validation_service.is_healthy() is False

    def test_is_healthy_not_initialized(self, validation_service, mock_logic_service):
        """is_healthy returns False when not initialized (even if logic_service is ok)."""
        validation_service.is_initialized = False
        mock_logic_service.is_healthy.return_value = True
        assert validation_service.is_healthy() is False

    @pytest.mark.asyncio
    async def test_validate_argument_valid(self, validation_service):
        """Heuristic validation with well-formed argument should succeed."""
        request = ValidationRequest(
            premises=[
                "Selon une etude, tous les chats sont des animaux domestiques",
                "Mon animal est un chat",
            ],
            conclusion="Donc mon animal est un animal domestique",
            argument_type="deductive",
        )
        response = await validation_service.validate_argument(request)
        assert response.success is True
        assert response.argument_type == "deductive"
        assert response.result.validity_score >= 0.0
        assert response.result.validity_score <= 1.0
        assert response.processing_time >= 0.0
        assert len(response.premises) == 2

    @pytest.mark.asyncio
    async def test_validate_argument_single_premise(self, validation_service):
        """Argument with single short premise should still work but may flag issues."""
        request = ValidationRequest(
            premises=["P1"],
            conclusion="C1",
            argument_type="deductive",
        )
        response = await validation_service.validate_argument(request)
        assert response.success is True
        # Single short premise typically gets low clarity
        assert response.result is not None

    @pytest.mark.asyncio
    async def test_validate_argument_inductive(self, validation_service):
        """Inductive argument should include type-specific suggestion."""
        request = ValidationRequest(
            premises=[
                "Le premier cygne observe est blanc",
                "Le deuxieme cygne observe est blanc",
            ],
            conclusion="Tous les cygnes sont blancs",
            argument_type="inductive",
        )
        response = await validation_service.validate_argument(request)
        assert response.success is True
        assert response.argument_type == "inductive"
        # Should contain inductive-specific suggestion
        has_inductive_suggestion = any(
            "inductif" in s for s in response.result.suggestions
        )
        assert has_inductive_suggestion

    @pytest.mark.asyncio
    async def test_validate_argument_returns_premise_analysis(self, validation_service):
        """Each premise should be individually analyzed."""
        request = ValidationRequest(
            premises=["Premise one is clear", "Premise two is also clear"],
            conclusion="The conclusion follows",
        )
        response = await validation_service.validate_argument(request)
        assert response.success is True
        assert len(response.result.premise_analysis) == 2
        for pa in response.result.premise_analysis:
            assert "text" in pa
            assert "clarity_score" in pa
            assert "strength" in pa

    @pytest.mark.asyncio
    async def test_validate_argument_conclusion_analysis(self, validation_service):
        """Conclusion should be analyzed for clarity and strength."""
        request = ValidationRequest(
            premises=["A valid premise statement"],
            conclusion="Therefore the conclusion is established clearly",
        )
        response = await validation_service.validate_argument(request)
        assert response.success is True
        ca = response.result.conclusion_analysis
        assert "clarity_score" in ca
        assert "strength" in ca

    @pytest.mark.asyncio
    async def test_validate_argument_logical_structure(self, validation_service):
        """Logical structure analysis should be present and include method=heuristic."""
        request = ValidationRequest(
            premises=["P1 with some words", "P2 with more words"],
            conclusion="The conclusion with some words from premises",
        )
        response = await validation_service.validate_argument(request)
        assert response.success is True
        ls = response.result.logical_structure
        assert ls.get("method") == "heuristic"
        assert "premise_relevance" in ls
        assert "logical_flow" in ls
        assert "completeness" in ls

    def test_assess_clarity_short_text(self, validation_service):
        """Very short text should get low clarity score."""
        assert validation_service._assess_clarity("hi") == 0.3

    def test_assess_clarity_normal_text(self, validation_service):
        """Normal length text should get good clarity score."""
        assert validation_service._assess_clarity("This is a normal length sentence") == 0.8

    def test_assess_clarity_long_text(self, validation_service):
        """Very long text should get medium clarity score."""
        long_text = " ".join(["word"] * 35)
        assert validation_service._assess_clarity(long_text) == 0.6

    def test_assess_specificity_vague(self, validation_service):
        """Text with vague terms should get low specificity."""
        assert validation_service._assess_specificity("Certains pensent souvent que") == 0.4

    def test_assess_specificity_precise(self, validation_service):
        """Text without vague terms should get higher specificity."""
        assert validation_service._assess_specificity("Le chat est sur le tapis") == 0.7

    def test_assess_credibility_with_source(self, validation_service):
        """Text mentioning sources should score higher."""
        assert validation_service._assess_credibility("Selon une etude recente") == 0.8

    def test_assess_credibility_without_source(self, validation_service):
        """Text without source indicators scores lower."""
        assert validation_service._assess_credibility("Le ciel est bleu") == 0.6

    def test_contains_qualifiers_true(self, validation_service):
        assert validation_service._contains_qualifiers("C'est probablement vrai") is True

    def test_contains_qualifiers_false(self, validation_service):
        assert validation_service._contains_qualifiers("C'est vrai") is False

    def test_is_factual_claim_true(self, validation_service):
        assert validation_service._is_factual_claim("La terre est ronde") is True

    def test_is_factual_claim_false_opinion(self, validation_service):
        assert validation_service._is_factual_claim("Je crois que c'est vrai") is False

    def test_has_logical_connectors_true(self, validation_service):
        assert validation_service._has_logical_connectors("donc il est vrai") is True
        assert validation_service._has_logical_connectors("par conséquent") is True

    def test_has_logical_connectors_false(self, validation_service):
        assert validation_service._has_logical_connectors("le chat est gris") is False

    def test_assess_consistency_single_premise(self, validation_service):
        """Single premise always consistent."""
        assert validation_service._assess_consistency(["one"]) == 1.0

    def test_assess_consistency_multiple_premises(self, validation_service):
        """Multiple premises get baseline consistency score."""
        assert validation_service._assess_consistency(["one", "two"]) == 0.7

    def test_identify_logical_gaps(self, validation_service):
        """Should identify gaps when premises are irrelevant and few."""
        gaps = validation_service._identify_logical_gaps(
            ["les pommes sont rouges"], "la lune est bleue"
        )
        assert any("pertinence" in g.lower() for g in gaps)
        assert any("insuffisant" in g.lower() for g in gaps)

    def test_soundness_score_empty_premises(self, validation_service):
        """Empty premise analysis should give 0.0 soundness."""
        score = validation_service._calculate_soundness_score([], 0.8)
        assert score == 0.0

    def test_validity_score_empty_premises(self, validation_service):
        """Empty premise analysis should give 0.0 validity."""
        score = validation_service._calculate_validity_score([], {}, {})
        assert score == 0.0


# ============================================================================
# FallacyService
# ============================================================================


class TestFallacyService:
    """Tests for FallacyService with mocked analyzers."""

    @pytest.fixture
    def fallacy_service(self):
        """Create a FallacyService with mocked analyzers (import-level patch)."""
        # Patch the analyzer imports so __init__ does not fail on missing deps
        with patch(
            "argumentation_analysis.services.web_api.services.fallacy_service.ContextualFallacyAnalyzer",
            None,
        ), patch(
            "argumentation_analysis.services.web_api.services.fallacy_service.FallacySeverityEvaluator",
            None,
        ), patch(
            "argumentation_analysis.services.web_api.services.fallacy_service.EnhancedContextualAnalyzer",
            None,
        ):
            from argumentation_analysis.services.web_api.services.fallacy_service import (
                FallacyService,
            )
            service = FallacyService()
        return service

    def test_init_without_analyzers(self, fallacy_service):
        """Service should still initialize (with patterns only) even without analyzers."""
        # is_initialized might be True because the try block succeeds even with None analyzers
        assert fallacy_service.fallacy_patterns is not None
        assert len(fallacy_service.fallacy_patterns) > 0

    def test_is_healthy_with_patterns(self, fallacy_service):
        """is_healthy should return True as long as fallacy_patterns are loaded."""
        assert fallacy_service.is_healthy() is True

    def test_fallacy_database_loaded(self, fallacy_service):
        """Database should contain expected fallacy types."""
        patterns = fallacy_service.fallacy_patterns
        assert "ad_hominem" in patterns
        assert "circular_reasoning" in patterns
        assert "straw_man" in patterns
        assert "false_dilemma" in patterns
        assert "slippery_slope" in patterns
        assert "appeal_to_authority" in patterns
        assert "appeal_to_emotion" in patterns
        assert "bandwagon" in patterns
        assert "hasty_generalization" in patterns

    def test_get_fallacy_types(self, fallacy_service):
        """get_fallacy_types should return structured info for each type."""
        types = fallacy_service.get_fallacy_types()
        assert "ad_hominem" in types
        ad_hominem_info = types["ad_hominem"]
        assert "name" in ad_hominem_info
        assert "description" in ad_hominem_info
        assert "category" in ad_hominem_info
        assert "severity" in ad_hominem_info

    def test_get_categories(self, fallacy_service):
        """Should return unique categories."""
        categories = fallacy_service.get_categories()
        assert "formal" in categories
        assert "informal" in categories

    def test_detect_fallacies_false_dilemma(self, fallacy_service):
        """Pattern detection should find false dilemma."""
        request = FallacyRequest(
            text="Soit vous etes avec nous, soit vous etes contre nous",
            options=FallacyOptions(
                use_contextual=False,
                use_enhanced=False,
                use_patterns=True,
                severity_threshold=0.0,
            ),
        )
        response = fallacy_service.detect_fallacies(request)
        assert response.success is True
        assert response.text_analyzed == "Soit vous etes avec nous, soit vous etes contre nous"
        # The "soit.*soit" pattern should match
        fallacy_types = [f.type for f in response.fallacies]
        assert "false_dilemma" in fallacy_types

    def test_detect_fallacies_appeal_to_emotion(self, fallacy_service):
        """Pattern detection should find appeal to emotion."""
        request = FallacyRequest(
            text="Pensez aux enfants qui souffrent, cette mesure est catastrophique",
            options=FallacyOptions(
                use_contextual=False,
                use_enhanced=False,
                use_patterns=True,
                severity_threshold=0.0,
            ),
        )
        response = fallacy_service.detect_fallacies(request)
        assert response.success is True
        fallacy_types = [f.type for f in response.fallacies]
        assert "appeal_to_emotion" in fallacy_types

    def test_detect_fallacies_no_match(self, fallacy_service):
        """Clean text should not trigger any pattern."""
        request = FallacyRequest(
            text="Le soleil se leve a l'est",
            options=FallacyOptions(
                use_contextual=False,
                use_enhanced=False,
                use_patterns=True,
                severity_threshold=0.0,
            ),
        )
        response = fallacy_service.detect_fallacies(request)
        assert response.success is True
        assert response.fallacy_count == 0

    def test_detect_fallacies_severity_filtering(self, fallacy_service):
        """High severity threshold should filter out low-severity detections."""
        request = FallacyRequest(
            text="Soit ceci soit cela, c'est un faux dilemme",
            options=FallacyOptions(
                use_contextual=False,
                use_enhanced=False,
                use_patterns=True,
                severity_threshold=0.9,  # false_dilemma has severity 0.6
            ),
        )
        response = fallacy_service.detect_fallacies(request)
        assert response.success is True
        # false_dilemma severity is 0.6, should be filtered at threshold 0.9
        fallacy_types = [f.type for f in response.fallacies]
        assert "false_dilemma" not in fallacy_types

    def test_detect_fallacies_response_structure(self, fallacy_service):
        """Response should have correct structure with distributions."""
        request = FallacyRequest(
            text="Pensez aux enfants, c'est terrible et catastrophique",
            options=FallacyOptions(
                use_contextual=False,
                use_enhanced=False,
                use_patterns=True,
                severity_threshold=0.0,
            ),
        )
        response = fallacy_service.detect_fallacies(request)
        assert response.success is True
        assert isinstance(response.severity_distribution, dict)
        assert isinstance(response.category_distribution, dict)
        assert response.processing_time >= 0.0

    def test_severity_distribution_calculation(self, fallacy_service):
        """Severity distribution should classify into low/medium/high."""
        fallacies = [
            FallacyDetection(type="a", name="A", description="d", severity=0.3, confidence=0.5),
            FallacyDetection(type="b", name="B", description="d", severity=0.5, confidence=0.5),
            FallacyDetection(type="c", name="C", description="d", severity=0.8, confidence=0.5),
        ]
        dist = fallacy_service._calculate_severity_distribution(fallacies)
        assert dist["low"] == 1      # 0.3 < 0.4
        assert dist["medium"] == 1   # 0.4 <= 0.5 < 0.7
        assert dist["high"] == 1     # 0.8 >= 0.7

    def test_category_distribution_calculation(self, fallacy_service):
        """Category distribution should count by type -> category mapping."""
        fallacies = [
            FallacyDetection(type="ad_hominem", name="AH", description="d", severity=0.5, confidence=0.5),
            FallacyDetection(type="affirming_consequent", name="AC", description="d", severity=0.5, confidence=0.5),
            FallacyDetection(type="unknown_type", name="U", description="d", severity=0.5, confidence=0.5),
        ]
        dist = fallacy_service._calculate_category_distribution(fallacies)
        assert dist.get("informal", 0) == 1  # ad_hominem is informal
        assert dist.get("formal", 0) == 1    # affirming_consequent is formal
        assert dist.get("unknown", 0) == 1   # unknown_type not in patterns

    def test_extract_context(self, fallacy_service):
        """Context extraction around a position."""
        text = "A" * 100
        ctx = fallacy_service._extract_context(text, 50, context_size=10)
        assert ctx is not None
        assert len(ctx) <= 20  # 10 before + 10 after

    def test_extract_context_invalid_position(self, fallacy_service):
        """Negative position should return None."""
        assert fallacy_service._extract_context("text", -1) is None

    def test_filter_and_deduplicate(self, fallacy_service):
        """Duplicate fallacies (same type+location) should be removed."""
        f1 = FallacyDetection(
            type="ad_hominem", name="AH", description="d",
            severity=0.8, confidence=0.5, location={"start": 10, "end": 20},
        )
        f2 = FallacyDetection(
            type="ad_hominem", name="AH", description="d",
            severity=0.8, confidence=0.5, location={"start": 10, "end": 25},
        )
        f3 = FallacyDetection(
            type="straw_man", name="SM", description="d",
            severity=0.7, confidence=0.5, location={"start": 30, "end": 40},
        )
        result = fallacy_service._filter_and_deduplicate([f1, f2, f3], None)
        # f1 and f2 have same type + start position -> deduplicated
        assert len(result) == 2

    def test_filter_and_deduplicate_max_fallacies(self, fallacy_service):
        """Should respect max_fallacies limit."""
        fallacies = [
            FallacyDetection(
                type=f"type_{i}", name=f"F{i}", description="d",
                severity=0.8, confidence=0.5,
            )
            for i in range(20)
        ]
        opts = FallacyOptions(max_fallacies=5, severity_threshold=0.0)
        result = fallacy_service._filter_and_deduplicate(fallacies, opts)
        assert len(result) == 5

    def test_pattern_matches_regex(self, fallacy_service):
        """Pattern matching should work with regex."""
        assert fallacy_service._pattern_matches("soit.*soit", "soit ceci soit cela") is True
        assert fallacy_service._pattern_matches("soit.*soit", "rien du tout") is False

    def test_pattern_matches_fallback(self, fallacy_service):
        """Invalid regex should fall back to substring search."""
        # This pattern has unbalanced brackets, should trigger fallback
        assert fallacy_service._pattern_matches("[invalid", "some [invalid text") is True

    def test_detect_fallacies_error_handling(self, fallacy_service):
        """If an internal error occurs, service should return success=False gracefully."""
        # Force an error by making fallacy_patterns a non-iterable
        original = fallacy_service.fallacy_patterns
        fallacy_service.fallacy_patterns = None  # Will cause iteration error

        request = FallacyRequest(
            text="test",
            options=FallacyOptions(
                use_contextual=False,
                use_enhanced=False,
                use_patterns=True,
            ),
        )
        response = fallacy_service.detect_fallacies(request)
        assert response.success is False
        assert response.fallacy_count == 0

        # Restore
        fallacy_service.fallacy_patterns = original
