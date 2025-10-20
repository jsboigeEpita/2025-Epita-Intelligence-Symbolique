#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
🚀 Analyse Rhétorique Collaborative par Agents IA - Orchestrateur Principal (v_py)

Ce script orchestre et exécute une analyse rhétorique multi-agents sur un texte donné,
en utilisant une structure de projet Python modulaire.

Structure Modulaire Utilisée:
* `config/`: Fichiers de configuration (`.env`).
* `core/`: Composants partagés (État, StateManager, Stratégies, Setup JVM & LLM).
* `utils/`: Fonctions utilitaires.
* `ui/`: Logique de l'interface utilisateur et lanceur.
* `agents/`: Définitions des agents spécialisés (PM, Informal, PL).
* `orchestration/`: Logique d'exécution de la conversation.

Flux d'Exécution:
1. Chargement de l'environnement (`.env`).
2. Configuration du Logging.
3. Initialisation de la JVM (via `core.jvm_setup`).
4. Création du service LLM (via `core.llm_service`).
5. Affichage de l'UI de configuration (via `ui.app`) pour obtenir le texte.
6. Exécution de l'analyse collaborative (via `orchestration.analysis_runner`) si un texte est fourni.
7. Affichage des résultats (logs, état final).

Prérequis:
* Un fichier `.env` à la racine contenant les clés API, configurations LLM, et la phrase secrète `TEXT_CONFIG_PASSPHRASE`.
* Un environnement Java Development Kit (JDK >= 11) correctement installé et configuré (`JAVA_HOME`).
* Les dépendances Python installées (voir `requirements.txt` ou `pyproject.toml` du projet).
* Les JARs Tweety placés dans le dossier `libs/`.
* Le fichier `extract_sources.json.gz.enc` (s'il existe déjà) dans `data/`.
"""

import os
import sys
import logging
import traceback
import asyncio
import argparse
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))

# Activation automatique de l'environnement

# ensure_env() # Désactivé pour les tests


def setup_logging():
    """Configuration du logging global"""
    # Configuration de base - Les modules peuvent définir des loggers plus spécifiques
    logging.basicConfig(
        level=logging.INFO,  # Mettre DEBUG pour voir plus de détails
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Réduire la verbosité de certaines bibliothèques
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("semantic_kernel.connectors.ai").setLevel(logging.WARNING)
    logging.getLogger("semantic_kernel.kernel").setLevel(logging.WARNING)
    logging.getLogger("semantic_kernel.functions").setLevel(logging.WARNING)

    # Garder INFO pour l'orchestration et les agents
    logging.getLogger("Orchestration").setLevel(logging.INFO)
    # logging.getLogger("semantic_kernel.agents").setLevel(logging.INFO) # Module inexistant
    logging.getLogger("App.UI").setLevel(logging.INFO)  # Logger pour l'UI

    logging.info("Logging configuré.")


async def main():
    """Fonction principale d'exécution de l'analyse rhétorique"""
    parser = argparse.ArgumentParser(
        description="Analyse Rhétorique Collaborative par Agents IA"
    )
    parser.add_argument(
        "--skip-ui",
        action="store_true",
        help="Sauter l'interface utilisateur et utiliser un texte prédéfini",
    )
    parser.add_argument(
        "--text-file",
        type=str,
        help="Chemin vers un fichier texte à analyser (utilisé avec --skip-ui)",
    )
    args = parser.parse_args()

    # Valider les arguments pour le mode non-interactif
    if args.skip_ui and not args.text_file:
        parser.error("--text-file est requis lorsque --skip-ui est utilisé.")

    # 1. Environnement déjà configuré par auto_env
    print("Environnement configuré via auto_env")

    # Vérification rapide de quelques variables clés (optionnel)
    print(f"LLM Model ID présent: {'OPENAI_CHAT_MODEL_ID' in os.environ}")
    print(f"LLM API Key présent: {'OPENAI_API_KEY' in os.environ}")
    print(f"UI Passphrase présente: {'TEXT_CONFIG_PASSPHRASE' in os.environ}")

    # 2. Configuration du Logging Global
    setup_logging()

    # 3. Initialisation de la JVM
    from argumentation_analysis.core.jvm_setup import initialize_jvm

    logging.info("Tentative d'initialisation de la JVM...")
    # La fonction initialize_jvm gère maintenant aussi le téléchargement des JARs
    jvm_ready_status = initialize_jvm()

    if jvm_ready_status:
        logging.info("[OK] JVM initialisée avec succès ou déjà active.")
    else:
        logging.warning(
            "JVM n'a pas pu être initialisée. L'agent PropositionalLogicAgent ne fonctionnera pas."
        )

    # 4. Création du Service LLM
    from argumentation_analysis.core.llm_service import create_llm_service

    llm_service = None
    try:
        logging.info("Création du service LLM...")
        llm_service = create_llm_service()  # Utilise l'ID par défaut
        logging.info(
            f"[OK] Service LLM créé avec succès (ID: {llm_service.service_id})."
        )
    except Exception as e:
        logging.critical(
            f"Échec critique de la création du service LLM: {e}", exc_info=True
        )
        print(
            f"ERREUR: Impossible de créer le service LLM. Vérifiez la configuration .env et les logs."
        )
        # raise  # Décommenter pour arrêter si LLM indispensable

    # 5. Configuration de la Tâche via l'Interface Utilisateur
    texte_pour_analyse = None  # Initialiser

    if args.skip_ui:
        # Mode sans UI: le fichier texte est maintenant requis
        try:
            with open(args.text_file, "r", encoding="utf-8") as f:
                texte_pour_analyse = f.read()
            logging.info(f"[OK] Texte chargé depuis le fichier: {args.text_file}")
        except FileNotFoundError:
            logging.error(f"❌ Fichier non trouvé: {args.text_file}")
            return
        except Exception as e:
            logging.error(f"❌ Erreur lors de la lecture du fichier texte: {e}")
            return
    else:
        # Mode normal avec UI
        try:
            # Importer la fonction UI depuis le module .py
            from argumentation_analysis.ui.app import configure_analysis_task

            logging.info("Fonction 'configure_analysis_task' importée depuis ui.app.")

            # Appeler la fonction pour afficher l'UI et obtenir le texte
            logging.info("Lancement de l'interface de configuration...")
            texte_pour_analyse = (
                configure_analysis_task()
            )  # Bloque jusqu'au clic sur "Lancer"

        except ImportError as e_import:
            logging.critical(f"ERREUR: Impossible d'importer l'UI: {e_import}")
            print(
                f"ERREUR d'importation de l'interface utilisateur: {e_import}. Vérifiez la structure du projet et les __init__.py."
            )
            return
        except Exception as e_ui:
            logging.error(
                f"Une erreur est survenue lors de l'exécution de l'interface utilisateur : {e_ui}",
                exc_info=True,
            )
            print(f"Une erreur est survenue pendant l'exécution de l'UI : {e_ui}")
            traceback.print_exc()
            return

    # Vérifier si on a bien reçu du texte après l'interaction UI
    if not texte_pour_analyse:
        logging.warning("\nAucun texte préparé. L'analyse ne peut pas continuer.")
        print("\nAucun texte préparé. L'analyse ne peut pas continuer.")
        return
    else:
        logging.info(
            f"\n[OK] Texte prêt pour l'analyse (longueur: {len(texte_pour_analyse)})."
        )
        print(
            f"\n[OK] Texte prêt pour l'analyse (longueur: {len(texte_pour_analyse)}). Passage à l'exécution."
        )
        # print("--- Extrait Texte --- \n", texte_pour_analyse[:500] + "...") # Décommenter pour voir extrait

    # 6. Exécution de l'Analyse Collaborative
    # Lancer seulement si on a un texte ET un service LLM valide
    if texte_pour_analyse and llm_service:
        logging.info(
            "\n[LAUNCH] Tentative de lancement de l'execution asynchrone de l'analyse..."
        )
        print(
            "\n[LAUNCH] Lancement de l'analyse collaborative (peut prendre du temps)... "
        )
        # Importer les dépendances nécessaires
        from argumentation_analysis.orchestration.analysis_runner import AnalysisRunner

        try:
            # Exécuter la fonction d'analyse en passant le texte et le service LLM
            runner = AnalysisRunner()
            await runner.run_analysis_async(
                text_content=texte_pour_analyse, llm_service=llm_service
            )

            logging.info("\n[FINISH] Execution terminee.")
            print("\n[FINISH] Analyse terminee.")

        except ImportError as e_import_run:
            logging.critical(
                f"ERREUR: Impossible d'importer 'AnalysisRunner': {e_import_run}"
            )
            print(
                f"ERREUR d'importation de la fonction d'orchestration: {e_import_run}"
            )
        except Exception as e_analysis:
            logging.error(
                f"\nUne erreur est survenue pendant l'exécution de l'analyse : {e_analysis}",
                exc_info=True,
            )
            print(
                f"\nUne erreur est survenue pendant l'exécution de l'analyse : {e_analysis}"
            )
            traceback.print_exc()

    elif not texte_pour_analyse:
        logging.warning("Analyse non lancée : aucun texte n'a été préparé.")
        print("\n Analyse non lancée : aucun texte n'a été préparé.")
    else:  # Implique que llm_service est None ou invalide
        logging.error(
            "Analyse non lancée : le service LLM n'a pas pu être configuré ou est invalide."
        )
        print("\n Analyse non lancée : le service LLM n'a pas pu être configuré.")


if __name__ == "__main__":
    # Utiliser asyncio.run() pour exécuter la fonction principale asynchrone
    asyncio.run(main())
