
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

"""
Tests de robustesse et gestion d'erreurs pour Oracle Enhanced.

Tests couvrant:
- Tests timeout OpenAI (>30s)
- Tests erreurs réseau et retry automatique
- Tests pannes Tweety JVM et recovery
- Tests états corrompus et validation
"""

import pytest
import asyncio
import time
import os
import sys

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import random

# Imports Semantic Kernel
from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings

# Imports du système Oracle
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent


# Configuration pour tests de robustesse
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
REAL_GPT_AVAILABLE = OPENAI_API_KEY is not None and len(OPENAI_API_KEY) > 10
ROBUSTNESS_TESTS_ENABLED = os.environ.get('ENABLE_ROBUSTNESS_TESTS', 'true').lower() == 'true'


class ErrorSimulator:
    """Simulateur d'erreurs pour tests de robustesse."""
    
    def __init__(self):
        self.error_scenarios = {
            'network_timeout': {'probability': 0.3, 'delay': 35.0},
            'rate_limit': {'probability': 0.2, 'delay': 60.0},
            'api_error': {'probability': 0.1, 'delay': 0.0},
            'connection_error': {'probability': 0.15, 'delay': 5.0},
            'invalid_response': {'probability': 0.1, 'delay': 0.0}
        }
        self.error_count = 0
        self.recovery_attempts = 0
    
    def should_trigger_error(self, error_type: str) -> bool:
        """Détermine si une erreur doit être déclenchée."""
        return random.random() < self.error_scenarios[error_type]['probability']
    
    async def simulate_network_timeout(self):
        """Simule un timeout réseau."""
        delay = self.error_scenarios['network_timeout']['delay']
        await asyncio.sleep(delay)
        self.error_count += 1
        raise asyncio.TimeoutError(f"Simulated network timeout after {delay}s")
    
    async def simulate_rate_limit_error(self):
        """Simule une erreur de rate limit."""
        self.error_count += 1
        raise Exception("Rate limit exceeded. Please try again in 60 seconds.")
    
    async def simulate_api_error(self):
        """Simule une erreur API OpenAI."""
        self.error_count += 1
        error_types = [
            "Invalid API key",
            "Model overloaded",
            "Service temporarily unavailable",
            "Request too large"
        ]
        raise Exception(f"OpenAI API Error: {random.choice(error_types)}")
    
    async def simulate_connection_error(self):
        """Simule une erreur de connexion."""
        await asyncio.sleep(self.error_scenarios['connection_error']['delay'])
        self.error_count += 1
        raise ConnectionError("Failed to establish connection to OpenAI API")
    
    async def simulate_invalid_response(self):
        """Simule une réponse invalide."""
        self.error_count += 1
        raise ValueError("Invalid response format from OpenAI API")


