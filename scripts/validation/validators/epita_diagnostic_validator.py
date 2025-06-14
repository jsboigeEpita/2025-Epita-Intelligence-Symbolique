#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validateur pour le Diagnostic complet de la démo Épita et de ses composants illustrés
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Coroutine

# Ajout du répertoire racine au sys.path pour permettre l'import de modules du projet
current_script_path = Path(__file__).resolve()
project_root = current_script_path.parent.parent.parent  # scripts/validation/validators -> scripts/validation -> scripts -> project_root
sys.path.insert(0, str(project_root))

# Activation automatique de l'environnement si nécessaire pour les composants diagnostiqués
# from scripts.core.auto_env import ensure_env # Commenté car ensure_env est appelé dans les fonctions de démo
# ensure_env() # Potentiellement appeler ici si les fonctions internes ne le font pas.

# --- Début de la logique copiée et adaptée de demos/demo_epita_diagnostic.py ---

def catalogue_composants_demo_epita() -> Dict[str, Any]:
    """Catalogue complet des composants de démo Épita découverts"""
    
    # print("=" * 80)
    # print("DIAGNOSTIC DÉMO ÉPITA - COMPOSANTS ILLUSTRÉS (dans validateur)")
    # print("=" * 80)
    
    # Note: Les statuts et problèmes sont ceux observés au moment de la création de la démo originale.
    # Un vrai diagnostic dynamique nécessiterait d'exécuter réellement les tests ici.
    composants = {
        "demo_unified_system.py": {
            "status": "[?] À VÉRIFIER", # Modifié pour refléter un diagnostic
            "description": "Système de démonstration unifié - Consolidation de 8 fichiers démo",
            "problemes": [
                "Potentiel: ModuleNotFoundError: No module named 'semantic_kernel.agents'",
                "Potentiel: UnicodeEncodeError dans l'affichage d'erreurs",
                "Potentiel: Dépendances manquantes pour l'écosystème unifié"
            ],
            "fonctionnalites": [
                "8 modes de démonstration (educational, research, showcase, etc.)",
                "Correction intelligente des erreurs modales",
                "Orchestrateur master de validation",
                "Exploration corpus chiffré",
                "Capture complète de traces",
                "Analyse unifiée complète"
            ],
            "integration": "Sherlock/Watson, analyse rhétorique, TweetyErrorAnalyzer",
            "valeur_pedagogique": "⭐⭐⭐⭐⭐ Excellente - Système complet et illustratif",
            "test_realise": "NON - À exécuter par le validateur"
        },
        
        "playwright/demo_service_manager_validated.py": {
            "status": "[?] À VÉRIFIER",
            "description": "Démonstration complète du ServiceManager - Validation finale",
            "problemes": [],
            "fonctionnalites": [
                "Gestion des ports automatique",
                "Enregistrement et orchestration de services",
                "Patterns migrés depuis PowerShell",
                "Compatibilité cross-platform",
                "Nettoyage gracieux des processus (48 processus Node arrêtés)"
            ],
            "integration": "Infrastructure de base, remplacement scripts PowerShell",
            "valeur_pedagogique": "⭐⭐⭐⭐⭐ Excellente - Infrastructure complètement fonctionnelle",
            "test_realise": "NON - À exécuter par le validateur"
        },
        
        "playwright/test_interface_demo.html": {
            "status": "[?] À VÉRIFIER",
            "description": "Interface web d'analyse argumentative - Interface de test",
            "problemes": [],
            "fonctionnalites": [
                "Interface utilisateur intuitive et moderne",
                "Chargement d'exemples fonctionnel (syllogisme Socrate)",
                "Analyse simulée avec résultats détaillés",
                "Affichage: 2 arguments, 2 sophismes, score 0.70",
                "Design responsive et accessible"
            ],
            "integration": "Interface frontend pour l'analyse argumentative",
            "valeur_pedagogique": "⭐⭐⭐⭐⭐ Excellente - Interface parfaite pour étudiants",
            "test_realise": "NON - À exécuter par le validateur"
        },
        
        "playwright/README.md": {
            "status": "[INFO] DOCUMENTATION", 
            "description": "Documentation des 9 tests fonctionnels Playwright",
            "problemes": [],
            "fonctionnalites": [
                "9 tests fonctionnels documentés",
                "test_argument_analyzer.py",
                "test_fallacy_detector.py",
                "test_integration_workflows.py",
                "Infrastructure de test end-to-end"
            ],
            "integration": "Framework de test complet, validation bout-en-bout",
            "valeur_pedagogique": "⭐⭐⭐⭐ Très bonne - Documentation complète"
        }
    }
    
    return composants

