#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Démo complète du système d'analyse rhétorique unifié

Ce script teste les différentes capacités du système :
1. Analyse rhétorique basique
2. Analyse multi-agents complexe
3. Détection de sophismes et fallacies
4. Construction d'arguments structurés
5. Validation logique des raisonnements
"""

import os
import sys
import asyncio
import logging
import time
import json
from pathlib import Path

# Configuration du chemin
current_dir = Path(__file__).parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("DemoRhetoriqueComplete")

class DemoRhetoriqueResults:
    """Classe pour collecter et organiser les résultats des démos"""
    
    def __init__(self):
        self.results = {
            "demos_executed": [],
            "performance_metrics": {},
            "errors": [],
            "summary": {}
        }
        self.start_time = time.time()
    
    def add_demo_result(self, demo_name: str, status: str, duration: float, details: dict = None):
        """Ajoute le résultat d'une démo"""
        result = {
            "name": demo_name,
            "status": status,
            "duration": duration,
            "timestamp": time.time(),
            "details": details or {}
        }
        self.results["demos_executed"].append(result)
    
    def add_error(self, demo_name: str, error: str, details: str = None):
        """Ajoute une erreur"""
        error_entry = {
            "demo": demo_name,
            "error": error,
            "details": details,
            "timestamp": time.time()
        }
        self.results["errors"].append(error_entry)
    
    def finalize(self):
        """Finalise les résultats avec un résumé"""
        total_duration = time.time() - self.start_time
        successful_demos = [d for d in self.results["demos_executed"] if d["status"] == "success"]
        failed_demos = [d for d in self.results["demos_executed"] if d["status"] == "error"]
        
        self.results["summary"] = {
            "total_duration": total_duration,
            "total_demos": len(self.results["demos_executed"]),
            "successful_demos": len(successful_demos),
            "failed_demos": len(failed_demos),
            "success_rate": len(successful_demos) / len(self.results["demos_executed"]) if self.results["demos_executed"] else 0,
            "average_demo_duration": sum(d["duration"] for d in self.results["demos_executed"]) / len(self.results["demos_executed"]) if self.results["demos_executed"] else 0
        }
        return self.results

# Textes de test pour différents types d'analyses
TEXTES_TEST = {
    "sophismes_basiques": """
    Le réchauffement climatique est un mythe créé par les scientifiques pour obtenir des financements.
    Regardez, il a neigé l'hiver dernier, ce qui prouve que le climat ne se réchauffe pas.
    De plus, des milliers de scientifiques ont signé une pétition contre cette théorie.
    """,
    
    "argumentation_complexe": """
    Les voitures électriques sont présentées comme la solution miracle aux problèmes environnementaux.
    Cependant, leur production nécessite des terres rares dont l'extraction est polluante.
    De plus, l'électricité provient souvent de centrales à charbon.
    Néanmoins, sur le long terme, l'impact environnemental reste inférieur aux voitures thermiques.
    Par conséquent, il faut développer les véhicules électriques tout en améliorant la production d'électricité verte.
    """,
    
    "logique_propositionnelle": """
    Si il pleut, alors la route est mouillée.
    La route n'est pas mouillée.
    Donc, il ne pleut pas.
    
    Tous les chats sont des mammifères.
    Garfield est un chat.
    Donc, Garfield est un mammifère.
    """,
    
    "analyse_informelle": """
    Cette décision politique est catastrophique ! Elle va ruiner notre économie et détruire des milliers d'emplois.
    Comment peut-on faire confiance à un gouvernement qui nous ment constamment ?
    Il faut absolument voter contre cette mesure avant qu'il ne soit trop tard.
    Tous ceux qui la soutiennent sont soit naïfs, soit complices.
    """
}

async def setup_environment_for_demo():
    """Configure l'environnement pour les démos"""
    try:
        # Chargement de l'environnement
        from dotenv import load_dotenv, find_dotenv
        load_dotenv(find_dotenv(), override=True)
        
        # Initialisation JVM
        from argumentation_analysis.core.jvm_setup import initialize_jvm
        from argumentation_analysis.paths import LIBS_DIR
        jvm_status = initialize_jvm(lib_dir_path=LIBS_DIR)
        
        # Création du service LLM
        from argumentation_analysis.core.llm_service import create_llm_service
        llm_service = create_llm_service()
        
        return llm_service, jvm_status
    except Exception as e:
        logger.error(f"Erreur lors de la configuration de l'environnement: {e}")
        raise

