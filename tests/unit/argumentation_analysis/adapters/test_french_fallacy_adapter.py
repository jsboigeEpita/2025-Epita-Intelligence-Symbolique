"""
Tests for FrenchFallacyAdapter (3-tier hybrid fallacy detection).

Tests validate:
- Module and class imports
- Symbolic detection tier (with/without spaCy)
- NLI detection tier availability check
- LLM detection tier availability check
- Ensemble merging logic
- FallacyAnalysisResult data class
- Adapter detect() returns correct structure
- CapabilityRegistry registration
- Graceful degradation when no tiers available
"""

from unittest.mock import MagicMock, patch

import pytest


class TestImports:
    """Test that adapter classes are importable."""

    def test_import_adapter(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        assert FrenchFallacyAdapter is not None

    def test_import_symbolic_detector(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            SymbolicFallacyDetector,
        )

        assert SymbolicFallacyDetector is not None

    def test_import_nli_detector(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            NLIFallacyDetector,
        )

        assert NLIFallacyDetector is not None

    def test_import_llm_detector(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )

        assert LLMFallacyDetector is not None

    def test_import_data_classes(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FallacyDetection,
            FallacyAnalysisResult,
        )

        assert FallacyDetection is not None
        assert FallacyAnalysisResult is not None

    def test_implements_abstract_interface(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )
        from argumentation_analysis.core.interfaces.fallacy_detector import (
            AbstractFallacyDetector,
        )

        assert issubclass(FrenchFallacyAdapter, AbstractFallacyDetector)


class TestFallacyDetection:
    """Test FallacyDetection data class."""

    def test_creation(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FallacyDetection,
        )

        d = FallacyDetection(
            fallacy_type="Ad Hominem",
            confidence=0.95,
            source="symbolic",
            matched_rule="tu es idiot",
        )
        assert d.fallacy_type == "Ad Hominem"
        assert d.confidence == 0.95
        assert d.source == "symbolic"

    def test_optional_fields(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FallacyDetection,
        )

        d = FallacyDetection(fallacy_type="test", confidence=0.5, source="nli")
        assert d.matched_rule is None
        assert d.description is None


class TestFallacyAnalysisResult:
    """Test FallacyAnalysisResult data class and to_dict()."""

    def test_empty_result(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FallacyAnalysisResult,
        )

        result = FallacyAnalysisResult(text="test")
        d = result.to_dict()
        assert d["text"] == "test"
        assert d["detected_fallacies"] == {}
        assert d["total_fallacies"] == 0
        assert d["tiers_used"] == []

    def test_result_with_fallacies(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FallacyAnalysisResult,
            FallacyDetection,
        )

        result = FallacyAnalysisResult(
            text="test",
            fallacies=[
                FallacyDetection("Ad Hominem", 1.0, "symbolic", "tu es"),
                FallacyDetection("Pente glissante", 0.8, "nli"),
            ],
            tiers_used=["symbolic", "nli"],
        )
        d = result.to_dict()
        assert d["total_fallacies"] == 2
        assert "Ad Hominem" in d["detected_fallacies"]
        assert d["detected_fallacies"]["Ad Hominem"]["confidence"] == 1.0


class TestSymbolicDetector:
    """Test the symbolic (spaCy) fallacy detector."""

    def test_is_available_without_spacy(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            SymbolicFallacyDetector,
        )

        detector = SymbolicFallacyDetector()
        with patch.dict("sys.modules", {"spacy": None}):
            detector._available = None  # Reset cache
            # May or may not be available depending on environment
            result = detector.is_available()
            assert isinstance(result, bool)

    def test_mine_arguments_fallback(self):
        """Without spaCy, mine_arguments returns text as single claim."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            SymbolicFallacyDetector,
        )

        detector = SymbolicFallacyDetector()
        detector._available = False
        result = detector.mine_arguments("Test text here")
        assert result["claims"] == ["Test text here"]
        assert result["premises"] == []

    def test_detect_empty_when_unavailable(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            SymbolicFallacyDetector,
        )

        detector = SymbolicFallacyDetector()
        detector._available = False
        assert detector.detect("test") == []


class TestNLIDetector:
    """Test the NLI zero-shot fallacy detector."""

    def test_default_model_name(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            NLIFallacyDetector,
        )

        detector = NLIFallacyDetector()
        assert "mDeBERTa" in detector._model_name or "xnli" in detector._model_name

    def test_custom_model_name(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            NLIFallacyDetector,
        )

        detector = NLIFallacyDetector(model_name="custom/model")
        assert detector._model_name == "custom/model"

    def test_custom_threshold(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            NLIFallacyDetector,
        )

        detector = NLIFallacyDetector(threshold=0.8)
        assert detector.threshold == 0.8

    def test_detect_empty_when_unavailable(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            NLIFallacyDetector,
        )

        detector = NLIFallacyDetector()
        detector._available = False
        assert detector.detect("test") == []

    def test_detect_with_mock_pipeline(self):
        """Test NLI detection with mocked transformers pipeline."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            NLIFallacyDetector,
        )

        detector = NLIFallacyDetector(threshold=0.5)
        detector._available = True

        mock_result = {
            "labels": ["Attaque personnelle (Ad Hominem)", "Pente glissante"],
            "scores": [0.85, 0.3],
        }
        mock_classifier = MagicMock(return_value=mock_result)
        detector._classifier = mock_classifier

        results = detector.detect("Tu es un idiot, ton argument est faux")
        assert len(results) == 1  # Only Ad Hominem passes threshold
        assert results[0].fallacy_type == "Attaque personnelle (Ad Hominem)"
        assert results[0].confidence == 0.85
        assert results[0].source == "nli"


