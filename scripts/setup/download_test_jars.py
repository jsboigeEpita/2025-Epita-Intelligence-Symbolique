"""
Script pour télécharger les JARs minimaux nécessaires pour les tests.

Ce script télécharge une version minimale des JARs Tweety nécessaires
pour les tests et les place dans le répertoire tests/resources/libs/.
"""

import argumentation_analysis.core.environment
import sys
from pathlib import Path
import argparse
import logging

# Ajouter le répertoire parent au PYTHONPATH (si nécessaire, bien que non utilisé directement ici après refactor)
project_root = Path(__file__).resolve().parent.parent.parent # MODIFIÉ: Décommenté et activé
if str(project_root) not in sys.path: # MODIFIÉ: Décommenté et activé
    sys.path.insert(0, str(project_root)) # MODIFIÉ: Décommenté et activé

try:
    # project_core.utils.network_utils.download_file n'est plus directement utilisé ici.
    # Il est utilisé par le pipeline.
    from project_core.pipelines.download_pipeline import run_download_jars_pipeline
    from argumentation_analysis.utils.core_utils.logging_utils import setup_logging # Pour configurer le logging centralisé
except ImportError as e:
    # Utilisation du logging standard si setup_logging n'est pas encore disponible
    # ou si l'import du pipeline échoue.
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    logging.error(f"Erreur d'importation: {e}")
    logging.error(
        "Impossible d'importer les modules nécessaires depuis project_core. "
        "Assurez-vous que le PYTHONPATH est correctement configuré ou que le package est installé."
    )
    sys.exit(1)

# La configuration JARS_TO_DOWNLOAD est retirée.
# Le pipeline `run_download_jars_pipeline` devrait gérer la source des informations sur les JARs
# (par exemple, via un fichier de configuration ou des paramètres internes).
# Si le pipeline attend une liste, on lui passera None ou une liste vide,
# et il devra gérer ce cas.

def main():
    # Configuration du logging via la fonction utilitaire
    # Le niveau de log peut être ajusté par argument de ligne de commande si nécessaire.
    # Pour l'instant, on utilise le niveau INFO par défaut de setup_logging.
    setup_logging() # Utilise la configuration par défaut (INFO, format standard)
    
    logger = logging.getLogger(__name__) # Obtenir un logger spécifique au module

    parser = argparse.ArgumentParser(description="Télécharge les JARs pour les tests")
    parser.add_argument(
        '--force',
        action='store_true',
        help="Force le téléchargement même si les JARs existent déjà."
    )
    parser.add_argument(
        '--target-dir',
        type=str,
        default=None,
        help="Répertoire de destination optionnel pour les JARs. "
             "Par défaut: 'argumentation_analysis/tests/resources/libs/'."
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Niveau de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)."
    )
    args = parser.parse_args()

    # Reconfigurer le logging avec le niveau spécifié si différent de INFO
    if args.log_level != "INFO":
        setup_logging(level=getattr(logging, args.log_level.upper()))
        logger.info(f"Niveau de logging configuré sur : {args.log_level}")


    # Définir le répertoire cible pour les JARs de test
    if args.target_dir:
        test_resources_dir = Path(args.target_dir)
    else:
        project_root_dir = Path(__file__).resolve().parent.parent.parent
        test_resources_dir = project_root_dir / "argumentation_analysis" / "tests" / "resources" / "libs"
    
    test_resources_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Répertoire cible pour les JARs: {test_resources_dir}")

    # Appel du pipeline de téléchargement
    # La logique de simulation est retirée, le pipeline gère le téléchargement réel.
    # Si JARS_TO_DOWNLOAD est vide, le pipeline le gérera et retournera True.
    logger.info("Lancement du pipeline de téléchargement des JARs...")
    # Appel du pipeline sans `jars_to_download` explicite ici.
    # Le pipeline doit savoir où trouver cette information ou accepter `None`.
    pipeline_successful = run_download_jars_pipeline(
        jars_to_download=None, # Ou une liste vide [], selon ce que le pipeline attend
        destination_dir=test_resources_dir,
        force_download=args.force
    )

    if pipeline_successful:
        # La vérification `if not JARS_TO_DOWNLOAD:` n'est plus pertinente ici.
        # Le pipeline devrait logger si aucun JAR n'a été téléchargé.
        logger.info("✅ Le pipeline de téléchargement des JARs s'est terminé avec succès.")

        # Créer un fichier .gitkeep dans le répertoire native
        native_dir = test_resources_dir / "native"
        native_dir.mkdir(exist_ok=True)
        gitkeep_file = native_dir / ".gitkeep"
        if not gitkeep_file.exists():
            gitkeep_file.touch()
            logging.info(f"Fichier .gitkeep créé/assuré dans {native_dir}")
        
        # Créer un fichier README.md pour expliquer le contenu du répertoire
        readme_content = """# JARs de test pour argumentation_analysis

Ce répertoire contient les JARs nécessaires pour exécuter les tests
qui dépendent de la JVM. Ces JARs peuvent être une version réduite des JARs Tweety
utilisés par le projet, ou d'autres dépendances Java.

## Contenu

Le contenu exact dépend des JARs configurés pour le téléchargement dans
`scripts/setup/download_test_jars.py`.

## Utilisation

Ces JARs sont utilisés automatiquement par la classe `JVMTestCase` ou d'autres
mécanismes de test qui dépendent de la JVM.

## Mise à jour

Pour mettre à jour ces JARs, exécutez le script `scripts/setup/download_test_jars.py`
avec l'option `--force`.
"""
        readme_file = test_resources_dir / "README.md"
        if not readme_file.exists() or args.force: # Recréer si forcé ou non existant
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            logger.info(f"Fichier README.md créé/mis à jour dans {test_resources_dir}")
        else:
            logger.info(f"Fichier README.md existe déjà dans {test_resources_dir}. Non modifié (utiliser --force pour écraser).")
            
    else:
        logger.error("❌ Échec du pipeline de téléchargement des JARs.")
        sys.exit(1)

if __name__ == "__main__":
    main()