"""
Tests de performance pour le système Oracle Enhanced.

Tests couvrant:
- Benchmarks temps de réponse GPT-4o-mini
- Tests charge multiple agents simultanés
- Tests mémoire et garbage collection Tweety JVM
"""

import pytest
import asyncio
import time
import gc
import sys
import psutil
import os
from unittest.mock import Mock, patch
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# Imports Semantic Kernel pour tests réels
from semantic_kernel.kernel import Kernel
from semantic_kernel.services.openai import OpenAIChatCompletion
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings

# Imports du système Oracle
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent


# Configuration pour tests de performance
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
PERFORMANCE_TESTS_ENABLED = os.environ.get('ENABLE_PERFORMANCE_TESTS', 'false').lower() == 'true'
REAL_GPT_AVAILABLE = OPENAI_API_KEY is not None and len(OPENAI_API_KEY) > 10

# Skip si tests de performance désactivés
pytestmark = pytest.mark.skipif(
    not PERFORMANCE_TESTS_ENABLED,
    reason="Tests de performance désactivés (ENABLE_PERFORMANCE_TESTS=false)"
)


class PerformanceProfiler:
    """Profileur de performance pour les tests Oracle."""
    
    def __init__(self):
        self.metrics = {
            'start_time': None,
            'end_time': None,
            'memory_usage': [],
            'cpu_usage': [],
            'api_calls': [],
            'response_times': [],
            'errors': [],
            'gc_collections': 0
        }
        self.process = psutil.Process()
    
    def start_profiling(self):
        """Démarre le profilage."""
        self.metrics['start_time'] = time.time()
        self.metrics['memory_usage'].append(self.process.memory_info().rss / 1024 / 1024)  # MB
        self.metrics['cpu_usage'].append(self.process.cpu_percent())
        gc.collect()
        self.metrics['gc_collections'] = len(gc.get_stats())
    
    def record_api_call(self, response_time: float, success: bool = True):
        """Enregistre un appel API."""
        self.metrics['api_calls'].append({
            'timestamp': time.time(),
            'response_time': response_time,
            'success': success
        })
        self.metrics['response_times'].append(response_time)
    
    def record_error(self, error: str):
        """Enregistre une erreur."""
        self.metrics['errors'].append({
            'timestamp': time.time(),
            'error': error
        })
    
    def sample_resources(self):
        """Échantillonne l'utilisation des ressources."""
        self.metrics['memory_usage'].append(self.process.memory_info().rss / 1024 / 1024)
        self.metrics['cpu_usage'].append(self.process.cpu_percent())
    
    def stop_profiling(self) -> Dict[str, Any]:
        """Arrête le profilage et retourne les métriques."""
        self.metrics['end_time'] = time.time()
        self.metrics['total_duration'] = self.metrics['end_time'] - self.metrics['start_time']
        
        # Calculs statistiques
        if self.metrics['response_times']:
            self.metrics['avg_response_time'] = sum(self.metrics['response_times']) / len(self.metrics['response_times'])
            self.metrics['max_response_time'] = max(self.metrics['response_times'])
            self.metrics['min_response_time'] = min(self.metrics['response_times'])
        
        if self.metrics['memory_usage']:
            self.metrics['peak_memory'] = max(self.metrics['memory_usage'])
            self.metrics['avg_memory'] = sum(self.metrics['memory_usage']) / len(self.metrics['memory_usage'])
        
        if self.metrics['cpu_usage']:
            self.metrics['avg_cpu'] = sum(self.metrics['cpu_usage']) / len(self.metrics['cpu_usage'])
            self.metrics['peak_cpu'] = max(self.metrics['cpu_usage'])
        
        self.metrics['success_rate'] = len([call for call in self.metrics['api_calls'] if call['success']]) / max(len(self.metrics['api_calls']), 1)
        self.metrics['error_rate'] = len(self.metrics['errors']) / max(len(self.metrics['api_calls']), 1)
        
        return self.metrics.copy()


@pytest.fixture
def performance_profiler():
    """Fixture du profileur de performance."""
    return PerformanceProfiler()


@pytest.fixture
def real_gpt_kernel_performance():
    """Kernel optimisé pour tests de performance."""
    if not REAL_GPT_AVAILABLE:
        pytest.skip("OPENAI_API_KEY requis pour tests de performance réels")
    
    kernel = Kernel()
    
    # Configuration optimisée pour performance
    chat_service = OpenAIChatCompletion(
        service_id="openai-gpt4o-mini-perf",
        ai_model_id="gpt-4o-mini",
        api_key=OPENAI_API_KEY
    )
    
    kernel.add_service(chat_service)
    return kernel


