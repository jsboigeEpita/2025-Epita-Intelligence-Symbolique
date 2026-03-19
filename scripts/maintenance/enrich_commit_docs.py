#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour enrichir les fichiers d'audit de commits avec un résumé LLM.
Ce script s'intègre à l'architecture du projet pour utiliser le service LLM
centralisé et résilient.
"""
import asyncio
import json
import logging
from pathlib import Path
import argparse
from filelock import AsyncFileLock
import aiofiles

# Imports depuis l'architecture du projet
from argumentation_analysis.core.environment import ensure_env
from argumentation_analysis.core.llm_service import create_llm_service
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
from semantic_kernel.contents.chat_history import ChatHistory
from tqdm.asyncio import tqdm_asyncio

# --- Configuration ---
# Configuration du logging
LOG_FILE = Path(__file__).resolve().parent / "enrich_commit_docs.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'),
        logging.StreamHandler()
    ]
)

# Initialisation de l'environnement (vérification et chargement du .env)
ensure_env(silent=True)


# --- Fonctions de traitement ---

async def process_file(filepath: Path, llm_service, semaphore: asyncio.Semaphore, force: bool, test_run: bool) -> Path | None:
    """
    Traite un seul fichier JSON de commit en utilisant le service LLM injecté,
    en respectant la limite de concurrence du sémaphore.
    """
    lock_path = filepath.with_suffix(filepath.suffix + '.lock')
    async with semaphore, AsyncFileLock(lock_path):
        try:
            async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
                content = await f.read()
            data = json.loads(content)

            # Vérifier si un résumé détaillé existe déjà
            is_detailed = data.get("llm_summary_is_detailed", False)
            if is_detailed and not force:
                logging.debug("Fichier déjà traité avec un résumé détaillé, ignoré : %s", filepath.name)
                return None

            previous_summary = data.get("llm_summary", "").strip()

            commit_message = data.get("message", "")
            files_changed = data.get("files_changed", [])

            # Préparation des diffs pour le prompt et détection du format
            files_changed_and_diffs = []
            has_real_diffs = False
            if files_changed and isinstance(files_changed[0], dict):
                # Nouveau format : liste de dictionnaires
                for file_info in files_changed:
                    file_path = file_info.get("file_path", "Unknown path")
                    diff = file_info.get("diff", "No diff available")
                    if diff and "not available" not in diff:
                        has_real_diffs = True
                    files_changed_and_diffs.append({"file_path": file_path, "diff": diff})
            elif files_changed:
                # Ancien format : liste de chaînes
                for file_path in files_changed:
                    files_changed_and_diffs.append({
                        "file_path": str(file_path),
                        "diff": "Diff data not available in this commit record."
                    })

            # Formatage pour l'inclure dans le JSON du prompt
            files_json_str = json.dumps(files_changed_and_diffs, indent=2, ensure_ascii=False)

            if not has_real_diffs:
                logging.warning("Aucune donnée de diff concrète trouvée pour %s. Le résumé sera de moindre qualité.", filepath.name)

            if not commit_message:
                logging.warning("Message de commit vide pour le fichier: %s", filepath.name)
                return None

            prompt = f"""
**Rôle** : Tu es un expert en documentation technique et en archéologie logicielle. Ton objectif est de transformer les informations brutes d'un commit en une explication claire, détaillée et contextuelle.

**Tâche** : En te basant **uniquement sur le diff fourni**, rédige un nouveau résumé technique explicatif en français. Le résumé doit se concentrer sur l'explication des **motivations** derrière les changements, détailler les modifications avec assez de précision pour qu'on puisse les comprendre, voire les reconstituer mentalement.

**Instructions impératives** :
1.  **Source de Vérité** : Ta source d'information principale est le `Diff détaillé des fichiers modifiés`. C'est sur cette base que tu dois construire ton analyse.
2.  **Gestion des Diffs Absents** : Si tous les `diff` ont la valeur "Diff data not available in this commit record.", reconnais-le explicitement en début de résumé. Dans ce cas, base ton analyse sur le message de commit et la liste des fichiers modifiés pour inférer l'intention et la portée des changements. L'analyse sera forcément de plus haut niveau.
3.  **Analyse des Diffs Présents** : Si des `diffs` sont disponibles, concentre-toi dessus. Explique la **motivation** (le "pourquoi"), décris les **changements techniques** (le "comment") et l'**impact** (le "quoi"). Sois précis : mentionne les fonctions, classes, variables.
4.  **Détail et Longueur** : Produis un résumé substantiel (7-10 lignes minimum), riche en détails techniques lorsque c'est possible.
5.  **Reconstitution** : Le but est qu'un développeur puisse comprendre la nature et la logique du changement sans avoir à lire le code.

**Contexte du commit** :

*   **Message de commit original** :
    ```
    {commit_message}
    ```

