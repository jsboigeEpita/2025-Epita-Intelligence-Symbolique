# -*- coding: utf-8 -*-
"""
Script pour identifier et réparer les fichiers d'audit de commit JSON mal formés.
Il utilise le contexte des rapports narratifs de haut niveau pour enrichir l'analyse.
"""
import json
import os
import glob
from pathlib import Path
import logging
import asyncio
from asyncio import Semaphore
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion, OpenAIPromptExecutionSettings
from semantic_kernel.functions import KernelArguments
from dotenv import load_dotenv
from tqdm import tqdm
import re
import sys
import subprocess

# Add project root to PYTHONPATH
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from project_core.llm.models.commit_analysis import CommitAnalysis

# --- Configuration du Logging ---
log_file_path = project_root.joinpath('repair_run.log')

# Créer un logger principal
logger = logging.getLogger()
logger.setLevel(logging.DEBUG) # Le niveau le plus bas pour capturer tous les messages

# Supprimer le handler par défaut s'il existe
if logger.hasHandlers():
    logger.handlers.clear()

# Supprimer l'ancien fichier de log pour une exécution propre
if os.path.exists(log_file_path):
    os.remove(log_file_path)

# Handler pour écrire les logs dans un fichier (niveau DEBUG)
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Handler pour afficher les logs dans la console (niveau INFO)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_formatter = logging.Formatter('%(levelname)s: %(message)s')
stream_handler.setFormatter(stream_formatter)
logger.addHandler(stream_handler)

logging.info(f"Le logging est configuré. Les logs détaillés seront sauvegardés dans : {log_file_path}")

# --- Fonctions Utilitaires (adaptées) ---


def find_malformed_json_files(directory):
    """Parcourt un répertoire et identifie les fichiers JSON qui ne respectent pas le format attendu."""
    malformed_files = []
    json_files = glob.glob(os.path.join(directory, "*.json"))
    logging.info(f"Analyse de {len(json_files)} fichiers JSON dans {directory}...")

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Un fichier est considéré comme mal formé si l'analyse qualitative est manquante ou incomplète.
            is_malformed = "qualitative_analysis" not in data or "detailed_summary" not in data.get("qualitative_analysis", {})
            
            if is_malformed:
                malformed_files.append(file_path)

        except json.JSONDecodeError:
            logging.warning(f"Impossible de décoder le JSON de {file_path}")
            malformed_files.append(file_path)
        except Exception as e:
            logging.error(f"Erreur inattendue avec {file_path}: {e}")
            malformed_files.append(file_path)

    return malformed_files

def load_narrative_context(reports_dir):
    """Charge et concatène le contenu de tous les rapports narratifs."""
    logging.info(f"Chargement du contexte narratif depuis {reports_dir}...")
    narrative_context = []
    report_files = glob.glob(os.path.join(reports_dir, "rapport_commits_*.md"))
    for report_path in report_files:
        with open(report_path, 'r', encoding='utf-8') as f:
            narrative_context.append(f.read())
    
    if not narrative_context:
        logging.warning("Aucun rapport narratif trouvé. L'analyse se fera sans contexte de haut niveau.")
        return ""
    
    logging.info(f"Contexte narratif chargé à partir de {len(report_files)} rapports.")
    return "\n\n---\n\n".join(narrative_context)

