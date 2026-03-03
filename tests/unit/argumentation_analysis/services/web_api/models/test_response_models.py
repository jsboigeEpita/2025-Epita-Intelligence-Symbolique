# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.services.web_api.models.response_models
Covers all Pydantic models: FallacyDetection, ArgumentStructure, AnalysisResponse,
ValidationResult, ValidationResponse, FallacyResponse, ArgumentNode, Extension,
FrameworkVisualization, FrameworkResponse, ErrorResponse, LogicQueryResult,
LogicBeliefSet, LogicBeliefSetResponse, LogicQueryResponse,
LogicGenerateQueriesResponse, LogicInterpretationResponse, SuccessResponse.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from argumentation_analysis.services.web_api.models.response_models import (
    FallacyDetection,
    ArgumentStructure,
    AnalysisResponse,
    ValidationResult,
    ValidationResponse,
    FallacyResponse,
    ArgumentNode,
    Extension,
    FrameworkVisualization,
    FrameworkResponse,
    ErrorResponse,
    LogicQueryResult,
    LogicBeliefSet,
    LogicBeliefSetResponse,
    LogicQueryResponse,
    LogicGenerateQueriesResponse,
    LogicInterpretationResponse,
    SuccessResponse,
)


# ============================================================
# FallacyDetection
# ============================================================

class TestFallacyDetection:
    def test_valid_creation(self):
        fd = FallacyDetection(
            type="ad_hominem", name="Ad Hominem",
            description="Attaque la personne", severity=0.8, confidence=0.9,
        )
        assert fd.type == "ad_hominem"
        assert fd.severity == 0.8

    def test_optional_fields_default_none(self):
        fd = FallacyDetection(
            type="t", name="n", description="d", severity=0.5, confidence=0.5,
        )
        assert fd.location is None
        assert fd.context is None
        assert fd.explanation is None

    def test_with_optional_fields(self):
        fd = FallacyDetection(
            type="t", name="n", description="d", severity=0.5, confidence=0.5,
            location={"start": 0, "end": 10}, context="ctx", explanation="expl",
        )
        assert fd.location == {"start": 0, "end": 10}
        assert fd.context == "ctx"

    def test_severity_out_of_range(self):
        with pytest.raises(ValidationError):
            FallacyDetection(
                type="t", name="n", description="d", severity=1.5, confidence=0.5,
            )

    def test_confidence_out_of_range(self):
        with pytest.raises(ValidationError):
            FallacyDetection(
                type="t", name="n", description="d", severity=0.5, confidence=-0.1,
            )

    def test_severity_boundaries(self):
        fd0 = FallacyDetection(type="t", name="n", description="d", severity=0.0, confidence=0.0)
        fd1 = FallacyDetection(type="t", name="n", description="d", severity=1.0, confidence=1.0)
        assert fd0.severity == 0.0
        assert fd1.severity == 1.0


# ============================================================
# ArgumentStructure
# ============================================================

class TestArgumentStructure:
    def test_defaults(self):
        a = ArgumentStructure()
        assert a.premises == []
        assert a.conclusion == ""
        assert a.argument_type == "unknown"
        assert a.strength == 0.0
        assert a.coherence == 0.0

    def test_custom_values(self):
        a = ArgumentStructure(
            premises=["P1", "P2"], conclusion="C",
            argument_type="deductive", strength=0.8, coherence=0.7,
        )
        assert len(a.premises) == 2
        assert a.argument_type == "deductive"

    def test_strength_out_of_range(self):
        with pytest.raises(ValidationError):
            ArgumentStructure(strength=1.5)

    def test_coherence_out_of_range(self):
        with pytest.raises(ValidationError):
            ArgumentStructure(coherence=-0.1)


# ============================================================
# AnalysisResponse
# ============================================================

class TestAnalysisResponse:
    def test_minimal_creation(self):
        r = AnalysisResponse(success=True, text_analyzed="Hello")
        assert r.success is True
        assert r.text_analyzed == "Hello"
        assert isinstance(r.analysis_timestamp, datetime)

    def test_defaults(self):
        r = AnalysisResponse(success=False, text_analyzed="X")
        assert r.fallacies == []
        assert r.argument_structure is None
        assert r.overall_quality == 0.0
        assert r.coherence_score == 0.0
        assert r.fallacy_count == 0
        assert r.processing_time == 0.0
        assert r.analysis_options == {}

    def test_with_fallacies(self):
        fd = FallacyDetection(
            type="t", name="n", description="d", severity=0.5, confidence=0.5,
        )
        r = AnalysisResponse(success=True, text_analyzed="X", fallacies=[fd])
        assert len(r.fallacies) == 1

    def test_quality_out_of_range(self):
        with pytest.raises(ValidationError):
            AnalysisResponse(success=True, text_analyzed="X", overall_quality=2.0)

    def test_negative_processing_time(self):
        with pytest.raises(ValidationError):
            AnalysisResponse(success=True, text_analyzed="X", processing_time=-1.0)