*   **Résumé précédent (si existant)** :
    ```
    {previous_summary if previous_summary else "N/A"}
    ```

**Données à analyser (ta source de vérité)** :

*   **Diff détaillé des fichiers modifiés** :
    ```json
    {files_json_str}
    ```

**Livraison** : Produis UNIQUEMENT le nouveau résumé détaillé. Ne rajoute aucun préambule comme "Voici le nouveau résumé :".
"""
            
            chat_history = ChatHistory()
            # Le rôle est maintenant directement dans le prompt utilisateur.
            # On garde un message système générique.
            chat_history.add_system_message("Tu es un assistant expert en analyse de code.")
            chat_history.add_user_message(prompt)

            # Utilisation du service LLM résilient de Semantic Kernel
            execution_settings = OpenAIChatPromptExecutionSettings(
                max_tokens=800, # Augmentation pour permettre des résumés plus longs
                temperature=0.6,
                top_p=0.9
            )
            completion = await llm_service.get_chat_message_contents(
                chat_history=chat_history,
                settings=execution_settings
            )
            
            summary = str(completion[0].content).strip()
            data["llm_summary"] = summary
            data["llm_summary_is_detailed"] = True

            if not test_run:
                async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(data, indent=2, ensure_ascii=False))
                logging.debug("Fichier mis à jour : %s", filepath.name)
            else:
                logging.info("[TEST RUN] Fichier traité (non modifié) : %s", filepath.name)
                logging.info("[TEST RUN] Nouveau résumé pour %s:\n%s", filepath.name, summary)

            return filepath

        except json.JSONDecodeError:
            logging.error("Erreur de décodage JSON pour le fichier: %s", filepath.name)
            return None
        except Exception as e:
            # Tenacity gère déjà les erreurs réseau. Ici, on capture d'autres problèmes.
            logging.error("Erreur inattendue pour le fichier %s: %s", filepath.name, e, exc_info=True)
            return None


async def main():
    """Fonction principale pour orchestrer le traitement des fichiers."""
    parser = argparse.ArgumentParser(description="Enrichit les fichiers de commit JSON avec des résumés générés par l'IA.")
    parser.add_argument("-l", "--limit", type=int, help="Limite le nombre de fichiers à traiter pour un test.")
    parser.add_argument("-c", "--concurrency", type=int, default=10, help="Nombre d'opérations concurrentes.")
    parser.add_argument("--force", action="store_true", help="Force le ré-enrichissement des fichiers déjà traités.")
    parser.add_argument("--test-run", action="store_true", help="Exécute le script sans modifier les fichiers (dry run).")

    args = parser.parse_args()
    
    if args.test_run:
        logging.info("--- MODE TEST RUN ACTIF : AUCUN FICHIER NE SERA MODIFIÉ ---")

    # Création du service LLM résilient via la factory du projet
    try:
        llm_service = create_llm_service(service_id="commit_enricher", force_authentic=True)
    except Exception as e:
        logging.critical(f"Impossible d'initialiser le service LLM. Arrêt du script. Erreur: {e}", exc_info=True)
        return

    audit_dir = Path(__file__).resolve().parent.parent.parent / "docs" / "commits_audit"
    if not audit_dir.exists():
        logging.error("Le répertoire d'audit des commits est introuvable: %s", audit_dir)
        return

    json_files_all = sorted(list(audit_dir.glob("*.json")))
    
    files_to_process = json_files_all
    if args.limit:
        logging.info(f"--- MODE TEST: Traitement limité aux {args.limit} premier(s) fichier(s) ---")
        files_to_process = json_files_all[:args.limit]

    logging.info("Nombre de fichiers JSON à traiter: %d", len(files_to_process))

    # Création d'un sémaphore pour limiter la concurrence
    semaphore = asyncio.Semaphore(args.concurrency)
    logging.info(f"Niveau de concurrence fixé à : {args.concurrency}")

    # Injection du service LLM et du sémaphore dans chaque tâche
    tasks = [process_file(f, llm_service, semaphore, args.force, args.test_run) for f in files_to_process]
    
    results = await tqdm_asyncio.gather(
        *tasks, desc="Enrichissement des commits", unit="fichier"
    )

    processed_files = [r for r in results if r is not None]
    updated_count = len(processed_files)
    total_files = len(files_to_process)
    skipped_count = total_files - updated_count
    
    logging.info("Traitement terminé.")
    logging.info(f"Fichiers traités avec succès : {updated_count}/{total_files}")
    logging.info(f"Fichiers ignorés (déjà traités ou erreur) : {skipped_count}")


if __name__ == "__main__":
    # Il est crucial d'exécuter le script dans son propre contexte asyncio
    # pour garantir la bonne gestion des clients HTTP asynchrones.
    asyncio.run(main())