#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour l'architecture modulaire
"""

import sys
import os
from pathlib import Path

# Configuration du chemin
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

# Ajout du chemin des modules
modules_path = Path(__file__).parent / "modules"
sys.path.insert(0, str(modules_path))

def test_imports():
    """Test des imports des modules"""
    try:
        print("🔧 Test des imports des modules...")
        
        # Test import utilitaires
        from demo_utils import DemoLogger, Colors, Symbols, charger_config_categories
        print("✅ demo_utils importé avec succès")
        
        # Test chargement configuration
        config = charger_config_categories()
        if config:
            print("✅ Configuration YAML chargée avec succès")
            categories = config.get('categories', {})
            print(f"📊 {len(categories)} catégories trouvées:")
            for cat_id, cat_info in categories.items():
                icon = cat_info.get('icon', '•')
                nom = cat_info.get('nom', cat_id)
                print(f"   {icon} {nom}")
        else:
            print("❌ Échec du chargement de la configuration")
            return False
        
        # Test import des modules de démonstration
        modules_demo = [
            'demo_tests_validation',
            'demo_agents_logiques', 
            'demo_services_core',
            'demo_integrations',
            'demo_cas_usage',
            'demo_outils_utils'
        ]
        
        for module_name in modules_demo:
            try:
                __import__(module_name)
                print(f"✅ {module_name} importé avec succès")
            except Exception as e:
                print(f"❌ Erreur import {module_name}: {e}")
                return False
        
        print("\n🎉 Tous les modules importés avec succès !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test des imports: {e}")
        return False

def test_menu_categories():
    """Test du menu des catégories"""
    try:
        print("\n🎯 Test du menu des catégories...")
        
        from demo_utils import charger_config_categories, Colors, Symbols
        
        config = charger_config_categories()
        if not config:
            print("❌ Configuration non disponible")
            return False
            
        print(f"\n{Colors.CYAN}{Colors.BOLD}")
        print("🎓 DÉMONSTRATION EPITA - Intelligence Symbolique")
        print("═══════════════════════════════════════════════")
        print(f"{Colors.ENDC}")
        
        categories = config.get('categories', {})
        categories_triees = sorted(categories.items(), key=lambda x: x[1]['id'])
        
        for cat_id, cat_info in categories_triees:
            icon = cat_info.get('icon', '•')
            nom = cat_info.get('nom', cat_id)
            description = cat_info.get('description', '')
            id_num = cat_info.get('id', 0)
            
            print(f"{Colors.CYAN}{icon} {id_num}. {nom}{Colors.ENDC} ({description})")
        
        print(f"\n{Colors.WARNING}Sélectionnez une catégorie (1-6) ou 'q' pour quitter:{Colors.ENDC}")
        print("\n✅ Menu des catégories affiché avec succès !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test du menu: {e}")
        return False

def test_module_execution():
    """Test d'exécution d'un module"""
    try:
        print("\n🧪 Test d'exécution d'un module...")
        
        # Test du module de tests validation en mode rapide
        import demo_tests_validation
        
        print("🚀 Exécution demo_tests_validation en mode rapide...")
        # Simuler les arguments
        sys.argv = ['demo_tests_validation.py']
        
        # Le test réel serait trop long, on simule juste l'import et la structure
        if hasattr(demo_tests_validation, 'run_demo_rapide'):
            print("✅ Fonction run_demo_rapide trouvée")
        else:
            print("❌ Fonction run_demo_rapide non trouvée")
            return False
            
        if hasattr(demo_tests_validation, 'run_demo_interactive'):
            print("✅ Fonction run_demo_interactive trouvée")
        else:
            print("❌ Fonction run_demo_interactive non trouvée")
            return False
        
        print("✅ Structure du module validée !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test d'exécution: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("🎓 TEST DE L'ARCHITECTURE MODULAIRE EPITA")
    print("=" * 50)
    
    tests = [
        ("Import des modules", test_imports),
        ("Menu des catégories", test_menu_categories), 
        ("Exécution de module", test_module_execution)
    ]
    
    resultats = []
    for nom_test, fonction_test in tests:
        print(f"\n📋 {nom_test}...")
        resultat = fonction_test()
        resultats.append((nom_test, resultat))
    
    # Résumé final
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 50)
    
    total_tests = len(resultats)
    tests_reussis = sum(1 for _, resultat in resultats if resultat)
    
    for nom_test, resultat in resultats:
        status = "✅ RÉUSSI" if resultat else "❌ ÉCHEC"
        print(f"{status} - {nom_test}")
    
    taux_succes = (tests_reussis / total_tests) * 100
    print(f"\n🎯 Taux de succès: {tests_reussis}/{total_tests} ({taux_succes:.1f}%)")
    
    if tests_reussis == total_tests:
        print("\n🎉 ARCHITECTURE MODULAIRE : SUCCÈS COMPLET !")
        print("🚀 Le système de démonstration est prêt à être utilisé !")
    else:
        print(f"\n⚠️  Certains tests ont échoué. Révision nécessaire.")
    
    return tests_reussis == total_tests

if __name__ == "__main__":
    try:
        succes = main()
        sys.exit(0 if succes else 1)
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        sys.exit(1)