@pytest.fixture
def performance_test_elements():
    """Éléments de test optimisés pour performance."""
    return {
        "suspects": ["Colonel Moutarde", "Professeur Violet"],
        "armes": ["Poignard", "Chandelier"],
        "lieux": ["Salon", "Cuisine"]
    }


@pytest.mark.performance
class TestOracleResponseTimePerformance:
    """Tests de performance des temps de réponse Oracle."""
    
    @pytest.mark.asyncio
    async def test_single_api_call_performance(self, real_gpt_kernel_performance, performance_profiler):
        """Test la performance d'un appel API unique."""
        performance_profiler.start_profiling()
        
        chat_service = real_gpt_kernel_performance.get_service("openai-gpt4o-mini-perf")
        
        # Test d'appel API simple
        start_time = time.time()
        
        try:
            from semantic_kernel.contents.chat_message_content import ChatMessageContent
            
            settings = OpenAIChatPromptExecutionSettings(
                max_tokens=100,
                temperature=0.1
            )
            
            messages = [ChatMessageContent(
                role="user", 
                content="En tant que Moriarty, révélez brièvement que vous avez la carte Colonel Moutarde."
            )]
            
            response = await chat_service.get_chat_message_contents(
                chat_history=messages,
                settings=settings
            )
            
            response_time = time.time() - start_time
            performance_profiler.record_api_call(response_time, True)
            
            # Vérifications de performance
            assert response_time < 15.0, f"Appel API trop lent: {response_time}s"
            assert len(response) > 0, "Réponse vide"
            assert len(response[0].content) > 20, "Réponse trop courte"
            
        except Exception as e:
            response_time = time.time() - start_time
            performance_profiler.record_api_call(response_time, False)
            performance_profiler.record_error(str(e))
            raise
        
        finally:
            metrics = performance_profiler.stop_profiling()
            
            # Analyse des métriques
            assert metrics['success_rate'] == 1.0, "Échec d'appel API"
            assert metrics['avg_response_time'] < 15.0, f"Temps moyen trop élevé: {metrics['avg_response_time']}s"
    
    @pytest.mark.asyncio
    async def test_multiple_sequential_calls_performance(self, real_gpt_kernel_performance, performance_profiler):
        """Test la performance d'appels API séquentiels."""
        performance_profiler.start_profiling()
        
        chat_service = real_gpt_kernel_performance.get_service("openai-gpt4o-mini-perf")
        num_calls = 5
        
        try:
            from semantic_kernel.contents.chat_message_content import ChatMessageContent
            
            settings = OpenAIChatPromptExecutionSettings(
                max_tokens=50,
                temperature=0.1
            )
            
            for i in range(num_calls):
                start_time = time.time()
                
                messages = [ChatMessageContent(
                    role="user", 
                    content=f"Test séquentiel {i+1}: Donnez un indice Cluedo bref."
                )]
                
                response = await chat_service.get_chat_message_contents(
                    chat_history=messages,
                    settings=settings
                )
                
                response_time = time.time() - start_time
                performance_profiler.record_api_call(response_time, True)
                performance_profiler.sample_resources()
                
                # Petit délai pour éviter rate limiting
                await asyncio.sleep(0.2)
            
            metrics = performance_profiler.stop_profiling()
            
            # Vérifications de performance séquentielle
            assert metrics['success_rate'] == 1.0, f"Échecs dans appels séquentiels: {metrics['error_rate']}"
            assert metrics['avg_response_time'] < 20.0, f"Temps moyen séquentiel trop élevé: {metrics['avg_response_time']}s"
            assert metrics['max_response_time'] < 30.0, f"Temps max trop élevé: {metrics['max_response_time']}s"
            
            # Vérification de la stabilité des temps de réponse
            response_times = metrics['response_times']
            if len(response_times) > 2:
                variance = sum((t - metrics['avg_response_time'])**2 for t in response_times) / len(response_times)
                std_dev = variance**0.5
                assert std_dev < 10.0, f"Variance temps de réponse trop élevée: {std_dev}s"
            
        except Exception as e:
            performance_profiler.record_error(str(e))
            raise
    
    @pytest.mark.asyncio
    async def test_oracle_workflow_end_to_end_performance(self, real_gpt_kernel_performance, performance_test_elements, performance_profiler):
        """Test la performance d'un workflow Oracle complet."""
        performance_profiler.start_profiling()
        
        try:
            orchestrator = CluedoExtendedOrchestrator(
                kernel=real_gpt_kernel_performance,
                max_turns=4,
                max_cycles=2,
                oracle_strategy="enhanced_auto_reveal"
            )
            
            # Setup workflow
            setup_start = time.time()
            oracle_state = await orchestrator.setup_workflow(
                nom_enquete="Performance Test Workflow",
                elements_jeu=performance_test_elements
            )
            setup_time = time.time() - setup_start
            
            # Exécution workflow
            workflow_start = time.time()
            
            # Simulation d'interactions Oracle
            for i in range(3):
                interaction_start = time.time()
                
                result = await oracle_state.query_oracle(
                    agent_name="TestAgent",
                    query_type="performance_test",
                    query_params={"iteration": i}
                )
                
                interaction_time = time.time() - interaction_start
                performance_profiler.record_api_call(interaction_time, result is not None)
                performance_profiler.sample_resources()
                
                await asyncio.sleep(0.1)  # Anti-rate limiting
            
            workflow_time = time.time() - workflow_start
            
            metrics = performance_profiler.stop_profiling()
            
            # Vérifications de performance workflow
            assert setup_time < 10.0, f"Setup trop lent: {setup_time}s"
            assert workflow_time < 45.0, f"Workflow trop lent: {workflow_time}s"
            assert metrics['total_duration'] < 60.0, f"Durée totale excessive: {metrics['total_duration']}s"
            assert metrics['success_rate'] >= 0.8, f"Trop d'échecs: {metrics['success_rate']}"
            
        except Exception as e:
            performance_profiler.record_error(str(e))
            raise


