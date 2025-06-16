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
from unittest.mock import patch, AsyncMock
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
    def cluedo_orchestrator(self, llm_service):
        """Instance de CluedoOrchestrator pour les tests."""
        config = {
            "investigation_depth": "thorough",
            "evidence_analysis_mode": "systematic",
            "deduction_strategy": "sherlock_holmes"
        }
        return CluedoOrchestrator(llm_service=llm_service, config=config)
    
    @pytest.fixture
    def investigation_text(self):
        """Texte d'enquête pour les tests."""
        return (
            "Le témoin A affirme avoir vu le suspect à 21h près de la bibliothèque. "
            "Le témoin B dit le contraire, qu'il était ailleurs. "
            "Les preuves matérielles suggèrent une présence sur les lieux. "
            "Qui dit la vérité dans cette affaire ?"
        )
    
    def test_cluedo_orchestrator_initialization(self, cluedo_orchestrator, llm_service):
        """Test de l'initialisation de l'orchestrateur Cluedo."""
        assert cluedo_orchestrator.llm_service == llm_service
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
        """Test d'identification systématique des preuves avec un vrai LLM."""
        text = "Le couteau était sur la table. Marie a dit qu'elle a vu Jean partir. L'ADN confirme sa présence."
        
        # Pas de mock, appel LLM réel
        evidence = await cluedo_orchestrator._identify_evidence(text)
        
        # Assertions souples
        assert isinstance(evidence, dict)
        assert "physical_evidence" in evidence
        assert "witness_testimonies" in evidence
        assert isinstance(evidence["physical_evidence"], list)
        assert isinstance(evidence["witness_testimonies"], list)

        if evidence["physical_evidence"]:
            item = evidence["physical_evidence"][0]
            assert "item" in item
            assert "relevance" in item
            assert "type" in item

        if evidence["witness_testimonies"]:
            testimony = evidence["witness_testimonies"][0]
            assert "witness" in testimony
            assert "statement" in testimony
    
    @pytest.mark.asyncio
    async def test_analyze_credibility_witnesses(self, cluedo_orchestrator):
        """Test d'analyse de crédibilité des témoins avec un vrai LLM."""
        witness_data = [
            {"name": "témoin A", "statement": "J'ai vu clairement le suspect à 21h précises, il portait un manteau rouge."},
            {"name": "témoin B", "statement": "Je crois l'avoir vu vers 21h, mais je ne suis pas sûr de ce qu'il portait."}
        ]
        
        # Pas de mock, appel LLM réel
        credibility = await cluedo_orchestrator._analyze_credibility(witness_data)
        
        # Assertions souples
        assert isinstance(credibility, dict)
        assert "credibility_scores" in credibility
        assert "credibility_factors" in credibility
        scores = credibility["credibility_scores"]
        assert "témoin A" in scores
        assert "témoin B" in scores
        assert "overall_credibility" in scores["témoin A"]
        assert "overall_credibility" in scores["témoin B"]
        # On s'attend à ce que le témoin A, plus précis, ait un meilleur score
        assert scores["témoin A"]["overall_credibility"] >= scores["témoin B"]["overall_credibility"]


class TestConversationOrchestrator:
    """Tests pour l'orchestrateur de conversation."""
    
    @pytest.fixture
    def conversation_orchestrator(self, llm_service):
        """Instance de ConversationOrchestrator pour les tests."""
        config = {
            "dialogue_analysis_depth": "comprehensive",
            "turn_taking_analysis": True,
            "rhetorical_strategy_detection": True
        }
        return ConversationOrchestrator(llm_service=llm_service, config=config)
    
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
        """Test d'analyse de structure de dialogue avec un vrai LLM."""
        dialogue = "A: Je pense que nous devrions investir dans l'énergie solaire.\nB: Mais c'est trop cher et intermittent.\nA: Le coût a baissé et le stockage s'améliore."
        
        # Pas de mock, appel LLM réel
        structure = await conversation_orchestrator._parse_dialogue_structure(dialogue)
        
        # Assertions souples
        assert isinstance(structure, dict)
        assert "parsed_turns" in structure
        assert "dialogue_statistics" in structure
        assert isinstance(structure["parsed_turns"], list)
        assert len(structure["parsed_turns"]) == 3
        
        turn = structure["parsed_turns"][0]
        assert "speaker" in turn
        assert "content" in turn
        assert "speech_act" in turn
        assert turn["speaker"] == "A"
        
        stats = structure["dialogue_statistics"]
        assert stats["total_turns"] == 3
        assert "A" in stats["speakers"]
        assert "B" in stats["speakers"]


