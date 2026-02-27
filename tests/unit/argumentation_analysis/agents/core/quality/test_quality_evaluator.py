"""
Tests for the Argument Quality Evaluator (integrated from 2.3.5).

Tests validate:
- Module import without errors
- CapabilityRegistry registration
- Individual virtue detectors
- Full evaluation pipeline
- Graceful degradation without spacy/textstat
"""

import pytest
from unittest.mock import patch


class TestQualityImport:
    """Test that the quality module can be imported."""

    def test_import_module(self):
        """Quality module imports without errors."""
        from argumentation_analysis.agents.core.quality import (
            ArgumentQualityEvaluator,
            VERTUES,
            evaluer_argument,
        )

        assert ArgumentQualityEvaluator is not None
        assert len(VERTUES) == 9
        assert callable(evaluer_argument)

    def test_import_detectors(self):
        """Individual detectors are importable."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            DETECTORS,
        )

        assert len(DETECTORS) == 9
        for name in [
            "clarte",
            "pertinence",
            "presence_sources",
            "refutation_constructive",
            "structure_logique",
            "analogie_pertinente",
            "fiabilite_sources",
            "exhaustivite",
            "redondance_faible",
        ]:
            assert name in DETECTORS


class TestQualityRegistration:
    """Test CapabilityRegistry registration."""

    def test_register_quality_evaluator(self):
        """Quality evaluator registers correctly in CapabilityRegistry."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.agents.core.quality import (
            ArgumentQualityEvaluator,
        )

        registry = CapabilityRegistry()
        registry.register_agent(
            "quality_evaluator",
            ArgumentQualityEvaluator,
            capabilities=["argument_quality", "virtue_scoring"],
        )

        agents = registry.find_agents_for_capability("argument_quality")
        assert len(agents) == 1
        assert agents[0].name == "quality_evaluator"

    def test_provides_declared_capabilities(self):
        """Quality evaluator provides the capabilities it declares."""
        from argumentation_analysis.core.capability_registry import (
            CapabilityRegistry,
        )
        from argumentation_analysis.agents.core.quality import (
            ArgumentQualityEvaluator,
        )

        registry = CapabilityRegistry()
        registry.register_agent(
            "quality_evaluator",
            ArgumentQualityEvaluator,
            capabilities=["argument_quality", "virtue_scoring"],
        )

        all_caps = registry.get_all_capabilities()
        assert "argument_quality" in all_caps
        assert "virtue_scoring" in all_caps


class TestVirtueDetectors:
    """Test individual virtue detectors."""

    def test_detect_presence_sources_found(self):
        """Source detector finds citations."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_presence_sources,
        )

        text = (
            "Selon Dupont (2019), les résultats montrent que d'après Martin (2020) ..."
        )
        score, comment = detect_presence_sources(text)
        assert score >= 0.5
        assert "source" in comment.lower()

    def test_detect_presence_sources_none(self):
        """Source detector handles text without citations."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_presence_sources,
        )

        text = "Les choses vont mal et tout est compliqué."
        score, comment = detect_presence_sources(text)
        assert score == 0.0

    def test_detect_refutation_markers(self):
        """Refutation detector finds constructive opposition markers."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_refutation_constructive,
        )

        text = "Certains pensent que les renouvelables sont coûteuses, cependant les prix baissent."
        score, comment = detect_refutation_constructive(text)
        assert score == 1.0

    def test_detect_analogie(self):
        """Analogy detector finds comparison patterns."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_analogie_pertinente,
        )

        text = "La transition est comparable à la révolution industrielle, tout comme le numérique transforme."
        score, comment = detect_analogie_pertinente(text)
        assert score == 1.0

    def test_detect_fiabilite_sources(self):
        """Source credibility detector finds known sources."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_fiabilite_sources,
        )

        text = "Selon l'OMS, les campagnes de vaccination sont essentielles."
        score, comment = detect_fiabilite_sources(text)
        assert score == 1.0

    def test_detect_structure_logique(self):
        """Structure detector finds logical connectors."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_structure_logique,
        )

        text = "Les abeilles sont essentielles car elles pollinisent. Donc la production dépend d'elles."
        score, comment = detect_structure_logique(text)
        assert score == 1.0

    def test_detect_redondance_faible(self):
        """Redundancy detector evaluates word uniqueness ratio."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_redondance_faible,
        )

        # High diversity text
        text = "Les énergies renouvelables transforment notre avenir économique et environnemental."
        score, _ = detect_redondance_faible(text)
        assert score >= 0.5

    def test_detect_redondance_faible_redundant(self):
        """Redundancy detector catches highly redundant text."""
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            detect_redondance_faible,
        )

        # Very redundant text
        text = "bon bon bon bon bon bon bon bon bon bon bon bon"
        score, _ = detect_redondance_faible(text)
        assert score <= 0.5


class TestFullEvaluation:
    """Test the full evaluation pipeline."""

    def test_evaluate_high_quality(self):
        """High-quality text gets a high score."""
        from argumentation_analysis.agents.core.quality import evaluer_argument

        text = (
            "Selon un rapport de l'Agence Internationale de l'Énergie (2023), "
            "les énergies renouvelables sont cruciales pour lutter contre le "
            "changement climatique, car elles réduisent les émissions de CO2. "
            "Par exemple, remplacer les centrales à charbon par des parcs solaires "
            "permettrait de diminuer drastiquement la pollution, tout comme remplacer "
            "une vieille chaudière par une pompe à chaleur moderne. "
            "Certains affirment que les renouvelables sont peu fiables, cependant, "
            "des avancées dans le stockage d'énergie réfutent cette idée. "
            "En effet, les batteries lithium-ion et les réseaux intelligents "
            "compensent les variations. De plus, l'ensemble des données montre "
            "une tendance globale à la baisse des coûts. "
            "Ainsi, la transition énergétique est non seulement possible, mais nécessaire."
        )
        result = evaluer_argument(text)

        assert "note_finale" in result
        assert "note_moyenne" in result
        assert "scores_par_vertu" in result
        assert "rapport_detaille" in result
        assert len(result["scores_par_vertu"]) == 9
        # High quality text should score well
        assert result["note_moyenne"] > 0.5

    def test_evaluate_low_quality(self):
        """Low-quality text gets a low score."""
        from argumentation_analysis.agents.core.quality import evaluer_argument

        text = "Manger des légumes est bon. C'est pourquoi les voitures polluent."
        result = evaluer_argument(text)

        assert result["note_finale"] < 5.0
        assert result["note_moyenne"] < 0.6

    def test_evaluate_returns_all_virtues(self):
        """Evaluation always returns all 9 virtues."""
        from argumentation_analysis.agents.core.quality import (
            evaluer_argument,
            VERTUES,
        )

        result = evaluer_argument("Un texte quelconque.")
        for vertu in VERTUES:
            assert vertu in result["scores_par_vertu"]
            assert vertu in result["rapport_detaille"]

    def test_evaluator_class_api(self):
        """ArgumentQualityEvaluator class has correct API."""
        from argumentation_analysis.agents.core.quality import (
            ArgumentQualityEvaluator,
        )

        evaluator = ArgumentQualityEvaluator()
        result = evaluator.evaluate("Selon l'OMS, la santé est un droit fondamental.")
        assert isinstance(result, dict)
        assert "note_finale" in result
