"""
Tests comparatifs Mock vs Réel pour Oracle Enhanced v2.1.0.
Récupéré et adapté pour Oracle Enhanced v2.1.0

Tests couvrant:
- Comparaison comportement mocks vs GPT-4o-mini réel
- Validation cohérence Oracle Enhanced
- Métriques différences performance/qualité
"""

import pytest
import asyncio
import time
import os
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List, Optional
from datetime import datetime
import statistics

# Imports conditionnels (adaptés v2.1.0)
try:
    from semantic_kernel.kernel import Kernel
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
    from semantic_kernel.contents.chat_message_content import ChatMessageContent
    SEMANTIC_KERNEL_AVAILABLE = True
except ImportError:
    SEMANTIC_KERNEL_AVAILABLE = False

try:
    from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
    from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
    ORACLE_SYSTEM_AVAILABLE = True
except ImportError:
    ORACLE_SYSTEM_AVAILABLE = False


# Configuration Oracle Enhanced v2.1.0
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
REAL_GPT_AVAILABLE = OPENAI_API_KEY is not None and len(OPENAI_API_KEY) > 10
COMPARISON_TESTS_ENABLED = os.environ.get('ENABLE_COMPARISON_TESTS', 'false').lower() == 'true'


class BehaviorComparator:
    """Comparateur de comportements Mock vs Réel Oracle Enhanced v2.1.0."""
    
    def __init__(self):
        self.mock_results = {}
        self.real_results = {}
        self.comparison_metrics = {}
    
    async def test_mock_behavior(self, test_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test le comportement avec mocks Oracle Enhanced v2.1.0."""
        start_time = time.time()
        
        # Création du kernel mocké
        mock_kernel = self._create_mock_kernel()
        
        try:
            if ORACLE_SYSTEM_AVAILABLE:
                orchestrator = CluedoExtendedOrchestrator(
                    kernel=mock_kernel,
                    max_turns=test_scenario.get('max_turns', 3),
                    max_cycles=test_scenario.get('max_cycles', 2),
                    oracle_strategy="enhanced_auto_reveal"
                )
                
                # Simulation d'exécution
                mock_result = await self._simulate_mock_execution(
                    orchestrator, 
                    test_scenario
                )
            else:
                mock_result = await self._simulate_basic_mock_execution(test_scenario)
            
            execution_time = time.time() - start_time
            
            return {
                'type': 'mock',
                'scenario': test_scenario['name'],
                'execution_time': execution_time,
                'response_content': mock_result.get('content', ''),
                'response_length': len(mock_result.get('content', '')),
                'success': True,
                'metadata': mock_result.get('metadata', {}),
                'predictable': True,
                'cost': 0.0,
                'oracle_enhanced_version': '2.1.0'
            }
            
        except Exception as e:
            return {
                'type': 'mock',
                'scenario': test_scenario['name'],
                'execution_time': time.time() - start_time,
                'success': False,
                'error': str(e),
                'predictable': True,
                'cost': 0.0,
                'oracle_enhanced_version': '2.1.0'
            }
    
    async def test_real_behavior(self, test_scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test le comportement avec GPT-4o-mini réel Oracle Enhanced v2.1.0."""
        if not REAL_GPT_AVAILABLE:
            return {
                'type': 'real',
                'scenario': test_scenario['name'],
                'success': False,
                'error': 'OpenAI API key not available',
                'cost': 0.0,
                'oracle_enhanced_version': '2.1.0'
            }
        
        start_time = time.time()
        estimated_cost = 0.0
        
        try:
            # Création du kernel réel
            real_kernel = self._create_real_kernel()
            
            if ORACLE_SYSTEM_AVAILABLE:
                orchestrator = CluedoExtendedOrchestrator(
                    kernel=real_kernel,
                    max_turns=test_scenario.get('max_turns', 3),
                    max_cycles=test_scenario.get('max_cycles', 2),
                    oracle_strategy="enhanced_auto_reveal"
                )
                
                real_result = await self._execute_real_gpt_scenario(
                    orchestrator,
                    test_scenario
                )
            else:
                real_result = await self._execute_basic_real_scenario(
                    real_kernel,
                    test_scenario
                )
            
            execution_time = time.time() - start_time
            
            # Estimation du coût (approximative)
            estimated_tokens = len(real_result.get('content', '')) + len(test_scenario.get('prompt', ''))
            estimated_cost = estimated_tokens * 0.000375 / 1000  # Estimation GPT-4o-mini
            
            return {
                'type': 'real',
                'scenario': test_scenario['name'],
                'execution_time': execution_time,
                'response_content': real_result.get('content', ''),
                'response_length': len(real_result.get('content', '')),
                'success': True,
                'metadata': real_result.get('metadata', {}),
                'predictable': False,
                'cost': estimated_cost,
                'tokens_estimated': estimated_tokens,
                'oracle_enhanced_version': '2.1.0'
            }
            
        except Exception as e:
            return {
                'type': 'real',
                'scenario': test_scenario['name'],
                'execution_time': time.time() - start_time,
                'success': False,
                'error': str(e),
                'predictable': False,
                'cost': estimated_cost,
                'oracle_enhanced_version': '2.1.0'
            }
    
    def _create_mock_kernel(self) -> Mock:
        """Crée un kernel mocké Oracle Enhanced v2.1.0."""
        kernel = Mock(spec=Kernel)
        kernel.add_service = Mock()
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.service_id = "mock-gpt4o-mini-v2.1.0"
        mock_service.ai_model_id = "gpt-4o-mini"
        
        # Réponses mock intelligentes Oracle Enhanced v2.1.0
        async def mock_chat_completion(chat_history=None, settings=None):
            await asyncio.sleep(0.1)  # Simulation latence
            
            if chat_history and len(chat_history) > 0:
                user_input = chat_history[-1].content.lower()
                
                mock_responses = {
                    'moriarty': "En tant que Moriarty Oracle Enhanced v2.1.0, je révèle que j'ai la carte Colonel Moutarde ! Cette révélation devrait faire avancer votre enquête.",
                    'sherlock': "En tant que Sherlock Holmes (Oracle Enhanced v2.1.0), j'examine méthodiquement les indices. L'analyse des preuves suggère plusieurs pistes d'investigation.",
                    'watson': "En tant que Dr Watson (Oracle Enhanced v2.1.0), j'applique la logique déductive. Les faits observés permettent de tirer certaines conclusions.",
                    'cluedo': "Dans cette enquête Cluedo Oracle Enhanced v2.1.0, analysons systématiquement les suspects, armes et lieux possibles.",
                    'einstein': "Pour ce puzzle Einstein (Oracle Enhanced v2.1.0), procédons par élimination logique en utilisant les contraintes données."
                }
                
                for key, response in mock_responses.items():
                    if key in user_input:
                        mock_msg = Mock()
                        mock_msg.content = response
                        return [mock_msg]
            
            # Réponse par défaut Oracle Enhanced v2.1.0
            mock_msg = Mock()
            mock_msg.content = "Réponse mock Oracle Enhanced v2.1.0 pour test de comparaison."
            return [mock_msg]
        
        mock_service.get_chat_message_contents = mock_chat_completion
        kernel.get_service = Mock(return_value=mock_service)
        
        return kernel
    
    def _create_real_kernel(self):
        """Crée un kernel réel GPT-4o-mini Oracle Enhanced v2.1.0."""
        kernel = Kernel()
        
        chat_service = OpenAIChatCompletion(
            service_id="comparison-real-gpt-v2.1.0",
            ai_model_id="gpt-4o-mini",
            api_key=OPENAI_API_KEY
        )
        
        kernel.add_service(chat_service)
        return kernel
    
    async def _simulate_mock_execution(self, orchestrator, scenario) -> Dict[str, Any]:
        """Simule l'exécution avec orchestrateur mocké Oracle Enhanced v2.1.0."""
        # Configuration du workflow (simulation)
        elements_jeu = scenario.get('elements_jeu', {
            "suspects": ["Colonel Moutarde", "Professeur Violet"],
            "armes": ["Poignard", "Chandelier"],
            "lieux": ["Salon", "Cuisine"]
        })
        
        # Simulation de setup
        await asyncio.sleep(0.1)
        
        # Simulation de requête Oracle Enhanced v2.1.0
        mock_content = f"Mock Oracle Enhanced v2.1.0: Simulation réussie pour {scenario['name']}"
        
        if 'moriarty' in scenario.get('prompt', '').lower():
            mock_content = "Mock Moriarty Oracle Enhanced v2.1.0: Je révèle automatiquement la carte Colonel Moutarde!"
        elif 'sherlock' in scenario.get('prompt', '').lower():
            mock_content = "Mock Sherlock Oracle Enhanced v2.1.0: J'enquête sur les suspects avec méthode."
        elif 'watson' in scenario.get('prompt', '').lower():
            mock_content = "Mock Watson Oracle Enhanced v2.1.0: J'analyse les preuves logiquement."
        
        return {
            'content': mock_content,
            'metadata': {
                'mock_behavior': True,
                'deterministic': True,
                'scenario_specific': True,
                'oracle_enhanced_version': '2.1.0'
            }
        }
    
    async def _simulate_basic_mock_execution(self, scenario) -> Dict[str, Any]:
        """Simulation basique sans orchestrateur Oracle Enhanced v2.1.0."""
        await asyncio.sleep(0.05)
        
        return {
            'content': f"Mock basic Oracle Enhanced v2.1.0 response for {scenario['name']}",
            'metadata': {
                'basic_mock': True,
                'oracle_enhanced_version': '2.1.0'
            }
        }
    
    async def _execute_real_gpt_scenario(self, orchestrator, scenario) -> Dict[str, Any]:
        """Exécute un scénario réel avec GPT-4o-mini Oracle Enhanced v2.1.0."""
        # Rate limiting
        await asyncio.sleep(0.2)
        
        # Setup workflow réel Oracle Enhanced v2.1.0
        elements_jeu = scenario.get('elements_jeu', {
            "suspects": ["Colonel Moutarde", "Professeur Violet"],
            "armes": ["Poignard", "Chandelier"],
            "lieux": ["Salon", "Cuisine"]
        })
        
        oracle_state = await orchestrator.setup_workflow(
            nom_enquete="Comparison Test Oracle Enhanced v2.1.0",
            elements_jeu=elements_jeu
        )
        
        # Exécution de requête Oracle réelle v2.1.0
        prompt = scenario.get('prompt', 'Test de comparaison Oracle Enhanced v2.1.0')
        
        result = await oracle_state.query_oracle(
            agent_name="ComparisonTest",
            query_type="comparison_test",
            query_params={'prompt': prompt}
        )
        
        content = getattr(result, 'content', str(result)) if result else "No response"
        
        return {
            'content': content,
            'metadata': {
                'real_gpt': True,
                'deterministic': False,
                'oracle_enhanced': True,
                'oracle_enhanced_version': '2.1.0'
            }
        }
    
    async def _execute_basic_real_scenario(self, kernel, scenario) -> Dict[str, Any]:
        """Exécution basique avec GPT réel Oracle Enhanced v2.1.0."""
        chat_service = kernel.get_service("comparison-real-gpt-v2.1.0")
        
        settings = OpenAIChatPromptExecutionSettings(
            max_tokens=150,
            temperature=0.3
        )
        
        prompt = scenario.get('prompt', 'Test de comparaison Oracle Enhanced v2.1.0')
        messages = [ChatMessageContent(role="user", content=prompt)]
        
        response = await chat_service.get_chat_message_contents(
            chat_history=messages,
            settings=settings
        )
        
        content = response[0].content if response and len(response) > 0 else "No response"
        
        return {
            'content': content,
            'metadata': {
                'basic_real': True,
                'oracle_enhanced_version': '2.1.0'
            }
        }
    
    def compare_results(self, mock_result: Dict[str, Any], real_result: Dict[str, Any]) -> Dict[str, Any]:
        """Compare les résultats mock vs réel Oracle Enhanced v2.1.0."""
        if not mock_result['success'] or not real_result['success']:
            return {
                'comparison_valid': False,
                'mock_success': mock_result['success'],
                'real_success': real_result['success'],
                'reason': 'One or both tests failed',
                'oracle_enhanced_version': '2.1.0'
            }
        
        # Métriques de comparaison Oracle Enhanced v2.1.0
        comparison = {
            'comparison_valid': True,
            'scenario': mock_result['scenario'],
            'oracle_enhanced_version': '2.1.0',
            
            # Performance
            'execution_time_ratio': real_result['execution_time'] / max(mock_result['execution_time'], 0.001),
            'mock_faster': mock_result['execution_time'] < real_result['execution_time'],
            
            # Contenu
            'content_length_ratio': real_result['response_length'] / max(mock_result['response_length'], 1),
            'real_more_verbose': real_result['response_length'] > mock_result['response_length'],
            
            # Cohérence
            'content_similarity': self._calculate_content_similarity(
                mock_result['response_content'],
                real_result['response_content']
            ),
            
            # Coût
            'cost_difference': real_result['cost'] - mock_result['cost'],
            'cost_per_char': real_result['cost'] / max(real_result['response_length'], 1),
            
            # Prévisibilité
            'predictability_difference': mock_result['predictable'] and not real_result['predictable'],
            
            # Qualité Oracle Enhanced v2.1.0
            'mock_quality_score': self._assess_response_quality(mock_result['response_content']),
            'real_quality_score': self._assess_response_quality(real_result['response_content']),
        }
        
        comparison['quality_advantage'] = comparison['real_quality_score'] - comparison['mock_quality_score']
        comparison['overall_assessment'] = self._overall_assessment(comparison)
        
        return comparison
    
    def _calculate_content_similarity(self, mock_content: str, real_content: str) -> float:
        """Calcule la similarité de contenu Oracle Enhanced v2.1.0."""
        if not mock_content or not real_content:
            return 0.0
        
        # Mots communs (simple)
        mock_words = set(mock_content.lower().split())
        real_words = set(real_content.lower().split())
        
        intersection = mock_words.intersection(real_words)
        union = mock_words.union(real_words)
        
        return len(intersection) / max(len(union), 1)
    
    def _assess_response_quality(self, content: str) -> float:
        """Évalue la qualité d'une réponse Oracle Enhanced v2.1.0."""
        if not content:
            return 0.0
        
        quality_score = 0.0
        
        # Longueur appropriée
        if 30 <= len(content) <= 500:
            quality_score += 0.3
        
        # Mots-clés pertinents Oracle Enhanced v2.1.0
        relevant_keywords = ['révèle', 'enquête', 'analyse', 'indice', 'déduction', 'logique', 'oracle', 'enhanced']
        keyword_count = sum(1 for keyword in relevant_keywords if keyword in content.lower())
        quality_score += min(keyword_count * 0.1, 0.3)
        
        # Structure (phrases complètes)
        sentence_count = content.count('.') + content.count('!') + content.count('?')
        if sentence_count >= 1:
            quality_score += 0.2
        
        # Pas de mots vagues
        vague_words = ['peut-être', 'probablement', 'je pense', 'sans doute']
        if not any(word in content.lower() for word in vague_words):
            quality_score += 0.2
        
        return min(quality_score, 1.0)
    
    def _overall_assessment(self, comparison: Dict[str, Any]) -> str:
        """Évaluation globale de la comparaison Oracle Enhanced v2.1.0."""
        if comparison['content_similarity'] > 0.7:
            return "high_similarity"
        elif comparison['quality_advantage'] > 0.3:
            return "real_quality_advantage"
        elif comparison['mock_faster'] and comparison['content_similarity'] > 0.4:
            return "mock_efficiency_advantage"
        elif comparison['cost_difference'] > 0.01:
            return "cost_consideration_needed"
        else:
            return "balanced_tradeoff"


@pytest.fixture
def behavior_comparator():
    """Fixture du comparateur de comportements Oracle Enhanced v2.1.0."""
    return BehaviorComparator()


@pytest.fixture
def comparison_test_scenarios():
    """Scénarios de test pour comparaison Oracle Enhanced v2.1.0."""
    return [
        {
            'name': 'moriarty_revelation_v2.1.0',
            'prompt': 'En tant que Moriarty Oracle Enhanced v2.1.0, révélez dramatiquement que vous avez la carte Colonel Moutarde.',
            'max_turns': 2,
            'expected_behaviors': ['révélation', 'dramatique', 'Colonel Moutarde', 'oracle', 'enhanced']
        },
        {
            'name': 'sherlock_investigation_v2.1.0',
            'prompt': 'En tant que Sherlock Holmes Oracle Enhanced v2.1.0, enquêtez sur cette affaire Cluedo.',
            'max_turns': 3,
            'expected_behaviors': ['enquête', 'méthode', 'indices', 'oracle', 'enhanced']
        },
        {
            'name': 'watson_analysis_v2.1.0',
            'prompt': 'En tant que Watson Oracle Enhanced v2.1.0, analysez logiquement les preuves disponibles.',
            'max_turns': 2,
            'expected_behaviors': ['analyse', 'logique', 'preuves', 'oracle', 'enhanced']
        },
        {
            'name': 'oracle_enhanced_workflow_v2.1.0',
            'prompt': 'Exécutez un workflow Oracle Enhanced v2.1.0 complet.',
            'max_turns': 4,
            'elements_jeu': {
                "suspects": ["Colonel Moutarde", "Professeur Violet"],
                "armes": ["Poignard", "Chandelier"],
                "lieux": ["Salon", "Cuisine"]
            },
            'expected_behaviors': ['oracle', 'enhanced', 'workflow', 'v2.1.0']
        }
    ]


@pytest.mark.comparison
@pytest.mark.skipif(not COMPARISON_TESTS_ENABLED, reason="Tests de comparaison désactivés")
class TestMockVsRealComparison:
    """Tests de comparaison Mock vs Réel Oracle Enhanced v2.1.0."""
    
    @pytest.mark.asyncio
    async def test_individual_scenario_comparison(self, behavior_comparator, comparison_test_scenarios):
        """Test la comparaison pour chaque scénario individuellement Oracle Enhanced v2.1.0."""
        comparison_results = []
        
        for scenario in comparison_test_scenarios:
            # Test Mock
            mock_result = await behavior_comparator.test_mock_behavior(scenario)
            
            # Test Réel (si disponible)
            real_result = await behavior_comparator.test_real_behavior(scenario)
            
            # Comparaison
            if mock_result['success'] and real_result['success']:
                comparison = behavior_comparator.compare_results(mock_result, real_result)
                comparison_results.append(comparison)
                
                # Vérifications spécifiques Oracle Enhanced v2.1.0
                assert comparison['comparison_valid'], f"Comparaison invalide pour {scenario['name']}"
                assert comparison['execution_time_ratio'] > 0, "Ratio temps d'exécution invalide"
                assert 0 <= comparison['content_similarity'] <= 1, "Similarité de contenu hors limites"
                assert comparison['mock_quality_score'] >= 0, "Score qualité mock négatif"
                assert comparison['real_quality_score'] >= 0, "Score qualité réel négatif"
                assert comparison['oracle_enhanced_version'] == '2.1.0', "Version Oracle Enhanced incorrecte"
        
        # Analyse globale
        assert len(comparison_results) > 0, "Aucune comparaison valide effectuée"
        
        # Métriques globales Oracle Enhanced v2.1.0
        avg_similarity = statistics.mean([c['content_similarity'] for c in comparison_results])
        avg_quality_advantage = statistics.mean([c['quality_advantage'] for c in comparison_results])
        mock_speed_advantage = sum(1 for c in comparison_results if c['mock_faster']) / len(comparison_results)
        
        print(f"\n=== RÉSULTATS COMPARAISON MOCK VS RÉEL Oracle Enhanced v2.1.0 ===")
        print(f"Similarité moyenne: {avg_similarity:.3f}")
        print(f"Avantage qualité réel: {avg_quality_advantage:.3f}")
        print(f"Avantage vitesse mock: {mock_speed_advantage:.1%}")
        
        # Assertions sur les attentes
        assert avg_similarity >= 0.3, f"Similarité trop faible: {avg_similarity}"
        assert mock_speed_advantage >= 0.8, f"Mocks pas assez rapides: {mock_speed_advantage}"
    
    @pytest.mark.asyncio
    async def test_oracle_enhanced_consistency(self, behavior_comparator):
        """Test la cohérence Oracle Enhanced v2.1.0 entre mock et réel."""
        oracle_scenario = {
            'name': 'oracle_consistency_test_v2.1.0',
            'prompt': 'Test de cohérence Oracle Enhanced v2.1.0 avec révélation automatique.',
            'max_turns': 3,
            'expected_behaviors': ['oracle', 'enhanced', 'révélation', 'automatique', 'v2.1.0']
        }
        
        # Tests multiples pour vérifier la cohérence
        mock_results = []
        real_results = []
        
        for i in range(3):  # 3 exécutions
            mock_result = await behavior_comparator.test_mock_behavior(oracle_scenario)
            mock_results.append(mock_result)
            
            if REAL_GPT_AVAILABLE:
                real_result = await behavior_comparator.test_real_behavior(oracle_scenario)
                real_results.append(real_result)
                
                # Délai entre appels réels
                await asyncio.sleep(0.5)
        
        # Vérifications de cohérence Mock Oracle Enhanced v2.1.0
        mock_contents = [r['response_content'] for r in mock_results if r['success']]
        if len(mock_contents) > 1:
            # Les mocks devraient être très cohérents
            mock_similarities = [
                behavior_comparator._calculate_content_similarity(mock_contents[0], content)
                for content in mock_contents[1:]
            ]
            avg_mock_consistency = statistics.mean(mock_similarities)
            assert avg_mock_consistency >= 0.8, f"Mocks pas assez cohérents: {avg_mock_consistency}"
        
        # Vérifications de cohérence Réel Oracle Enhanced v2.1.0
        real_contents = [r['response_content'] for r in real_results if r['success']]
        if len(real_contents) > 1:
            # Les réels peuvent être moins cohérents (créativité)
            real_similarities = [
                behavior_comparator._calculate_content_similarity(real_contents[0], content)
                for content in real_contents[1:]
            ]
            avg_real_consistency = statistics.mean(real_similarities)
            assert avg_real_consistency >= 0.3, f"Réels incohérents: {avg_real_consistency}"
            
            # Mais devraient garder une cohérence Oracle Enhanced v2.1.0
            oracle_keywords = ['oracle', 'enhanced', 'révèle', 'indice', 'v2.1.0']
            for content in real_contents:
                oracle_relevance = sum(1 for kw in oracle_keywords if kw in content.lower())
                assert oracle_relevance >= 1, f"Contenu réel pas assez Oracle v2.1.0: {content[:100]}"
    
    @pytest.mark.asyncio
    async def test_performance_vs_quality_tradeoff(self, behavior_comparator, comparison_test_scenarios):
        """Test l'équilibre performance vs qualité Oracle Enhanced v2.1.0."""
        tradeoff_analysis = {
            'scenarios_tested': 0,
            'mock_faster_count': 0,
            'real_better_quality_count': 0,
            'cost_per_quality_point': [],
            'speed_advantage_ratios': [],
            'oracle_enhanced_version': '2.1.0'
        }
        
        for scenario in comparison_test_scenarios[:2]:  # Limité pour coût
            mock_result = await behavior_comparator.test_mock_behavior(scenario)
            real_result = await behavior_comparator.test_real_behavior(scenario)
            
            if mock_result['success'] and real_result['success']:
                comparison = behavior_comparator.compare_results(mock_result, real_result)
                
                tradeoff_analysis['scenarios_tested'] += 1
                
                if comparison['mock_faster']:
                    tradeoff_analysis['mock_faster_count'] += 1
                    tradeoff_analysis['speed_advantage_ratios'].append(comparison['execution_time_ratio'])
                
                if comparison['quality_advantage'] > 0:
                    tradeoff_analysis['real_better_quality_count'] += 1
                    
                    if real_result['cost'] > 0:
                        cost_per_quality = real_result['cost'] / comparison['quality_advantage']
                        tradeoff_analysis['cost_per_quality_point'].append(cost_per_quality)
        
        # Analyses des équilibres Oracle Enhanced v2.1.0
        if tradeoff_analysis['scenarios_tested'] > 0:
            mock_speed_rate = tradeoff_analysis['mock_faster_count'] / tradeoff_analysis['scenarios_tested']
            real_quality_rate = tradeoff_analysis['real_better_quality_count'] / tradeoff_analysis['scenarios_tested']
            
            print(f"\n=== ANALYSE PERFORMANCE VS QUALITÉ Oracle Enhanced v2.1.0 ===")
            print(f"Taux avantage vitesse mock: {mock_speed_rate:.1%}")
            print(f"Taux avantage qualité réel: {real_quality_rate:.1%}")
            
            if tradeoff_analysis['speed_advantage_ratios']:
                avg_speed_advantage = statistics.mean(tradeoff_analysis['speed_advantage_ratios'])
                print(f"Ratio vitesse moyen: {avg_speed_advantage:.2f}x")
            
            if tradeoff_analysis['cost_per_quality_point']:
                avg_cost_per_quality = statistics.mean(tradeoff_analysis['cost_per_quality_point'])
                print(f"Coût moyen par point qualité: ${avg_cost_per_quality:.4f}")
            
            # Assertions sur l'équilibre
            assert mock_speed_rate >= 0.7, f"Mocks pas assez rapides: {mock_speed_rate:.1%}"
            
            if real_quality_rate > 0.5:
                print("✅ GPT réel montre un avantage qualité significatif Oracle Enhanced v2.1.0")
            else:
                print("ℹ️ Mocks compétitifs en qualité Oracle Enhanced v2.1.0")


@pytest.mark.comparison
class TestComparisonMetrics:
    """Tests des métriques de comparaison Oracle Enhanced v2.1.0."""
    
    def test_content_similarity_calculation(self, behavior_comparator):
        """Test le calcul de similarité de contenu Oracle Enhanced v2.1.0."""
        test_cases = [
            {
                'mock': "Mock Moriarty Oracle Enhanced v2.1.0 révèle la carte Colonel Moutarde",
                'real': "En tant que Moriarty Oracle Enhanced v2.1.0, je révèle que j'ai la carte Colonel Moutarde!",
                'expected_similarity': 0.6  # Approximatif
            },
            {
                'mock': "Réponse mock Oracle Enhanced v2.1.0 générique",
                'real': "Réponse réelle Oracle Enhanced v2.1.0 spécifique et détaillée",
                'expected_similarity': 0.2  # Faible
            },
            {
                'mock': "Test Oracle Enhanced v2.1.0 identique",
                'real': "Test Oracle Enhanced v2.1.0 identique",
                'expected_similarity': 1.0  # Parfait
            }
        ]
        
        for case in test_cases:
            similarity = behavior_comparator._calculate_content_similarity(
                case['mock'], 
                case['real']
            )
            
            assert 0 <= similarity <= 1, f"Similarité hors limites: {similarity}"
            
            # Tolérance sur l'estimation
            if case['expected_similarity'] == 1.0:
                assert similarity == 1.0, f"Textes identiques mal calculés: {similarity}"
            else:
                # Pour les autres cas, vérifier l'ordre de grandeur
                assert abs(similarity - case['expected_similarity']) < 0.4, \
                    f"Similarité inattendue: {similarity} vs {case['expected_similarity']}"
    
    def test_quality_assessment(self, behavior_comparator):
        """Test l'évaluation de qualité Oracle Enhanced v2.1.0."""
        quality_test_cases = [
            {
                'content': "En tant que Moriarty Oracle Enhanced v2.1.0, je révèle dramatiquement que j'ai la carte Colonel Moutarde! Cette révélation devrait faire avancer votre enquête.",
                'expected_high_quality': True
            },
            {
                'content': "Peut-être que c'est probablement quelqu'un...",
                'expected_high_quality': False
            },
            {
                'content': "Analyse logique des indices disponibles Oracle Enhanced v2.1.0. Déduction méthodique.",
                'expected_high_quality': True
            },
            {
                'content': "Réponse très courte",
                'expected_high_quality': False
            }
        ]
        
        for case in quality_test_cases:
            quality_score = behavior_comparator._assess_response_quality(case['content'])
            
            assert 0 <= quality_score <= 1, f"Score qualité hors limites: {quality_score}"
            
            if case['expected_high_quality']:
                assert quality_score >= 0.5, f"Qualité élevée mal évaluée: {quality_score} pour '{case['content'][:50]}...'"
            else:
                assert quality_score <= 0.6, f"Qualité faible mal évaluée: {quality_score} pour '{case['content'][:50]}...'"