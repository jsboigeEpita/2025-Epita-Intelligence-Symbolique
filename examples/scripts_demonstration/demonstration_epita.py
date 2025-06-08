# -*- coding: utf-8 -*-
"""
Script principal de démonstration EPITA - Architecture Modulaire
Intelligence Symbolique - Menu Catégorisé + Validation Données Custom

VERSION 2.1 - Ajout validation avec données dédiées en paramètre
Détection automatique des mocks vs traitement réel

Utilisation :
  python demonstration_epita.py                    # Menu interactif
  python demonstration_epita.py --interactive      # Mode interactif avec modules
  python demonstration_epita.py --quick-start      # Quick start étudiants
  python demonstration_epita.py --metrics          # Métriques seulement
  python demonstration_epita.py --validate-custom  # Validation avec données dédiées
  python demonstration_epita.py --custom-data "texte"  # Test avec données custom
"""

import sys
import os
import argparse
import importlib.util
import subprocess
import time
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime

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

# Classes pour la validation avec données dédiées
@dataclass
class CustomTestDataset:
    """Dataset de test personnalisé pour validation Épita."""
    name: str
    content: str
    content_hash: str
    expected_indicators: List[str]
    test_purpose: str
    marker: str

@dataclass
class ValidationResult:
    """Résultat de validation d'un test."""
    dataset_name: str
    mode_tested: str
    timestamp: str
    success: bool
    output_captured: str
    real_processing_detected: bool
    mock_detected: bool
    custom_data_processed: bool
    execution_time: float
    error: str = ""