async def demo_analyse_basique(llm_service, results: DemoRhetoriqueResults):
    """Démo 1: Analyse rhétorique basique"""
    demo_name = "Analyse Rhétorique Basique"
    logger.info(f"=== {demo_name} ===")
    demo_start = time.time()
    
    try:
        from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
        
        # Analyser un texte simple avec des sophismes
        await run_analysis_conversation(
            texte_a_analyser=TEXTES_TEST["sophismes_basiques"],
            llm_service=llm_service
        )
        
        duration = time.time() - demo_start
        results.add_demo_result(demo_name, "success", duration, {
            "text_length": len(TEXTES_TEST["sophismes_basiques"]),
            "analysis_type": "basic_rhetorical"
        })
        logger.info(f"✅ {demo_name} terminée en {duration:.2f}s")
        
    except Exception as e:
        duration = time.time() - demo_start
        error_msg = str(e)
        results.add_demo_result(demo_name, "error", duration)
        results.add_error(demo_name, error_msg)
        logger.error(f"❌ {demo_name} échouée: {error_msg}")

async def demo_analyse_multi_agents(llm_service, results: DemoRhetoriqueResults):
    """Démo 2: Analyse multi-agents complexe"""
    demo_name = "Analyse Multi-Agents Complexe"
    logger.info(f"=== {demo_name} ===")
    demo_start = time.time()
    
    try:
        from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
        
        # Analyser un texte complexe avec argumentation structurée
        await run_analysis_conversation(
            texte_a_analyser=TEXTES_TEST["argumentation_complexe"],
            llm_service=llm_service
        )
        
        duration = time.time() - demo_start
        results.add_demo_result(demo_name, "success", duration, {
            "text_length": len(TEXTES_TEST["argumentation_complexe"]),
            "analysis_type": "multi_agent_complex"
        })
        logger.info(f"✅ {demo_name} terminée en {duration:.2f}s")
        
    except Exception as e:
        duration = time.time() - demo_start
        error_msg = str(e)
        results.add_demo_result(demo_name, "error", duration)
        results.add_error(demo_name, error_msg)
        logger.error(f"❌ {demo_name} échouée: {error_msg}")

async def demo_detection_sophismes(llm_service, results: DemoRhetoriqueResults):
    """Démo 3: Détection spécialisée de sophismes"""
    demo_name = "Détection de Sophismes et Fallacies"
    logger.info(f"=== {demo_name} ===")
    demo_start = time.time()
    
    try:
        # Utiliser l'exemple rhétorique existant
        from argumentation_analysis.examples.rhetorical_analysis_example import run_rhetorical_analysis_example
        
        await run_rhetorical_analysis_example()
        
        duration = time.time() - demo_start
        results.add_demo_result(demo_name, "success", duration, {
            "analysis_type": "sophism_detection",
            "techniques": ["complex_fallacy_analysis", "contextual_fallacy_analysis"]
        })
        logger.info(f"✅ {demo_name} terminée en {duration:.2f}s")
        
    except Exception as e:
        duration = time.time() - demo_start
        error_msg = str(e)
        results.add_demo_result(demo_name, "error", duration)
        results.add_error(demo_name, error_msg)
        logger.error(f"❌ {demo_name} échouée: {error_msg}")

async def demo_logique_propositionnelle(llm_service, results: DemoRhetoriqueResults):
    """Démo 4: Validation logique propositionnelle"""
    demo_name = "Validation Logique Propositionnelle"
    logger.info(f"=== {demo_name} ===")
    demo_start = time.time()
    
    try:
        from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
        
        # Analyser des arguments logiques
        await run_analysis_conversation(
            texte_a_analyser=TEXTES_TEST["logique_propositionnelle"],
            llm_service=llm_service
        )
        
        duration = time.time() - demo_start
        results.add_demo_result(demo_name, "success", duration, {
            "text_length": len(TEXTES_TEST["logique_propositionnelle"]),
            "analysis_type": "propositional_logic"
        })
        logger.info(f"✅ {demo_name} terminée en {duration:.2f}s")
        
    except Exception as e:
        duration = time.time() - demo_start
        error_msg = str(e)
        results.add_demo_result(demo_name, "error", duration)
        results.add_error(demo_name, error_msg)
        logger.error(f"❌ {demo_name} échouée: {error_msg}")