class TestLLMDetector:
    """Test the LLM zero-shot fallacy detector (#297)."""

    def test_unavailable_without_api_key(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )
        from unittest.mock import patch

        detector = LLMFallacyDetector()
        detector._available = None  # reset cache
        with patch.dict("os.environ", {}, clear=True):
            assert detector.is_available() is False

    def test_available_with_api_key(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )
        from unittest.mock import patch

        detector = LLMFallacyDetector()
        detector._available = None  # reset cache
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            assert detector.is_available() is True

    def test_detect_empty_when_unavailable(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            LLMFallacyDetector,
        )
        from unittest.mock import patch

        detector = LLMFallacyDetector()
        detector._available = None
        with patch.dict("os.environ", {}, clear=True):
            assert detector.detect("test") == []


class TestFrenchFallacyAdapter:
    """Test the main adapter class."""

    def test_creation_defaults(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_self_hosted_llm=False,
            enable_nli=False,
            enable_llm=False,
        )
        assert not adapter.is_available()

    def test_get_available_tiers_none(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_self_hosted_llm=False,
            enable_nli=False,
            enable_llm=False,
        )
        assert adapter.get_available_tiers() == []

    def test_detect_no_tiers(self):
        """Detect with no available tiers returns empty result."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=False,
            enable_self_hosted_llm=False,
            enable_nli=False,
            enable_llm=False,
        )
        result = adapter.detect("test text")
        assert result["total_fallacies"] == 0
        assert result["tiers_used"] == ["none"]

    def test_detect_with_mocked_symbolic(self):
        """Detect with symbolic tier returns correct structure."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
            FallacyDetection,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=True,
            enable_self_hosted_llm=False,
            enable_nli=False,
            enable_llm=False,
        )
        # Mock the symbolic detector
        mock_detections = [FallacyDetection("Ad Hominem", 1.0, "symbolic", "tu es nul")]
        adapter._symbolic.detect = MagicMock(return_value=mock_detections)
        adapter._symbolic._available = True
        adapter._symbolic.mine_arguments = MagicMock(
            return_value={"claims": ["test"], "premises": []}
        )

        result = adapter.detect("tu es nul donc ton argument est faux")
        assert result["total_fallacies"] == 1
        assert "Ad Hominem" in result["detected_fallacies"]
        assert "symbolic" in result["tiers_used"]

    def test_ensemble_symbolic_overrides_nli(self):
        """Symbolic detection (confidence=1.0) overrides NLI on same type."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
            FallacyDetection,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=True,
            enable_self_hosted_llm=False,
            enable_nli=True,
            enable_llm=False,
        )
        symbolic_result = [FallacyDetection("Ad Hominem", 1.0, "symbolic", "tu es nul")]
        nli_result = [FallacyDetection("Ad Hominem", 0.7, "nli")]

        adapter._symbolic.detect = MagicMock(return_value=symbolic_result)
        adapter._symbolic._available = True
        adapter._symbolic.mine_arguments = MagicMock(
            return_value={"claims": ["test"], "premises": []}
        )
        adapter._nli.detect = MagicMock(return_value=nli_result)
        adapter._nli._available = True

        result = adapter.detect("tu es nul")
        assert result["total_fallacies"] == 1
        fallacy = result["detected_fallacies"]["Ad Hominem"]
        assert fallacy["confidence"] == 1.0
        assert "symbolic" in fallacy["source"]

    def test_explanation_generated(self):
        """Detect generates a textual explanation."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
            FallacyDetection,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=True,
            enable_self_hosted_llm=False,
            enable_nli=False,
            enable_llm=False,
        )
        adapter._symbolic.detect = MagicMock(
            return_value=[FallacyDetection("Ad Hominem", 1.0, "symbolic")]
        )
        adapter._symbolic._available = True
        adapter._symbolic.mine_arguments = MagicMock(
            return_value={"claims": ["x"], "premises": []}
        )

        result = adapter.detect("test")
        assert "sophisme" in result["explanation"].lower()

    def test_no_fallacies_explanation(self):
        """No fallacies generates appropriate message."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        adapter = FrenchFallacyAdapter(
            enable_symbolic=True,
            enable_self_hosted_llm=False,
            enable_nli=False,
            enable_llm=False,
        )
        adapter._symbolic.detect = MagicMock(return_value=[])
        adapter._symbolic._available = True
        adapter._symbolic.mine_arguments = MagicMock(
            return_value={"claims": ["x"], "premises": []}
        )

        result = adapter.detect("Ceci est un argument valide.")
        assert result["total_fallacies"] == 0
        assert "aucun" in result["explanation"].lower()


class TestCapabilityRegistration:
    """Test CapabilityRegistry integration."""

    def test_register_french_fallacy_adapter(self):
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FrenchFallacyAdapter,
        )

        registry = CapabilityRegistry()
        registry.register_service(
            "french_fallacy_detector",
            FrenchFallacyAdapter,
            capabilities=[
                "fallacy_detection",
                "neural_fallacy_detection",
                "symbolic_fallacy_detection",
            ],
        )
        services = registry.find_services_for_capability("fallacy_detection")
        assert len(services) == 1
        assert services[0].name == "french_fallacy_detector"


class TestG4RestoredSubRules:
    """G4 (#1186): the 3 symbolic sub-rules dropped at #35 are restored AND fire.

    Faithful to student 2.3.2-detection-sophismes/symbolic_rules.py:40-52 /
    104-115 / 132-140, with minimal punctuation/POS fixes so the spaCy Matcher
    actually matches real French (the student originals never fired — verified).
    """

    def test_three_families_have_restored_subrule(self):
        """AD_HOMINEM char-attack + GENERALISATION base-de + APPEL_TRADITION c'est-la."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            _SYMBOLIC_FALLACY_RULES,
        )

        # Character/motive attack restored under AD_HOMINEM_DIRECT.
        adhominem_patterns = _SYMBOLIC_FALLACY_RULES["AD_HOMINEM_DIRECT"]
        assert any(
            any(tok.get("POS") == "PROPN" for tok in r["PATTERN"])
            and any(tok.get("LOWER") == "faux" for tok in r["PATTERN"])
            for r in adhominem_patterns
        ), "character-attack sub-rule (PROPN ... faux) not restored"

        # "Sur la base de N exemples" restored under GENERALISATION_HATIVE.
        gen_patterns = _SYMBOLIC_FALLACY_RULES["GENERALISATION_HATIVE"]
        assert any(
            any(tok.get("LOWER") == "sur" for tok in r["PATTERN"])
            and any(tok.get("LOWER") == "base" for tok in r["PATTERN"])
            for r in gen_patterns
        ), "sur-la-base-de sub-rule not restored"

        # "C'est la tradition" restored under APPEL_A_LA_TRADITION.
        tradition_patterns = _SYMBOLIC_FALLACY_RULES["APPEL_A_LA_TRADITION"]
        assert any(
            any(tok.get("LOWER") == "tradition" for tok in r["PATTERN"])
            and any(tok.get("LEMMA") == "être" for tok in r["PATTERN"])
            for r in tradition_patterns
        ), "c'est-la-tradition sub-rule not restored"

    def test_all_symbolic_subrules_wired_to_fire(self):
        """Every sub-rule dict carries a FALLACY_TYPE (detector iterates them all)."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            _SYMBOLIC_FALLACY_RULES,
        )

        for fam, rules in _SYMBOLIC_FALLACY_RULES.items():
            for i, rule in enumerate(rules):
                assert "PATTERN" in rule, f"{fam}[{i}] has no PATTERN"
                assert isinstance(rule["PATTERN"], list) and rule["PATTERN"]
                assert "FALLACY_TYPE" in rule, f"{fam}[{i}] has no FALLACY_TYPE"
                assert rule["FALLACY_TYPE"], f"{fam}[{i}] FALLACY_TYPE empty"

    def test_restored_subrules_fire_with_spacy(self):
        """When spaCy FR is available, the 3 restored sub-rules actually fire."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            SymbolicFallacyDetector,
        )

        det = SymbolicFallacyDetector()
        if not det.is_available():
            pytest.skip("spaCy French model unavailable — firing verified elsewhere")

        cases = {
            "Attaque personnelle (Ad Hominem)": (
                "Pierre est malhonnête, donc son argument est faux."
            ),
            "Généralisation hâtive (Hasty Generalization)": (
                "Sur la base de 3 exemples, tous les touristes sont désagréables."
            ),
            "Appel à la tradition (Appeal to Tradition)": (
                "C'est la tradition, il ne faut rien changer."
            ),
        }
        for expected, text in cases.items():
            hits = det.detect(text)
            types = [h.fallacy_type for h in hits]
            assert expected in types, (
                f"restored sub-rule did not fire: expected {expected!r}, got {types}"
            )


