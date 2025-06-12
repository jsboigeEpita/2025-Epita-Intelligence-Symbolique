#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de nettoyage des fichiers obsolètes

Ce script permet de:
1. Sauvegarder les fichiers obsolètes dans un répertoire d'archives
2. Vérifier que la sauvegarde est complète et valide
3. Supprimer les fichiers obsolètes de leur emplacement d'origine
4. Générer un rapport de suppression
import project_core.core_from_scripts.auto_env
5. Restaurer les fichiers supprimés si nécessaire

Options:
    --dry-run: Simule les opérations sans effectuer de modifications
    --no-backup: Supprime les fichiers sans sauvegarde (déconseillé)
    --restore: Restaure les fichiers depuis les archives
    --list: Liste les fichiers obsolètes sans effectuer d'actions
    --force: Force la suppression même en cas d'erreur de sauvegarde
    --verbose: Affiche des informations détaillées pendant l'exécution
"""

import os
import sys
import shutil
import json
import argparse
import logging
import hashlib
import datetime
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cleanup_obsolete_files.log')
    ]
)
logger = logging.getLogger(__name__)

# Liste des fichiers obsolètes à supprimer
OBSOLETE_FILES = [
    # Scripts d'extraction refactorisés
    "argumentiation_analysis/utils/extract_repair/repair_extract_markers.py",
    "argumentiation_analysis/utils/extract_repair/verify_extracts.py",
    "argumentiation_analysis/utils/extract_repair/fix_missing_first_letter.py",
    "argumentiation_analysis/utils/extract_repair/verify_extracts_with_llm.py",
    "argumentiation_analysis/utils/extract_repair/repair_extract_markers.ipynb",
    # Utilitaires remplacés par des services
    "argumentiation_analysis/ui/extract_utils.py",
]

# Répertoire d'archives
ARCHIVE_DIR = "_archives"
METADATA_FILE = "metadata.json"


def parse_arguments() -> argparse.Namespace:
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        argparse.Namespace: Les arguments parsés
    """
    parser = argparse.ArgumentParser(
        description="Script de nettoyage des fichiers obsolètes"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simule les opérations sans effectuer de modifications"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Supprime les fichiers sans sauvegarde (déconseillé)"
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Restaure les fichiers depuis les archives"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Liste les fichiers obsolètes sans effectuer d'actions"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force la suppression même en cas d'erreur de sauvegarde"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Affiche des informations détaillées pendant l'exécution"
    )
    return parser.parse_args()


def calculate_file_hash(file_path: str) -> str:
    """
    Calcule le hash SHA-256 d'un fichier.
    
    Args:
        file_path (str): Chemin du fichier
        
    Returns:
        str: Hash SHA-256 du fichier
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def create_archive_directory() -> str:
    """
    Crée le répertoire d'archives avec un horodatage.
    
    Returns:
        str: Chemin du répertoire d'archives créé
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = os.path.join(ARCHIVE_DIR, f"backup_{timestamp}")
    
    if not os.path.exists(ARCHIVE_DIR):
        os.mkdir(ARCHIVE_DIR)
        logger.info(f"Répertoire principal d'archives créé: {ARCHIVE_DIR}")
    
    os.makedirs(archive_path, exist_ok=True)
    logger.info(f"Répertoire d'archives créé: {archive_path}")
    
    return archive_path


def backup_files(files: List[str], archive_path: str, dry_run: bool = False) -> Dict[str, Dict[str, Any]]:
    """
    Sauvegarde les fichiers dans le répertoire d'archives.
    
    Args:
        files (List[str]): Liste des fichiers à sauvegarder
        archive_path (str): Chemin du répertoire d'archives
        dry_run (bool): Mode simulation
        
    Returns:
        Dict[str, Dict[str, Any]]: Métadonnées des fichiers sauvegardés
    """
    metadata = {}
    
    for file_path in files:
        if not os.path.exists(file_path):
            logger.warning(f"Fichier non trouvé: {file_path}")
            continue
        
        # Calcul du hash avant sauvegarde
        original_hash = calculate_file_hash(file_path)
        
        # Création des répertoires intermédiaires dans l'archive
        relative_dir = os.path.dirname(file_path)
        archive_file_dir = os.path.join(archive_path, relative_dir)
        
        if not dry_run:
            os.makedirs(archive_file_dir, exist_ok=True)
            
            # Copie du fichier
            archive_file_path = os.path.join(archive_path, file_path)
            shutil.copy2(file_path, archive_file_path)
            
            # Vérification du hash après sauvegarde
            archived_hash = calculate_file_hash(archive_file_path)
            
            if original_hash != archived_hash:
                logger.error(f"Erreur de vérification du hash pour {file_path}")
                logger.error(f"  Original: {original_hash}")
                logger.error(f"  Archive: {archived_hash}")
                raise ValueError(f"Erreur de vérification du hash pour {file_path}")
            
            logger.info(f"Fichier sauvegardé: {file_path} -> {archive_file_path}")
        else:
            logger.info(f"[DRY-RUN] Fichier qui serait sauvegardé: {file_path}")
            archived_hash = original_hash  # En mode simulation, on considère que les hash sont identiques
        
        # Stockage des métadonnées
        file_stat = os.stat(file_path)
        metadata[file_path] = {
            "original_path": file_path,
            "archive_path": os.path.join(archive_path, file_path),
            "size": file_stat.st_size,
            "modified_time": datetime.datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            "original_hash": original_hash,
            "archived_hash": archived_hash,
            "backup_time": datetime.datetime.now().isoformat()
        }
    
    return metadata