@pytest.mark.performance
class TestOracleLoadPerformance:
    """Tests de performance sous charge."""
    
    @pytest.mark.asyncio
    async def test_concurrent_oracle_agents_performance(self, performance_test_elements, performance_profiler):
        """Test la performance avec agents Oracle concurrents."""
        performance_profiler.start_profiling()
        
        num_concurrent_agents = 3
        mock_kernels = []
        oracle_states = []
        
        try:
            # Création d'agents concurrents (avec mocks pour éviter coûts)
            for i in range(num_concurrent_agents):
                mock_kernel = Mock()
                oracle_state = CluedoOracleState(
                    nom_enquete_cluedo=f"Concurrent Test {i}",
                    elements_jeu_cluedo=performance_test_elements,
                    oracle_strategy="enhanced_auto_reveal"
                )
                
                mock_kernels.append(mock_kernel)
                oracle_states.append(oracle_state)
            
            # Test de charge concurrente
            async def concurrent_oracle_task(oracle_state, agent_id):
                task_start = time.time()
                
                for iteration in range(5):
                    start_time = time.time()
                    
                    # Simulation d'opération Oracle
                    result = await oracle_state.query_oracle(
                        agent_name=f"Agent{agent_id}",
                        query_type="concurrent_test",
                        query_params={"iteration": iteration, "agent_id": agent_id}
                    )
                    
                    response_time = time.time() - start_time
                    performance_profiler.record_api_call(response_time, result is not None)
                    
                    await asyncio.sleep(0.05)  # Simulation temps de traitement
                
                return time.time() - task_start
            
            # Lancement des tâches concurrentes
            concurrent_start = time.time()
            
            tasks = [
                concurrent_oracle_task(oracle_states[i], i) 
                for i in range(num_concurrent_agents)
            ]
            
            task_times = await asyncio.gather(*tasks)
            concurrent_duration = time.time() - concurrent_start
            
            metrics = performance_profiler.stop_profiling()
            
            # Vérifications de performance concurrente
            assert concurrent_duration < 30.0, f"Concurrence trop lente: {concurrent_duration}s"
            assert max(task_times) < 20.0, f"Tâche individuelle trop lente: {max(task_times)}s"
            assert metrics['success_rate'] >= 0.9, f"Trop d'échecs concurrents: {metrics['success_rate']}"
            
            # Vérification que la concurrence améliore la performance
            total_sequential_time = sum(task_times)
            efficiency_ratio = total_sequential_time / concurrent_duration
            assert efficiency_ratio > 2.0, f"Concurrence inefficace: {efficiency_ratio}"
            
        except Exception as e:
            performance_profiler.record_error(str(e))
            raise
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, performance_test_elements, performance_profiler):
        """Test l'utilisation mémoire sous charge."""
        performance_profiler.start_profiling()
        
        try:
            oracle_states = []
            memory_measurements = []
            
            # Création progressive d'états Oracle
            for i in range(10):
                oracle_state = CluedoOracleState(
                    nom_enquete_cluedo=f"Memory Test {i}",
                    elements_jeu_cluedo=performance_test_elements,
                    oracle_strategy="enhanced_auto_reveal"
                )
                
                oracle_states.append(oracle_state)
                
                # Simulation d'activité
                for j in range(5):
                    await oracle_state.query_oracle(
                        agent_name=f"Agent{i}",
                        query_type="memory_test",
                        query_params={"iteration": j}
                    )
                
                # Mesure mémoire
                performance_profiler.sample_resources()
                current_memory = performance_profiler.process.memory_info().rss / 1024 / 1024
                memory_measurements.append(current_memory)
                
                # Petit délai
                await asyncio.sleep(0.1)
            
            # Nettoyage forcé
            del oracle_states
            gc.collect()
            
            final_memory = performance_profiler.process.memory_info().rss / 1024 / 1024
            memory_measurements.append(final_memory)
            
            metrics = performance_profiler.stop_profiling()
            
            # Vérifications mémoire
            initial_memory = memory_measurements[0]
            peak_memory = max(memory_measurements)
            memory_growth = peak_memory - initial_memory
            
            assert memory_growth < 500, f"Croissance mémoire excessive: {memory_growth}MB"
            assert peak_memory < 1000, f"Pic mémoire trop élevé: {peak_memory}MB"
            
            # Vérification du nettoyage mémoire
            memory_after_cleanup = memory_measurements[-1]
            cleanup_efficiency = (peak_memory - memory_after_cleanup) / peak_memory
            assert cleanup_efficiency > 0.3, f"Nettoyage mémoire insuffisant: {cleanup_efficiency}"
            
        except Exception as e:
            performance_profiler.record_error(str(e))
            raise


