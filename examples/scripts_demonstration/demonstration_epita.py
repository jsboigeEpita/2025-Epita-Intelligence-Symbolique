# -*- coding: utf-8 -*-
"""
Script principal de démonstration EPITA - Architecture Modulaire
Intelligence Symbolique - Menu Catégorisé

VERSION 2.0 - Refactorisation complète en architecture modulaire
Ancien script sauvegardé dans demonstration_epita_legacy.py

Utilisation :
  python demonstration_epita.py                    # Menu interactif
  python demonstration_epita.py --interactive      # Mode interactif avec modules
  python demonstration_epita.py --quick-start      # Quick start étudiants  
  python demonstration_epita.py --metrics          # Métriques seulement
"""

import sys
import os
import argparse
import importlib.util
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Configuration du chemin pour les modules
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
os.chdir(project_root)

# Vérifier et installer PyYAML si nécessaire
def ensure_yaml_dependency():
    try:
        import yaml
    except ImportError:
        print("Installation de PyYAML...")
        subprocess.run([sys.executable, "-m", "pip", "install", "PyYAML"], check=True)
        import yaml

ensure_yaml_dependency()

# Import des utilitaires depuis le module
modules_path = Path(__file__).parent / "modules"
sys.path.insert(0, str(modules_path))

try:
    from demo_utils import (
        DemoLogger, Colors, Symbols, charger_config_categories,
        afficher_progression, pause_interactive, confirmer_action,
        valider_environnement
    )
except ImportError as e:
    print(f"Erreur d'import des utilitaires : {e}")
    print("Chargement du mode legacy...")
    # Fallback vers le mode legacy si les modules ne sont pas disponibles
    from demonstration_epita_legacy import main as legacy_main
    legacy_main()
    sys.exit(0)

def afficher_banniere_principale():
    """Affiche la bannière principale du système"""
    print(f"""
{Colors.CYAN}{Colors.BOLD}
+==============================================================================+
|                [EPITA] DEMONSTRATION - Intelligence Symbolique              |
|                        Architecture Modulaire v2.0                         |
+==============================================================================+
{Colors.ENDC}""")

def afficher_menu_categories(config: Dict[str, Any]) -> None:
    """Affiche le menu catégorisé principal"""
    print(f"\n{Colors.BOLD}{'=' * 47}{Colors.ENDC}")
    
    if 'categories' not in config:
        print(f"{Colors.FAIL}Configuration des catégories non trouvée{Colors.ENDC}")
        return
    
    categories = config['categories']
    categories_triees = sorted(categories.items(), key=lambda x: x[1]['id'])
    
    for cat_id, cat_info in categories_triees:
        icon = cat_info.get('icon', '•')
        nom = cat_info.get('nom', cat_id)
        description = cat_info.get('description', '')
        id_num = cat_info.get('id', 0)
        
        print(f"{Colors.CYAN}{icon} {id_num}. {nom}{Colors.ENDC} ({description})")
    
    print(f"\n{Colors.WARNING}Sélectionnez une catégorie (1-6) ou 'q' pour quitter:{Colors.ENDC}")