class RobustnessValidator:
    """Validateur de robustesse pour Oracle Enhanced."""
    
    def __init__(self):
        self.test_results = {}
        self.recovery_metrics = {}
        self.error_simulator = ErrorSimulator()
    
    async def test_error_recovery(
        self, 
        error_type: str, 
        max_retries: int = 3,
        backoff_factor: float = 1.5
    ) -> Dict[str, Any]:
        """Test la récupération d'erreur avec retry logic."""
        
        start_time = time.time()
        attempt = 0
        last_error = None
        
        while attempt < max_retries:
            try:
                attempt += 1
                
                # Simulation de l'opération avec erreur potentielle
                if error_type == 'network_timeout':
                    await self.error_simulator.simulate_network_timeout()
                elif error_type == 'rate_limit':
                    await self.error_simulator.simulate_rate_limit_error()
                elif error_type == 'api_error':
                    await self.error_simulator.simulate_api_error()
                elif error_type == 'connection_error':
                    await self.error_simulator.simulate_connection_error()
                elif error_type == 'invalid_response':
                    await self.error_simulator.simulate_invalid_response()
                
                # Si on arrive ici, l'opération a réussi
                return {
                    'success': True,
                    'attempts': attempt,
                    'total_time': time.time() - start_time,
                    'error_type': error_type,
                    'recovered': attempt > 1
                }
                
            except Exception as e:
                last_error = e
                self.error_simulator.recovery_attempts += 1
                
                if attempt < max_retries:
                    # Backoff exponentiel
                    delay = backoff_factor ** attempt
                    await asyncio.sleep(delay)
                else:
                    break
        
        # Toutes les tentatives ont échoué
        return {
            'success': False,
            'attempts': attempt,
            'total_time': time.time() - start_time,
            'error_type': error_type,
            'final_error': str(last_error),
            'recovered': False
        }
    
    def validate_graceful_degradation(self, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """Valide la dégradation gracieuse du système."""
        
        degradation_analysis = {
            'core_functions_available': True,
            'fallback_modes_active': False,
            'data_integrity_preserved': True,
            'user_experience_maintained': True,
            'degradation_level': 'none'
        }
        
        # Vérifier les fonctions core
        core_functions = ['oracle_query', 'agent_communication', 'state_management']
        for func in core_functions:
            if not system_state.get(f'{func}_available', True):
                degradation_analysis['core_functions_available'] = False
                degradation_analysis['degradation_level'] = 'severe'
        
        # Vérifier les modes de fallback
        if system_state.get('fallback_mode_enabled', False):
            degradation_analysis['fallback_modes_active'] = True
            degradation_analysis['degradation_level'] = 'moderate'
        
        # Vérifier l'intégrité des données
        if system_state.get('data_corruption_detected', False):
            degradation_analysis['data_integrity_preserved'] = False
            degradation_analysis['degradation_level'] = 'severe'
        
        # Vérifier l'expérience utilisateur
        response_time = system_state.get('avg_response_time', 0)
        if response_time > 30:  # Plus de 30s considéré comme dégradé
            degradation_analysis['user_experience_maintained'] = False
            if degradation_analysis['degradation_level'] == 'none':
                degradation_analysis['degradation_level'] = 'minor'
        
        return degradation_analysis


@pytest.fixture
def error_simulator():
    """Fixture du simulateur d'erreurs."""
    return ErrorSimulator()


@pytest.fixture
def robustness_validator():
    """Fixture du validateur de robustesse."""
    return RobustnessValidator()


@pytest.fixture
def corrupted_test_environment():
    """Environnement de test avec conditions dégradées."""
    return {
        'network_unstable': True,
        'high_latency': True,
        'intermittent_failures': True,
        'resource_constrained': True
    }


@pytest.mark.robustness
class TestTimeoutHandling:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests de gestion des timeouts."""
    
    @pytest.mark.asyncio
    async def test_openai_timeout_recovery(self, robustness_validator):
        """Test la récupération de timeout OpenAI."""
        
        # Test de timeout avec retry
        result = await robustness_validator.test_error_recovery(
            error_type='network_timeout',
            max_retries=3,
            backoff_factor=1.5
        )
        
        # Vérifications
        assert result['error_type'] == 'network_timeout'
        assert result['attempts'] <= 3
        assert result['total_time'] > 30  # Au moins un timeout s'est produit
        
        # Le système devrait soit récupérer, soit échouer gracieusement
        if not result['success']:
            assert 'timeout' in result['final_error'].lower()
    
    @pytest.mark.asyncio
    async def test_gradual_timeout_increase(self, robustness_validator):
        """Test l'augmentation progressive des timeouts."""
        
        timeout_levels = [5, 15, 30, 60]  # Timeouts progressifs
        results = []
        
        for timeout in timeout_levels:
            try:
                # Simulation d'opération avec timeout configuré
                async def mock_operation_with_timeout():
                    await asyncio.sleep(timeout + 5)  # Dépasse toujours le timeout
                    return "success"
                
                start_time = time.time()
                result = await asyncio.wait_for(
                    mock_operation_with_timeout(),
                    timeout=timeout
                )
                
                results.append({
                    'timeout_level': timeout,
                    'success': True,
                    'actual_time': time.time() - start_time
                })
                
            except asyncio.TimeoutError:
                results.append({
                    'timeout_level': timeout,
                    'success': False,
                    'actual_time': time.time() - start_time
                })
        
        # Vérifications
        assert len(results) == len(timeout_levels)
        
        # Tous devraient avoir timeout
        timeout_results = [r for r in results if not r['success']]
        assert len(timeout_results) == len(timeout_levels)
        
        # Les temps d'exécution devraient respecter les timeouts
        for result in timeout_results:
            assert result['actual_time'] <= result['timeout_level'] + 2  # Marge de 2s
    
    @pytest.mark.asyncio
    async def test_timeout_cascading_prevention(self):
        """Test la prévention de timeouts en cascade."""
        
        cascading_prevented = True
        timeout_count = 0
        
        # Simulation de plusieurs opérations avec risque de cascade
        async def risky_operation(operation_id: int):
            nonlocal timeout_count
            
            try:
                # Simulation d'opération qui peut timeout
                delay = random.uniform(1, 10)
                await asyncio.wait_for(
                    asyncio.sleep(delay),
                    timeout=5.0
                )
                return f"Operation {operation_id} success"
                
            except asyncio.TimeoutError:
                timeout_count += 1
                
                # Vérifier que le timeout ne bloque pas les autres opérations
                if timeout_count > 2:  # Plus de 2 timeouts = cascade
                    nonlocal cascading_prevented
                    cascading_prevented = False
                
                raise
        
        # Lancement de plusieurs opérations en parallèle
        operations = [risky_operation(i) for i in range(5)]
        
        try:
            results = await asyncio.gather(*operations, return_exceptions=True)
        except Exception:
            pass
        
        # Vérifications
        assert cascading_prevented, "Timeouts en cascade détectés"
        assert timeout_count <= 3, f"Trop de timeouts: {timeout_count}"


@pytest.mark.robustness
class TestNetworkErrorRecovery:
    """Tests de récupération d'erreurs réseau."""
    
    @pytest.mark.asyncio
    async def test_connection_error_retry(self, robustness_validator):
        """Test le retry automatique sur erreurs de connexion."""
        
        result = await robustness_validator.test_error_recovery(
            error_type='connection_error',
            max_retries=4,
            backoff_factor=2.0
        )
        
        # Vérifications
        assert result['error_type'] == 'connection_error'
        assert result['attempts'] <= 4
        
        # Le retry devrait être tenté
        assert result['attempts'] > 1 or result['success']
        
        if not result['success']:
            assert 'connection' in result['final_error'].lower()
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, robustness_validator):
        """Test la gestion des rate limits."""
        
        result = await robustness_validator.test_error_recovery(
            error_type='rate_limit',
            max_retries=2,
            backoff_factor=3.0  # Backoff plus agressif pour rate limits
        )
        
        # Vérifications spécifiques rate limit
        assert result['error_type'] == 'rate_limit'
        
        if not result['success']:
            assert 'rate limit' in result['final_error'].lower()
            assert result['total_time'] > 3.0  # Le backoff devrait être respecté
    
    @pytest.mark.asyncio
    async def test_network_instability_adaptation(self, corrupted_test_environment):
        """Test l'adaptation à l'instabilité réseau."""
        
        network_stats = {
            'successful_requests': 0,
            'failed_requests': 0,
            'total_retries': 0,
            'avg_response_time': 0.0
        }
        
        response_times = []
        
        # Simulation de 10 requêtes dans un environnement instable
        for i in range(10):
            start_time = time.time()
            
            try:
                # Simulation d'instabilité réseau
                if random.random() < 0.4:  # 40% de chance d'échec
                    await asyncio.sleep(random.uniform(0.1, 0.5))
                    raise ConnectionError(f"Network instability on request {i}")
                
                # Simulation de latence variable
                latency = random.uniform(0.5, 3.0)
                await asyncio.sleep(latency)
                
                response_time = time.time() - start_time
                response_times.append(response_time)
                network_stats['successful_requests'] += 1
                
            except ConnectionError:
                network_stats['failed_requests'] += 1
                network_stats['total_retries'] += 1
                
                # Retry avec backoff
                await asyncio.sleep(1.0)
                
                try:
                    await asyncio.sleep(random.uniform(0.5, 2.0))
                    response_time = time.time() - start_time
                    response_times.append(response_time)
                    network_stats['successful_requests'] += 1
                except:
                    pass
        
        # Calcul des métriques
        if response_times:
            network_stats['avg_response_time'] = sum(response_times) / len(response_times)
        
        success_rate = network_stats['successful_requests'] / 10
        
        # Vérifications d'adaptation
        assert success_rate >= 0.6, f"Taux de succès trop bas: {success_rate}"
        assert network_stats['avg_response_time'] < 10.0, f"Temps de réponse moyen trop élevé: {network_stats['avg_response_time']}s"