class EpitaValidator:
    """Validateur pour détecter mocks vs traitement réel."""
    
    def __init__(self):
        self.real_indicators = [
            "analyse en cours", "traitement", "parsing", "détection",
            "calcul", "métrique", "score", "résultat", "argument", "sophisme"
        ]
        self.mock_indicators = [
            "simulation", "mock", "exemple générique", "données factices",
            "placeholder", "test pattern", "demo content"
        ]
    
    def create_custom_datasets(self) -> List[CustomTestDataset]:
        """Crée des datasets avec marqueurs uniques."""
        timestamp = int(time.time())
        datasets = []
        
        # Dataset 1: Logique Épita avec marqueur unique
        content1 = f"[EPITA_VALID_{timestamp}] Tous les algorithmes Épita sont optimisés. Cet algorithme est optimisé. Donc cet algorithme est un algorithme Épita."
        datasets.append(CustomTestDataset(
            name="logique_epita_custom",
            content=content1,
            content_hash=hashlib.md5(content1.encode()).hexdigest(),
            expected_indicators=["syllogisme", "logique", "prémisse"],
            test_purpose="Test logique avec identifiant unique",
            marker=f"EPITA_VALID_{timestamp}"
        ))
        
        # Dataset 2: Sophisme technique avec marqueur
        content2 = f"[EPITA_TECH_{timestamp + 1}] Cette technologie est adoptée par 90% des entreprises. Notre projet doit donc l'utiliser pour réussir."
        datasets.append(CustomTestDataset(
            name="sophisme_tech_custom",
            content=content2,
            content_hash=hashlib.md5(content2.encode()).hexdigest(),
            expected_indicators=["argumentum ad populum", "sophisme", "fallacy"],
            test_purpose="Détection sophisme technique",
            marker=f"EPITA_TECH_{timestamp + 1}"
        ))
        
        # Dataset 3: Unicode et caractères spéciaux
        content3 = f"[EPITA_UNICODE_{timestamp + 2}] Algorithme: O(n²) → O(n log n) 🚀 Performance: +100% ✓ Café ☕"
        datasets.append(CustomTestDataset(
            name="unicode_test_custom",
            content=content3,
            content_hash=hashlib.md5(content3.encode()).hexdigest(),
            expected_indicators=["algorithme", "complexité", "unicode"],
            test_purpose="Test robustesse Unicode",
            marker=f"EPITA_UNICODE_{timestamp + 2}"
        ))
        
        return datasets
    
    def validate_with_dataset(self, dataset: CustomTestDataset, module_func, mode: str) -> ValidationResult:
        """Valide un module avec un dataset custom."""
        start_time = time.time()
        
        try:
            # Créer un fichier temporaire avec les données custom
            temp_file = Path(f"temp_epita_test_{dataset.name}_{int(time.time())}.txt")
            temp_file.write_text(dataset.content, encoding='utf-8')
            
            # Capturer stdout/stderr pour analyser la sortie
            import io
            import contextlib
            
            captured_output = io.StringIO()
            
            with contextlib.redirect_stdout(captured_output), contextlib.redirect_stderr(captured_output):
                try:
                    if hasattr(module_func, '__call__'):
                        # Tenter de passer les données custom au module
                        result = module_func() if not module_func.__code__.co_argcount else module_func(dataset.content)
                    else:
                        result = True
                except Exception as e:
                    result = False
            
            output = captured_output.getvalue()
            execution_time = time.time() - start_time
            
            # Analyser la sortie pour détecter traitement réel vs mock
            real_processing = any(indicator.lower() in output.lower() for indicator in self.real_indicators)
            mock_detected = any(indicator.lower() in output.lower() for indicator in self.mock_indicators)
            
            # Vérifier si le marqueur custom apparaît (preuve que les données ont été lues)
            custom_data_processed = (dataset.marker in output or
                                   dataset.content_hash in output or
                                   any(expected.lower() in output.lower() for expected in dataset.expected_indicators))
            
            # Nettoyer le fichier temporaire
            if temp_file.exists():
                temp_file.unlink()
            
            return ValidationResult(
                dataset_name=dataset.name,
                mode_tested=mode,
                timestamp=datetime.now().isoformat(),
                success=result is not False,
                output_captured=output[:500],  # Limiter la sortie
                real_processing_detected=real_processing,
                mock_detected=mock_detected,
                custom_data_processed=custom_data_processed,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return ValidationResult(
                dataset_name=dataset.name,
                mode_tested=mode,
                timestamp=datetime.now().isoformat(),
                success=False,
                output_captured="",
                real_processing_detected=False,
                mock_detected=False,
                custom_data_processed=False,
                execution_time=execution_time,
                error=str(e)
            )

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

def mode_validation_custom_data(config: Dict[str, Any]) -> None:
    """Mode validation avec données dédiées pour détecter mocks vs réel."""
    logger = DemoLogger("validation_custom")
    
    print(f"""
{Colors.CYAN}{Colors.BOLD}
+==============================================================================+
|              [EPITA] VALIDATION AVEC DONNÉES DÉDIÉES                        |
|                   Détection Mocks vs Traitement Réel                        |
+==============================================================================+
{Colors.ENDC}""")
    
    validator = EpitaValidator()
    datasets = validator.create_custom_datasets()
    
    logger.info(f"🧪 Création de {len(datasets)} datasets de test personnalisés")
    
    # Tester chaque catégorie avec les datasets custom
    categories = config.get('categories', {})
    categories_triees = sorted(categories.items(), key=lambda x: x[1]['id'])
    
    all_results = []
    
    for cat_id, cat_info in categories_triees:
        nom_module = cat_info.get('module', '')
        nom_cat = cat_info.get('nom', cat_id)
        
        print(f"\n{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
        print(f"{Colors.CYAN}🔍 VALIDATION MODULE: {nom_cat}{Colors.ENDC}")
        print(f"{'=' * 60}")
        
        for dataset in datasets:
            print(f"\n{Colors.WARNING}📊 Test avec dataset: {dataset.name}{Colors.ENDC}")
            print(f"   Marqueur: {dataset.marker}")
            print(f"   Objectif: {dataset.test_purpose}")
            
            try:
                # Charger le module et tester avec le dataset
                module_path = modules_path / f"{nom_module}.py"
                if module_path.exists():
                    spec = importlib.util.spec_from_file_location(nom_module, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Trouver la fonction de démo appropriée
                    demo_func = None
                    if hasattr(module, 'run_demo_rapide'):
                        demo_func = module.run_demo_rapide
                    elif hasattr(module, 'run_demo_interactive'):
                        demo_func = module.run_demo_interactive
                    
                    if demo_func:
                        result = validator.validate_with_dataset(dataset, demo_func, nom_cat)
                        all_results.append(result)
                        
                        # Afficher les résultats
                        if result.success:
                            print(f"   {Colors.GREEN}✅ Exécution: SUCCÈS{Colors.ENDC}")
                        else:
                            print(f"   {Colors.FAIL}❌ Exécution: ÉCHEC{Colors.ENDC}")
                        
                        if result.custom_data_processed:
                            print(f"   {Colors.GREEN}📝 Données custom: TRAITÉES{Colors.ENDC}")
                        else:
                            print(f"   {Colors.WARNING}📝 Données custom: NON DÉTECTÉES{Colors.ENDC}")
                        
                        if result.real_processing_detected:
                            print(f"   {Colors.GREEN}🔧 Traitement réel: DÉTECTÉ{Colors.ENDC}")
                        else:
                            print(f"   {Colors.WARNING}🔧 Traitement réel: NON DÉTECTÉ{Colors.ENDC}")
                        
                        if result.mock_detected:
                            print(f"   {Colors.FAIL}🎭 Mocks détectés: OUI{Colors.ENDC}")
                        else:
                            print(f"   {Colors.GREEN}🎭 Mocks détectés: NON{Colors.ENDC}")
                        
                        print(f"   ⏱️ Temps d'exécution: {result.execution_time:.3f}s")
                        
                        if result.error:
                            print(f"   {Colors.FAIL}💥 Erreur: {result.error}{Colors.ENDC}")
                    else:
                        print(f"   {Colors.WARNING}⚠️ Aucune fonction de démo trouvée{Colors.ENDC}")
                else:
                    print(f"   {Colors.FAIL}❌ Module non trouvé: {module_path}{Colors.ENDC}")
                    
            except Exception as e:
                print(f"   {Colors.FAIL}💥 Erreur lors du test: {e}{Colors.ENDC}")
    
    # Rapport final de validation
    print(f"\n{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.CYAN}{Colors.BOLD}           RAPPORT FINAL - VALIDATION DONNÉES CUSTOM{Colors.ENDC}")
    print(f"{'=' * 80}")
    
    if all_results:
        total_tests = len(all_results)
        success_tests = sum(1 for r in all_results if r.success)
        real_processing_tests = sum(1 for r in all_results if r.real_processing_detected)
        custom_data_tests = sum(1 for r in all_results if r.custom_data_processed)
        mock_detected_tests = sum(1 for r in all_results if r.mock_detected)
        
        print(f"\n{Colors.BOLD}📊 STATISTIQUES GÉNÉRALES:{Colors.ENDC}")
        print(f"   Total tests effectués: {total_tests}")
        print(f"   Tests réussis: {success_tests}/{total_tests} ({success_tests/total_tests*100:.1f}%)")
        print(f"   Traitement réel détecté: {real_processing_tests}/{total_tests} ({real_processing_tests/total_tests*100:.1f}%)")
        print(f"   Données custom traitées: {custom_data_tests}/{total_tests} ({custom_data_tests/total_tests*100:.1f}%)")
        print(f"   Mocks détectés: {mock_detected_tests}/{total_tests} ({mock_detected_tests/total_tests*100:.1f}%)")
        
        print(f"\n{Colors.BOLD}🎯 ÉVALUATION CAPACITÉS:{Colors.ENDC}")
        if custom_data_tests > total_tests * 0.7:
            print(f"   {Colors.GREEN}✅ EXCELLENTE acceptation des données custom{Colors.ENDC}")
        elif custom_data_tests > total_tests * 0.4:
            print(f"   {Colors.WARNING}⚠️ MODÉRÉE acceptation des données custom{Colors.ENDC}")
        else:
            print(f"   {Colors.FAIL}❌ FAIBLE acceptation des données custom{Colors.ENDC}")
        
        if real_processing_tests > total_tests * 0.6:
            print(f"   {Colors.GREEN}✅ TRAITEMENT RÉEL prédominant{Colors.ENDC}")
        else:
            print(f"   {Colors.WARNING}⚠️ MOCKS ou simulations détectés{Colors.ENDC}")
        
        # Sauvegarder le rapport détaillé
        rapport_path = Path("logs") / f"validation_epita_custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        rapport_path.parent.mkdir(exist_ok=True)
        
        with open(rapport_path, 'w', encoding='utf-8') as f:
            json.dump([result.__dict__ for result in all_results], f, indent=2, ensure_ascii=False)
        
        print(f"\n{Colors.BLUE}📄 Rapport détaillé sauvegardé: {rapport_path}{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}❌ Aucun résultat de validation généré{Colors.ENDC}")

def mode_custom_data_test(custom_text: str, config: Dict[str, Any]) -> None:
    """Test avec des données custom spécifiques fournies par l'utilisateur."""
    logger = DemoLogger("custom_data_test")
    
    print(f"""
{Colors.CYAN}{Colors.BOLD}
+==============================================================================+
|              [EPITA] TEST AVEC DONNÉES CUSTOM SPÉCIFIQUES                   |
|                        Texte fourni par l'utilisateur                       |
+==============================================================================+
{Colors.ENDC}""")
    
    print(f"\n{Colors.BOLD}📝 DONNÉES À TESTER:{Colors.ENDC}")
    print(f"   Longueur: {len(custom_text)} caractères")
    print(f"   Hash: {hashlib.md5(custom_text.encode()).hexdigest()[:8]}...")
    print(f"   Aperçu: {custom_text[:100]}{'...' if len(custom_text) > 100 else ''}")
    
    # Créer un dataset custom avec les données utilisateur
    timestamp = int(time.time())
    marker = f"USER_DATA_{timestamp}"
    custom_dataset = CustomTestDataset(
        name="user_provided_data",
        content=f"[{marker}] {custom_text}",
        content_hash=hashlib.md5(custom_text.encode()).hexdigest(),
        expected_indicators=["analyse", "traitement", "résultat"],
        test_purpose="Test avec données utilisateur spécifiques",
        marker=marker
    )
    
    validator = EpitaValidator()
    categories = config.get('categories', {})
    
    print(f"\n{Colors.BOLD}🔍 TEST SUR TOUTES LES CATÉGORIES:{Colors.ENDC}")
    
    results = []
    for cat_id, cat_info in sorted(categories.items(), key=lambda x: x[1]['id']):
        nom_module = cat_info.get('module', '')
        nom_cat = cat_info.get('nom', cat_id)
        
        print(f"\n{Colors.CYAN}📊 {nom_cat}:{Colors.ENDC}")
        
        try:
            module_path = modules_path / f"{nom_module}.py"
            if module_path.exists():
                spec = importlib.util.spec_from_file_location(nom_module, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                demo_func = getattr(module, 'run_demo_rapide', None) or getattr(module, 'run_demo_interactive', None)
                
                if demo_func:
                    result = validator.validate_with_dataset(custom_dataset, demo_func, nom_cat)
                    results.append(result)
                    
                    status = "✅ SUCCÈS" if result.success else "❌ ÉCHEC"
                    data_processed = "📝 TRAITÉES" if result.custom_data_processed else "📝 NON DÉTECTÉES"
                    real_processing = "🔧 RÉEL" if result.real_processing_detected else "🔧 SIMULÉ"
                    
                    print(f"   {status} | {data_processed} | {real_processing} | ⏱️ {result.execution_time:.3f}s")
                else:
                    print(f"   {Colors.WARNING}⚠️ Fonction de démo non trouvée{Colors.ENDC}")
            else:
                print(f"   {Colors.FAIL}❌ Module non trouvé{Colors.ENDC}")
        except Exception as e:
            print(f"   {Colors.FAIL}💥 Erreur: {str(e)[:50]}...{Colors.ENDC}")
    
    # Résumé final
    if results:
        success_rate = sum(1 for r in results if r.success) / len(results) * 100
        processing_rate = sum(1 for r in results if r.custom_data_processed) / len(results) * 100
        real_rate = sum(1 for r in results if r.real_processing_detected) / len(results) * 100
        
        print(f"\n{Colors.BOLD}📈 RÉSUMÉ VALIDATION DONNÉES CUSTOM:{Colors.ENDC}")
        print(f"   Taux de succès: {success_rate:.1f}%")
        print(f"   Taux de traitement des données: {processing_rate:.1f}%")
        print(f"   Taux de traitement réel: {real_rate:.1f}%")
        
        if processing_rate > 70:
            print(f"   {Colors.GREEN}🎯 CONCLUSION: Les données custom sont bien acceptées et traitées{Colors.ENDC}")
        elif processing_rate > 30:
            print(f"   {Colors.WARNING}🎯 CONCLUSION: Acceptation partielle des données custom{Colors.ENDC}")
        else:
            print(f"   {Colors.FAIL}🎯 CONCLUSION: Les données custom ne semblent pas être traitées{Colors.ENDC}")

def parse_arguments():
    """Parse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(
        description="Script de démonstration EPITA - Architecture Modulaire v2.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes disponibles :
  [défaut]           Menu interactif catégorisé
  --interactive      Mode interactif avec pauses pédagogiques
  --quick-start      Mode Quick Start pour étudiants
  --metrics          Affichage des métriques uniquement
  --all-tests        Exécution complète non-interactive de toutes les catégories
  --validate-custom  Validation avec datasets dédiés pour détecter mocks vs réel
  --custom-data      Test avec des données custom spécifiques
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
    parser.add_argument('--validate-custom', action='store_true',
                       help='Mode validation avec données dédiées pour détecter mocks vs traitement réel')
    parser.add_argument('--custom-data', type=str, metavar='TEXT',
                       help='Test avec des données custom spécifiques fournies en paramètre')
    
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
    if args.validate_custom:
        mode_validation_custom_data(config)
    elif args.custom_data:
        mode_custom_data_test(args.custom_data, config)
    elif args.all_tests:
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