def charger_et_executer_module(nom_module: str, mode_interactif: bool = False) -> bool:
    """Charge et exécute dynamiquement un module de démonstration"""
    try:
        module_path = modules_path / f"{nom_module}.py"
        if not module_path.exists():
            print(f"{Colors.FAIL}{Symbols.CROSS} Module {nom_module} non trouvé{Colors.ENDC}")
            return False
        
        # Chargement dynamique du module
        spec = importlib.util.spec_from_file_location(nom_module, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Exécution selon le mode
        if mode_interactif and hasattr(module, 'run_demo_interactive'):
            return module.run_demo_interactive()
        elif hasattr(module, 'run_demo_rapide'):
            return module.run_demo_rapide()
        else:
            print(f"{Colors.WARNING}Fonction de démonstration non trouvée dans {nom_module}{Colors.ENDC}")
            return False
            
    except Exception as e:
        print(f"{Colors.FAIL}{Symbols.CROSS} Erreur lors de l'exécution de {nom_module}: {e}{Colors.ENDC}")
        return False

def mode_menu_interactif(config: Dict[str, Any]) -> None:
    """Mode menu interactif principal"""
    logger = DemoLogger("menu_principal")
    
    while True:
        afficher_banniere_principale()
        afficher_menu_categories(config)
        
        try:
            choix = input(f"\n{Colors.CYAN}> {Colors.ENDC}").strip().lower()
            
            if choix == 'q' or choix == 'quit':
                logger.info("Au revoir !")
                break
            
            # Conversion en entier pour la sélection
            if choix.isdigit():
                num_choix = int(choix)
                
                # Trouver la catégorie correspondante
                categories = config.get('categories', {})
                cat_selectionnee = None
                
                for cat_id, cat_info in categories.items():
                    if cat_info.get('id') == num_choix:
                        cat_selectionnee = (cat_id, cat_info)
                        break
                
                if cat_selectionnee:
                    cat_id, cat_info = cat_selectionnee
                    nom_module = cat_info.get('module', '')
                    nom_cat = cat_info.get('nom', cat_id)
                    
                    logger.header(f"{Symbols.ROCKET} Lancement de : {nom_cat}")
                    
                    if confirmer_action(f"Exécuter la démonstration '{nom_cat}' ?"):
                        succes = charger_et_executer_module(nom_module, mode_interactif=True)
                        
                        if succes:
                            logger.success(f"{Symbols.CHECK} Démonstration '{nom_cat}' terminée avec succès !")
                        else:
                            logger.error(f"{Symbols.CROSS} Échec de la démonstration '{nom_cat}'")
                        
                        pause_interactive("Appuyez sur Entrée pour revenir au menu principal...")
                else:
                    print(f"{Colors.FAIL}Choix invalide : {num_choix}{Colors.ENDC}")
                    pause_interactive()
            else:
                print(f"{Colors.FAIL}Veuillez entrer un numéro (1-6) ou 'q'{Colors.ENDC}")
                pause_interactive()
                
        except KeyboardInterrupt:
            logger.info("\nInterruption utilisateur - Au revoir !")
            break
        except Exception as e:
            logger.error(f"Erreur inattendue : {e}")
            pause_interactive()

def mode_quick_start() -> None:
    """Mode Quick Start pour les étudiants"""
    logger = DemoLogger("quick_start")
    afficher_banniere_principale()
    logger.header(f"{Symbols.ROCKET} MODE QUICK-START - Démonstration rapide")
    
    # Charger la configuration
    config = charger_config_categories()
    if not config:
        return
    
    # Exécuter une démo rapide de chaque catégorie
    categories = config.get('categories', {})
    
    for cat_id, cat_info in categories.items():
        module_name = cat_info.get('module')
        if module_name:
            try:
                print(f"\n{Colors.CYAN}{cat_info.get('icon', '[INFO]')} {cat_info.get('nom', 'Catégorie')}{Colors.ENDC}")
                succes = charger_et_executer_module(module_name, mode_interactif=False)
                if succes:
                    print(f"{Colors.GREEN}  [OK] Terminé{Colors.ENDC}")
                else:
                    print(f"{Colors.FAIL}  [FAIL] Erreur{Colors.ENDC}")
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Erreur module {module_name}: {e}")
    
    print(f"\n{Colors.GREEN}{Symbols.CHECK} Quick-start terminé !{Colors.ENDC}")

def mode_metrics_only(config: Dict[str, Any]) -> None:
    """Affiche uniquement les métriques du projet"""
    afficher_banniere_principale()
    
    config_global = config.get('config', {})
    taux_succes = config_global.get('taux_succes_tests', 99.7)
    architecture = config_global.get('architecture', 'Python + Java (JPype)')
    domaines = config_global.get('domaines', [])
    
    print(f"\n{Colors.BOLD}{Symbols.CHART} MÉTRIQUES DU PROJET{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * 50}{Colors.ENDC}")
    print(f"{Colors.GREEN}{Symbols.CHECK} Taux de succès des tests : {taux_succes}%{Colors.ENDC}")
    print(f"{Colors.BLUE}{Symbols.GEAR} Architecture : {architecture}{Colors.ENDC}")
    print(f"{Colors.CYAN}{Symbols.BRAIN} Domaines couverts :{Colors.ENDC}")
    for domaine in domaines:
        print(f"  • {domaine}")
    
    print(f"\n{Colors.BOLD}Modules disponibles :{Colors.ENDC}")
    categories = config.get('categories', {})
    for cat_info in sorted(categories.values(), key=lambda x: x.get('id', 0)):
        icon = cat_info.get('icon', '•')
        nom = cat_info.get('nom', 'Module')
        print(f"  {icon} {nom}")

def mode_execution_legacy() -> None:
    """Exécute le comportement legacy pour compatibilité"""
    print(f"{Colors.WARNING}{Symbols.WARNING} Mode legacy - Chargement du script original...{Colors.ENDC}")
    
    try:
        # Import et exécution du script legacy
        legacy_path = Path(__file__).parent / "demonstration_epita_legacy.py"
        spec = importlib.util.spec_from_file_location("legacy", legacy_path)
        legacy_module = importlib.util.module_from_spec(spec)
        
        # Simuler les arguments pour le mode normal
        import sys
        original_argv = sys.argv.copy()
        sys.argv = ['demonstration_epita_legacy.py']  # Mode normal
        
        try:
            spec.loader.exec_module(legacy_module)
        finally:
            sys.argv = original_argv
            
    except Exception as e:
        print(f"{Colors.FAIL}Erreur lors de l'exécution du mode legacy : {e}{Colors.ENDC}")

def execute_all_categories_non_interactive(config: Dict[str, Any]) -> None:
    """Exécute toutes les catégories de tests en mode non-interactif avec trace complète."""
    logger = DemoLogger("all_tests")
    
    # Bannière pour le mode all-tests
    print(f"""
{Colors.CYAN}{Colors.BOLD}
+==============================================================================+
|              [EPITA] MODE --ALL-TESTS - Trace Complète Non-Interactive     |
|                     Exécution de toutes les catégories                     |
+==============================================================================+
{Colors.ENDC}""")
    
    start_time = time.time()
    categories = config.get('categories', {})
    categories_triees = sorted(categories.items(), key=lambda x: x[1]['id'])
    
    logger.info(f"{Symbols.ROCKET} Début de l'exécution complète - {len(categories_triees)} catégories à traiter")
    logger.info(f"[TIME] Timestamp de démarrage : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Statistiques globales
    total_categories = len(categories_triees)
    categories_reussies = 0
    categories_echouees = 0
    resultats_detailles = []
    
    for i, (cat_id, cat_info) in enumerate(categories_triees, 1):
        nom_module = cat_info.get('module', '')
        nom_cat = cat_info.get('nom', cat_id)
        icon = cat_info.get('icon', '•')
        description = cat_info.get('description', '')
        
        print(f"\n{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.CYAN}{icon} CATÉGORIE {i}/{total_categories} : {nom_cat}{Colors.ENDC}")
        print(f"{Colors.BLUE}Description : {description}{Colors.ENDC}")
        print(f"{Colors.WARNING}Module : {nom_module}{Colors.ENDC}")
        print(f"{'=' * 80}")
        
        cat_start_time = time.time()
        
        try:
            # Exécution non-interactive du module
            logger.info(f"[CAT] Début exécution catégorie : {nom_cat}")
            succes = charger_et_executer_module(nom_module, mode_interactif=False)
            cat_end_time = time.time()
            cat_duration = cat_end_time - cat_start_time
            
            if succes:
                categories_reussies += 1
                status = "SUCCÈS"
                color = Colors.GREEN
                symbol = Symbols.CHECK
                logger.success(f"{Symbols.CHECK} Catégorie '{nom_cat}' terminée avec succès en {cat_duration:.2f}s")
            else:
                categories_echouees += 1
                status = "ÉCHEC"
                color = Colors.FAIL
                symbol = Symbols.CROSS
                logger.error(f"[FAIL] Échec de la catégorie '{nom_cat}' après {cat_duration:.2f}s")
            
            resultats_detailles.append({
                'categorie': nom_cat,
                'module': nom_module,
                'status': status,
                'duration': cat_duration,
                'index': i
            })
            
            print(f"\n{color}{symbol} Statut : {status} (durée: {cat_duration:.2f}s){Colors.ENDC}")
            
        except Exception as e:
            categories_echouees += 1
            cat_end_time = time.time()
            cat_duration = cat_end_time - cat_start_time
            
            logger.error(f"[ERROR] Erreur critique dans la catégorie '{nom_cat}': {e}")
            print(f"\n{Colors.FAIL}{Symbols.CROSS} ERREUR CRITIQUE : {e}{Colors.ENDC}")
            
            resultats_detailles.append({
                'categorie': nom_cat,
                'module': nom_module,
                'status': 'ERREUR',
                'duration': cat_duration,
                'index': i,
                'erreur': str(e)
            })
    
    # Rapport final
    end_time = time.time()
    total_duration = end_time - start_time
    taux_reussite = (categories_reussies / total_categories) * 100 if total_categories > 0 else 0
    
    print(f"\n{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.CYAN}{Colors.BOLD}           RAPPORT FINAL - EXÉCUTION COMPLÈTE{Colors.ENDC}")
    print(f"{'=' * 80}")
    
    print(f"\n{Colors.BOLD}[STATS] STATISTIQUES GÉNÉRALES :{Colors.ENDC}")
    print(f"   [TIME] Timestamp de fin : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   [TIME] Durée totale : {total_duration:.2f} secondes")
    print(f"   [INFO] Total catégories : {total_categories}")
    print(f"   [OK] Catégories réussies : {categories_reussies}")
    print(f"   [FAIL] Catégories échouées : {categories_echouees}")
    print(f"   [CHART] Taux de réussite : {taux_reussite:.1f}%")
    
    print(f"\n{Colors.BOLD}[INFO] DÉTAILS PAR CATÉGORIE :{Colors.ENDC}")
    for resultat in resultats_detailles:
        status_color = Colors.GREEN if resultat['status'] == 'SUCCÈS' else Colors.FAIL
        status_symbol = '[OK]' if resultat['status'] == 'SUCCÈS' else '[FAIL]'
        
        print(f"   {status_symbol} {resultat['index']:2d}. {resultat['categorie']:<30} "
              f"{status_color}[{resultat['status']}]{Colors.ENDC} "
              f"({resultat['duration']:.2f}s)")
        
        if 'erreur' in resultat:
            print(f"      [ERROR] Erreur: {resultat['erreur']}")
    
    # Métriques techniques
    print(f"\n{Colors.BOLD}[TECH] MÉTRIQUES TECHNIQUES :{Colors.ENDC}")
    print(f"   [PYTHON] Architecture : {config.get('config', {}).get('architecture', 'Python + Java (JPype)')}")
    print(f"   [VERSION] Version : {config.get('config', {}).get('version', '2.0.0')}")
    print(f"   [TARGET] Taux succès tests : {config.get('config', {}).get('taux_succes_tests', 99.7)}%")
    
    domaines = config.get('config', {}).get('domaines', [])
    if domaines:
        print(f"   [BRAIN] Domaines couverts :")
        for domaine in domaines:
            print(f"      • {domaine}")
    
    # Message final
    if categories_echouees == 0:
        final_color = Colors.GREEN
        final_message = f"[SUCCESS] EXÉCUTION COMPLÈTE RÉUSSIE - Tous les tests ont été exécutés avec succès !"
        logger.success(final_message)
    else:
        final_color = Colors.WARNING
        final_message = f"[WARNING] EXÉCUTION TERMINÉE AVEC {categories_echouees} ÉCHEC(S)"
        logger.warning(final_message)
    
    print(f"\n{final_color}{Colors.BOLD}{final_message}{Colors.ENDC}")
    print(f"{'=' * 80}")

def parse_arguments():
    """Parse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(
        description="Script de démonstration EPITA - Architecture Modulaire v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes disponibles :
  [défaut]           Menu interactif catégorisé
  --interactive      Mode interactif avec pauses pédagogiques
  --quick-start      Mode Quick Start pour étudiants
  --metrics          Affichage des métriques uniquement
  --all-tests        Exécution complète non-interactive de toutes les catégories
  --legacy           Exécution du script original (compatibilité)
        """
    )
    
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Mode interactif avec pauses pédagogiques')
    parser.add_argument('--quick-start', '-q', action='store_true',
                       help='Mode Quick Start pour étudiants')
    parser.add_argument('--metrics', '-m', action='store_true',
                       help='Affichage des métriques uniquement')
    parser.add_argument('--legacy', '-l', action='store_true',
                       help='Exécution du script original (compatibilité)')
    parser.add_argument('--all-tests', action='store_true',
                       help='Exécute tous les tests de toutes les catégories en mode non-interactif')
    
    return parser.parse_args()

def main():
    """Fonction principale"""
    # Validation de l'environnement
    if not valider_environnement():
        print(f"{Colors.FAIL}Environnement non valide. Exécutez depuis la racine du projet.{Colors.ENDC}")
        sys.exit(1)
    
    # Parse des arguments
    args = parse_arguments()
    
    # Chargement de la configuration
    config = charger_config_categories()
    if not config:
        print(f"{Colors.FAIL}Impossible de charger la configuration. Exécution en mode legacy.{Colors.ENDC}")
        mode_execution_legacy()
        return
    
    # Sélection du mode d'exécution
    if args.all_tests:
        execute_all_categories_non_interactive(config)
    elif args.quick_start:
        mode_quick_start()
    elif args.metrics:
        mode_metrics_only(config)
    elif args.legacy:
        mode_execution_legacy()
    elif args.interactive:
        # Mode interactif avancé - exécution séquentielle des modules
        logger = DemoLogger("demo_complet")
        logger.header("[EPITA] DÉMONSTRATION COMPLÈTE - MODE INTERACTIF")
        
        categories = config.get('categories', {})
        categories_triees = sorted(categories.items(), key=lambda x: x[1]['id'])
        
        for i, (cat_id, cat_info) in enumerate(categories_triees, 1):
            nom_module = cat_info.get('module', '')
            nom_cat = cat_info.get('nom', cat_id)
            
            afficher_progression(i, len(categories_triees), f"Module : {nom_cat}")
            
            if confirmer_action(f"Exécuter '{nom_cat}' ?"):
                charger_et_executer_module(nom_module, mode_interactif=True)
            
            if i < len(categories_triees):
                pause_interactive()
        
        logger.success("🎓 Démonstration complète terminée !")
    else:
        # Mode menu interactif par défaut
        mode_menu_interactif(config)

if __name__ == "__main__":
    main()