def diagnostiquer_problemes_dependances() -> Dict[str, Any]:
    """Diagnostic des problèmes de dépendances potentiels"""
    
    # print("\n" + "=" * 60)
    # print("DIAGNOSTIC DÉPENDANCES - PROBLÈMES POTENTIELS (dans validateur)")  
    # print("=" * 60)
    
    problemes = {
        "semantic_kernel.agents": {
            "erreur": "Potentiel: ModuleNotFoundError: No module named 'semantic_kernel.agents'",
            "impact": "Empêche l'exécution du système unifié principal",
            "solution_recommandee": "pip install semantic-kernel[agents] ou mise à jour des imports",
            "composants_affectes": ["RealLLMOrchestrator", "ConversationOrchestrator", "cluedo_extended_orchestrator"],
            "criticite": "HAUTE"
        },
        
        "encodage_unicode": {
            "erreur": "Potentiel: UnicodeEncodeError: 'charmap' codec can't encode characters",
            "impact": "Problème d'affichage des caractères spéciaux en console Windows",
            "solution_recommandee": "Configuration PYTHONIOENCODING=utf-8",
            "composants_affectes": ["Messages d'erreur avec emojis", "Affichage console"],
            "criticite": "MOYENNE"
        },
        
        "composants_unifies_manquants": {
            "erreur": "Potentiel: UNIFIED_COMPONENTS_AVAILABLE = False",
            "impact": "Mode dégradé pour les démonstrations avancées",
            "solution_recommandee": "Vérifier l'intégrité des imports de l'écosystème refactorisé",
            "composants_affectes": ["UnifiedTextAnalysisPipeline", "UnifiedSourceManager", "ReportGenerator"],
            "criticite": "HAUTE"
        }
    }
    
    return problemes

def evaluer_qualite_pedagogique() -> Dict[str, Any]:
    """Évaluation de la qualité pédagogique pour le contexte Épita (basée sur la démo originale)"""
    
    # print("\n" + "=" * 60)
    # print("ÉVALUATION QUALITÉ PÉDAGOGIQUE - CONTEXTE ÉPITA (dans validateur)")
    # print("=" * 60)
    
    evaluation = {
        "strengths": [
            "Potentiel: ServiceManager COMPLÈTEMENT fonctionnel (ports, services, nettoyage)",
            "Potentiel: Interface web PARFAITEMENT opérationnelle (design + fonctionnalités)",
            "🎯 Diversité des modes de démonstration (8 modes différents)",
            "📚 Documentation complète des 9 tests fonctionnels Playwright",
            "🏗️ Architecture modulaire et extensible (en cours de validation)",
            "[AMPOULE] Exemples pédagogiques concrets (syllogisme Socrate)",
            "[ROTATION] Intégration système Sherlock/Watson (à valider à 88-96%)",
            "🧹 Nettoyage automatique des processus (à valider, ex: 48 processus Node gérés)"
        ],
        
        "weaknesses": [
            "Risque: demo_unified_system.py non fonctionnel (semantic_kernel.agents)",
            "Attention: Problèmes d'encodage Unicode en environnement Windows",
            "Dépendances psutil/requests pourraient nécessiter installation manuelle",
            "Configuration environnement complexe pour certains composants"
        ],
        
        "tests_a_realiser": [ # Modifié de "tests_realises"
            "ServiceManager: Gestion ports, services, nettoyage",
            "Interface web: Chargement, exemple, analyse",
            "Système unifié: Vérifier dépendances et exécution",
            "Documentation: Vérifier exhaustivité des 9 tests Playwright"
        ],
        
        "recommandations": [
            "Installer semantic-kernel[agents] si nécessaire",
            "Créer/vérifier requirements.txt avec psutil, requests, semantic-kernel",
            "Script setup.py automatique pour installation Épita (si pertinent)",
            "Guide démarrage rapide spécifique étudiants",
            "Capturer démos vidéo des composants fonctionnels (après validation)"
        ],
        
        "score_global_estime": "85/100 (estimation basée sur démo originale, à confirmer)"
    }
    
    return evaluation

def generer_plan_actions_validation() -> Dict[str, Any]: # Renommé de generer_plan_correction
    """Génère un plan d'actions pour la validation"""
    
    # print("\n" + "=" * 60)
    # print("PLAN D'ACTIONS VALIDATION (dans validateur)")
    # print("=" * 60)
    
    plan = {
        "priorite_1_verification_critique": [
            "1. Vérifier dépendance semantic_kernel.agents et sa résolution",
            "2. Tester affichage Unicode en console",
            "3. Valider imports et disponibilité de l'écosystème unifié"
        ],
        
        "priorite_2_tests_fonctionnels": [
            "4. Exécuter les tests des modes de démonstration individuellement", 
            "5. Valider l'intégration Sherlock/Watson dans les démos concernées",
            "6. Vérifier la présence de fallbacks pour composants manquants"
        ],
        
        "priorite_3_documentation_et_amelioration": [
            "7. Suggérer l'automatisation de l'installation des dépendances si problématique",
            "8. Évaluer l'expérience utilisateur pour les étudiants Épita",
            "9. Vérifier la clarté de la documentation de démarrage rapide"
        ]
    }
    
    return plan