# ============================================================
# ValidationResult
# ============================================================

class TestValidationResult:
    def test_creation(self):
        v = ValidationResult(is_valid=True, validity_score=0.9, soundness_score=0.8)
        assert v.is_valid is True
        assert v.validity_score == 0.9

    def test_defaults(self):
        v = ValidationResult(is_valid=False, validity_score=0.5, soundness_score=0.5)
        assert v.premise_analysis == []
        assert v.conclusion_analysis == {}
        assert v.logical_structure == {}
        assert v.issues == []
        assert v.suggestions == []

    def test_score_out_of_range(self):
        with pytest.raises(ValidationError):
            ValidationResult(is_valid=True, validity_score=1.5, soundness_score=0.5)


# ============================================================
# ValidationResponse
# ============================================================

class TestValidationResponse:
    def test_creation(self):
        vr = ValidationResult(is_valid=True, validity_score=0.9, soundness_score=0.8)
        resp = ValidationResponse(
            success=True, premises=["P1"], conclusion="C",
            argument_type="deductive", result=vr,
        )
        assert resp.success is True
        assert resp.result.is_valid is True
        assert isinstance(resp.validation_timestamp, datetime)

    def test_default_processing_time(self):
        vr = ValidationResult(is_valid=True, validity_score=0.5, soundness_score=0.5)
        resp = ValidationResponse(
            success=True, premises=[], conclusion="C",
            argument_type="inductive", result=vr,
        )
        assert resp.processing_time == 0.0


# ============================================================
# FallacyResponse
# ============================================================

class TestFallacyResponse:
    def test_creation(self):
        resp = FallacyResponse(success=True, text_analyzed="Test")
        assert resp.fallacy_count == 0
        assert resp.fallacies == []

    def test_defaults(self):
        resp = FallacyResponse(success=False, text_analyzed="X")
        assert resp.severity_distribution == {}
        assert resp.category_distribution == {}
        assert resp.processing_time == 0.0
        assert resp.detection_options == {}


# ============================================================
# ArgumentNode
# ============================================================

class TestArgumentNode:
    def test_creation(self):
        node = ArgumentNode(id="a1", content="Argument 1")
        assert node.id == "a1"
        assert node.status == "undecided"

    def test_defaults(self):
        node = ArgumentNode(id="a1", content="X")
        assert node.attacks == []
        assert node.attacked_by == []
        assert node.supports == []
        assert node.supported_by == []

    def test_with_relations(self):
        node = ArgumentNode(
            id="a1", content="X",
            attacks=["a2"], attacked_by=["a3"],
            supports=["a4"], supported_by=["a5"],
        )
        assert "a2" in node.attacks
        assert "a3" in node.attacked_by


# ============================================================
# Extension
# ============================================================

class TestExtension:
    def test_creation(self):
        ext = Extension(type="grounded")
        assert ext.type == "grounded"
        assert ext.arguments == []
        assert ext.is_complete is False
        assert ext.is_preferred is False

    def test_with_arguments(self):
        ext = Extension(type="preferred", arguments=["a1", "a2"], is_preferred=True)
        assert len(ext.arguments) == 2
        assert ext.is_preferred is True


# ============================================================
# FrameworkVisualization
# ============================================================

class TestFrameworkVisualization:
    def test_defaults(self):
        fv = FrameworkVisualization()
        assert fv.nodes == []
        assert fv.edges == []
        assert fv.layout == {}

    def test_with_data(self):
        fv = FrameworkVisualization(
            nodes=[{"id": "a1"}], edges=[{"from": "a1", "to": "a2"}],
            layout={"type": "force"},
        )
        assert len(fv.nodes) == 1
        assert len(fv.edges) == 1


# ============================================================
# FrameworkResponse
# ============================================================

class TestFrameworkResponse:
    def test_creation(self):
        resp = FrameworkResponse(success=True, semantics_used="grounded")
        assert resp.success is True
        assert resp.semantics_used == "grounded"
        assert isinstance(resp.framework_timestamp, datetime)

    def test_defaults(self):
        resp = FrameworkResponse(success=True, semantics_used="preferred")
        assert resp.arguments == []
        assert resp.attack_relations == []
        assert resp.support_relations == []
        assert resp.extensions == []
        assert resp.argument_count == 0
        assert resp.attack_count == 0
        assert resp.support_count == 0
        assert resp.extension_count == 0
        assert resp.visualization is None
        assert resp.processing_time == 0.0
        assert resp.framework_options == {}


