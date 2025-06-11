#!/usr/bin/env python3
"""
Script de validation complète du projet d'argumentation Dung
Exécute tous les tests, benchmarks et validations
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Exécute une commande et retourne le résultat"""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=120
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - SUCCÈS")
            print(result.stdout)
            return True
        else:
            print(f"❌ {description} - ÉCHEC")
            print(f"Erreur: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} - TIMEOUT (>120s)")
        return False
    except Exception as e:
        print(f"💥 {description} - EXCEPTION: {e}")
        return False

def check_files():
    """Vérifie la présence des fichiers essentiels"""
    essential_files = [
        'agent.py',
        'enhanced_agent.py', 
        'framework_generator.py',
        'io_utils.py',
        'cli.py',
        'config.py',
        'test_agent.py',
        'advanced_tests.py',
        'benchmark.py',
        'README.md',
        'requirements.txt'
    ]
    
    missing_files = []
    for file in essential_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Fichiers manquants: {missing_files}")
        return False
    
    print("✅ Tous les fichiers essentiels sont présents")
    return True

def validate_project():
    """Validation complète du projet"""
    print("🎯 VALIDATION COMPLÈTE DU PROJET D'ARGUMENTATION DUNG")
    print("=" * 70)
    
    results = []
    
    # 1. Vérification des fichiers
    print("\n1️⃣ VÉRIFICATION DES FICHIERS")
    results.append(check_files())
    
    # 2. Validation de la configuration
    print("\n2️⃣ VALIDATION DE LA CONFIGURATION")
    results.append(run_command("python config.py", "Configuration du projet"))
    
    # 3. Informations du projet
    print("\n3️⃣ INFORMATIONS DU PROJET")
    results.append(run_command("python project_info.py", "Métadonnées du projet"))
    
    # 4. Tests de base
    print("\n4️⃣ TESTS DE BASE")
    results.append(run_command("python test_agent.py", "Tests unitaires de base"))
    
    # 5. Tests avancés
    print("\n5️⃣ TESTS AVANCÉS")
    results.append(run_command("python advanced_tests.py", "Tests avancés et complexes"))
    
    # 6. Tests CLI
    print("\n6️⃣ TESTS CLI")
    results.append(run_command("python cli.py info", "Interface ligne de commande"))
    
    # 7. Tests d'import/export
    print("\n7️⃣ TESTS IMPORT/EXPORT")
    results.append(run_command("python io_utils.py", "Utilitaires d'import/export"))
    
    # 8. Tests de génération
    print("\n8️⃣ TESTS DE GÉNÉRATION")
    results.append(run_command("python framework_generator.py", "Générateur de frameworks"))
    
    # 9. Agent amélioré
    print("\n9️⃣ TESTS AGENT AMÉLIORÉ")
    results.append(run_command("python enhanced_agent.py", "Agent avec corrections"))
    
    # 10. Benchmark complet (version allégée pour validation)
    print("\n🔟 BENCHMARK RAPIDE")
    benchmark_cmd = """python -c "
from benchmark import ArgumentationBenchmark
b = ArgumentationBenchmark()
b.benchmark_computation_time(sizes=[5, 8], trials=2)
b.generate_report()
print('Benchmark rapide terminé!')
" """
    results.append(run_command(benchmark_cmd, "Benchmark de performance"))
    
    # Résumé final
    print("\n" + "="*70)
    print("📊 RÉSUMÉ DE LA VALIDATION")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total) * 100 if total > 0 else 0
    
    print(f"Tests passés: {passed}/{total}")
    print(f"Taux de réussite: {success_rate:.1f}%")
    
    if passed == total:
        print("🎉 PROJET ENTIÈREMENT VALIDÉ !")
        print("✅ Votre implémentation d'argumentation Dung est complète et fonctionnelle")
        return True
    else:
        print("⚠️  Quelques problèmes détectés")
        print("🔧 Vérifiez les erreurs ci-dessus")
        return False

if __name__ == "__main__":
    print("Agent d'Argumentation Abstraite de Dung - Validation")
    print("Auteur: Wassim")
    print("Date: 10 juin 2025")
    
    success = validate_project()
    
    if success:
        print("\n🚀 Le projet est prêt pour la démonstration !")
        sys.exit(0)
    else:
        print("\n🛠️  Corrections nécessaires avant finalisation")
        sys.exit(1)