async def repair_commit_file(kernel, prompt, file_path, narrative_context, semaphore: Semaphore):
    """Régénère l'analyse qualitative pour un fichier JSON en utilisant 'git show'."""
    async with semaphore:
        logging.debug(f"Début de la régénération pour : {file_path}")
        
        # Extraire le hash du commit du nom de fichier
        filename = os.path.basename(file_path)
        match = re.search(r'\d+_(.*)\.json', filename)
        if not match:
            # Tenter une deuxième regex pour les formats plus anciens
            match = re.search(r'(\w{40})', filename)
        
        if not match:
            logging.error(f"Impossible d'extraire le hash du commit de '{filename}'")
            return False
            
        commit_hash_match = re.search(r'([a-f0-9]{40})', filename)
        if not commit_hash_match:
            logging.error(f"Format de hash invalide ou introuvable dans '{filename}'")
            return False
        commit_hash = commit_hash_match.group(1)

        try:
            # Obtenir le diff stat et les métadonnées du commit
            git_command = ["git", "show", "--stat", commit_hash]
            logging.debug(f"Exécution de la commande : {' '.join(git_command)}")
            result = subprocess.run(git_command, capture_output=True, text=True, check=True, encoding='utf-8')
            commit_diff = result.stdout
            
        except FileNotFoundError:
            logging.error("La commande 'git' est introuvable. Assurez-vous que Git est installé et dans le PATH.")
            return False
        except subprocess.CalledProcessError as e:
            logging.error(f"Erreur en exécutant 'git show {commit_hash}': {e.stderr}")
            return False
        except Exception as e:
            logging.error(f"Erreur inattendue avec git show : {e}")
            return False

        if not commit_diff:
            logging.warning(f"Aucun diff trouvé pour le commit {commit_hash}. Ignoré.")
            return True

        logging.debug(f"[{filename}] Appel de l'IA pour analyser le commit complet...")
        
        # Tronquer le contexte pour éviter les problèmes de mémoire potentiels
        narrative_context_truncated = narrative_context[:5000]
        logging.debug(f"Taille du contexte narratif (tronqué) : {len(narrative_context_truncated)} caractères.")

        execution_settings = OpenAIPromptExecutionSettings(
            service_id="default",
            response_format={"type": "json_object"},
        )
        
        try:
            logging.info(f"[{filename}] Invocation du kernel avec un contexte tronqué...")
            # Invoquer le kernel avec le diff complet et le contexte tronqué
            invoke_result = await kernel.invoke_prompt(
                prompt,
                arguments=KernelArguments(input=commit_diff, narrative_context=narrative_context_truncated),
                settings=execution_settings
            )
            logging.info(f"[{filename}] Invocation du kernel terminée avec succès.")
            raw_result_str = str(invoke_result)
            logging.debug(f"[{filename}] Réponse brute de l'IA reçue.")
            
            json_str = raw_result_str
            if not json_str:
                logging.error(f"[{filename}] La réponse de l'IA est vide.'")
                return False

            # Valider et structurer la nouvelle analyse
            new_analysis = CommitAnalysis.model_validate_json(json_str)

            # Lire les données existantes pour les conserver (auteur, date, etc.)
            with open(file_path, 'r', encoding='utf-8') as f:
                commit_data = json.load(f)

            # Mettre à jour avec la nouvelle analyse
            commit_data["qualitative_analysis"] = new_analysis.model_dump()

            # Sauvegarder le fichier réparé
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(commit_data, f, indent=4, ensure_ascii=False)
            logging.info(f"Régénération et sauvegarde réussies pour : {filename}")
            return True

        except Exception as e:
            logging.error(f"[{filename}] Échec de l'analyse IA ou de la sauvegarde du fichier : {e}", exc_info=True)
            return False


async def main():
    """Fonction principale pour orchestrer l'identification et la réparation."""
    load_dotenv()
    
    # --- Initialisation du Kernel ---
    kernel = sk.Kernel()
    api_key = os.environ.get("OPENAI_API_KEY")
    model_id = os.environ.get("OPENAI_CHAT_MODEL_ID")
    if not all([api_key, model_id]):
        logging.error("Variables d'environnement OPENAI_API_KEY et OPENAI_CHAT_MODEL_ID manquantes.")
        return
        
    kernel.add_service(OpenAIChatCompletion(service_id="default", ai_model_id=model_id, api_key=api_key))

    # --- Préparation du Prompt ---
    prompt = """
    Votre mission est de fournir une analyse qualitative d'un `git commit` complet (métadonnées et diff).
    Utilisez le **contexte narratif global** pour comprendre l'importance stratégique de ce commit.
    
    **Contexte Narratif Global:**
    {{$narrative_context}}
    
    **Commit Complet (métadonnées + diff):**
    {{$input}}
    
    Fournissez votre analyse directement au format JSON, en respectant ce modèle Pydantic. Ne l'encapsulez PAS dans un bloc de code markdown.
    
    ```python
    class CommitAnalysis(BaseModel):
        detailed_summary: str
        technical_debt_signals: List[str]
        quality_leaps: List[str]
    ```
        
    JSON Output:
    """

    # --- Exécution ---
    commits_dir = "docs/commits_audit"
    reports_dir = "docs/audit/synthesis_reports"
    
    narrative_context = load_narrative_context(reports_dir)
    malformed_files = find_malformed_json_files(commits_dir)
    logging.info(f"{len(malformed_files)} fichiers mal formés trouvés.")
    
    if not malformed_files:
        logging.info("Aucun fichier JSON mal formé trouvé.")
        return

    files_to_process = malformed_files
    logging.info(f"Début de la réparation pour {len(files_to_process)} fichiers sur {len(malformed_files)} restants.")
    
    # Limiter la concurrence pour éviter l'erreur "too many file descriptors"
    semaphore = Semaphore(50)
    
    tasks = [repair_commit_file(kernel, prompt, f, narrative_context, semaphore) for f in files_to_process]
    
    results = []
    with tqdm(total=len(tasks), desc="Réparation des fichiers JSON", unit="fichier") as pbar:
        for f in asyncio.as_completed(tasks):
            try:
                result = await f
                results.append(result)
            except Exception as e:
                logging.error(f"Une exception a été levée pendant le traitement d'une tâche : {e}", exc_info=True)
                results.append(False)
            finally:
                pbar.update(1)

    successful_repairs = sum(1 for r in results if r)
    logging.info(f"Réparation du lot terminée. {successful_repairs}/{len(files_to_process)} fichiers ont été traités avec succès.")

if __name__ == "__main__":
    # Correction pour l'exécution asynchrone dans un environnement existant
    if sys.platform == "win32" and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())