# ============================================================
# ErrorResponse
# ============================================================

class TestErrorResponse:
    def test_creation(self):
        err = ErrorResponse(error="NotFound", message="Not found", status_code=404)
        assert err.error == "NotFound"
        assert err.status_code == 404
        assert isinstance(err.timestamp, datetime)

    def test_optional_details(self):
        err = ErrorResponse(error="E", message="M", status_code=500)
        assert err.details is None

    def test_with_details(self):
        err = ErrorResponse(
            error="E", message="M", status_code=500,
            details={"trace": "stack"},
        )
        assert err.details["trace"] == "stack"


# ============================================================
# LogicQueryResult
# ============================================================

class TestLogicQueryResult:
    def test_creation(self):
        r = LogicQueryResult(query="p -> q", result=True, formatted_result="True")
        assert r.query == "p -> q"
        assert r.result is True

    def test_null_result(self):
        r = LogicQueryResult(query="q", result=None, formatted_result="Unknown")
        assert r.result is None

    def test_optional_explanation(self):
        r = LogicQueryResult(query="q", result=True, formatted_result="T")
        assert r.explanation is None

    def test_with_explanation(self):
        r = LogicQueryResult(
            query="q", result=True, formatted_result="T",
            explanation="Because...",
        )
        assert r.explanation == "Because..."


# ============================================================
# LogicBeliefSet
# ============================================================

class TestLogicBeliefSet:
    def test_creation(self):
        bs = LogicBeliefSet(
            id="bs1", logic_type="propositional",
            content="p -> q, p", source_text="If p then q, p.",
        )
        assert bs.id == "bs1"
        assert bs.logic_type == "propositional"
        assert isinstance(bs.creation_timestamp, datetime)


# ============================================================
# LogicBeliefSetResponse
# ============================================================

class TestLogicBeliefSetResponse:
    def test_creation(self):
        bs = LogicBeliefSet(
            id="bs1", logic_type="first_order",
            content="forall X: P(X)", source_text="All X are P",
        )
        resp = LogicBeliefSetResponse(success=True, belief_set=bs)
        assert resp.success is True
        assert resp.processing_time == 0.0
        assert resp.conversion_options == {}


# ============================================================
# LogicQueryResponse
# ============================================================

class TestLogicQueryResponse:
    def test_creation(self):
        qr = LogicQueryResult(query="p", result=True, formatted_result="True")
        resp = LogicQueryResponse(
            success=True, belief_set_id="bs1",
            logic_type="propositional", result=qr,
        )
        assert resp.belief_set_id == "bs1"
        assert resp.processing_time == 0.0


# ============================================================
# LogicGenerateQueriesResponse
# ============================================================

class TestLogicGenerateQueriesResponse:
    def test_creation(self):
        resp = LogicGenerateQueriesResponse(
            success=True, belief_set_id="bs1", logic_type="modal",
            queries=["p", "q", "p -> q"],
        )
        assert len(resp.queries) == 3

    def test_defaults(self):
        resp = LogicGenerateQueriesResponse(
            success=True, belief_set_id="bs1", logic_type="modal",
        )
        assert resp.queries == []
        assert resp.processing_time == 0.0
        assert resp.generation_options == {}


# ============================================================
# LogicInterpretationResponse
# ============================================================

class TestLogicInterpretationResponse:
    def test_creation(self):
        resp = LogicInterpretationResponse(
            success=True, belief_set_id="bs1",
            logic_type="propositional", interpretation="The results show...",
        )
        assert resp.interpretation == "The results show..."

    def test_defaults(self):
        resp = LogicInterpretationResponse(
            success=True, belief_set_id="bs1",
            logic_type="propositional", interpretation="X",
        )
        assert resp.queries == []
        assert resp.results == []
        assert resp.processing_time == 0.0
        assert resp.interpretation_options == {}


# ============================================================
# SuccessResponse
# ============================================================

class TestSuccessResponse:
    def test_defaults(self):
        resp = SuccessResponse()
        assert resp.message == "Operation successful"
        assert resp.data is None
        assert resp.status_code == 200
        assert isinstance(resp.timestamp, datetime)

    def test_custom_values(self):
        resp = SuccessResponse(
            message="Created", data={"id": 1}, status_code=201,
        )
        assert resp.message == "Created"
        assert resp.data == {"id": 1}
        assert resp.status_code == 201