def save_metadata(metadata: Dict[str, Dict[str, Any]], archive_path: str, dry_run: bool = False) -> str:
    """
    Sauvegarde les métadonnées dans un fichier JSON.
    
    Args:
        metadata (Dict[str, Dict[str, Any]]): Métadonnées à sauvegarder
        archive_path (str): Chemin du répertoire d'archives
        dry_run (bool): Mode simulation
        
    Returns:
        str: Chemin du fichier de métadonnées
    """
    metadata_path = os.path.join(archive_path, METADATA_FILE)
    
    if not dry_run:
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"Métadonnées sauvegardées: {metadata_path}")
    else:
        logger.info(f"[DRY-RUN] Métadonnées qui seraient sauvegardées: {metadata_path}")
    
    return metadata_path


def verify_backup(metadata: Dict[str, Dict[str, Any]], dry_run: bool = False) -> bool:
    """
    Vérifie que la sauvegarde est complète et valide.
    
    Args:
        metadata (Dict[str, Dict[str, Any]]): Métadonnées des fichiers sauvegardés
        dry_run (bool): Mode simulation
        
    Returns:
        bool: True si la sauvegarde est valide, False sinon
    """
    if dry_run:
        logger.info("[DRY-RUN] Vérification de la sauvegarde simulée")
        return True
    
    for file_path, file_meta in metadata.items():
        archive_path = file_meta["archive_path"]
        
        # Vérification de l'existence du fichier archivé
        if not os.path.exists(archive_path):
            logger.error(f"Fichier archivé non trouvé: {archive_path}")
            return False
        
        # Vérification de la taille
        archive_size = os.path.getsize(archive_path)
        if archive_size != file_meta["size"]:
            logger.error(f"Taille incorrecte pour {archive_path}")
            logger.error(f"  Attendu: {file_meta['size']}, Obtenu: {archive_size}")
            return False
        
        # Vérification du hash
        archive_hash = calculate_file_hash(archive_path)
        if archive_hash != file_meta["original_hash"]:
            logger.error(f"Hash incorrect pour {archive_path}")
            logger.error(f"  Attendu: {file_meta['original_hash']}, Obtenu: {archive_hash}")
            return False
    
    logger.info("Vérification de la sauvegarde: OK")
    return True


def delete_files(files: List[str], dry_run: bool = False) -> List[str]:
    """
    Supprime les fichiers obsolètes.
    
    Args:
        files (List[str]): Liste des fichiers à supprimer
        dry_run (bool): Mode simulation
        
    Returns:
        List[str]: Liste des fichiers supprimés
    """
    deleted_files = []
    
    for file_path in files:
        if not os.path.exists(file_path):
            logger.warning(f"Fichier déjà supprimé ou non trouvé: {file_path}")
            continue
        
        if not dry_run:
            os.remove(file_path)
            logger.info(f"Fichier supprimé: {file_path}")
        else:
            logger.info(f"[DRY-RUN] Fichier qui serait supprimé: {file_path}")
        
        deleted_files.append(file_path)
    
    return deleted_files


def generate_report(metadata: Dict[str, Dict[str, Any]], deleted_files: List[str], archive_path: str, dry_run: bool = False) -> str:
    """
    Génère un rapport de suppression.
    
    Args:
        metadata (Dict[str, Dict[str, Any]]): Métadonnées des fichiers sauvegardés
        deleted_files (List[str]): Liste des fichiers supprimés
        archive_path (str): Chemin du répertoire d'archives
        dry_run (bool): Mode simulation
        
    Returns:
        str: Chemin du rapport généré
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(archive_path, f"rapport_suppression_{timestamp}.md")
    
    report_content = f"""# Rapport de suppression des fichiers obsolètes

Date: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Mode: {"Simulation (dry-run)" if dry_run else "Exécution réelle"}
Répertoire d'archives: {archive_path}

## Fichiers sauvegardés

| Fichier | Taille | Date de modification | Hash SHA-256 |
|---------|--------|----------------------|--------------|
"""
    
    for file_path, file_meta in metadata.items():
        report_content += f"| {file_path} | {file_meta['size']} octets | {file_meta['modified_time']} | {file_meta['original_hash'][:8]}... |\n"
    
    report_content += f"""
## Fichiers supprimés

Total: {len(deleted_files)} fichiers

"""
    
    for file_path in deleted_files:
        report_content += f"- {file_path}\n"
    
    report_content += f"""
## Restauration

Pour restaurer ces fichiers, exécutez:

```
python cleanup_obsolete_files.py --restore
```

Ou spécifiez le répertoire d'archives:

