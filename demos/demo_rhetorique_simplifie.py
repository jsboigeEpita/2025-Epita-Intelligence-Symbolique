#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Démo simplifiée du système d'analyse rhétorique unifié

Ce script teste les capacités fonctionnelles du système en évitant 
les problèmes JVM et d'encodage Unicode.
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

# Configuration du logging sans emojis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("DemoRhetoriqueSimplifie")

class DemoResults:
    """Classe pour collecter les résultats des démos"""
    
    def __init__(self):
        self.results = {
            "demos_executed": [],
            "capabilities_tested": [],
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
    
    def add_capability(self, capability: str, status: str, details: dict = None):
        """Ajoute une capacité testée"""
        self.results["capabilities_tested"].append({
            "capability": capability,
            "status": status,
            "details": details or {}
        })
    
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
            "average_demo_duration": sum(d["duration"] for d in self.results["demos_executed"]) / len(self.results["demos_executed"]) if self.results["demos_executed"] else 0,
            "capabilities_working": len([c for c in self.results["capabilities_tested"] if c["status"] == "working"]),
            "capabilities_failed": len([c for c in self.results["capabilities_tested"] if c["status"] == "failed"])
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
        
        # Création du service LLM (sans JVM)
        from argumentation_analysis.core.llm_service import create_llm_service
        llm_service = create_llm_service()
        
        return llm_service
    except Exception as e:
        logger.error(f"Erreur lors de la configuration de l'environnement: {e}")
        raise

async def test_agent_initialization(llm_service, results: DemoResults):
    """Test l'initialisation des agents individuels"""
    demo_name = "Initialisation des Agents"
    logger.info(f"=== {demo_name} ===")
    demo_start = time.time()
    
    try:
        # Test ProjectManager Agent
        from argumentation_analysis.agents.core.pm.pm_agent import ProjectManagerAgent
        pm_agent = ProjectManagerAgent("TestPM")
        pm_agent.setup_agent_components(llm_service_id=llm_service.service_id)
        results.add_capability("ProjectManager Agent", "working", {"agent_name": pm_agent.name})
        logger.info("ProjectManager Agent initialisé avec succès")
        
        # Test Informal Analysis Agent
        from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
        informal_agent = InformalAnalysisAgent("TestInformal")
        informal_agent.setup_agent_components(llm_service_id=llm_service.service_id)
        results.add_capability("InformalAnalysis Agent", "working", {"agent_name": informal_agent.name})
        logger.info("InformalAnalysis Agent initialisé avec succès")
        
        # Test Extract Agent
        from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
        extract_agent = ExtractAgent("TestExtract")
        extract_agent.setup_agent_components(llm_service_id=llm_service.service_id)
        results.add_capability("Extract Agent", "working", {"agent_name": extract_agent.name})
        logger.info("Extract Agent initialisé avec succès")
        
        # Test PropositionalLogic Agent (peut échouer à cause de la JVM)
        try:
            from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
            pl_agent = PropositionalLogicAgent("TestPL")
            pl_agent.setup_agent_components(llm_service_id=llm_service.service_id)
            results.add_capability("PropositionalLogic Agent", "working", {"agent_name": pl_agent.name})
            logger.info("PropositionalLogic Agent initialisé avec succès")
        except Exception as e:
            results.add_capability("PropositionalLogic Agent", "failed", {"error": str(e)})
            logger.warning(f"PropositionalLogic Agent échoué (attendu): {e}")
        
        duration = time.time() - demo_start
        results.add_demo_result(demo_name, "success", duration)
        logger.info(f"OK - {demo_name} terminé en {duration:.2f}s")
        
    except Exception as e:
        duration = time.time() - demo_start
        error_msg = str(e)
        results.add_demo_result(demo_name, "error", duration)
        results.add_error(demo_name, error_msg)
        logger.error(f"ERREUR - {demo_name} échoué: {error_msg}")

async def test_state_management(results: DemoResults):
    """Test la gestion de l'état d'analyse"""
    demo_name = "Gestion d'État"
    logger.info(f"=== {demo_name} ===")
    demo_start = time.time()
    
    try:
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
        from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
        
        # Créer un état d'analyse
        analysis_state = RhetoricalAnalysisState(raw_text=TEXTES_TEST["sophismes_basiques"])
        results.add_capability("RhetoricalAnalysisState", "working", {
            "text_length": len(analysis_state.raw_text),
            "state_id": id(analysis_state)
        })
        
        # Créer le plugin de gestion d'état
        state_plugin = StateManagerPlugin(analysis_state)
        results.add_capability("StateManagerPlugin", "working", {
            "plugin_id": id(state_plugin)
        })
        
        # Tester l'ajout d'arguments
        analysis_state.add_argument("arg1", {
            "type": "premise",
            "content": "Test argument",
            "confidence": 0.8
        })
        
        # Tester l'ajout de sophismes
        analysis_state.add_fallacy("fallacy1", {
            "type": "ad_hominem",
            "description": "Test fallacy",
            "severity": "medium"
        })
        
        results.add_capability("State Manipulation", "working", {
            "arguments_count": len(analysis_state.identified_arguments),
            "fallacies_count": len(analysis_state.identified_fallacies)
        })
        
        duration = time.time() - demo_start
        results.add_demo_result(demo_name, "success", duration)
        logger.info(f"OK - {demo_name} terminé en {duration:.2f}s")
        
    except Exception as e:
        duration = time.time() - demo_start
        error_msg = str(e)
        results.add_demo_result(demo_name, "error", duration)
        results.add_error(demo_name, error_msg)
        logger.error(f"ERREUR - {demo_name} échoué: {error_msg}")

async def test_semantic_kernel_integration(llm_service, results: DemoResults):
    """Test l'intégration avec Semantic Kernel"""
    demo_name = "Intégration Semantic Kernel"
    logger.info(f"=== {demo_name} ===")
    demo_start = time.time()
    
    try:
        import semantic_kernel as sk
        from semantic_kernel.functions.kernel_arguments import KernelArguments
        
        # Créer un kernel
        kernel = sk.Kernel()
        kernel.add_service(llm_service)
        results.add_capability("Kernel Creation", "working", {
            "service_id": llm_service.service_id
        })
        
        # Tester une fonction simple
        @kernel.function(
            name="analyze_text",
            description="Analyze text for arguments"
        )
        def analyze_text_function(text: str) -> str:
            return f"Analyzed: {text[:50]}..."
        
        # Exécuter la fonction
        result = await kernel.invoke(analyze_text_function, KernelArguments(text=TEXTES_TEST["sophismes_basiques"]))
        results.add_capability("Function Execution", "working", {
            "result_length": len(str(result))
        })
        
        duration = time.time() - demo_start
        results.add_demo_result(demo_name, "success", duration)
        logger.info(f"OK - {demo_name} terminé en {duration:.2f}s")
        
    except Exception as e:
        duration = time.time() - demo_start
        error_msg = str(e)
        results.add_demo_result(demo_name, "error", duration)
        results.add_error(demo_name, error_msg)
        logger.error(f"ERREUR - {demo_name} échoué: {error_msg}")

async def test_analysis_without_jvm(llm_service, results: DemoResults):
    """Test l'analyse sans composants JVM"""
    demo_name = "Analyse Sans JVM"
    logger.info(f"=== {demo_name} ===")
    demo_start = time.time()
    
    try:
        from argumentation_analysis.agents.core.pm.pm_agent import ProjectManagerAgent
        from argumentation_analysis.agents.core.informal.informal_agent import InformalAnalysisAgent
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
        import semantic_kernel as sk
        
        # Créer l'environnement d'analyse
        analysis_state = RhetoricalAnalysisState(raw_text=TEXTES_TEST["argumentation_complexe"])
        kernel = sk.Kernel()
        kernel.add_service(llm_service)
        
        # Créer les agents
        pm_agent = ProjectManagerAgent("PM_Demo")
        pm_agent.setup_agent_components(llm_service_id=llm_service.service_id)
        
        informal_agent = InformalAnalysisAgent("Informal_Demo")
        informal_agent.setup_agent_components(llm_service_id=llm_service.service_id)
        
        # Simuler une analyse simple
        analysis_state.add_argument("demo_arg", {
            "type": "conclusion",
            "content": "Les voitures électriques sont globalement bénéfiques",
            "confidence": 0.7
        })
        
        analysis_state.add_fallacy("demo_fallacy", {
            "type": "false_dilemma",
            "description": "Présentation simpliste électrique vs thermique",
            "severity": "low"
        })
        
        results.add_capability("Analysis Without JVM", "working", {
            "agents_created": 2,
            "arguments_added": len(analysis_state.identified_arguments),
            "fallacies_added": len(analysis_state.identified_fallacies)
        })
        
        duration = time.time() - demo_start
        results.add_demo_result(demo_name, "success", duration)
        logger.info(f"OK - {demo_name} terminé en {duration:.2f}s")
        
    except Exception as e:
        duration = time.time() - demo_start
        error_msg = str(e)
        results.add_demo_result(demo_name, "error", duration)
        results.add_error(demo_name, error_msg)
        logger.error(f"ERREUR - {demo_name} échoué: {error_msg}")

async def test_rhetorical_tools(results: DemoResults):
    """Test les outils rhétoriques disponibles"""
    demo_name = "Outils Rhétoriques"
    logger.info(f"=== {demo_name} ===")
    demo_start = time.time()
    
    try:
        # Test des utilitaires de base
        from argumentation_analysis.utils.core_utils.text_utils import TextUtils
        text_utils = TextUtils()
        
        # Test de traitement de texte
        test_text = TEXTES_TEST["analyse_informelle"]
        cleaned_text = text_utils.clean_text(test_text)
        results.add_capability("Text Processing", "working", {
            "original_length": len(test_text),
            "cleaned_length": len(cleaned_text)
        })
        
        # Test des utilitaires de fichiers
        from argumentation_analysis.utils.core_utils.file_utils import FileUtils
        file_utils = FileUtils()
        results.add_capability("File Utils", "working")
        
        # Test des utilitaires de reporting
        from argumentation_analysis.utils.core_utils.reporting_utils import ReportingUtils
        reporting_utils = ReportingUtils()
        results.add_capability("Reporting Utils", "working")
        
        duration = time.time() - demo_start
        results.add_demo_result(demo_name, "success", duration)
        logger.info(f"OK - {demo_name} terminé en {duration:.2f}s")
        
    except Exception as e:
        duration = time.time() - demo_start
        error_msg = str(e)
        results.add_demo_result(demo_name, "error", duration)
        results.add_error(demo_name, error_msg)
        logger.error(f"ERREUR - {demo_name} échoué: {error_msg}")

async def main():
    """Fonction principale de démonstration"""
    print("\n" + "="*60)
    print("  DEMO SIMPLIFIEE DU SYSTEME D'ANALYSE RHETORIQUE UNIFIE")
    print("="*60)
    
    results = DemoResults()
    
    try:
        # Configuration de l'environnement
        logger.info("Configuration de l'environnement...")
        llm_service = await setup_environment_for_demo()
        
        if not llm_service:
            logger.error("ERREUR - Impossible de configurer le service LLM. Arrêt des démos.")
            return
        
        logger.info("OK - Environnement configuré avec succès")
        
        # Exécution des démos
        demos = [
            (test_agent_initialization, (llm_service, results)),
            (test_state_management, (results,)),
            (test_semantic_kernel_integration, (llm_service, results)),
            (test_analysis_without_jvm, (llm_service, results)),
            (test_rhetorical_tools, (results,))
        ]
        
        for demo_func, args in demos:
            try:
                await demo_func(*args)
                # Pause entre les démos
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Erreur inattendue dans {demo_func.__name__}: {e}")
        
        # Finaliser et afficher les résultats
        final_results = results.finalize()
        
        print("\n" + "="*60)
        print("  RESULTATS FINAUX DES DEMOS")
        print("="*60)
        
        print(f"Demos executees: {final_results['summary']['total_demos']}")
        print(f"Succes: {final_results['summary']['successful_demos']}")
        print(f"Echecs: {final_results['summary']['failed_demos']}")
        print(f"Taux de succes: {final_results['summary']['success_rate']:.1%}")
        print(f"Duree totale: {final_results['summary']['total_duration']:.2f}s")
        print(f"Duree moyenne par demo: {final_results['summary']['average_demo_duration']:.2f}s")
        print(f"Capacites fonctionnelles: {final_results['summary']['capabilities_working']}")
        print(f"Capacites en echec: {final_results['summary']['capabilities_failed']}")
        
        print(f"\nCapacites testees:")
        for capability in final_results['capabilities_tested']:
            status_symbol = "OK" if capability['status'] == 'working' else "KO"
            print(f"  [{status_symbol}] {capability['capability']}")
        
        if final_results['errors']:
            print(f"\nErreurs detaillees:")
            for error in final_results['errors']:
                print(f"  - {error['demo']}: {error['error']}")
        
        # Sauvegarder les résultats
        results_file = Path("demos/rapport_demo_rhetorique_simplifie.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False)
        
        print(f"\nResultats sauvegardes dans: {results_file}")
        print("\n" + "="*60)
        
    except Exception as e:
        logger.error(f"Erreur critique dans la demo principale: {e}")
        results.add_error("main", str(e))

if __name__ == "__main__":
    asyncio.run(main())