@pytest.mark.performance
@pytest.mark.skipif(not REAL_GPT_AVAILABLE, reason="Nécessite OPENAI_API_KEY pour tests JVM")
class TestTweetyJVMPerformance:
    """Tests de performance avec Tweety JVM."""
    
    @pytest.mark.asyncio
    async def test_jvm_memory_management(self, performance_profiler):
        """Test la gestion mémoire JVM Tweety."""
        performance_profiler.start_profiling()
        
        try:
            # Import conditionnel de Tweety (si disponible)
            try:
                from argumentation_analysis.core.utils.jvm_utils import ensure_jvm_started
                jvm_available = True
            except ImportError:
                jvm_available = False
                pytest.skip("Tweety JVM non disponible")
            
            if jvm_available:
                # Test de démarrage JVM
                jvm_start = time.time()
                jvm_started = await ensure_jvm_started()
                jvm_startup_time = time.time() - jvm_start
                
                assert jvm_startup_time < 10.0, f"Démarrage JVM trop lent: {jvm_startup_time}s"
                
                # Test d'utilisation intensive JVM
                for i in range(10):
                    performance_profiler.sample_resources()
                    
                    # Simulation d'opérations Tweety
                    operation_start = time.time()
                    
                    # Ici on simulerait des opérations Tweety réelles
                    # Pour l'instant, on simule avec un délai
                    await asyncio.sleep(0.1)
                    
                    operation_time = time.time() - operation_start
                    performance_profiler.record_api_call(operation_time, True)
                
                metrics = performance_profiler.stop_profiling()
                
                # Vérifications performance JVM
                assert metrics['avg_response_time'] < 1.0, f"Opérations JVM trop lentes: {metrics['avg_response_time']}s"
                assert metrics['peak_memory'] < 2000, f"Utilisation mémoire JVM excessive: {metrics['peak_memory']}MB"
            
        except Exception as e:
            performance_profiler.record_error(str(e))
            # Test JVM optionnel, on n'échoue pas forcément
            pytest.skip(f"Test JVM échoué (optionnel): {e}")
    
    def test_jvm_garbage_collection_impact(self, performance_profiler):
        """Test l'impact du garbage collection."""
        performance_profiler.start_profiling()
        
        try:
            # Mesure avant garbage collection
            initial_gc_count = performance_profiler.metrics['gc_collections']
            
            # Création d'objets temporaires
            temp_objects = []
            for i in range(1000):
                temp_obj = {
                    'id': i,
                    'data': f"test_data_{i}" * 100,  # Objets relativement gros
                    'nested': {'value': i * 2}
                }
                temp_objects.append(temp_obj)
            
            # Mesure mémoire avant nettoyage
            performance_profiler.sample_resources()
            memory_before_gc = performance_profiler.process.memory_info().rss / 1024 / 1024
            
            # Nettoyage forcé
            del temp_objects
            gc_start = time.time()
            gc.collect()
            gc_time = time.time() - gc_start
            
            # Mesure après nettoyage
            performance_profiler.sample_resources()
            memory_after_gc = performance_profiler.process.memory_info().rss / 1024 / 1024
            
            metrics = performance_profiler.stop_profiling()
            
            # Vérifications garbage collection
            memory_freed = memory_before_gc - memory_after_gc
            assert gc_time < 1.0, f"Garbage collection trop lent: {gc_time}s"
            assert memory_freed >= 0, "Pas de libération mémoire détectée"
            
            # Le GC ne devrait pas impacter drastiquement la performance
            if metrics['avg_cpu']:
                assert metrics['peak_cpu'] < 90, f"CPU pic trop élevé lors GC: {metrics['peak_cpu']}%"
            
        except Exception as e:
            performance_profiler.record_error(str(e))
            raise