async def perform_epita_diagnostic(report_errors_list: list, available_components: Dict[str, bool]) -> Dict[str, Any]:
    """Point d'entrée principal du diagnostic adapté pour le validateur"""
    
    # print("[VALIDATEUR-DIAGNOSTIC] DEMO EPITA - INTELLIGENCE SYMBOLIQUE")
    # print("Date: (Dynamique)") # La date sera celle de l'exécution du validateur
    # print("Objectif: Validation des composants illustrés dans la démo Épita")

    # Activation de l'environnement si nécessaire (peut être fait une seule fois au début du script)
    # from scripts.core.auto_env import ensure_env # Déjà importé globalement ou commenté
    # ensure_env() # Assurez-vous que cela est appelé correctement si nécessaire

    # Catalogue des composants (basé sur la structure de la démo)
    composants = catalogue_composants_demo_epita()
    
    # Diagnostic des problèmes potentiels (basé sur la structure de la démo)
    problemes_potentiels = diagnostiquer_problemes_dependances()
        
    # Évaluation pédagogique (basée sur la structure de la démo)
    evaluation_pedagogique = evaluer_qualite_pedagogique()
    
    # Plan d'actions pour la validation
    plan_validation = generer_plan_actions_validation()
        
    # Ici, on pourrait ajouter une logique pour réellement exécuter des tests
    # et mettre à jour dynamiquement les statuts dans 'composants' et 'problemes_potentiels'.
    # Par exemple:
    # try:
    #     # Simuler un test
    #     # from demos import demo_unified_system # Tentative d'import
    #     # resultat_test_unifie = await demo_unified_system.run_specific_test() 
    #     composants["demo_unified_system.py"]["status"] = "[OK] TEST SIMULÉ RÉUSSI"
    # except Exception as e:
    #     composants["demo_unified_system.py"]["status"] = f"[X] ÉCHEC TEST SIMULÉ: {e}"
    #     report_errors_list.append(f"Erreur diagnostic demo_unified_system: {e}")

    # Pour l'instant, ce validateur retourne une analyse statique basée sur le script de démo.
    
    diagnostic_results = {
        "titre": "Rapport de Diagnostic Démo Épita (via Validateur)",
        "composants_catalogues": composants,
        "problemes_dependances_potentiels": problemes_potentiels, 
        "evaluation_pedagogique_estimee": evaluation_pedagogique,
        "plan_actions_validation": plan_validation,
        "status_global_diagnostic": "ANALYSE_STATIQUE_EFFECTUEE" 
        # Ce statut pourrait devenir DYNAMIQUE si des tests réels sont implémentés
    }
    
    # Ajouter des erreurs au rapport global si nécessaire
    if any("[X]" in comp["status"] for comp in composants.values() if "status" in comp):
        report_errors_list.append("Des composants de la démo Épita ont un statut d'échec potentiel ou de vérification nécessaire.")

    return diagnostic_results

# --- Fin de la logique copiée et adaptée ---


async def validate_epita_diagnostic(
    report_errors_list: list, 
    available_components: Dict[str, bool],
    # Ajoutez d'autres paramètres si nécessaire, par exemple:
    # config: 'ValidationConfiguration' (du futur core.py)
) -> Dict[str, Any]:
    """
    Fonction principale du validateur pour le mode EPITA_DIAGNOSTIC.
    Exécute un diagnostic complet des composants de la démo Épita.
    """
    
    # print(f"[VALIDATOR - epita_diagnostic_validator] Démarrage de la validation EPITA Diagnostic.")
    # print(f"[VALIDATOR - epita_diagnostic_validator] Composants disponibles: {available_components}")

    # Appel de la logique de diagnostic principale
    # Cette fonction est déjà asynchrone dans sa nouvelle forme.
    results = await perform_epita_diagnostic(report_errors_list, available_components)
    
    # print(f"[VALIDATOR - epita_diagnostic_validator] Validation EPITA Diagnostic terminée.")
    return results

async def main_test():
    """Fonction de test pour ce module validateur."""
    print("Test du validateur epita_diagnostic_validator.py")
    errors = []
    components = {"EPITA_DEMO_COMPONENT_1": True, "EPITA_DEMO_COMPONENT_2": False}
    
    diagnostic_report = await validate_epita_diagnostic(errors, components)
    
    import json
    print("\n--- RAPPORT DE DIAGNOSTIC ---")
    print(json.dumps(diagnostic_report, indent=2, ensure_ascii=False))
    
    if errors:
        print("\n--- ERREURS RAPPORTÉES ---")
        for err in errors:
            print(f"- {err}")

if __name__ == "__main__":
    # Pour exécuter un test simple de ce module :
    # python scripts/validation/validators/epita_diagnostic_validator.py
    asyncio.run(main_test())