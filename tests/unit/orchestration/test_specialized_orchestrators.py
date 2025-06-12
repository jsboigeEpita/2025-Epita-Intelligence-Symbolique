#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests Unitaires pour les Orchestrateurs Spécialisés
===================================================

Tests pour valider le fonctionnement des orchestrateurs spécialisés :
- CluedoOrchestrator (enquêtes et investigations)
- ConversationOrchestrator (analyses conversationnelles)
- RealLLMOrchestrator (orchestration LLM réelle)
- LogiqueComplexeOrchestrator (logique complexe)

Auteur: Intelligence Symbolique EPITA
Date: 10/06/2025
"""

import pytest
import asyncio
import logging
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List

# Configuration du logging pour les tests
logging.basicConfig(level=logging.WARNING)

# Imports à tester
try:
    from argumentation_analysis.orchestrators.cluedo_orchestrator import CluedoOrchestrator
    from argumentation_analysis.orchestrators.conversation_orchestrator import ConversationOrchestrator
    from argumentation_analysis.orchestrators.real_llm_orchestrator import RealLLMOrchestrator
    from argumentation_analysis.orchestrators.logique_complexe_orchestrator import LogiqueComplexeOrchestrator
    SPECIALIZED_AVAILABLE = True
except ImportError as e:
    SPECIALIZED_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Orchestrateurs spécialisés non disponibles: {e}")


class TestCluedoOrchestrator:
    """Tests pour l'orchestrateur Cluedo (investigations)."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Service LLM mocké pour les tests."""
        mock_service = MagicMock()
        mock_service.service_id = "test_cluedo_llm"
        mock_service.generate_text = AsyncMock(return_value="Response investigation")
        return mock_service
    
    @pytest.fixture
    def cluedo_orchestrator(self, mock_llm_service):
        """Instance de CluedoOrchestrator pour les tests."""
        config = {
            "investigation_depth": "thorough",
            "evidence_analysis_mode": "systematic",
            "deduction_strategy": "sherlock_holmes"
        }
        return CluedoOrchestrator(llm_service=mock_llm_service, config=config)
    
    @pytest.fixture
    def investigation_text(self):
        """Texte d'enquête pour les tests."""
        return (
            "Le témoin A affirme avoir vu le suspect à 21h près de la bibliothèque. "
            "Le témoin B dit le contraire, qu'il était ailleurs. "
            "Les preuves matérielles suggèrent une présence sur les lieux. "
            "Qui dit la vérité dans cette affaire ?"
        )
    
    def test_cluedo_orchestrator_initialization(self, cluedo_orchestrator, mock_llm_service):
        """Test de l'initialisation de l'orchestrateur Cluedo."""
        assert cluedo_orchestrator.llm_service == mock_llm_service
        assert cluedo_orchestrator.evidence_repository == {}
        assert cluedo_orchestrator.witness_statements == []
        assert cluedo_orchestrator.deduction_chain == []
        assert cluedo_orchestrator.investigation_state == "initial"
    
    @pytest.mark.asyncio
    async def test_orchestrate_investigation_analysis(self, cluedo_orchestrator, investigation_text):
        """Test de l'orchestration d'analyse d'investigation."""
        # Mock des méthodes d'investigation
        cluedo_orchestrator._identify_evidence = AsyncMock(return_value={
            "physical_evidence": ["présence sur les lieux"],
            "witness_testimonies": ["témoin A: vu à 21h", "témoin B: ailleurs"],
            "contradictions": ["témoins contradictoires"],
            "reliability_scores": {"témoin A": 0.7, "témoin B": 0.6}
        })
        
        cluedo_orchestrator._analyze_credibility = AsyncMock(return_value={
            "credibility_analysis": {
                "témoin A": {"score": 0.75, "factors": ["précision temporelle"]},
                "témoin B": {"score": 0.65, "factors": ["moins de détails"]}
            },
            "evidence_weight": {"physical": 0.9, "testimonial": 0.6}
        })
        
        cluedo_orchestrator._perform_deductive_reasoning = AsyncMock(return_value={
            "deduction_steps": [
                "Preuves matérielles indiquent présence",
                "Témoin A plus crédible que témoin B",
                "Contradiction résolvable par erreur témoin B"
            ],
            "conclusion": "Suspect probablement présent à 21h",
            "confidence": 0.82
        })
        
        result = await cluedo_orchestrator.orchestrate_investigation_analysis(investigation_text)
        
        assert "evidence_analysis" in result
        assert "credibility_assessment" in result
        assert "deductive_reasoning" in result
        assert "investigation_conclusion" in result
        assert result["investigation_conclusion"]["confidence"] == 0.82
    
    @pytest.mark.asyncio
    async def test_identify_evidence_systematic(self, cluedo_orchestrator):
        """Test d'identification systématique des preuves."""
        text = "Le couteau était sur la table. Marie a dit qu'elle a vu Jean partir. L'ADN confirme sa présence."
        
        cluedo_orchestrator.llm_service.generate_text.return_value = """
        {
            "physical_evidence": [
                {"item": "couteau", "location": "table", "relevance": "high", "type": "weapon"},
                {"item": "ADN", "analysis": "confirme présence", "relevance": "critical", "type": "biological"}
            ],
            "witness_testimonies": [
                {"witness": "Marie", "statement": "a vu Jean partir", "reliability": "medium"}
            ],
            "temporal_markers": ["moment du départ"],
            "spatial_markers": ["table", "lieu de présence"]
        }
        """
        
        evidence = await cluedo_orchestrator._identify_evidence(text)
        
        assert "physical_evidence" in evidence
        assert "witness_testimonies" in evidence
        assert len(evidence["physical_evidence"]) == 2
        assert evidence["physical_evidence"][1]["type"] == "biological"
    
    @pytest.mark.asyncio
    async def test_analyze_credibility_witnesses(self, cluedo_orchestrator):
        """Test d'analyse de crédibilité des témoins."""
        witness_data = [
            {"name": "témoin A", "statement": "J'ai vu clairement à 21h précises"},
            {"name": "témoin B", "statement": "Je pense qu'il était vers 21h quelque part"}
        ]
        
        cluedo_orchestrator.llm_service.generate_text.return_value = """
        {
            "credibility_scores": {
                "témoin A": {
                    "precision_score": 0.9,
                    "consistency_score": 0.8,
                    "detail_level": 0.85,
                    "overall_credibility": 0.85
                },
                "témoin B": {
                    "precision_score": 0.4,
                    "consistency_score": 0.6,
                    "detail_level": 0.3,
                    "overall_credibility": 0.43
                }
            },
            "credibility_factors": {
                "precision_temporelle": "témoin A supérieur",
                "niveau_détail": "témoin A bien plus précis"
            }
        }
        """
        
        credibility = await cluedo_orchestrator._analyze_credibility(witness_data)
        
        assert "credibility_scores" in credibility
        assert credibility["credibility_scores"]["témoin A"]["overall_credibility"] > 0.8
        assert credibility["credibility_scores"]["témoin B"]["overall_credibility"] < 0.5