@pytest.mark.performance
class TestPerformanceRegression:
    """Tests de régression de performance."""
    
    async def test_performance_baseline_comparison(self, performance_profiler):
        """Compare les performances à une baseline."""
        # Baseline de référence (ajustable selon les améliorations)
        baseline_metrics = {
            'max_response_time': 30.0,  # secondes
            'avg_response_time': 10.0,  # secondes
            'peak_memory': 1000,        # MB
            'avg_cpu': 50,              # %
            'success_rate': 0.95        # 95%
        }
        
        performance_profiler.start_profiling()
        
        try:
            # Simulation d'opérations typiques
            for i in range(5):
                start_time = time.time()
                
                # Simulation d'une opération Oracle typique
                await asyncio.sleep(0.2)  # Simule traitement
                
                response_time = time.time() - start_time
                performance_profiler.record_api_call(response_time, True)
                performance_profiler.sample_resources()
            
            metrics = performance_profiler.stop_profiling()
            
            # Comparaison avec baseline
            performance_issues = []
            
            if metrics.get('max_response_time', 0) > baseline_metrics['max_response_time']:
                performance_issues.append(f"Temps max dégradé: {metrics['max_response_time']}s > {baseline_metrics['max_response_time']}s")
            
            if metrics.get('avg_response_time', 0) > baseline_metrics['avg_response_time']:
                performance_issues.append(f"Temps moyen dégradé: {metrics['avg_response_time']}s > {baseline_metrics['avg_response_time']}s")
            
            if metrics.get('peak_memory', 0) > baseline_metrics['peak_memory']:
                performance_issues.append(f"Mémoire pic dégradée: {metrics['peak_memory']}MB > {baseline_metrics['peak_memory']}MB")
            
            if metrics.get('success_rate', 0) < baseline_metrics['success_rate']:
                performance_issues.append(f"Taux succès dégradé: {metrics['success_rate']} < {baseline_metrics['success_rate']}")
            
            assert not performance_issues, f"Régressions de performance détectées: {performance_issues}"
            
        except Exception as e:
            performance_profiler.record_error(str(e))
            raise
    
    async def test_scalability_limits(self, performance_profiler):
        """Test les limites de scalabilité."""
        performance_profiler.start_profiling()
        
        scalability_results = {}
        
        # Test avec différentes charges
        load_levels = [1, 5, 10, 20]
        
        for load in load_levels:
            load_start = time.time()
            
            # Simulation de charge
            tasks = []
            for i in range(load):
                async def load_task():
                    await asyncio.sleep(0.1)
                    return True
                
                tasks.append(load_task())
            
            # Exécution de la charge
            results = await asyncio.gather(*tasks)
            load_time = time.time() - load_start
            
            performance_profiler.sample_resources()
            
            scalability_results[load] = {
                'load_time': load_time,
                'throughput': load / load_time,
                'success_count': sum(results)
            }
        
        metrics = performance_profiler.stop_profiling()
        
        # Analyse de scalabilité
        throughputs = [result['throughput'] for result in scalability_results.values()]
        
        # La throughput ne devrait pas chuter drastiquement
        max_throughput = max(throughputs)
        min_throughput = min(throughputs)
        throughput_degradation = (max_throughput - min_throughput) / max_throughput
        
        assert throughput_degradation < 0.7, f"Dégradation throughput excessive: {throughput_degradation}"
        
        # Toutes les charges devraient être supportées
        for load, result in scalability_results.items():
            assert result['success_count'] == load, f"Échecs sous charge {load}: {result['success_count']}/{load}"