```
python cleanup_obsolete_files.py --restore --archive-dir={archive_path}
```
"""
    
    if not dry_run:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        logger.info(f"Rapport généré: {report_path}")
    else:
        logger.info(f"[DRY-RUN] Rapport qui serait généré: {report_path}")
    
    return report_path


def find_latest_archive() -> Optional[str]:
    """
    Trouve le répertoire d'archives le plus récent.
    
    Returns:
        Optional[str]: Chemin du répertoire d'archives le plus récent, ou None si aucun n'est trouvé
    """
    if not os.path.exists(ARCHIVE_DIR):
        logger.error(f"Répertoire d'archives non trouvé: {ARCHIVE_DIR}")
        return None
    
    archives = [os.path.join(ARCHIVE_DIR, d) for d in os.listdir(ARCHIVE_DIR) if os.path.isdir(os.path.join(ARCHIVE_DIR, d))]
    
    if not archives:
        logger.error(f"Aucune archive trouvée dans {ARCHIVE_DIR}")
        return None
    
    # Tri par date de modification (la plus récente en premier)
    archives.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    return archives[0]


def restore_files(archive_dir: Optional[str] = None, dry_run: bool = False) -> bool:
    """
    Restaure les fichiers depuis les archives.
    
    Args:
        archive_dir (Optional[str]): Répertoire d'archives spécifique (utilise le plus récent si None)
        dry_run (bool): Mode simulation
        
    Returns:
        bool: True si la restauration a réussi, False sinon
    """
    # Trouver le répertoire d'archives
    if archive_dir is None:
        archive_dir = find_latest_archive()
        if archive_dir is None:
            return False
    
    logger.info(f"Utilisation du répertoire d'archives: {archive_dir}")
    
    # Charger les métadonnées
    metadata_path = os.path.join(archive_dir, METADATA_FILE)
    if not os.path.exists(metadata_path):
        logger.error(f"Fichier de métadonnées non trouvé: {metadata_path}")
        return False
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Restaurer chaque fichier
    for file_path, file_meta in metadata.items():
        archive_path = file_meta["archive_path"]
        
        if not os.path.exists(archive_path):
            logger.error(f"Fichier archivé non trouvé: {archive_path}")
            continue
        
        # Création des répertoires intermédiaires
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        if not dry_run:
            shutil.copy2(archive_path, file_path)
            logger.info(f"Fichier restauré: {archive_path} -> {file_path}")
            
            # Vérification du hash
            restored_hash = calculate_file_hash(file_path)
            if restored_hash != file_meta["original_hash"]:
                logger.warning(f"Hash différent après restauration pour {file_path}")
                logger.warning(f"  Original: {file_meta['original_hash']}")
                logger.warning(f"  Restauré: {restored_hash}")
        else:
            logger.info(f"[DRY-RUN] Fichier qui serait restauré: {archive_path} -> {file_path}")
    
    logger.info("Restauration terminée")
    return True


def list_obsolete_files() -> None:
    """
    Liste les fichiers obsolètes et leur statut.
    """
    logger.info("Liste des fichiers obsolètes:")
    
    for file_path in OBSOLETE_FILES:
        status = "Présent" if os.path.exists(file_path) else "Absent"
        logger.info(f"- {file_path} [{status}]")


def main() -> int:
    """
    Fonction principale du script.
    
    Returns:
        int: Code de retour (0 pour succès, 1 pour erreur)
    """
    args = parse_arguments()
    
    # Configuration du niveau de logging
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Mode liste
    if args.list:
        list_obsolete_files()
        return 0
    
    # Mode restauration
    if args.restore:
        success = restore_files(dry_run=args.dry_run)
        return 0 if success else 1
    
    # Vérification des options incompatibles
    if args.no_backup and not args.force:
        logger.error("L'option --no-backup nécessite l'option --force pour confirmer")
        return 1
    
    # Création du répertoire d'archives (sauf si --no-backup)
    if not args.no_backup:
        archive_path = create_archive_directory()
        
        # Sauvegarde des fichiers
        try:
            metadata = backup_files(OBSOLETE_FILES, archive_path, dry_run=args.dry_run)
            save_metadata(metadata, archive_path, dry_run=args.dry_run)
            
            # Vérification de la sauvegarde
            if not args.dry_run:
                backup_valid = verify_backup(metadata)
                if not backup_valid and not args.force:
                    logger.error("La sauvegarde n'est pas valide. Utilisez --force pour forcer la suppression.")
                    return 1
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde: {str(e)}")
            if not args.force:
                return 1
    else:
        logger.warning("Mode sans sauvegarde activé. Les fichiers seront supprimés définitivement.")
        archive_path = None
        metadata = {}
    
    # Suppression des fichiers
    deleted_files = delete_files(OBSOLETE_FILES, dry_run=args.dry_run)
    
    # Génération du rapport (sauf si --no-backup)
    if not args.no_backup:
        generate_report(metadata, deleted_files, archive_path, dry_run=args.dry_run)
    
    logger.info("Opération terminée avec succès")
    return 0


if __name__ == "__main__":
    sys.exit(main())