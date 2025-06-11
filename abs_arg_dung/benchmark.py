import time
import statistics
from agent import DungAgent
from enhanced_agent import EnhancedDungAgent
from framework_generator import FrameworkGenerator
from config import RANDOM_GENERATION_CONFIG, TEST_CONFIG

class ArgumentationBenchmark:
    
    def __init__(self):
        self.results = {}
    
    def benchmark_computation_time(self, sizes=[5, 10, 15, 20], trials=5):
        """Benchmark du temps de calcul des extensions"""
        print("=== BENCHMARK TEMPS DE CALCUL ===")
        
        for size in sizes:
            times = []
            for trial in range(trials):
                agent = FrameworkGenerator.generate_random_framework(
                    size, 
                    RANDOM_GENERATION_CONFIG['default_attack_probability'], 
                    seed=trial
                )
                
                start_time = time.time()
                # Forcer le calcul de toutes les extensions
                agent.get_grounded_extension()
                agent.get_preferred_extensions()
                agent.get_stable_extensions()
                agent.get_complete_extensions()
                agent.get_admissible_sets()
                agent.get_ideal_extension()
                end_time = time.time()
                
                times.append(end_time - start_time)
            
            avg_time = statistics.mean(times)
            std_time = statistics.stdev(times) if len(times) > 1 else 0
            
            print(f"Taille {size:2d}: {avg_time:.4f}s ± {std_time:.4f}s")
            self.results[f"time_{size}"] = {'mean': avg_time, 'std': std_time}
    
    def benchmark_semantics_consistency(self, num_frameworks=20):
        """Vérifie la cohérence des sémantiques"""
        print("\n=== BENCHMARK COHÉRENCE SÉMANTIQUES ===")
        
        inconsistencies = 0
        total_checks = 0
        
        for i in range(num_frameworks):
            agent = FrameworkGenerator.generate_random_framework(8, 0.4, seed=i)
            relations = agent.get_semantics_relationships()
            
            checks = relations['theoretical_checks']
            total_checks += len(checks)
            
            failed_checks = [check for check, result in checks.items() if not result]
            if failed_checks:
                inconsistencies += len(failed_checks)
                print(f"Framework {i}: Incohérences détectées")
                for check in failed_checks:
                    print(f"  - {check}: ÉCHEC")
        
        consistency_rate = (total_checks - inconsistencies) / total_checks if total_checks > 0 else 1.0
        print(f"\nTaux de cohérence: {consistency_rate:.2%}")
        print(f"Total vérifications: {total_checks}")
        print(f"Échecs: {inconsistencies}")
        self.results['consistency_rate'] = consistency_rate
        self.results['total_checks'] = total_checks
        self.results['failed_checks'] = inconsistencies
    
    def compare_standard_vs_enhanced(self, num_tests=10):
        """Compare l'agent standard avec l'agent amélioré"""
        print("\n=== COMPARAISON STANDARD vs AMÉLIORÉ ===")
        
        differences = []
        
        for i in range(num_tests):
            # Test sur différents types de frameworks problématiques
            test_cases = [
                # Cas 1: Self-attack simple
                lambda: self._create_self_attack_case(),
                # Cas 2: Cycle parfait
                lambda: self._create_perfect_cycle(),
                # Cas 3: Framework complexe
                lambda: self._create_complex_case(i)
            ]
            
            for j, create_case in enumerate(test_cases):
                std_agent, enh_agent = create_case()
                
                # Comparer les extensions
                std_grounded = std_agent.get_grounded_extension()
                enh_grounded = enh_agent.get_grounded_extension()
                std_preferred = std_agent.get_preferred_extensions()
                enh_preferred = enh_agent.get_preferred_extensions()
                
                if std_grounded != enh_grounded or std_preferred != enh_preferred:
                    differences.append({
                        'test': i,
                        'case': j,
                        'std_grounded': std_grounded,
                        'enh_grounded': enh_grounded,
                        'std_preferred': std_preferred,
                        'enh_preferred': enh_preferred
                    })
                    
                    print(f"Test {i}-{j}: Différence détectée")
                    print(f"  Standard grounded: {std_grounded}")
                    print(f"  Amélioré grounded: {enh_grounded}")
        
        print(f"\nNombre de différences: {len(differences)}/{num_tests * 3}")
        self.results['differences'] = len(differences)
        self.results['total_comparisons'] = num_tests * 3
        self.results['difference_details'] = differences
    
    def _create_self_attack_case(self):
        """Crée un cas de self-attack pour comparaison"""
        std_agent = DungAgent()
        enh_agent = EnhancedDungAgent()
        
        for agent in [std_agent, enh_agent]:
            agent.add_argument("a")
            agent.add_argument("b")
            agent.add_attack("a", "a")
            agent.add_attack("a", "b")
        
        return std_agent, enh_agent
    
    def _create_perfect_cycle(self):
        """Crée un cycle parfait pour comparaison"""
        std_agent = DungAgent()
        enh_agent = EnhancedDungAgent()
        
        for agent in [std_agent, enh_agent]:
            for arg in ["a", "b", "c"]:
                agent.add_argument(arg)
            agent.add_attack("a", "b")
            agent.add_attack("b", "c")
            agent.add_attack("c", "a")
        
        return std_agent, enh_agent
    
    def _create_complex_case(self, seed):
        """Crée un framework complexe aléatoire"""
        std_agent = FrameworkGenerator.generate_random_framework(6, 0.3, seed)
        
        # Recréer le même framework avec l'agent amélioré
        enh_agent = EnhancedDungAgent()
        for arg_name in std_agent._arguments.keys():
            enh_agent.add_argument(arg_name)
        for attack in std_agent.af.getAttacks():
            source = attack.getAttacker().getName()
            target = attack.getAttacked().getName()
            enh_agent.add_attack(source, target)
        
        return std_agent, enh_agent
    
    def benchmark_scalability(self, max_size=25, step=5):
        """Test de passage à l'échelle"""
        print("\n=== BENCHMARK PASSAGE À L'ÉCHELLE ===")
        
        sizes = list(range(step, max_size + 1, step))
        scalability_data = []
        
        for size in sizes:
            agent = FrameworkGenerator.generate_random_framework(size, 0.3, seed=42)
            
            start_time = time.time()
            try:
                grounded = agent.get_grounded_extension()
                preferred = agent.get_preferred_extensions()
                computation_time = time.time() - start_time
                
                data_point = {
                    'size': size,
                    'time': computation_time,
                    'grounded_size': len(grounded),
                    'num_preferred': len(preferred),
                    'success': True
                }
                
                print(f"Taille {size:2d}: {computation_time:.3f}s, "
                      f"grounded={len(grounded)}, preferred={len(preferred)}")
                
            except Exception as e:
                data_point = {
                    'size': size,
                    'time': float('inf'),
                    'error': str(e),
                    'success': False
                }
                print(f"Taille {size:2d}: ÉCHEC - {e}")
            
            scalability_data.append(data_point)
            
            # Arrêter si le calcul devient trop lent
            if data_point.get('time', 0) > TEST_CONFIG['performance_timeout']:
                print(f"Arrêt: temps de calcul > {TEST_CONFIG['performance_timeout']}s")
                break
        
        self.results['scalability'] = scalability_data
    
    def benchmark_framework_properties(self, num_samples=50):
        """Analyse statistique des propriétés des frameworks"""
        print("\n=== BENCHMARK PROPRIÉTÉS FRAMEWORKS ===")
        
        stats = {
            'sizes': [],
            'attack_densities': [],
            'cycle_rates': [],
            'grounded_sizes': [],
            'preferred_counts': []
        }
        
        for i in range(num_samples):
            size = 5 + (i % 10)  # Tailles variées 5-14
            prob = 0.2 + (i % 5) * 0.1  # Probabilités 0.2-0.6
            
            agent = FrameworkGenerator.generate_random_framework(size, prob, seed=i)
            props = agent.get_framework_properties()
            semantics = agent.get_semantics_relationships()
            
            density = props['num_attacks'] / (props['num_arguments'] ** 2) if props['num_arguments'] > 0 else 0
            
            stats['sizes'].append(props['num_arguments'])
            stats['attack_densities'].append(density)
            stats['cycle_rates'].append(1 if props['has_cycles'] else 0)
            stats['grounded_sizes'].append(len(semantics['extensions']['grounded']))
            stats['preferred_counts'].append(len(semantics['extensions']['preferred']))
        
        # Calculer les statistiques
        summary = {}
        for key, values in stats.items():
            if values:
                summary[key] = {
                    'mean': statistics.mean(values),
                    'std': statistics.stdev(values) if len(values) > 1 else 0,
                    'min': min(values),
                    'max': max(values)
                }
        
        print("Statistiques sur les frameworks générés:")
        for key, data in summary.items():
            print(f"{key}: μ={data['mean']:.2f} σ={data['std']:.2f} "
                  f"[{data['min']}, {data['max']}]")
        
        self.results['framework_stats'] = summary
    
    def generate_report(self):
        """Génère un rapport complet de benchmark"""
        print("\n" + "="*70)
        print("RAPPORT DE BENCHMARK COMPLET")
        print("="*70)
        
        print("\n1. PERFORMANCE TEMPORELLE:")
        time_results = {k: v for k, v in self.results.items() if k.startswith('time_')}
        for key, value in time_results.items():
            size = key.split('_')[1]
            print(f"   Taille {size}: {value['mean']:.4f}s ± {value['std']:.4f}s")
        
        print("\n2. COHÉRENCE SÉMANTIQUE:")
        if 'consistency_rate' in self.results:
            rate = self.results['consistency_rate']
            print(f"   Taux de cohérence: {rate:.1%}")
            print(f"   Vérifications: {self.results.get('total_checks', 0)}")
            print(f"   Échecs: {self.results.get('failed_checks', 0)}")
        
        print("\n3. COMPARAISON AGENTS:")
        if 'differences' in self.results:
            diff_count = self.results['differences']
            total_comp = self.results.get('total_comparisons', 0)
            print(f"   Différences détectées: {diff_count}/{total_comp}")
            if diff_count > 0:
                print(f"   Taux de divergence: {diff_count/total_comp:.1%}")
        
        print("\n4. PASSAGE À L'ÉCHELLE:")
        if 'scalability' in self.results:
            scalability = self.results['scalability']
            successful = [d for d in scalability if d['success']]
            if successful:
                max_size = max(d['size'] for d in successful)
                max_time = max(d['time'] for d in successful)
                print(f"   Taille maximale testée: {max_size}")
                print(f"   Temps maximal: {max_time:.3f}s")
        
        print("\n5. PROPRIÉTÉS FRAMEWORKS:")
        if 'framework_stats' in self.results:
            stats = self.results['framework_stats']
            if 'cycle_rates' in stats:
                cycle_rate = stats['cycle_rates']['mean']
                print(f"   Taux de cycles: {cycle_rate:.1%}")
            if 'attack_densities' in stats:
                density = stats['attack_densities']['mean']
                print(f"   Densité d'attaques moyenne: {density:.2f}")
        
        return self.results

# Script principal de benchmark
if __name__ == "__main__":
    print("🚀 DÉMARRAGE DU BENCHMARK COMPLET")
    print("=" * 50)
    
    benchmark = ArgumentationBenchmark()
    
    try:
        # Exécuter tous les benchmarks
        benchmark.benchmark_computation_time(sizes=[5, 8, 12, 15], trials=3)
        benchmark.benchmark_semantics_consistency(num_frameworks=15)
        benchmark.compare_standard_vs_enhanced(num_tests=5)
        benchmark.benchmark_scalability(max_size=20, step=4)
        benchmark.benchmark_framework_properties(num_samples=30)
        
        # Générer le rapport final
        results = benchmark.generate_report()
        
        print(f"\n✅ Benchmark terminé avec succès!")
        print(f"📊 {len(results)} métriques collectées")
        
    except KeyboardInterrupt:
        print("\n⚠️  Benchmark interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur durant le benchmark: {e}")
        import traceback
        traceback.print_exc()