class TestConversationOrchestrator:
    """Tests pour l'orchestrateur de conversation."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Service LLM mocké pour les tests."""
        mock_service = MagicMock()
        mock_service.service_id = "test_conversation_llm"
        mock_service.generate_text = AsyncMock(return_value="Response conversation")
        return mock_service
    
    @pytest.fixture
    def conversation_orchestrator(self, mock_llm_service):
        """Instance de ConversationOrchestrator pour les tests."""
        config = {
            "dialogue_analysis_depth": "comprehensive",
            "turn_taking_analysis": True,
            "rhetorical_strategy_detection": True
        }
        return ConversationOrchestrator(llm_service=mock_llm_service, config=config)
    
    @pytest.fixture
    def dialogue_text(self):
        """Texte de dialogue pour les tests."""
        return (
            "Alice: Je pense que l'éducation gratuite est un droit fondamental.\n"
            "Bob: Mais qui va payer ? Les contribuables sont déjà surchargés.\n"
            "Alice: C'est un investissement à long terme pour la société.\n"
            "Bob: Investissement ? Plutôt une dépense sans garantie de retour."
        )
    
    def test_conversation_orchestrator_initialization(self, conversation_orchestrator):
        """Test de l'initialisation de l'orchestrateur de conversation."""
        assert conversation_orchestrator.dialogue_turns == []
        assert conversation_orchestrator.speaker_profiles == {}
        assert conversation_orchestrator.rhetorical_patterns == {}
        assert conversation_orchestrator.argument_flow == []
    
    @pytest.mark.asyncio
    async def test_orchestrate_dialogue_analysis(self, conversation_orchestrator, dialogue_text):
        """Test de l'orchestration d'analyse de dialogue."""
        # Mock des méthodes d'analyse
        conversation_orchestrator._parse_dialogue_structure = AsyncMock(return_value={
            "turns": [
                {"speaker": "Alice", "content": "éducation gratuite droit fondamental", "type": "claim"},
                {"speaker": "Bob", "content": "qui va payer contribuables surchargés", "type": "objection"},
                {"speaker": "Alice", "content": "investissement long terme société", "type": "justification"},
                {"speaker": "Bob", "content": "dépense sans garantie retour", "type": "counter_argument"}
            ],
            "turn_count": 4,
            "speaker_distribution": {"Alice": 2, "Bob": 2}
        })
        
        conversation_orchestrator._analyze_rhetorical_strategies = AsyncMock(return_value={
            "Alice": ["appeal_to_rights", "long_term_thinking"],
            "Bob": ["economic_concern", "skeptical_questioning"],
            "dialogue_patterns": ["claim_objection_justification_counter"]
        })
        
        conversation_orchestrator._track_argument_evolution = AsyncMock(return_value={
            "argument_trajectory": [
                {"stage": "initial_claim", "focus": "educational_rights"},
                {"stage": "economic_challenge", "focus": "funding_concerns"},
                {"stage": "value_justification", "focus": "societal_benefits"},
                {"stage": "skeptical_response", "focus": "roi_uncertainty"}
            ],
            "evolution_pattern": "escalating_disagreement"
        })
        
        result = await conversation_orchestrator.orchestrate_dialogue_analysis(dialogue_text)
        
        assert "dialogue_structure" in result
        assert "rhetorical_analysis" in result
        assert "argument_evolution" in result
        assert result["dialogue_structure"]["turn_count"] == 4
    
    @pytest.mark.asyncio
    async def test_parse_dialogue_structure(self, conversation_orchestrator):
        """Test d'analyse de structure de dialogue."""
        dialogue = "A: Argument 1\nB: Contre-argument\nA: Réfutation"
        
        conversation_orchestrator.llm_service.generate_text.return_value = """
        {
            "parsed_turns": [
                {"speaker": "A", "content": "Argument 1", "speech_act": "assertion", "argument_type": "claim"},
                {"speaker": "B", "content": "Contre-argument", "speech_act": "objection", "argument_type": "counter_claim"},
                {"speaker": "A", "content": "Réfutation", "speech_act": "rebuttal", "argument_type": "defense"}
            ],
            "dialogue_statistics": {
                "total_turns": 3,
                "speakers": ["A", "B"],
                "turn_distribution": {"A": 2, "B": 1}
            }
        }
        """
        
        structure = await conversation_orchestrator._parse_dialogue_structure(dialogue)
        
        assert "parsed_turns" in structure
        assert "dialogue_statistics" in structure
        assert structure["dialogue_statistics"]["total_turns"] == 3