async def demo_analyse_informelle(llm_service, results: DemoRhetoriqueResults):
    """Démo 5: Analyse informelle et émotionnelle"""
    demo_name = "Analyse Informelle et Émotionnelle"
    logger.info(f"=== {demo_name} ===")
    demo_start = time.time()
    
    try:
        from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
        
        # Analyser un texte avec beaucoup d'émotion et d'arguments informels
        await run_analysis_conversation(
            texte_a_analyser=TEXTES_TEST["analyse_informelle"],
            llm_service=llm_service
        )
        
        duration = time.time() - demo_start
        results.add_demo_result(demo_name, "success", duration, {
            "text_length": len(TEXTES_TEST["analyse_informelle"]),
            "analysis_type": "informal_emotional"
        })
        logger.info(f"✅ {demo_name} terminée en {duration:.2f}s")
        
    except Exception as e:
        duration = time.time() - demo_start
        error_msg = str(e)
        results.add_demo_result(demo_name, "error", duration)
        results.add_error(demo_name, error_msg)
        logger.error(f"❌ {demo_name} échouée: {error_msg}")

async def demo_hierarchique_complet(results: DemoRhetoriqueResults):
    """Démo 6: Orchestration hiérarchique complète"""
    demo_name = "Orchestration Hiérarchique Complète"
    logger.info(f"=== {demo_name} ===")
    demo_start = time.time()
    
    try:
        # Utiliser l'exemple hiérarchique existant
        from argumentation_analysis.examples.hierarchical_architecture_example import run_hierarchical_example
        
        await run_hierarchical_example()
        
        duration = time.time() - demo_start
        results.add_demo_result(demo_name, "success", duration, {
            "analysis_type": "hierarchical_orchestration",
            "levels": ["strategic", "tactical", "operational"]
        })
        logger.info(f"✅ {demo_name} terminée en {duration:.2f}s")
        
    except Exception as e:
        duration = time.time() - demo_start
        error_msg = str(e)
        results.add_demo_result(demo_name, "error", duration)
        results.add_error(demo_name, error_msg)
        logger.error(f"❌ {demo_name} échouée: {error_msg}")

async def main():
    """Fonction principale de démonstration"""
    print("\n" + "="*60)
    print("  DÉMO COMPLÈTE DU SYSTÈME D'ANALYSE RHÉTORIQUE UNIFIÉ")
    print("="*60)
    
    results = DemoRhetoriqueResults()
    
    try:
        # Configuration de l'environnement
        logger.info("Configuration de l'environnement...")
        llm_service, jvm_status = await setup_environment_for_demo()
        
        if not llm_service:
            logger.error("❌ Impossible de configurer le service LLM. Arrêt des démos.")
            return
        
        logger.info(f"✅ Environnement configuré. JVM: {'✅' if jvm_status else '⚠️'}")
        
        # Exécution des démos
        demos = [
            (demo_analyse_basique, (llm_service, results)),
            (demo_analyse_multi_agents, (llm_service, results)),
            (demo_detection_sophismes, (llm_service, results)),
            (demo_logique_propositionnelle, (llm_service, results)),
            (demo_analyse_informelle, (llm_service, results)),
            (demo_hierarchique_complet, (results,))
        ]
        
        for demo_func, args in demos:
            try:
                await demo_func(*args)
                # Pause entre les démos
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Erreur inattendue dans {demo_func.__name__}: {e}")
        
        # Finaliser et afficher les résultats
        final_results = results.finalize()
        
        print("\n" + "="*60)
        print("  RÉSULTATS FINAUX DES DÉMOS")
        print("="*60)
        
        print(f"📊 Démos exécutées: {final_results['summary']['total_demos']}")
        print(f"✅ Succès: {final_results['summary']['successful_demos']}")
        print(f"❌ Échecs: {final_results['summary']['failed_demos']}")
        print(f"📈 Taux de succès: {final_results['summary']['success_rate']:.1%}")
        print(f"⏱️  Durée totale: {final_results['summary']['total_duration']:.2f}s")
        print(f"⏱️  Durée moyenne par démo: {final_results['summary']['average_demo_duration']:.2f}s")
        
        if final_results['errors']:
            print(f"\n🔍 Erreurs détaillées:")
            for error in final_results['errors']:
                print(f"  - {error['demo']}: {error['error']}")
        
        # Sauvegarder les résultats
        results_file = Path("demos/rapport_demo_rhetorique_complete.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Résultats sauvegardés dans: {results_file}")
        print("\n" + "="*60)
        
    except Exception as e:
        logger.error(f"Erreur critique dans la démo principale: {e}")
        results.add_error("main", str(e))

if __name__ == "__main__":
    asyncio.run(main())