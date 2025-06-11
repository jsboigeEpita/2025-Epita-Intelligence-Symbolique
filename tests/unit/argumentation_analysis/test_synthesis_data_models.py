"""
Tests unitaires pour les modèles de données de synthèse.

Ce module teste les classes LogicAnalysisResult, InformalAnalysisResult et UnifiedReport,
y compris leur sérialisation/désérialisation, validation et fonctionnalités.
"""

import pytest
import json
from datetime import datetime
from dataclasses import asdict
from typing import Dict, Any, List

# Import des modules à tester
from argumentation_analysis.agents.core.synthesis.data_models import (
    LogicAnalysisResult,
    InformalAnalysisResult,
    UnifiedReport
)


class TestLogicAnalysisResult:
    """Tests pour LogicAnalysisResult."""
    
    def test_init_default(self):
        """Test l'initialisation avec valeurs par défaut."""
        result = LogicAnalysisResult()
        
        assert result.propositional_result is None
        assert result.first_order_result is None
        assert result.modal_result is None
        assert result.logical_validity is None
        assert result.consistency_check is None
        assert result.satisfiability is None
        assert result.formulas_extracted == []
        assert result.queries_executed == []
        assert result.processing_time_ms == 0.0
        assert result.analysis_timestamp is not None
        
        # Vérifier que le timestamp est au format ISO
        datetime.fromisoformat(result.analysis_timestamp)
    
    def test_init_with_values(self):
        """Test l'initialisation avec valeurs spécifiques."""
        formulas = ["p => q", "[]p"]
        queries = ["p", "q"]
        timestamp = "2023-01-01T12:00:00"
        
        result = LogicAnalysisResult(
            propositional_result="Valid PL",
            first_order_result="Valid FOL",
            modal_result="Valid ML",
            logical_validity=True,
            consistency_check=True,
            satisfiability=True,
            formulas_extracted=formulas,
            queries_executed=queries,
            analysis_timestamp=timestamp,
            processing_time_ms=150.5
        )
        
        assert result.propositional_result == "Valid PL"
        assert result.first_order_result == "Valid FOL"
        assert result.modal_result == "Valid ML"
        assert result.logical_validity == True
        assert result.consistency_check == True
        assert result.satisfiability == True
        assert result.formulas_extracted == formulas
        assert result.queries_executed == queries
        assert result.analysis_timestamp == timestamp
        assert result.processing_time_ms == 150.5
    
    def test_to_dict(self):
        """Test la conversion en dictionnaire."""
        result = LogicAnalysisResult(
            propositional_result="Test PL",
            logical_validity=True,
            formulas_extracted=["p", "q"],
            processing_time_ms=100.0
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["propositional_result"] == "Test PL"
        assert result_dict["logical_validity"] == True
        assert result_dict["formulas_extracted"] == ["p", "q"]
        assert result_dict["processing_time_ms"] == 100.0
        assert "analysis_timestamp" in result_dict
        
        # Vérifier que toutes les clés attendues sont présentes
        expected_keys = {
            'propositional_result', 'first_order_result', 'modal_result',
            'logical_validity', 'consistency_check', 'satisfiability',
            'formulas_extracted', 'queries_executed', 'analysis_timestamp',
            'processing_time_ms'
        }
        assert set(result_dict.keys()) == expected_keys
    
    def test_serialization_json_compatible(self):
        """Test que to_dict produit un dictionnaire sérialisable en JSON."""
        result = LogicAnalysisResult(
            propositional_result="Test",
            logical_validity=True,
            formulas_extracted=["formula1", "formula2"]
        )
        
        result_dict = result.to_dict()
        
        # Doit pouvoir être sérialisé en JSON sans erreur
        json_str = json.dumps(result_dict)
        assert isinstance(json_str, str)
        
        # Doit pouvoir être désérialisé
        reconstructed = json.loads(json_str)
        assert reconstructed["propositional_result"] == "Test"
        assert reconstructed["logical_validity"] == True


class TestInformalAnalysisResult:
    """Tests pour InformalAnalysisResult."""
    
    def test_init_default(self):
        """Test l'initialisation avec valeurs par défaut."""
        result = InformalAnalysisResult()
        
        assert result.fallacies_detected == []
        assert result.arguments_structure is None
        assert result.rhetorical_devices == []
        assert result.argument_strength is None
        assert result.persuasion_level is None
        assert result.credibility_score is None
        assert result.text_segments_analyzed == []
        assert result.context_factors == {}
        assert result.processing_time_ms == 0.0
        assert result.analysis_timestamp is not None
        
        # Vérifier le format du timestamp
        datetime.fromisoformat(result.analysis_timestamp)
    
    def test_init_with_values(self):
        """Test l'initialisation avec valeurs spécifiques."""
        fallacies = [
            {"type": "ad_hominem", "confidence": 0.8, "location": "line 5"},
            {"type": "strawman", "confidence": 0.6, "location": "line 10"}
        ]
        devices = ["metaphor", "repetition"]
        segments = ["segment1", "segment2"]
        context = {"speaker": "politician", "audience": "public"}
        
        result = InformalAnalysisResult(
            fallacies_detected=fallacies,
            arguments_structure="Structured argument",
            rhetorical_devices=devices,
            argument_strength=0.75,
            persuasion_level="high",
            credibility_score=0.65,
            text_segments_analyzed=segments,
            context_factors=context,
            processing_time_ms=200.0
        )
        
        assert result.fallacies_detected == fallacies
        assert result.arguments_structure == "Structured argument"
        assert result.rhetorical_devices == devices
        assert result.argument_strength == 0.75
        assert result.persuasion_level == "high"
        assert result.credibility_score == 0.65
        assert result.text_segments_analyzed == segments
        assert result.context_factors == context
        assert result.processing_time_ms == 200.0
    
    def test_to_dict(self):
        """Test la conversion en dictionnaire."""
        fallacies = [{"type": "ad_hominem", "confidence": 0.9}]
        
        result = InformalAnalysisResult(
            fallacies_detected=fallacies,
            arguments_structure="Test structure",
            argument_strength=0.8
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["fallacies_detected"] == fallacies
        assert result_dict["arguments_structure"] == "Test structure"
        assert result_dict["argument_strength"] == 0.8
        
        # Vérifier toutes les clés
        expected_keys = {
            'fallacies_detected', 'arguments_structure', 'rhetorical_devices',
            'argument_strength', 'persuasion_level', 'credibility_score',
            'text_segments_analyzed', 'context_factors', 'analysis_timestamp',
            'processing_time_ms'
        }
        assert set(result_dict.keys()) == expected_keys
    
    def test_complex_fallacies_structure(self):
        """Test avec une structure complexe de sophismes."""
        complex_fallacies = [
            {
                "type": "ad_hominem",
                "confidence": 0.85,
                "location": {"start": 10, "end": 25},
                "severity": "high",
                "description": "Attack on person rather than argument",
                "evidence": ["phrase1", "phrase2"]
            },
            {
                "type": "false_dilemma",
                "confidence": 0.70,
                "location": {"start": 50, "end": 80},
                "severity": "medium",
                "alternatives_ignored": ["option1", "option2"]
            }
        ]
        
        result = InformalAnalysisResult(fallacies_detected=complex_fallacies)
        result_dict = result.to_dict()
        
        # Vérifier que la structure complexe est préservée
        assert len(result_dict["fallacies_detected"]) == 2
        assert result_dict["fallacies_detected"][0]["type"] == "ad_hominem"
        assert result_dict["fallacies_detected"][0]["evidence"] == ["phrase1", "phrase2"]
        
        # Test de sérialisation JSON
        json_str = json.dumps(result_dict)
        reconstructed = json.loads(json_str)
        assert reconstructed["fallacies_detected"][1]["alternatives_ignored"] == ["option1", "option2"]


class TestUnifiedReport:
    """Tests pour UnifiedReport."""
    
    def test_init_minimal(self):
        """Test l'initialisation minimale requise."""
        original_text = "Text to analyze"
        logic_analysis = LogicAnalysisResult()
        informal_analysis = InformalAnalysisResult()
        
        report = UnifiedReport(
            original_text=original_text,
            logic_analysis=logic_analysis,
            informal_analysis=informal_analysis
        )
        
        assert report.original_text == original_text
        assert report.logic_analysis == logic_analysis
        assert report.informal_analysis == informal_analysis
        assert report.executive_summary == ""
        assert report.coherence_assessment is None
        assert report.contradictions_identified == []
        assert report.overall_validity is None
        assert report.confidence_level is None
        assert report.recommendations == []
        assert report.logic_informal_alignment is None
        assert report.analysis_completeness is None
        assert report.synthesis_version == "1.0.0"
        assert report.total_processing_time_ms == 0.0
        
        # Vérifier timestamp automatique
        assert report.synthesis_timestamp is not None
        datetime.fromisoformat(report.synthesis_timestamp)
    
    def test_init_complete(self):
        """Test l'initialisation avec tous les paramètres."""
        original_text = "Complete analysis text"
        logic_analysis = LogicAnalysisResult(logical_validity=True)
        informal_analysis = InformalAnalysisResult(argument_strength=0.8)
        
        contradictions = ["Contradiction 1", "Contradiction 2"]
        recommendations = ["Recommendation 1", "Recommendation 2"]
        
        report = UnifiedReport(
            original_text=original_text,
            logic_analysis=logic_analysis,
            informal_analysis=informal_analysis,
            executive_summary="Comprehensive summary",
            coherence_assessment="High coherence",
            contradictions_identified=contradictions,
            overall_validity=True,
            confidence_level=0.85,
            recommendations=recommendations,
            logic_informal_alignment=0.90,
            analysis_completeness=0.95,
            total_processing_time_ms=500.0
        )
        
        assert report.executive_summary == "Comprehensive summary"
        assert report.coherence_assessment == "High coherence"
        assert report.contradictions_identified == contradictions
        assert report.overall_validity == True
        assert report.confidence_level == 0.85
        assert report.recommendations == recommendations
        assert report.logic_informal_alignment == 0.90
        assert report.analysis_completeness == 0.95
        assert report.total_processing_time_ms == 500.0
    
    def test_to_dict(self):
        """Test la conversion en dictionnaire."""
        logic_analysis = LogicAnalysisResult(propositional_result="Test PL")
        informal_analysis = InformalAnalysisResult(arguments_structure="Test structure")
        
        report = UnifiedReport(
            original_text="Test text",
            logic_analysis=logic_analysis,
            informal_analysis=informal_analysis,
            overall_validity=True,
            confidence_level=0.75
        )
        
        report_dict = report.to_dict()
        
        assert isinstance(report_dict, dict)
        assert report_dict["original_text"] == "Test text"
        assert report_dict["overall_validity"] == True
        assert report_dict["confidence_level"] == 0.75
        assert report_dict["synthesis_version"] == "1.0.0"
        
        # Vérifier que les analyses sont correctement incluses
        assert isinstance(report_dict["logic_analysis"], dict)
        assert isinstance(report_dict["informal_analysis"], dict)
        assert report_dict["logic_analysis"]["propositional_result"] == "Test PL"
        assert report_dict["informal_analysis"]["arguments_structure"] == "Test structure"
        
        # Vérifier toutes les clés attendues
        expected_keys = {
            'original_text', 'logic_analysis', 'informal_analysis',
            'executive_summary', 'coherence_assessment', 'contradictions_identified',
            'overall_validity', 'confidence_level', 'recommendations',
            'logic_informal_alignment', 'analysis_completeness',
            'synthesis_timestamp', 'total_processing_time_ms', 'synthesis_version'
        }
        assert set(report_dict.keys()) == expected_keys
    
    def test_to_json(self):
        """Test la sérialisation JSON."""
        logic_analysis = LogicAnalysisResult(logical_validity=True)
        informal_analysis = InformalAnalysisResult(
            fallacies_detected=[{"type": "test", "confidence": 0.8}]
        )
        
        report = UnifiedReport(
            original_text="JSON test text",
            logic_analysis=logic_analysis,
            informal_analysis=informal_analysis,
            recommendations=["Test recommendation"]
        )
        
        # Test sérialisation
        json_str = report.to_json()
        assert isinstance(json_str, str)
        
        # Test désérialisation
        parsed = json.loads(json_str)
        assert parsed["original_text"] == "JSON test text"
        assert parsed["logic_analysis"]["logical_validity"] == True
        assert len(parsed["informal_analysis"]["fallacies_detected"]) == 1
        assert parsed["recommendations"] == ["Test recommendation"]
    
    def test_to_json_formatted(self):
        """Test la sérialisation JSON avec indentation."""
        report = UnifiedReport(
            original_text="Formatted test",
            logic_analysis=LogicAnalysisResult(),
            informal_analysis=InformalAnalysisResult()
        )
        
        json_str = report.to_json(indent=4)
        
        # Vérifier que l'indentation est appliquée
        assert "    " in json_str  # 4 espaces d'indentation
        assert "\n" in json_str    # Sauts de ligne
        
        # Vérifier que le contenu est correct
        parsed = json.loads(json_str)
        assert parsed["original_text"] == "Formatted test"
    
    def test_get_summary_statistics(self):
        """Test la génération de statistiques de résumé."""
        logic_analysis = LogicAnalysisResult(
            formulas_extracted=["formula1", "formula2", "formula3"]
        )
        
        informal_analysis = InformalAnalysisResult(
            fallacies_detected=[
                {"type": "ad_hominem"},
                {"type": "strawman"}
            ]
        )
        
        report = UnifiedReport(
            original_text="Statistics test text with some length",
            logic_analysis=logic_analysis,
            informal_analysis=informal_analysis,
            contradictions_identified=["contradiction1"],
            recommendations=["rec1", "rec2"],
            overall_validity=True,
            confidence_level=0.85
        )
        
        stats = report.get_summary_statistics()
        
        assert isinstance(stats, dict)
        assert stats["text_length"] == len("Statistics test text with some length")
        assert stats["formulas_count"] == 3
        assert stats["fallacies_count"] == 2
        assert stats["contradictions_count"] == 1
        assert stats["recommendations_count"] == 2
        assert stats["overall_validity"] == True
        assert stats["confidence_level"] == 0.85
    
    def test_get_summary_statistics_empty(self):
        """Test les statistiques avec des données vides."""
        logic_analysis = LogicAnalysisResult()
        informal_analysis = InformalAnalysisResult()
        
        report = UnifiedReport(
            original_text="",
            logic_analysis=logic_analysis,
            informal_analysis=informal_analysis
        )
        
        stats = report.get_summary_statistics()
        
        assert stats["text_length"] == 0
        assert stats["formulas_count"] == 0
        assert stats["fallacies_count"] == 0
        assert stats["contradictions_count"] == 0
        assert stats["recommendations_count"] == 0
        assert stats["overall_validity"] is None
        assert stats["confidence_level"] is None


class TestDataModelsIntegration:
    """Tests d'intégration entre les modèles de données."""
    
    def test_complete_workflow_data_models(self):
        """Test du workflow complet avec tous les modèles."""
        # 1. Créer une analyse logique
        logic_analysis = LogicAnalysisResult(
            propositional_result="Valid propositional logic",
            first_order_result="Valid first-order logic",
            modal_result="Valid modal logic",
            logical_validity=True,
            consistency_check=True,
            satisfiability=True,
            formulas_extracted=["p => q", "[]p", "forall x P(x)"],
            queries_executed=["p", "q", "[]p"],
            processing_time_ms=150.0
        )
        
        # 2. Créer une analyse informelle
        informal_analysis = InformalAnalysisResult(
            fallacies_detected=[
                {
                    "type": "ad_hominem",
                    "confidence": 0.85,
                    "location": {"start": 10, "end": 25},
                    "severity": "high"
                }
            ],
            arguments_structure="Clear argumentative structure",
            rhetorical_devices=["metaphor", "repetition"],
            argument_strength=0.75,
            persuasion_level="medium",
            credibility_score=0.80,
            text_segments_analyzed=["intro", "body", "conclusion"],
            context_factors={"domain": "politics", "audience": "general"},
            processing_time_ms=120.0
        )
        
        # 3. Créer un rapport unifié
        unified_report = UnifiedReport(
            original_text="Complete test argument with logical structure and rhetorical elements",
            logic_analysis=logic_analysis,
            informal_analysis=informal_analysis,
            executive_summary="The argument is logically valid but contains fallacies",
            coherence_assessment="High logical coherence, moderate rhetorical coherence",
            contradictions_identified=["Logic valid but contains ad hominem fallacy"],
            overall_validity=False,  # Fallacies reduce overall validity
            confidence_level=0.70,
            recommendations=[
                "Remove ad hominem attacks",
                "Strengthen rhetorical elements",
                "Maintain logical structure"
            ],
            logic_informal_alignment=0.60,
            analysis_completeness=0.90,
            total_processing_time_ms=270.0
        )
        
        # 4. Tester la conversion complète en dictionnaire
        full_dict = unified_report.to_dict()
        
        # Vérifications de structure
        assert isinstance(full_dict, dict)
        assert len(full_dict["logic_analysis"]["formulas_extracted"]) == 3
        assert len(full_dict["informal_analysis"]["fallacies_detected"]) == 1
        assert len(full_dict["recommendations"]) == 3
        
        # 5. Tester la sérialisation JSON complète
        json_str = unified_report.to_json()
        parsed_report = json.loads(json_str)
        
        # Vérifications après désérialisation
        assert parsed_report["overall_validity"] == False
        assert parsed_report["logic_analysis"]["logical_validity"] == True
        assert parsed_report["informal_analysis"]["fallacies_detected"][0]["type"] == "ad_hominem"
        assert len(parsed_report["recommendations"]) == 3
        
        # 6. Tester les statistiques
        stats = unified_report.get_summary_statistics()
        assert stats["formulas_count"] == 3
        assert stats["fallacies_count"] == 1
        assert stats["contradictions_count"] == 1
        assert stats["recommendations_count"] == 3
        assert stats["overall_validity"] == False
        assert stats["confidence_level"] == 0.70
    
    def test_nested_serialization_deserialization(self):
        """Test la sérialisation/désérialisation de structures imbriquées."""
        # Créer des données avec structures complexes imbriquées
        complex_fallacy = {
            "type": "complex_fallacy",
            "sub_fallacies": [
                {"type": "sub1", "confidence": 0.8},
                {"type": "sub2", "confidence": 0.6}
            ],
            "context": {
                "paragraph": 2,
                "sentences": [3, 4, 5],
                "linguistic_markers": ["however", "but", "although"]
            }
        }
        
        informal_analysis = InformalAnalysisResult(
            fallacies_detected=[complex_fallacy],
            context_factors={
                "meta_analysis": {
                    "source": "political_speech",
                    "classification": {
                        "primary": "persuasive",
                        "secondary": ["emotional", "logical"]
                    }
                }
            }
        )
        
        report = UnifiedReport(
            original_text="Complex nested test",
            logic_analysis=LogicAnalysisResult(),
            informal_analysis=informal_analysis
        )
        
        # Sérialisation
        json_str = report.to_json()
        
        # Désérialisation et vérification
        parsed = json.loads(json_str)
        fallacy = parsed["informal_analysis"]["fallacies_detected"][0]
        
        assert fallacy["type"] == "complex_fallacy"
        assert len(fallacy["sub_fallacies"]) == 2
        assert fallacy["context"]["paragraph"] == 2
        assert "however" in fallacy["context"]["linguistic_markers"]
        
        meta = parsed["informal_analysis"]["context_factors"]["meta_analysis"]
        assert meta["source"] == "political_speech"
        assert "emotional" in meta["classification"]["secondary"]
    
    def test_data_consistency_validation(self):
        """Test la validation de la cohérence des données."""
        # Test avec temps de traitement cohérents
        logic_time = 100.0
        informal_time = 80.0
        total_time = 200.0  # Supérieur à la somme (overhead)
        
        logic_analysis = LogicAnalysisResult(processing_time_ms=logic_time)
        informal_analysis = InformalAnalysisResult(processing_time_ms=informal_time)
        
        report = UnifiedReport(
            original_text="Consistency test",
            logic_analysis=logic_analysis,
            informal_analysis=informal_analysis,
            total_processing_time_ms=total_time
        )
        
        # Vérifier la cohérence des temps
        assert report.total_processing_time_ms >= max(logic_time, informal_time)
        
        # Test des dates (timestamp récent)
        from datetime import datetime, timedelta
        
        report_time = datetime.fromisoformat(report.synthesis_timestamp)
        now = datetime.now()
        time_diff = abs((now - report_time).total_seconds())
        
        # Le timestamp doit être récent (moins d'1 minute)
        assert time_diff < 60
    
    def test_edge_cases_and_limits(self):
        """Test des cas limites et edge cases."""
        # Texte très long
        very_long_text = "x" * 10000
        
        # Beaucoup de formules
        many_formulas = [f"formula_{i}" for i in range(100)]
        
        # Beaucoup de sophismes
        many_fallacies = [{"type": f"fallacy_{i}", "confidence": 0.5} for i in range(50)]
        
        logic_analysis = LogicAnalysisResult(formulas_extracted=many_formulas)
        informal_analysis = InformalAnalysisResult(fallacies_detected=many_fallacies)
        
        report = UnifiedReport(
            original_text=very_long_text,
            logic_analysis=logic_analysis,
            informal_analysis=informal_analysis
        )
        
        # Test que tout fonctionne avec des données volumineuses
        report_dict = report.to_dict()
        assert len(report_dict["original_text"]) == 10000
        assert len(report_dict["logic_analysis"]["formulas_extracted"]) == 100
        assert len(report_dict["informal_analysis"]["fallacies_detected"]) == 50
        
        # Test sérialisation JSON (peut être lente mais doit fonctionner)
        json_str = report.to_json()
        assert isinstance(json_str, str)
        assert len(json_str) > 1000  # JSON substantial
        
        # Test statistiques
        stats = report.get_summary_statistics()
        assert stats["text_length"] == 10000
        assert stats["formulas_count"] == 100
        assert stats["fallacies_count"] == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])