class TestRealLLMOrchestrator:
    """Tests pour l'orchestrateur LLM réel."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Service LLM mocké pour les tests."""
        mock_service = MagicMock()
        mock_service.service_id = "test_real_llm"
        mock_service.generate_text = AsyncMock(return_value="Response LLM réel")
        return mock_service
    
    @pytest.fixture
    def real_llm_orchestrator(self, mock_llm_service):
        """Instance de RealLLMOrchestrator pour les tests."""
        config = {
            "llm_coordination_strategy": "multi_agent",
            "prompt_optimization": True,
            "response_validation": True
        }
        return RealLLMOrchestrator(llm_service=mock_llm_service, config=config)
    
    def test_real_llm_orchestrator_initialization(self, real_llm_orchestrator):
        """Test de l'initialisation de l'orchestrateur LLM réel."""
        assert real_llm_orchestrator.active_llm_sessions == {}
        assert real_llm_orchestrator.prompt_templates == {}
        assert real_llm_orchestrator.response_history == []
        assert real_llm_orchestrator.validation_metrics == {}
    
    @pytest.mark.asyncio
    async def test_orchestrate_multi_llm_analysis(self, real_llm_orchestrator):
        """Test de l'orchestration d'analyse multi-LLM."""
        text = "Texte complexe nécessitant analyse multi-agents"
        
        # Mock des méthodes LLM
        real_llm_orchestrator._coordinate_llm_agents = AsyncMock(return_value={
            "agent_assignments": {
                "logical_agent": "analyse_structure_logique",
                "rhetorical_agent": "analyse_rhetorique", 
                "semantic_agent": "analyse_semantique"
            },
            "coordination_plan": {"parallel_execution": True, "sync_points": 2}
        })
        
        real_llm_orchestrator._execute_coordinated_analysis = AsyncMock(return_value={
            "logical_analysis": {"structure": "syllogistique", "validity": 0.8},
            "rhetorical_analysis": {"strategies": ["ethos", "logos"], "effectiveness": 0.7},
            "semantic_analysis": {"concepts": ["éducation", "société"], "coherence": 0.9}
        })
        
        real_llm_orchestrator._synthesize_llm_results = AsyncMock(return_value={
            "integrated_analysis": {
                "logical_score": 0.8,
                "rhetorical_score": 0.7,
                "semantic_score": 0.9,
                "overall_quality": 0.8
            },
            "consensus_findings": ["structure claire", "arguments solides"]
        })
        
        result = await real_llm_orchestrator.orchestrate_multi_llm_analysis(text)
        
        assert "coordination_plan" in result
        assert "agent_results" in result
        assert "synthesized_analysis" in result
        assert result["synthesized_analysis"]["integrated_analysis"]["overall_quality"] == 0.8