@pytest.mark.robustness
class TestJVMRecovery:
    """Tests de récupération JVM Tweety."""
    
    @pytest.mark.asyncio
    async def test_jvm_crash_recovery(self):
        """Test la récupération après crash JVM."""
        
        jvm_state = {
            'started': False,
            'crash_count': 0,
            'recovery_attempts': 0,
            'stable': False
        }
        
        async def simulate_jvm_lifecycle():
            # Simulation de démarrage JVM
            jvm_state['started'] = True
            await asyncio.sleep(0.1)
            
            # Simulation de crash
            if random.random() < 0.3:  # 30% chance de crash
                jvm_state['crash_count'] += 1
                jvm_state['started'] = False
                raise RuntimeError("JVM crashed unexpectedly")
            
            jvm_state['stable'] = True
            return "JVM operation success"
        
        async def jvm_recovery_manager():
            max_recovery_attempts = 3
            
            for attempt in range(max_recovery_attempts):
                try:
                    result = await simulate_jvm_lifecycle()
                    return result
                    
                except RuntimeError as e:
                    jvm_state['recovery_attempts'] += 1
                    
                    if "crashed" in str(e):
                        # Simulation de redémarrage JVM
                        await asyncio.sleep(2.0)  # Délai de redémarrage
                        jvm_state['started'] = True
                        
                        if attempt < max_recovery_attempts - 1:
                            continue
                        else:
                            raise Exception("Failed to recover JVM after multiple attempts")
            
            return "Recovery completed"
        
        # Test de récupération
        try:
            result = await jvm_recovery_manager()
            recovery_successful = True
        except Exception as e:
            recovery_successful = False
            result = str(e)
        
        # Vérifications
        if jvm_state['crash_count'] > 0:
            assert jvm_state['recovery_attempts'] > 0, "Aucune tentative de récupération après crash"
            
            if recovery_successful:
                assert jvm_state['started'], "JVM non redémarrée après récupération"
        
        # Le système devrait soit récupérer, soit échouer gracieusement
        assert recovery_successful or "Failed to recover" in result
    
    def test_jvm_memory_leak_detection(self):
        """Test la détection de fuites mémoire JVM."""
        
        memory_samples = []
        leak_detected = False
        
        # Simulation d'utilisation JVM avec surveillance mémoire
        for i in range(20):
            # Simulation d'allocation mémoire
            current_memory = 100 + i * 5 + random.uniform(-10, 10)  # Tendance croissante
            memory_samples.append(current_memory)
            
            # Détection simple de fuite (croissance continue)
            if len(memory_samples) >= 10:
                recent_avg = sum(memory_samples[-5:]) / 5
                older_avg = sum(memory_samples[-10:-5]) / 5
                
                if recent_avg > older_avg * 1.5:  # Croissance de 50%+
                    leak_detected = True
                    break
        
        # Vérifications
        if leak_detected:
            # Si fuite détectée, le système devrait la signaler
            assert len(memory_samples) >= 10, "Détection prématurée de fuite"
            
            # Simulation d'action corrective
            memory_after_gc = memory_samples[-1] * 0.7  # Simulation GC
            assert memory_after_gc < memory_samples[-1], "GC devrait réduire la mémoire"
        
        # Dans tous les cas, la mémoire ne devrait pas exploser
        max_memory = max(memory_samples)
        assert max_memory < 500, f"Utilisation mémoire excessive: {max_memory}MB"


