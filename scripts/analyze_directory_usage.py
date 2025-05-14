"""
Script pour analyser l'utilisation des répertoires config/ et data/ dans le code.
"""

import re
from pathlib import Path
import json
import logging
import argparse

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

def analyze_directory_references(directory, patterns):
    """
    Analyse les références aux répertoires spécifiés dans le code.
    
    Args:
        directory (str): Répertoire racine à analyser
        patterns (dict): Dictionnaire des motifs à rechercher
    
    Returns:
        dict: Statistiques et exemples d'utilisation pour chaque motif
    """
    results = {pattern: {"count": 0, "files": {}, "examples": []} for pattern in patterns}
    
    for file_path in Path(directory).rglob('*.py'):
        # Ignorer les répertoires __pycache__
        if '__pycache__' in str(file_path):
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                for pattern, regex in patterns.items():
                    matches = regex.finditer(content)
                    
                    for match in matches:
                        results[pattern]["count"] += 1
                        
                        if str(file_path) not in results[pattern]["files"]:
                            results[pattern]["files"][str(file_path)] = 0
                        
                        results[pattern]["files"][str(file_path)] += 1
                        
                        # Extraire la ligne contenant le match
                        line_start = content[:match.start()].count('\n') + 1
                        line_content = content.splitlines()[line_start - 1]
                        
                        # Ajouter l'exemple si moins de 5 exemples sont déjà stockés
                        if len(results[pattern]["examples"]) < 5:
                            results[pattern]["examples"].append({
                                "file": str(file_path),
                                "line": line_start,
                                "content": line_content.strip()
                            })
        
        except Exception as e:
            logging.error(f"Erreur lors de la lecture du fichier {file_path}: {e}")
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Analyse des références aux répertoires dans le code")
    parser.add_argument('--dir', type=str, default='argumentiation_analysis', help="Répertoire à analyser")
    parser.add_argument('--output', type=str, default='directory_usage_report.json', help="Fichier de sortie pour le rapport JSON")
    args = parser.parse_args()
    
    patterns = {
        "config_dir": re.compile(r'config/'),
        "data_dir": re.compile(r'data/')
    }
    
    logging.info(f"Analyse des références aux répertoires config/ et data/ dans {args.dir}...")
    results = analyze_directory_references(args.dir, patterns)
    
    # Afficher les résultats
    for pattern, data in results.items():
        logging.info(f"\n{pattern}:")
        logging.info(f"  Nombre total de références: {data['count']}")
        logging.info(f"  Nombre de fichiers contenant des références: {len(data['files'])}")
        
        if data["examples"]:
            logging.info("  Exemples:")
            for example in data["examples"]:
                logging.info(f"    {example['file']} (ligne {example['line']}): {example['content']}")
    
    # Générer un rapport JSON
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    logging.info(f"\nRapport généré: {args.output}")

if __name__ == "__main__":
    main()