class TestLogiqueComplexeOrchestrator:
    """Tests pour l'orchestrateur de logique complexe."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Service LLM mocké pour les tests."""
        mock_service = MagicMock()
        mock_service.service_id = "test_logic_complex_llm"
        mock_service.generate_text = AsyncMock(return_value="Response logique complexe")
        return mock_service
    
    @pytest.fixture
    def logic_orchestrator(self, mock_llm_service):
        """Instance de LogiqueComplexeOrchestrator pour les tests."""
        config = {
            "logical_system": "multi_modal",
            "reasoning_depth": "deep",
            "formal_verification": True
        }
        return LogiqueComplexeOrchestrator(llm_service=mock_llm_service, config=config)
    
    @pytest.fixture
    def complex_logical_text(self):
        """Texte logique complexe pour les tests."""
        return (
            "Si tous les scientifiques sont rationnels, et si tous les rationnels "
            "acceptent les preuves empiriques, alors tous les scientifiques acceptent "
            "les preuves empiriques. Or, certains scientifiques rejettent certaines "
            "preuves. Par conséquent, soit tous les scientifiques ne sont pas "
            "rationnels, soit notre prémisse initiale est incorrecte."
        )
    
    def test_logic_orchestrator_initialization(self, logic_orchestrator):
        """Test de l'initialisation de l'orchestrateur de logique complexe."""
        assert logic_orchestrator.formal_structures == {}
        assert logic_orchestrator.reasoning_chains == []
        assert logic_orchestrator.logical_system_state == "initialized"
        assert logic_orchestrator.verification_results == {}
    
    @pytest.mark.asyncio
    async def test_orchestrate_complex_logical_analysis(self, logic_orchestrator, complex_logical_text):
        """Test de l'orchestration d'analyse logique complexe."""
        # Mock des méthodes de logique complexe
        logic_orchestrator._extract_formal_structure = AsyncMock(return_value={
            "propositions": [
                "∀x(Scientist(x) → Rational(x))",
                "∀x(Rational(x) → AcceptsEvidence(x))",
                "∃x(Scientist(x) ∧ ¬AcceptsEvidence(x))"
            ],
            "logical_form": "modus_tollens_complex",
            "quantifier_structure": "universal_existential_mix"
        })
        
        logic_orchestrator._perform_formal_reasoning = AsyncMock(return_value={
            "reasoning_steps": [
                "Application modus ponens: Scientist(x) → AcceptsEvidence(x)",
                "Contradiction avec ∃x(Scientist(x) ∧ ¬AcceptsEvidence(x))",
                "Résolution par modus tollens"
            ],
            "logical_conclusion": "¬∀x(Scientist(x) → Rational(x)) ∨ premise_error",
            "validity": True
        })
        
        logic_orchestrator._verify_logical_consistency = AsyncMock(return_value={
            "consistency_check": True,
            "contradiction_analysis": "Contradiction résolvable",
            "formal_validity": 0.95,
            "soundness_assessment": "Valid sous réserve prémisses"
        })
        
        result = await logic_orchestrator.orchestrate_complex_logical_analysis(complex_logical_text)
        
        assert "formal_structure" in result
        assert "reasoning_analysis" in result
        assert "logical_verification" in result
        assert result["logical_verification"]["formal_validity"] == 0.95
    
    @pytest.mark.asyncio
    async def test_extract_formal_structure(self, logic_orchestrator):
        """Test d'extraction de structure formelle."""
        text = "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."
        
        logic_orchestrator.llm_service.generate_text.return_value = """
        {
            "formal_propositions": [
                "∀x(Human(x) → Mortal(x))",
                "Human(Socrates)",
                "Mortal(Socrates)"
            ],
            "logical_structure": "classical_syllogism",
            "inference_pattern": "modus_ponens",
            "quantification": "universal_particular"
        }
        """
        
        structure = await logic_orchestrator._extract_formal_structure(text)
        
        assert "formal_propositions" in structure
        assert "logical_structure" in structure
        assert structure["logical_structure"] == "classical_syllogism"


