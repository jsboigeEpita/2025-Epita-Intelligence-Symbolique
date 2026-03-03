# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.services.fact_verification_service
Covers VerificationStatus, SourceReliability, VerificationResult,
FactVerificationService, and get_verification_service singleton.
"""

import pytest
from datetime import datetime
from argumentation_analysis.services.fact_verification_service import (
    VerificationStatus,
    SourceReliability,
    VerificationResult,
    FactVerificationService,
    get_verification_service,
    _global_verification_service,
)
import argumentation_analysis.services.fact_verification_service as fvs_module


# ============================================================
# VerificationStatus enum
# ============================================================

class TestVerificationStatus:
    def test_all_values(self):
        expected = {
            "verified_true", "verified_false", "partially_true",
            "disputed", "unverifiable", "insufficient_info", "error",
        }
        assert {vs.value for vs in VerificationStatus} == expected

    def test_member_count(self):
        assert len(VerificationStatus) == 7

    def test_from_value(self):
        assert VerificationStatus("verified_true") is VerificationStatus.VERIFIED_TRUE
        assert VerificationStatus("error") is VerificationStatus.ERROR

    def test_invalid_value(self):
        with pytest.raises(ValueError):
            VerificationStatus("invalid")


# ============================================================
# SourceReliability enum
# ============================================================

class TestSourceReliability:
    def test_all_values(self):
        expected = {
            "highly_reliable", "moderately_reliable",
            "questionable", "unreliable", "unknown",
        }
        assert {sr.value for sr in SourceReliability} == expected

    def test_member_count(self):
        assert len(SourceReliability) == 5

    def test_from_value(self):
        assert SourceReliability("unknown") is SourceReliability.UNKNOWN


# ============================================================
# VerificationResult dataclass
# ============================================================

class TestVerificationResult:
    @pytest.fixture
    def sample_result(self):
        return VerificationResult(
            claim="The earth is round",
            status=VerificationStatus.VERIFIED_TRUE,
            confidence=0.95,
            verification_date=datetime(2025, 6, 1, 12, 0, 0),
            sources=[{"url": "https://nasa.gov", "reliability": "highly_reliable"}],
        )

    def test_creation(self, sample_result):
        assert sample_result.claim == "The earth is round"
        assert sample_result.status is VerificationStatus.VERIFIED_TRUE
        assert sample_result.confidence == 0.95
        assert len(sample_result.sources) == 1

    def test_to_dict(self, sample_result):
        d = sample_result.to_dict()
        assert d["claim"] == "The earth is round"
        assert d["status"] == "verified_true"
        assert d["confidence"] == 0.95
        assert d["verification_date"] == "2025-06-01T12:00:00"
        assert len(d["sources"]) == 1

    def test_to_dict_with_non_string_claim(self):
        result = VerificationResult(
            claim=42,
            status=VerificationStatus.UNVERIFIABLE,
            confidence=0.1,
            verification_date=datetime.now(),
            sources=[],
        )
        d = result.to_dict()
        assert d["claim"] == "42"

    def test_empty_sources(self):
        result = VerificationResult(
            claim="test",
            status=VerificationStatus.INSUFFICIENT_INFO,
            confidence=0.0,
            verification_date=datetime.now(),
            sources=[],
        )
        assert result.sources == []


# ============================================================
# FactVerificationService
# ============================================================

class TestFactVerificationService:
    def test_init_default_config(self):
        service = FactVerificationService()
        assert service.api_config == {}
        assert len(service.source_reliability_map) > 0

    def test_init_custom_config(self):
        config = {"api_key": "test_key"}
        service = FactVerificationService(api_config=config)
        assert service.api_config == config

    def test_source_reliability_map_contains_known_sources(self):
        service = FactVerificationService()
        assert "wikipedia.org" in service.source_reliability_map
        assert service.source_reliability_map["wikipedia.org"] is SourceReliability.HIGHLY_RELIABLE
        assert "lemonde.fr" in service.source_reliability_map
        assert "huffingtonpost.fr" in service.source_reliability_map
        assert service.source_reliability_map["huffingtonpost.fr"] is SourceReliability.MODERATELY_RELIABLE

    def test_assess_source_reliability_known(self):
        service = FactVerificationService()
        assert service._assess_source_reliability("wikipedia.org") is SourceReliability.HIGHLY_RELIABLE
        assert service._assess_source_reliability("bbc.com") is SourceReliability.HIGHLY_RELIABLE
        assert service._assess_source_reliability("huffingtonpost.fr") is SourceReliability.MODERATELY_RELIABLE

    def test_assess_source_reliability_unknown(self):
        service = FactVerificationService()
        assert service._assess_source_reliability("randomsite.xyz") is SourceReliability.UNKNOWN

    def test_assess_source_reliability_case_insensitive(self):
        service = FactVerificationService()
        assert service._assess_source_reliability("WIKIPEDIA.ORG") is SourceReliability.HIGHLY_RELIABLE

    def test_assess_source_reliability_subdomain(self):
        service = FactVerificationService()
        # "bbc.com" is in map, so "news.bbc.com" should match
        assert service._assess_source_reliability("news.bbc.com") is SourceReliability.HIGHLY_RELIABLE

    @pytest.mark.asyncio
    async def test_verify_claim(self):
        service = FactVerificationService()
        result = await service.verify_claim("Test claim")
        assert isinstance(result, VerificationResult)
        assert result.status is VerificationStatus.UNVERIFIABLE
        assert result.confidence == 0.3
        assert result.sources == []
        assert result.claim == "Test claim"

    @pytest.mark.asyncio
    async def test_verify_claims_multiple(self):
        service = FactVerificationService()
        results = await service.verify_claims(["claim1", "claim2", "claim3"])
        assert len(results) == 3
        for r in results:
            assert isinstance(r, VerificationResult)
            assert r.status is VerificationStatus.UNVERIFIABLE

    @pytest.mark.asyncio
    async def test_verify_claims_empty(self):
        service = FactVerificationService()
        results = await service.verify_claims([])
        assert results == []


# ============================================================
# get_verification_service singleton
# ============================================================

class TestGetVerificationService:
    def setup_method(self):
        # Reset singleton between tests
        fvs_module._global_verification_service = None

    def test_returns_instance(self):
        service = get_verification_service()
        assert isinstance(service, FactVerificationService)

    def test_singleton_same_instance(self):
        s1 = get_verification_service()
        s2 = get_verification_service()
        assert s1 is s2

    def test_with_config(self):
        service = get_verification_service(api_config={"key": "val"})
        assert isinstance(service, FactVerificationService)
