#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'exécution pour la réparation des marqueurs de début corrompus.

Ce script utilise la logique de `argumentation_analysis.utils.extract_repair.fix_missing_first_letter`
pour corriger les marqueurs et générer un rapport.
"""

import argparse
import logging
from pathlib import Path
import sys
import os

# Ajouter le répertoire parent au chemin d'importation pour trouver le package argumentation_analysis
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from argumentation_analysis.utils.extract_repair.fix_missing_first_letter import (
    fix_missing_first_letter,
    logger as fix_logger,
)

# Configuration du logging pour ce script (peut être différent du module importé)
logger = logging.getLogger("RunFixMissingFirstLetter")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(
        description="Correction des marqueurs de début corrompus"
    )
    parser.add_argument(
        "--input",
        "-i",
        default="C:/dev/2025-Epita-Intelligence-Symbolique/argumentation_analysis/data/extract_sources.json",
        help="Fichier d'entrée (extract_sources.json)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Fichier de sortie (si non spécifié, écrase le fichier d'entrée)",
    )
    parser.add_argument(
        "--report",
        "-r",
        action="store_true",
        help="Générer un rapport détaillé des corrections",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Activer le mode verbeux"
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        fix_logger.setLevel(
            logging.DEBUG
        )  # Assurer que le logger du module est aussi en DEBUG
        for handler in logging.getLogger().handlers:  # Mettre à jour tous les handlers
            handler.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé.")

    # Vérifier que le fichier d'entrée existe
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Le fichier {args.input} n'existe pas.")
        return

    # Corriger les marqueurs
    fixed_count, corrections = fix_missing_first_letter(
        str(input_path), args.output
    )  # S'assurer que input_path est une string

    # Générer un rapport si demandé
    if args.report and corrections:
        report_file_name = "fix_missing_first_letter_report.md"
        # Placer le rapport dans le même répertoire que le script ou un répertoire de rapports défini
        # Pour l'instant, dans le répertoire courant du script
        script_dir = Path(__file__).parent
        report_path = (
            script_dir / report_file_name
        )  # Ou un sous-dossier comme script_dir / "reports" / report_file_name

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# Rapport de correction des marqueurs de début\n\n")
            f.write(f"**Nombre d'extraits corrigés:** {fixed_count}\n\n")
            f.write("## Détails des corrections\n\n")

            for i, correction in enumerate(corrections, 1):
                f.write(
                    f"### {i}. {correction['source_name']} - {correction['extract_name']}\n\n"
                )
                f.write(f"- **Template:** `{correction['template']}`\n")
                f.write(f"- **Ancien marqueur:** `{correction['old_marker']}`\n")
                f.write(f"- **Nouveau marqueur:** `{correction['new_marker']}`\n\n")

        logger.info(f"Rapport généré dans {report_path.resolve()}")


if __name__ == "__main__":
    main()