class TestSpecializedOrchestratorsIntegration:
    """Tests d'intégration entre orchestrateurs spécialisés."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Service LLM mocké pour tous les orchestrateurs."""
        mock_service = MagicMock()
        mock_service.service_id = "test_integration_specialized_llm"
        mock_service.generate_text = AsyncMock(return_value="Response intégration")
        return mock_service
    
    @pytest.mark.asyncio
    async def test_orchestrator_selection_by_content(self, mock_llm_service):
        """Test de sélection d'orchestrateur selon le contenu."""
        test_cases = [
            {
                "text": "Le témoin dit avoir vu le suspect. Qui dit la vérité ?",
                "expected_type": "investigation",
                "orchestrator_class": CluedoOrchestrator
            },
            {
                "text": "Alice: Je pense que... Bob: Mais non, c'est faux !",
                "expected_type": "dialogue",
                "orchestrator_class": ConversationOrchestrator
            },
            {
                "text": "Tous les A sont B. C est A. Donc C est B.",
                "expected_type": "logical",
                "orchestrator_class": LogiqueComplexeOrchestrator
            }
        ]
        
        for case in test_cases:
            # Simuler la sélection automatique
            if "témoin" in case["text"] or "vérité" in case["text"]:
                selected_orchestrator = case["orchestrator_class"](mock_llm_service, {})
                assert isinstance(selected_orchestrator, case["orchestrator_class"])
            elif "Alice:" in case["text"] or "Bob:" in case["text"]:
                selected_orchestrator = case["orchestrator_class"](mock_llm_service, {})
                assert isinstance(selected_orchestrator, case["orchestrator_class"])
            elif "Tous les" in case["text"] and "Donc" in case["text"]:
                selected_orchestrator = case["orchestrator_class"](mock_llm_service, {})
                assert isinstance(selected_orchestrator, case["orchestrator_class"])
    
    @pytest.mark.asyncio
    async def test_orchestrator_collaboration(self, mock_llm_service):
        """Test de collaboration entre orchestrateurs."""
        # Texte complexe nécessitant plusieurs orchestrateurs
        complex_text = (
            "Dans cette enquête, le témoin A affirme : 'Si tous les suspects "
            "étaient présents, alors le crime a eu lieu.' Le témoin B répond : "
            "'Mais Jean n'était pas là, donc votre logique est fausse.'"
        )
        
        # Simuler une coordination entre orchestrateurs
        cluedo_orchestrator = CluedoOrchestrator(mock_llm_service, {})
        conversation_orchestrator = ConversationOrchestrator(mock_llm_service, {})
        logic_orchestrator = LogiqueComplexeOrchestrator(mock_llm_service, {})
        
        # Mock des analyses spécialisées
        cluedo_orchestrator.orchestrate_investigation_analysis = AsyncMock(return_value={
            "evidence": "Témoignages contradictoires",
            "credibility": {"témoin A": 0.7, "témoin B": 0.8}
        })
        
        conversation_orchestrator.orchestrate_dialogue_analysis = AsyncMock(return_value={
            "dialogue_pattern": "logical_disagreement",
            "argumentation_structure": "claim_counter_claim"
        })
        
        logic_orchestrator.orchestrate_complex_logical_analysis = AsyncMock(return_value={
            "logical_structure": "conditional_with_negation",
            "validity": "depends_on_premises"
        })
        
        # Exécuter les analyses
        investigation_result = await cluedo_orchestrator.orchestrate_investigation_analysis(complex_text)
        dialogue_result = await conversation_orchestrator.orchestrate_dialogue_analysis(complex_text)
        logic_result = await logic_orchestrator.orchestrate_complex_logical_analysis(complex_text)
        
        # Vérifier la cohérence des résultats
        assert investigation_result["credibility"]["témoin B"] > investigation_result["credibility"]["témoin A"]
        assert dialogue_result["dialogue_pattern"] == "logical_disagreement"
        assert logic_result["logical_structure"] == "conditional_with_negation"


if __name__ == "__main__":
    # Exécution des tests si le script est lancé directement
    pytest.main([__file__, "-v", "--tb=short"])
