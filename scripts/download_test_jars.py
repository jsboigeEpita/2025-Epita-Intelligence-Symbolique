"""
Script pour télécharger les JARs minimaux nécessaires pour les tests.

Ce script télécharge une version minimale des JARs Tweety nécessaires
pour les tests et les place dans le répertoire tests/resources/libs/.
"""

import os
import sys
from pathlib import Path
import argparse
import logging
import shutil

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

# Ajouter le répertoire parent au PYTHONPATH
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))
    logging.info(f"Répertoire parent ajouté au PYTHONPATH: {parent_dir}")

def main():
    parser = argparse.ArgumentParser(description="Télécharge les JARs minimaux pour les tests")
    parser.add_argument('--force', action='store_true', help="Force le téléchargement même si les JARs existent déjà")
    args = parser.parse_args()
    
    try:
        # Importer la fonction de téléchargement
        from argumentiation_analysis.core.jvm_setup import download_tweety_jars
    except ImportError as e:
        logging.error(f"Erreur d'importation: {e}")
        logging.error("Assurez-vous que le package argumentiation_analysis est installé ou dans le PYTHONPATH.")
        sys.exit(1)
    
    # Définir le répertoire cible
    test_resources_dir = parent_dir / "argumentiation_analysis" / "tests" / "resources" / "libs"
    test_resources_dir.mkdir(parents=True, exist_ok=True)
    
    # Vérifier si les JARs existent déjà
    if not args.force and test_resources_dir.exists() and any(test_resources_dir.glob("*.jar")):
        logging.info(f"Des JARs existent déjà dans {test_resources_dir}. Utilisez --force pour les remplacer.")
        sys.exit(0)
    
    logging.info(f"Téléchargement des JARs minimaux pour les tests dans {test_resources_dir}...")
    
    # Liste des modules minimaux nécessaires pour les tests
    minimal_modules = [
        "logics.pl",  # Module de logique propositionnelle
        "commons"     # Module de base
    ]
    
    # Télécharger les JARs minimaux
    try:
        success = download_tweety_jars(
            target_dir=str(test_resources_dir),
            minimal_modules=minimal_modules
        )
        
        if success:
            logging.info("✅ JARs minimaux téléchargés avec succès.")
            
            # Créer un fichier .gitkeep dans le répertoire native
            native_dir = test_resources_dir / "native"
            native_dir.mkdir(exist_ok=True)
            gitkeep_file = native_dir / ".gitkeep"
            gitkeep_file.touch()
            
            # Créer un fichier README.md pour expliquer le contenu du répertoire
            readme_content = """# JARs de test pour argumentiation_analysis

Ce répertoire contient les JARs minimaux nécessaires pour exécuter les tests
qui dépendent de la JVM. Ces JARs sont une version réduite des JARs Tweety
utilisés par le projet.

## Contenu

- `org.tweetyproject.tweety-full-*.jar`: JAR principal de Tweety
- `org.tweetyproject.logics.pl-*.jar`: Module de logique propositionnelle
- `org.tweetyproject.commons-*.jar`: Module de base

## Utilisation

Ces JARs sont utilisés automatiquement par la classe `JVMTestCase` lorsque
des tests qui dépendent de la JVM sont exécutés.

## Mise à jour

Pour mettre à jour ces JARs, exécutez le script `scripts/download_test_jars.py`
avec l'option `--force`.
"""
            readme_file = test_resources_dir / "README.md"
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            logging.info(f"Fichier README.md créé dans {test_resources_dir}")
        else:
            logging.error("❌ Échec du téléchargement des JARs minimaux.")
            sys.exit(1)
    except Exception as e:
        logging.error(f"❌ Erreur lors du téléchargement des JARs: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()