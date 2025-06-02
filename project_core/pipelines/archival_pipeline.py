# project_core/pipelines/archival_pipeline.py
import logging
from pathlib import Path
from typing import Union # Ajout pour compatibilité avec Python < 3.9 pour PathLike

# Supposons que ces utilitaires existent et sont importables
# Ces chemins seront ajustés si les modules sont ailleurs ou si les noms de fonctions diffèrent
from project_core.utils.logging_utils import setup_logging
from project_core.utils.file_utils import check_path_exists, create_archive_path, archive_file

def run_archival_pipeline(
    source_dir: Union[str, Path],
    archive_base_dir: Union[str, Path],
    file_pattern: str,
    preserve_levels: int,
    log_level_str: str = "INFO"
) -> None:
    """
    Exécute le pipeline d'archivage des données.

    Cette fonction configure le logging, vérifie les chemins source et de base
    d'archivage, puis itère sur les fichiers correspondant au motif spécifié
    dans le répertoire source. Pour chaque fichier, elle détermine le chemin
    d'archivage de destination et déplace le fichier. Les opérations
    sont loggées.

    Args:
        source_dir (Union[str, Path]): Le répertoire source contenant les fichiers à archiver.
        archive_base_dir (Union[str, Path]): Le répertoire de base où les archives
                                            seront stockées.
        file_pattern (str): Le motif de glob pour trouver les fichiers à archiver
                            (ex: "*.txt", "**/*.log").
        preserve_levels (int): Le nombre de niveaux de répertoires à préserver
                               depuis le chemin source lors de la création du
                               chemin d'archivage.
        log_level_str (str, optional): Le niveau de logging (ex: "INFO", "DEBUG").
                                       Par défaut à "INFO".

    Returns:
        None
    """
    logger = setup_logging(log_level_str, "archival_pipeline")
    logger.info("Démarrage du pipeline d'archivage.")

    try:
        source_dir_path = Path(source_dir)
        archive_base_dir_path = Path(archive_base_dir)

        # 1. Vérifier que source_dir et archive_base_dir existent et sont des répertoires
        check_path_exists(source_dir_path, "répertoire source", is_dir=True)
        check_path_exists(archive_base_dir_path, "répertoire de base d'archivage", is_dir=True)
        logger.info(f"Répertoire source: {source_dir_path}")
        logger.info(f"Répertoire de base d'archivage: {archive_base_dir_path}")
        logger.info(f"Motif de fichier: {file_pattern}, Niveaux à préserver: {preserve_levels}")

        # 2. Itérer sur les fichiers dans source_dir
        archived_files_count = 0
        processed_files_count = 0
        for source_file in source_dir_path.rglob(file_pattern):
            processed_files_count += 1
            if source_file.is_file():
                logger.debug(f"Traitement du fichier source: {source_file}")
                try:
                    # a. Déterminer le chemin de destination
                    archive_path = create_archive_path(
                        source_file_path=source_file,
                        source_base_dir=source_dir_path,
                        archive_base_dir=archive_base_dir_path,
                        preserve_levels=preserve_levels
                    )
                    logger.debug(f"Chemin d'archivage calculé: {archive_path}")

                    # b. Archiver le fichier
                    # archive_file gère la création des répertoires parents si nécessaire
                    archive_file(source_file, archive_path, create_parent_dirs=True)
                    
                    # c. Logger l'opération
                    logger.info(f"Archivé: '{source_file}' -> '{archive_path}'")
                    archived_files_count += 1
                except Exception as e:
                    logger.error(f"Erreur lors de l'archivage du fichier '{source_file}': {e}", exc_info=True)
            else:
                logger.debug(f"Ignoré (n'est pas un fichier): {source_file}")
        
        logger.info(f"Pipeline d'archivage terminé. {archived_files_count} fichier(s) archivé(s) sur {processed_files_count} élément(s) traité(s) correspondant au motif.")

    except FileNotFoundError as fnf_error:
        logger.error(f"Erreur de configuration du pipeline (chemin non trouvé): {fnf_error}", exc_info=True)
    except ValueError as val_error:
        logger.error(f"Erreur de configuration du pipeline (valeur invalide): {val_error}", exc_info=True)
    except Exception as e:
        logger.error(f"Une erreur inattendue est survenue dans le pipeline d'archivage: {e}", exc_info=True)

if __name__ == '__main__':
    # Section pour des tests locaux rapides (optionnel)
    # Assurez-vous que les répertoires de test existent et contiennent des fichiers exemples
    print("Exécution d'un test local du pipeline d'archivage...")
    
    # Créer des répertoires et fichiers de test
    test_source_dir = Path("temp_test_source")
    test_archive_dir = Path("temp_test_archive")
    
    # Nettoyer les exécutions précédentes
    import shutil
    if test_source_dir.exists():
        shutil.rmtree(test_source_dir)
    if test_archive_dir.exists():
        shutil.rmtree(test_archive_dir)
        
    test_source_dir.mkdir(parents=True, exist_ok=True)
    test_archive_dir.mkdir(parents=True, exist_ok=True)
    
    (test_source_dir / "sub1").mkdir(exist_ok=True)
    (test_source_dir / "sub1" / "sub2").mkdir(exist_ok=True)
    
    (test_source_dir / "file1.txt").write_text("contenu file1")
    (test_source_dir / "file2.log").write_text("contenu file2")
    (test_source_dir / "sub1" / "file3.txt").write_text("contenu file3")
    (test_source_dir / "sub1" / "sub2" / "file4.data").write_text("contenu file4")
    (test_source_dir / "sub1" / "sub2" / "another.txt").write_text("contenu another")

    print(f"Répertoire source de test: {test_source_dir.resolve()}")
    print(f"Répertoire d'archive de test: {test_archive_dir.resolve()}")
    print("Structure source:")
    for item in test_source_dir.rglob("*"):
        print(f"  {item.relative_to(test_source_dir)}")

    # Exécuter le pipeline
    run_archival_pipeline(
        source_dir=test_source_dir,
        archive_base_dir=test_archive_dir,
        file_pattern="*.txt",
        preserve_levels=1,
        log_level_str="DEBUG"
    )
    
    print("\nStructure d'archive après exécution (pattern=*.txt, preserve_levels=1):")
    for item in test_archive_dir.rglob("*"):
        print(f"  {item.relative_to(test_archive_dir)}")

    # Nettoyage après test
    # shutil.rmtree(test_source_dir)
    # shutil.rmtree(test_archive_dir)
    # print("\nRépertoires de test nettoyés.")
    print(f"\nVérifiez les répertoires {test_source_dir.resolve()} et {test_archive_dir.resolve()} manuellement.")