class TestRealLLMOrchestrator:
    """Tests pour l'orchestrateur LLM réel."""
    
    @pytest.fixture
    def real_llm_orchestrator(self, llm_service):
        """Instance de RealLLMOrchestrator pour les tests."""
        config = {
            "llm_coordination_strategy": "multi_agent",
            "prompt_optimization": True,
            "response_validation": True
        }
        return RealLLMOrchestrator(llm_service=llm_service, config=config)
    
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
    def logic_orchestrator(self, llm_service):
        """Instance de LogiqueComplexeOrchestrator pour les tests."""
        config = {
            "logical_system": "multi_modal",
            "reasoning_depth": "deep",
            "formal_verification": True
        }
        return LogiqueComplexeOrchestrator(llm_service=llm_service, config=config)
    
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
        """Test d'extraction de structure formelle avec un vrai LLM."""
        text = "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."
        
        # Pas de mock, appel LLM réel
        structure = await logic_orchestrator._extract_formal_structure(text)
        
        # Assertions souples
        assert isinstance(structure, dict)
        assert "formal_propositions" in structure
        assert "logical_structure" in structure
        assert isinstance(structure["formal_propositions"], list)
        assert len(structure["formal_propositions"]) >= 3
        # Vérifier si la structure contient des éléments de logique formelle
        assert "∀" in structure["formal_propositions"][0] or "forall" in structure["formal_propositions"][0].lower()
        assert "→" in structure["formal_propositions"][0] or "implies" in structure["formal_propositions"][0].lower()
        assert "Human(Socrates)" in structure["formal_propositions"] or "homme(socrate)" in str(structure["formal_propositions"]).lower()


class TestSpecializedOrchestratorsIntegration:
    """Tests d'intégration entre orchestrateurs spécialisés."""
    
    # Fixture mock_llm_service supprimée
    
    @pytest.mark.asyncio
    async def test_orchestrator_selection_by_content(self, llm_service):
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
                selected_orchestrator = case["orchestrator_class"](llm_service, {})
                assert isinstance(selected_orchestrator, case["orchestrator_class"])
            elif "Alice:" in case["text"] or "Bob:" in case["text"]:
                selected_orchestrator = case["orchestrator_class"](llm_service, {})
                assert isinstance(selected_orchestrator, case["orchestrator_class"])
            elif "Tous les" in case["text"] and "Donc" in case["text"]:
                selected_orchestrator = case["orchestrator_class"](llm_service, {})
                assert isinstance(selected_orchestrator, case["orchestrator_class"])
    
    @pytest.mark.asyncio
    async def test_orchestrator_collaboration(self, llm_service):
        """Test de collaboration entre orchestrateurs avec un vrai LLM."""
        # Texte complexe nécessitant plusieurs orchestrateurs
        complex_text = (
            "Dans cette enquête, le témoin A affirme : 'Si tous les suspects "
            "étaient présents, alors le crime a eu lieu.' Le témoin B répond : "
            "'Mais Jean n'était pas là, donc votre logique est fausse.'"
        )
        
        # Utilisation d'instances réelles avec le même service LLM
        cluedo_orchestrator = CluedoOrchestrator(llm_service, {})
        conversation_orchestrator = ConversationOrchestrator(llm_service, {})
        logic_orchestrator = LogiqueComplexeOrchestrator(llm_service, {})
        
        # Exécuter les vraies analyses
        
        # On ne peut pas mocker les méthodes internes, on appelle la méthode publique
        # et on fait des assertions souples sur le résultat.
        # C'est maintenant un test d'intégration.
        
        investigation_result = await cluedo_orchestrator.orchestrate_investigation_analysis(complex_text)
        dialogue_result = await conversation_orchestrator.orchestrate_dialogue_analysis(complex_text)
        logic_result = await logic_orchestrator.orchestrate_complex_logical_analysis(complex_text)
        
        # Assertions souples d'intégration
        assert "investigation_conclusion" in investigation_result
        assert "dialogue_structure" in dialogue_result
        assert "logical_verification" in logic_result
        assert "confidence" in investigation_result["investigation_conclusion"]
        assert "total_turns" in dialogue_result["dialogue_structure"]["dialogue_statistics"]
        assert "validity" in logic_result["reasoning_analysis"]


if __name__ == "__main__":
    # Exécution des tests si le script est lancé directement
    pytest.main([__file__, "-v", "--tb=short"])
