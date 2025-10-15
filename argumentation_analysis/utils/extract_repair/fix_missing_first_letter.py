#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de réparation des marqueurs de début corrompus dans extract_sources.json

Ce script corrige spécifiquement les marqueurs de début (start_marker) qui ont
leur première lettre manquante, en utilisant le champ template_start pour
reconstruire le marqueur complet.
"""

import json
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("FixMissingFirstLetter")


def fix_missing_first_letter(input_file, output_file=None):
    """
    Corrige les marqueurs de début (start_marker) dans les définitions d'extraits
    qui ont potentiellement leur première lettre manquante, en utilisant le champ
    `template_start` pour reconstruire le marqueur complet.

    Charge les définitions depuis `input_file`, effectue les corrections,
    et sauvegarde le résultat dans `output_file` (ou écrase `input_file` si
    `output_file` n'est pas spécifié).

    :param input_file: Chemin vers le fichier JSON des définitions d'extraits
                       (par exemple, `extract_sources.json`).
    :type input_file: str # Peut aussi accepter Path, mais le code interne convertit en str.
    :param output_file: Chemin optionnel pour sauvegarder le fichier corrigé.
                        Si None, le fichier d'entrée est écrasé.
    :type output_file: Optional[str] # Peut aussi accepter Path.
    :return: Un tuple contenant le nombre d'extraits corrigés (int) et une liste
             de dictionnaires détaillant chaque correction effectuée. Chaque dictionnaire
             de correction contient "source_name", "extract_name", "old_marker",
             "new_marker", et "template".
    :rtype: Tuple[int, List[Dict[str, str]]]
    """
    # Si output_file n'est pas spécifié, utiliser le même fichier que input_file
    if output_file is None:
        output_file = input_file

    # Charger le fichier JSON
    logger.info(f"Chargement du fichier {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        extract_sources = json.load(f)

    # Compteur pour les extraits corrigés
    fixed_count = 0
    corrections = []

    # Parcourir toutes les sources et leurs extraits
    for source_idx, source_info in enumerate(extract_sources):
        source_name = source_info.get("source_name", f"Source #{source_idx}")
        logger.info(f"Analyse de la source '{source_name}'...")

        extracts = source_info.get("extracts", [])
        for extract_idx, extract_info in enumerate(extracts):
            extract_name = extract_info.get("extract_name", f"Extrait #{extract_idx}")

            # Vérifier si l'extrait a un template_start
            if "template_start" in extract_info:
                start_marker = extract_info.get("start_marker", "")
                template_start = extract_info.get("template_start", "")

                # Vérifier si le template_start est au format attendu (lettre + {0})
                if template_start and "{0}" in template_start:
                    # Extraire la lettre du template
                    first_letter = template_start.replace("{0}", "")

                    # Vérifier si le start_marker ne commence pas déjà par cette lettre
                    if start_marker and not start_marker.startswith(first_letter):
                        # Corriger le start_marker en ajoutant la première lettre
                        old_marker = start_marker
                        new_marker = first_letter + start_marker

                        logger.info(f"Correction de l'extrait '{extract_name}':")
                        logger.info(f"  - Ancien marqueur: '{old_marker}'")
                        logger.info(f"  - Nouveau marqueur: '{new_marker}'")

                        # Mettre à jour le marqueur
                        extract_info["start_marker"] = new_marker

                        # Incrémenter le compteur
                        fixed_count += 1

                        # Enregistrer la correction
                        corrections.append(
                            {
                                "source_name": source_name,
                                "extract_name": extract_name,
                                "old_marker": old_marker,
                                "new_marker": new_marker,
                                "template": template_start,
                            }
                        )

    # Sauvegarder le fichier corrigé
    logger.info(f"Sauvegarde du fichier corrigé dans {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(extract_sources, f, indent=4, ensure_ascii=False)

    logger.info(f"Terminé. {fixed_count} extraits corrigés.")
    return fixed_count, corrections


# La fonction main() et la section if __name__ == "__main__": ont été déplacées
# vers argumentation_analysis/scripts/run_fix_missing_first_letter.py
