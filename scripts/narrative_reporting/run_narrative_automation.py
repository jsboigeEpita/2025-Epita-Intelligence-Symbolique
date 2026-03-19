# -*- coding: utf-8 -*-
"""
Script principal pour l'automatisation de la génération de rapports narratifs par lots.

Ce script identifie les commits d'audit qui n'ont pas encore été traités,
les regroupe en lots, et génère un rapport de synthèse narratif pour chaque lot,
en suivant la convention de nommage rapport_commits_START-END.md.
"""
import json
import os
import glob
from pathlib import Path
import logging
import re
import asyncio
import time
from dotenv import load_dotenv
from semantic_kernel.exceptions import ServiceResponseException, KernelInvokeException
from openai import APIConnectionError, APITimeoutError
from scripts.narrative_reporting.agent.narrative_agent import NarrativeAgent
from scripts.narrative_reporting.utils.context_builder import build_context, build_historical_context


# Configuration du logging pour une sortie claire et informative
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_config():
    """
    Charge la configuration depuis le fichier narrative_config.json.
    Lève une exception si le fichier n'est pas trouvé.
    """
    config_path = Path(__file__).parent / "narrative_config.json"
    if not config_path.exists():
        logging.error(f"Fichier de configuration introuvable : {config_path}")
        raise FileNotFoundError(f"Fichier de configuration introuvable : {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_last_processed_commit(reports_dir):
    """
    Analyse les noms des rapports existants dans le répertoire de sortie
    pour trouver le numéro du dernier commit qui a été inclus dans un rapport.

    Args:
        reports_dir (str): Le chemin vers le répertoire des rapports de synthèse.

    Returns:
        int: Le numéro du dernier commit traité. Retourne 0 si aucun rapport
             conforme n'est trouvé.
    """
    last_commit = 0
    # Regex pour extraire les numéros de début et de fin des noms de fichiers
    report_pattern = re.compile(r"rapport_commits_(\d+)-(\d+)\.md")
    
    if not os.path.exists(reports_dir):
        logging.warning(f"Le répertoire des rapports '{reports_dir}' n'existe pas. Aucun commit précédent n'est considéré comme traité.")
        return 0
        
    for filename in os.listdir(reports_dir):
        match = report_pattern.match(filename)
        if match:
            # On se base sur le numéro de commit de fin pour déterminer la progression
            end_commit = int(match.group(2))
            if end_commit > last_commit:
                last_commit = end_commit
    
    logging.info(f"Dernier commit traité trouvé dans les rapports existants : {last_commit}")
    return last_commit

def get_new_commit_files(input_dir, last_processed_commit, max_commits=None):
    """
    Liste tous les fichiers de commit JSON dans le répertoire d'entrée et
    filtre ceux qui doivent être traités.

    Args:
        input_dir (str): Le répertoire contenant les fichiers d'audit JSON.
        last_processed_commit (int): Le numéro du dernier commit déjà traité.
        max_commits (int, optional): Le nombre maximum de commits à traiter.
                                     Par défaut, None (pas de limite).

    Returns:
        list: Une liste triée des chemins de fichiers des nouveaux commits,
              limitée par max_commits si spécifié.
    """
    all_commit_files = sorted(glob.glob(os.path.join(input_dir, "*.json")))
    new_commit_files = []
    # Regex pour extraire le numéro de commit du début du nom de fichier
    commit_file_pattern = re.compile(r"(\d+)_.*\.json")

    for file_path in all_commit_files:
        filename = os.path.basename(file_path)
        match = commit_file_pattern.match(filename)
        if match:
            commit_number = int(match.group(1))
            if commit_number > last_processed_commit:
                new_commit_files.append(file_path)
    
    logging.info(f"Trouvé {len(new_commit_files)} nouveau(x) commit(s) à traiter.")

    # Appliquer la limite max_commits si elle est définie et positive
    if max_commits is not None and max_commits > 0:
        logging.info(f"Application de la limite max_commits : {max_commits}")
        return new_commit_files[:max_commits]
        
    return new_commit_files
    
def create_report_skeleton(output_dir, report_name):
    """
    Crée un fichier de rapport vide (squelette) avec un en-tête.
    Crée le répertoire de sortie s'il n'existe pas.
    
    Args:
        output_dir (str): Le répertoire où créer le rapport.
        report_name (str): Le nom du fichier de rapport.

    Returns:
        Path: Le chemin vers le fichier de rapport créé.
    """
    report_path = Path(output_dir) / report_name
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Rapport d'Audit Narratif : {report_name}\n\n")
    logging.info(f"Fichier de rapport squelette créé : {report_path}")
    return report_path

def get_commit_number_from_file(file_path):
    """
    Utilitaire pour extraire le numéro de commit à partir d'un chemin de fichier.
    """
    match = re.match(r"(\d+)_.*\.json", os.path.basename(file_path))
    if match:
        return int(match.group(1))
    return None

async def main():
    """
    Orchestre la génération de rapports narratifs structurés.
    1. Charge la config, le préambule stratégique et le contexte historique.
    2. Identifie les nouveaux commits à traiter.
    3. Les groupe en rapports de `report_batch_size` (ex: 200 commits).
    4. Pour chaque rapport, génère 10 chapitres de `chapter_batch_size` (ex: 20 commits).
    5. Invoque l'agent avec un contexte enrichi pour chaque chapitre.
    """
    load_dotenv()
    logging.info("Démarrage de la refonte du script de narration stratégique.")

    try:
        # 1. Chargement de la configuration et des contextes globaux
        config = get_config()
        report_batch_size = config.get("report_batch_size", 200)
        chapter_batch_size = config.get("chapter_batch_size", 20)
        input_dir = config["input_directory"]
        output_dir = Path(config["output_directory"])
        max_commits = config.get("max_commits_to_process")
        strategic_preamble = config.get("strategic_preamble_text", "")
        
        logging.info(f"Configuration : Rapport={report_batch_size}, Chapitre={chapter_batch_size}")
        
        agent = NarrativeAgent(config["semantic_kernel"])
        historical_context = build_historical_context(output_dir)

        # 2. Identification des nouveaux commits
        last_processed_commit = get_last_processed_commit(str(output_dir))
        all_new_commits = get_new_commit_files(input_dir, last_processed_commit, max_commits)

        if not all_new_commits:
            logging.warning("Aucun nouveau commit à traiter. Arrêt.")
            return

        # 3. Traitement par rapports de 200
        num_reports = (len(all_new_commits) + report_batch_size - 1) // report_batch_size
        logging.info(f"Génération de {num_reports} rapport(s) à partir de {len(all_new_commits)} commits.")

        for i in range(num_reports):
            report_start_index = i * report_batch_size
            report_end_index = report_start_index + report_batch_size
            report_commit_files = all_new_commits[report_start_index:report_end_index]

            if not report_commit_files:
                continue

            start_commit_num = get_commit_number_from_file(report_commit_files[0])
            end_commit_num = get_commit_number_from_file(report_commit_files[-1])
            report_name = f"rapport_commits_{start_commit_num}-{end_commit_num}.md"
            report_path = create_report_skeleton(str(output_dir), report_name)
            
            logging.info(f"Génération du rapport {i+1}/{num_reports}: {report_name}")
            
            # Le contenu du rapport est lu à chaque itération pour le contexte
            # narratif, pas besoin de le stocker dans une variable ici.

            # 4. Traitement par chapitres de 20
            num_chapters = (len(report_commit_files) + chapter_batch_size - 1) // chapter_batch_size
            for j in range(num_chapters):
                chapter_start_index = j * chapter_batch_size
                chapter_end_index = chapter_start_index + chapter_batch_size
                chapter_commit_files = report_commit_files[chapter_start_index:chapter_end_index]

                if not chapter_commit_files:
                    continue
                
                # Lire le contenu actuel du rapport pour le contexte narratif
                with open(report_path, 'r', encoding='utf-8') as f:
                    full_report_content = f.read()

                ch_start = get_commit_number_from_file(chapter_commit_files[0])
                ch_end = get_commit_number_from_file(chapter_commit_files[-1])
                commit_range_str = f"Commits {ch_start}-{ch_end}"
                logging.info(f"  -> Génération du chapitre {j+1}/{num_chapters} ({commit_range_str})")

                # 5. Appel de l'agent avec le contexte enrichi
                context = build_context(
                    batch_files=chapter_commit_files,
                    full_report_content=full_report_content, # Contenu à jour
                    historical_context=historical_context,   # Contexte plus léger
                    strategic_preamble=strategic_preamble
                )
                
                # Logique de re-tentative pour la génération de chapitre
                max_retries = 5
                retry_delay_base = 30  # secondes
                retries = 0
                chapter_generated = False
                narrative_chapter = ""

                while not chapter_generated and retries < max_retries:
                    try:
                        narrative_chapter = await agent.generate_narrative(context, commit_range=commit_range_str)
                        if narrative_chapter and narrative_chapter.strip():
                            chapter_generated = True
                        else:
                            # Si le résultat est vide, on considère cela comme une erreur à réessayer
                            raise ValueError("La génération du chapitre a retourné un contenu vide.")

                    except (ServiceResponseException, KernelInvokeException, APIConnectionError, APITimeoutError, ValueError) as e:
                        retries += 1
                        delay = retry_delay_base * (2 ** (retries - 1)) # Backoff exponentiel
                        logging.warning(
                            f"Échec de la génération du chapitre {j+1}/{num_chapters} (Essai {retries}/{max_retries}). "
                            f"Raison: {type(e).__name__}. Nouvelle tentative dans {delay} secondes."
                        )
                        if retries >= max_retries:
                            logging.error(
                                f"Échec final de la génération du chapitre {j+1}/{num_chapters} après {max_retries} tentatives."
                            )
                            # On repackage l'erreur pour la faire remonter et arrêter le script proprement
                            raise e
                        
                        await asyncio.sleep(delay)
                
                # Ajout du chapitre généré au rapport, avec vérification
                if narrative_chapter and narrative_chapter.strip():
                    with open(report_path, 'a', encoding='utf-8') as f:
                        # Ajouter un saut de ligne pour séparer les chapitres
                        f.write("\n" + narrative_chapter.strip() + "\n")
                    logging.info(f"  -> Chapitre {j+1} ajouté à '{report_name}'.")
                else:
                    logging.error(f"  -> La génération du chapitre {j+1} a retourné un contenu vide.")

            logging.info(f"Rapport '{report_name}' finalisé.")
            
            # Le script va maintenant traiter tous les rapports sans s'arrêter.

        logging.info("Script de narration stratégique terminé avec succès.")

    except FileNotFoundError as e:
        logging.error(e)
    except Exception as e:
        logging.error(f"Une erreur inattendue est survenue : {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())