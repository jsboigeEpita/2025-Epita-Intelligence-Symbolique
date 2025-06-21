import argumentation_analysis.core.environment
import os
import sys
import json
import requests
import logging
from pathlib import Path
from datetime import datetime

# Assurer l'accès aux modules du projet
try:
    current_script_path = Path(__file__).resolve()
    project_root = current_script_path.parent.parent.parent
except NameError:
    project_root = Path(os.getcwd())

sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "examples/scripts_demonstration"))

try:
    from generate_complex_synthetic_data import ComplexSyntheticDataGenerator
except ImportError as e:
    print(f"Erreur: Impossible d'importer ComplexSyntheticDataGenerator. Vérifiez PYTHONPATH.")
    print(f"Détails: {e}")
    print(f"project_root: {project_root}")
    sys.exit(1)

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RhetoricalAnalysisPipeline")

API_URL = "http://localhost:5003/api/analyze" # Correction: Port 5003

def run_analysis_pipeline():
    """
    Génère des données complexes, les envoie à l'API d'analyse rhétorique
    et enregistre la requête et la réponse.
    """
    logger.info("Démarrage du pipeline d'analyse rhétorique...")

    # 1. Générer des données complexes
    logger.info("Génération de données d'entrée complexes...")
    data_generator = ComplexSyntheticDataGenerator()
    # Générer un seul scénario complexe pour ce test
    # Le générateur crée une liste, nous prenons le premier élément.
    # La méthode generate_complex_scenario prend (complexité, id_scénario)
    complex_scenario_list = data_generator.generate_multiple_scenarios(complexity='high', num_scenarios=1)
    if not complex_scenario_list:
        logger.error("Aucun scénario complexe n'a été généré.")
        return

    complex_scenario = complex_scenario_list[0]
    
    # Nous avons besoin d'un texte unique pour l'API, pas de la structure complète du scénario.
    # Construisons un texte à partir des arguments du scénario.
    # Cela pourrait être amélioré pour être plus représentatif d'une entrée utilisateur réelle.
    input_text_parts = [arg['content'] for arg in complex_scenario.get('arguments', [])]
    input_text = " ".join(input_text_parts)

    if not input_text:
        logger.error("Le scénario généré n'a pas produit de texte d'entrée.")
        return

    logger.info(f"Texte d'entrée généré (premiers 200 caractères): {input_text[:200]}...")

    # 2. Préparer la requête pour l'API
    request_payload = {"text": input_text}
    
    # Enregistrer la requête
    trace_dir = project_root / "logs" / "rhetorical_analysis_traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    request_file = trace_dir / f"request_{timestamp}.json"
    response_file = trace_dir / f"response_{timestamp}.json"
    
    logger.info(f"Enregistrement de la requête dans {request_file}")
    with open(request_file, 'w', encoding='utf-8') as f:
        json.dump(request_payload, f, ensure_ascii=False, indent=2)

    # 3. Envoyer la requête à l'API
    logger.info(f"Envoi de la requête à {API_URL}...")
    try:
        start_time = datetime.now()
        response = requests.post(API_URL, json=request_payload, timeout=300) # Timeout de 5 minutes
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Requête envoyée. Statut: {response.status_code}. Durée: {duration:.2f}s")

        response_data = response.json()
        
        logger.info(f"Enregistrement de la réponse dans {response_file}")
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, ensure_ascii=False, indent=2)

        if response.status_code == 200:
            logger.info("Analyse réussie.")
            logger.info(f"Réponse (extrait): {str(response_data)[:500]}...") # Log un extrait de la réponse
            # Ici, on pourrait ajouter une analyse plus poussée de la réponse
            # pour vérifier l'authenticité (temps de réponse, complexité, etc.)
        else:
            logger.error(f"L'API a retourné une erreur: {response.status_code}")
            logger.error(f"Détails de la réponse: {response_data}")

    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de la communication avec l'API: {e}")
    except json.JSONDecodeError:
        logger.error(f"Impossible de décoder la réponse JSON de l'API. Contenu brut: {response.text}")

    logger.info("Pipeline d'analyse rhétorique terminé.")

if __name__ == "__main__":
    # Il faut s'assurer que l'API FastAPI est en cours d'exécution avant de lancer ce script.
    # Ce script ne démarre pas l'API lui-même.
    logger.info("Veuillez vous assurer que l'API FastAPI (api/main.py) est en cours d'exécution sur http://localhost:8000.")
    run_analysis_pipeline()