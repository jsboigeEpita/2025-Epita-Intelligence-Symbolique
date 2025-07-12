import argumentation_analysis.core.environment
import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime

# Assurer l'accès aux modules du projet
try:
    current_script_path = Path(__file__).resolve()
    project_root = current_script_path.parent.parent.parent.parent
except NameError:
    project_root = Path(os.getcwd())

sys.path.insert(0, str(project_root))

# Import des composants locaux nécessaires
from argumentation_analysis.orchestration import analysis_runner_v2 as analysis_runner
from examples.scripts_demonstration.generate_complex_synthetic_data import ComplexSyntheticDataGenerator
from argumentation_analysis.core.llm_service import create_llm_service

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RhetoricalAnalysisPipelineLocal")

async def main():
    """
    Génère des données complexes, les envoie au pipeline d'analyse rhétorique local
    et enregistre le résultat.
    """
    logger.info("Démarrage du pipeline d'analyse rhétorique local...")

    # 1. Générer des données complexes
    logger.info("Génération de données d'entrée complexes...")
    data_generator = ComplexSyntheticDataGenerator()
    complex_scenario_list = data_generator.generate_multiple_scenarios(complexity='high', num_scenarios=1)
    if not complex_scenario_list:
        logger.error("Aucun scénario complexe n'a été généré.")
        return

    complex_scenario = complex_scenario_list[0]
    input_text_parts = [arg['content'] for arg in complex_scenario.get('arguments', [])]
    input_text = " ".join(input_text_parts)

    if not input_text:
        logger.error("Le scénario généré n'a pas produit de texte d'entrée.")
        return

    logger.info(f"Texte d'entrée généré (premiers 200 caractères): {input_text[:200]}...")
    logger.debug(f"Texte d'entrée complet: {input_text}")

    # 2. Exécuter l'analyse locale
    
    try:
        logger.info("Initialisation du service LLM...")
        llm_service = create_llm_service(service_id="default", model_id="gpt-4-turbo")
        if not llm_service:
            logger.error("Échec de l'initialisation du service LLM. Vérifiez la configuration.")
            return
        logger.info("Service LLM initialisé avec succès.")

        start_time = datetime.now()
        
        logger.info("Exécution de l'analyse de la conversation...")
        analysis_result = await analysis_runner.run_analysis_v2(text_content=input_text, llm_service=llm_service)
        logger.info("Analyse de la conversation terminée.")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"Analyse locale terminée en {duration:.2f}s.")

        # 3. Enregistrer les résultats de l'analyse
        trace_dir = project_root / "logs" / "rhetorical_analysis_traces"
        trace_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = trace_dir / f"local_analysis_result_{timestamp}.json"
        
        logger.info(f"Enregistrement du résultat de l'analyse dans {result_file}")
        
        result_to_save = {}
        if isinstance(analysis_result, dict):
            if analysis_result.get('status') == 'success' and 'analysis' in analysis_result:
                result_to_save = json.loads(analysis_result['analysis'])
                logger.info("Analyse locale réussie.")
                logger.info(f"Résultat (extrait): {str(result_to_save)[:500]}...")
            else:
                logger.error(f"L'analyse locale a échoué ou n'a pas retourné de résultat valide: {analysis_result.get('message', 'Raison inconnue')}")
                result_to_save = analysis_result
        else:
            logger.error(f"Le résultat de l'analyse n'est pas un dictionnaire: {type(analysis_result)}")
            result_to_save = {"error": "Invalid result type", "data": str(analysis_result)}

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_to_save, f, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Une erreur est survenue lors de l'exécution du pipeline d'analyse local: {e}", exc_info=True)

    logger.info("Pipeline d'analyse rhétorique local terminé.")

if __name__ == "__main__":
    logger.info("Lancement du pipeline d'analyse rhétorique en mode local.")
    asyncio.run(main())