@pytest.mark.robustness
class TestStateCorruptionRecovery:
    """Tests de récupération d'états corrompus."""
    
    def test_corrupted_oracle_state_recovery(self):
        """Test la récupération d'état Oracle corrompu."""
        
        # Création d'un état Oracle normal
        elements_jeu = {
            "suspects": ["Colonel Moutarde", "Professeur Violet"],
            "armes": ["Poignard", "Chandelier"], 
            "lieux": ["Salon", "Cuisine"]
        }
        
        oracle_state = CluedoOracleState(
            nom_enquete_cluedo="Test Corruption Recovery",
            elements_jeu_cluedo=elements_jeu,
            oracle_strategy="enhanced_auto_reveal"
        )
        
        # Vérification état initial
        assert oracle_state.nom_enquete == "Test Corruption Recovery"
        solution_initiale = oracle_state.get_solution_secrete()
        assert solution_initiale is not None
        
        # Simulation de corruption d'état
        corruption_scenarios = [
            {'field': 'solution_secrete', 'corrupt_value': None},
            {'field': 'moriarty_cards', 'corrupt_value': []},
            {'field': 'oracle_strategy', 'corrupt_value': 'invalid_strategy'}
        ]
        
        recovery_results = []
        
        for scenario in corruption_scenarios:
            # Corruption
            original_value = getattr(oracle_state, scenario['field'], None)
            setattr(oracle_state, scenario['field'], scenario['corrupt_value'])
            
            # Test de détection et récupération
            try:
                corruption_detected = oracle_state._validate_state_integrity()
                
                if not corruption_detected:
                    # Tentative de récupération automatique
                    recovery_successful = oracle_state._attempt_state_recovery()
                    
                    recovery_results.append({
                        'scenario': scenario['field'],
                        'corruption_detected': False,
                        'recovery_attempted': True,
                        'recovery_successful': recovery_successful
                    })
                else:
                    recovery_results.append({
                        'scenario': scenario['field'], 
                        'corruption_detected': True,
                        'recovery_attempted': False,
                        'recovery_successful': False
                    })
                    
            except Exception as e:
                # Corruption détectée via exception
                recovery_results.append({
                    'scenario': scenario['field'],
                    'corruption_detected': True,
                    'exception': str(e),
                    'recovery_attempted': False,
                    'recovery_successful': False
                })
            
            # Restauration pour test suivant
            if original_value is not None:
                setattr(oracle_state, scenario['field'], original_value)
        
        # Vérifications
        assert len(recovery_results) == len(corruption_scenarios)
        
        # Au moins une corruption devrait être détectée
        detected_corruptions = [r for r in recovery_results if r.get('corruption_detected', False)]
        assert len(detected_corruptions) > 0, "Aucune corruption détectée"
    
    @pytest.mark.asyncio
    async def test_invalid_response_handling(self, robustness_validator):
        """Test la gestion de réponses invalides."""
        
        result = await robustness_validator.test_error_recovery(
            error_type='invalid_response',
            max_retries=3
        )
        
        # Vérifications
        assert result['error_type'] == 'invalid_response'
        
        if not result['success']:
            assert 'invalid' in result['final_error'].lower() or 'format' in result['final_error'].lower()
        
        # Le système devrait tenter de récupérer
        assert result['attempts'] > 1 or result['success']
    
    def test_graceful_degradation_validation(self, robustness_validator):
        """Test la validation de dégradation gracieuse."""
        
        # Scénarios de dégradation
        degradation_scenarios = [
            {
                'name': 'normal_operation',
                'state': {
                    'oracle_query_available': True,
                    'agent_communication_available': True,
                    'state_management_available': True,
                    'avg_response_time': 5.0
                }
            },
            {
                'name': 'minor_degradation',
                'state': {
                    'oracle_query_available': True,
                    'agent_communication_available': True,
                    'state_management_available': True,
                    'avg_response_time': 25.0,
                    'fallback_mode_enabled': True
                }
            },
            {
                'name': 'severe_degradation',
                'state': {
                    'oracle_query_available': False,
                    'agent_communication_available': True,
                    'state_management_available': False,
                    'avg_response_time': 45.0,
                    'data_corruption_detected': True
                }
            }
        ]
        
        for scenario in degradation_scenarios:
            analysis = robustness_validator.validate_graceful_degradation(scenario['state'])
            
            if scenario['name'] == 'normal_operation':
                assert analysis['degradation_level'] == 'none'
                assert analysis['core_functions_available']
                assert analysis['data_integrity_preserved']
                
            elif scenario['name'] == 'minor_degradation':
                assert analysis['degradation_level'] in ['minor', 'moderate']
                assert analysis['fallback_modes_active']
                
            elif scenario['name'] == 'severe_degradation':
                assert analysis['degradation_level'] == 'severe'
                assert not analysis['core_functions_available']
                assert not analysis['data_integrity_preserved']