class TestG5FrenchExplanationTemplates:
    """G5 (#1186): 4 per-family FR explanation templates restored from student
    2.3.2-detection-sophismes/fallacy_pipeline.py:279-288, collapsed to generic
    at #35. ``justify_fallacy`` is fail-loud (#1019): unknown → None."""

    def test_four_templates_present(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            _FALLACY_JUSTIFICATIONS_FR,
        )

        assert len(_FALLACY_JUSTIFICATIONS_FR) == 4
        for entry in _FALLACY_JUSTIFICATIONS_FR:
            assert "template" in entry and entry["template"]
            assert "matches" in entry and isinstance(entry["matches"], list)

    def test_student_symbolic_labels_resolve(self):
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            justify_fallacy,
        )

        # The student's own symbolic FALLACY_TYPE labels must resolve.
        assert justify_fallacy("Attaque personnelle (Ad Hominem)") is not None
        assert justify_fallacy("Généralisation hâtive (Hasty Generalization)") is not None
        assert justify_fallacy("Argument d'autorité (Appeal to Authority)") is not None

    def test_trunk_taxonomy_leaf_labels_resolve(self):
        """The trunk LLM descent emits taxonomy leaf labels — they must match too."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            justify_fallacy,
        )

        assert justify_fallacy("Ad hominem (Obstruction)") is not None
        assert (
            justify_fallacy("Généralisation abusive (Erreur mathématique)") is not None
        )
        assert justify_fallacy("Appel à l'émotion (Influence)") is not None

    def test_fail_loud_on_unknown_family(self):
        """#1019: unknown family → None, never a fabricated/generic line."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            justify_fallacy,
        )

        assert justify_fallacy("Mauvaise déduction (Erreur de raisonnement)") is None
        assert justify_fallacy("Comparaison fallacieuse (Abus de langage)") is None
        assert justify_fallacy("Unknown fallacy") is None
        assert justify_fallacy("") is None

    def test_description_populated_in_to_dict(self):
        """The single output boundary populates description via the template."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FallacyAnalysisResult,
            FallacyDetection,
        )

        # A symbolic-tier detection (description=None) resolves the template.
        result = FallacyAnalysisResult(
            text="Pierre est malhonnête, donc son argument est faux.",
            fallacies=[
                FallacyDetection(
                    fallacy_type="Attaque personnelle (Ad Hominem)",
                    confidence=1.0,
                    source="symbolic",
                    matched_rule="Pierre est malhonnête",
                    description=None,  # symbolic path leaves it unset
                )
            ],
        )
        d = result.to_dict()
        desc = d["detected_fallacies"]["Attaque personnelle (Ad Hominem)"]["description"]
        assert desc is not None
        assert "personne" in desc.lower() or "caractère" in desc.lower()

    def test_description_fails_loud_when_no_template(self):
        """A fallacy with no family template keeps description=None (no fabrication)."""
        from argumentation_analysis.adapters.french_fallacy_adapter import (
            FallacyAnalysisResult,
            FallacyDetection,
        )

        result = FallacyAnalysisResult(
            text="...",
            fallacies=[
                FallacyDetection(
                    fallacy_type="Pente glissante (Slippery Slope)",
                    confidence=1.0,
                    source="symbolic",
                    description=None,
                )
            ],
        )
        d = result.to_dict()
        assert (
            d["detected_fallacies"]["Pente glissante (Slippery Slope)"]["description"]
            is None
        )


class TestG5StateWriterFallback:
    """G5 (#1186): state-writer fills per-family FR template when LLM explanation
    is empty, surfacing per-family explanations in the restitution report."""

    def test_empty_explanation_filled_by_family_template(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_hierarchical_fallacy_to_state,
        )

        state = MagicMock()
        state.identified_arguments = {}
        state.identified_fallacies = {}
        state.add_fallacy = MagicMock(return_value="fallacy_1")

        output = {
            "fallacies": [
                {
                    "type": "Ad hominem (Obstruction)",
                    "explanation": "",  # LLM gave nothing
                    "confidence": 0.9,
                }
            ]
        }
        _write_hierarchical_fallacy_to_state(output, state, {})

        state.add_fallacy.assert_called_once()
        kwargs = state.add_fallacy.call_args.kwargs
        # The per-family FR template was injected (not empty/generic).
        assert "caractère" in kwargs["justification"] or "personne" in kwargs[
            "justification"
        ].lower()

    def test_llm_explanation_preserved_when_present(self):
        """When the LLM already produced an explanation, it is NOT overwritten."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_hierarchical_fallacy_to_state,
        )

        state = MagicMock()
        state.identified_arguments = {}
        state.identified_fallacies = {}
        state.add_fallacy = MagicMock(return_value="fallacy_1")

        output = {
            "fallacies": [
                {
                    "type": "Ad hominem (Obstruction)",
                    "explanation": "Analyse LLM détaillée du sophisme.",
                    "confidence": 0.9,
                }
            ]
        }
        _write_hierarchical_fallacy_to_state(output, state, {})

        kwargs = state.add_fallacy.call_args.kwargs
        assert "Analyse LLM détaillée" in kwargs["justification"]

    def test_no_template_no_fabrication(self):
        """Unknown family + empty LLM explanation → justification stays sparse,
        no fabricated template injected (#1019)."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_hierarchical_fallacy_to_state,
        )

        state = MagicMock()
        state.identified_arguments = {}
        state.identified_fallacies = {}
        state.add_fallacy = MagicMock(return_value="fallacy_1")

        output = {
            "fallacies": [
                {
                    "type": "Mauvaise déduction (Erreur de raisonnement)",
                    "explanation": "",
                    "confidence": 0.9,
                }
            ]
        }
        _write_hierarchical_fallacy_to_state(output, state, {})

        kwargs = state.add_fallacy.call_args.kwargs
        # No family template for Erreur de raisonnement → justification holds
        # only the metadata decorations, no per-family prose.
        assert "caractère" not in kwargs["justification"]
        assert "échantillon" not in kwargs["justification"]
