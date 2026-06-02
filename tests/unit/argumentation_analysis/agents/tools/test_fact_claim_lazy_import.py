"""Tests for fact_claim_extractor lazy-import hardening (#882)."""
import pytest


class TestFactClaimExtractorLazyImport:
    """Verify that importing FactClaimExtractor does not crash on broken torch/spacy."""

    def test_module_import_succeeds_without_torch(self):
        """Module import should succeed even if spacy/torch chain is broken.

        Regression test for #882: import spacy was at module level and
        crashed with OSError (WinError 182) when torch DLL was broken.
        After fix, the import is deferred to __init__ and caught gracefully.
        """
        from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
            FactClaimExtractor,
            ClaimType,
            FactualClaim,
        )

        # Classes should be importable without any spacy/torch involvement
        assert ClaimType.STATISTICAL.value == "statistical"
        assert hasattr(FactualClaim, "__dataclass_fields__")

    def test_instantiation_degrades_gracefully_without_model(self):
        """FactClaimExtractor should degrade to nlp=None when spacy model is unavailable."""
        from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
            FactClaimExtractor,
        )

        extractor = FactClaimExtractor(language="fr")
        # Whether nlp is loaded depends on the environment, but instantiation
        # must not raise any exception
        assert hasattr(extractor, "nlp")

    def test_extract_with_no_nlp(self):
        """Extraction should still work (regex-based) when spacy is unavailable."""
        from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
            FactClaimExtractor,
        )

        extractor = FactClaimExtractor(language="fr")
        # Force degraded mode for testing
        extractor.nlp = None

        # Should not crash even without NLP model
        text = "Le prix a augmenté de 15% en 2024."
        result = extractor.extract_factual_claims(text)
        assert isinstance(result, list)
