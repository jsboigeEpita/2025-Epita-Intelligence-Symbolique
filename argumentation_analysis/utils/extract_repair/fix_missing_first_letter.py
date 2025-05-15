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
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("FixMissingFirstLetter")

def fix_missing_first_letter(input_file, output_file=None):
    """
    Corrige les marqueurs de début qui ont leur première lettre manquante.
    
    Args:
        input_file (str): Chemin vers le fichier extract_sources.json
        output_file (str, optional): Chemin pour sauvegarder le fichier corrigé.
            Si None, écrase le fichier d'entrée.
    
    Returns:
        tuple: (nombre d'extraits corrigés, liste des corrections)
    """
    # Si output_file n'est pas spécifié, utiliser le même fichier que input_file
    if output_file is None:
        output_file = input_file
    
    # Charger le fichier JSON
    logger.info(f"Chargement du fichier {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
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
                        corrections.append({
                            "source_name": source_name,
                            "extract_name": extract_name,
                            "old_marker": old_marker,
                            "new_marker": new_marker,
                            "template": template_start
                        })
    
    # Sauvegarder le fichier corrigé
    logger.info(f"Sauvegarde du fichier corrigé dans {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extract_sources, f, indent=4, ensure_ascii=False)
    
    logger.info(f"Terminé. {fixed_count} extraits corrigés.")
    return fixed_count, corrections

def main():
    """Fonction principale."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Correction des marqueurs de début corrompus")
    parser.add_argument("--input", "-i", default="C:/dev/2025-Epita-Intelligence-Symbolique/argumentation_analysis/data/extract_sources.json", 
                        help="Fichier d'entrée (extract_sources.json)")
    parser.add_argument("--output", "-o", default=None, 
                        help="Fichier de sortie (si non spécifié, écrase le fichier d'entrée)")
    parser.add_argument("--report", "-r", action="store_true", 
                        help="Générer un rapport détaillé des corrections")
    
    args = parser.parse_args()
    
    # Vérifier que le fichier d'entrée existe
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Le fichier {args.input} n'existe pas.")
        return
    
    # Corriger les marqueurs
    fixed_count, corrections = fix_missing_first_letter(args.input, args.output)
    
    # Générer un rapport si demandé
    if args.report and corrections:
        report_path = Path("fix_missing_first_letter_report.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Rapport de correction des marqueurs de début\n\n")
            f.write(f"**Nombre d'extraits corrigés:** {fixed_count}\n\n")
            f.write("## Détails des corrections\n\n")
            
            for i, correction in enumerate(corrections, 1):
                f.write(f"### {i}. {correction['source_name']} - {correction['extract_name']}\n\n")
                f.write(f"- **Template:** `{correction['template']}`\n")
                f.write(f"- **Ancien marqueur:** `{correction['old_marker']}`\n")
                f.write(f"- **Nouveau marqueur:** `{correction['new_marker']}`\n\n")
        
        logger.info(f"Rapport généré dans {report_path}")

if __name__ == "__main__":
    main()