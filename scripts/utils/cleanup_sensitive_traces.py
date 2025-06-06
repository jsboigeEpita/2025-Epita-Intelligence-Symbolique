#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de nettoyage automatique des traces sensibles.

Ce script nettoie automatiquement les traces sensibles générées lors de l'analyse
de discours politiques complexes, en préservant la sécurité des données.
"""

import os
import sys
import shutil
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

# Ajouter le chemin du projet
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from argumentation_analysis.paths import PROJECT_ROOT_DIR

logger = logging.getLogger(__name__)

class SensitiveDataCleaner:
    """
    Gestionnaire de nettoyage des données sensibles.
    """
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        """
        Initialise le nettoyeur de données sensibles.
        
        Args:
            dry_run: Mode simulation (aucune suppression réelle)
            verbose: Mode verbeux pour les logs
        """
        self.dry_run = dry_run
        self.verbose = verbose
        self.project_root = PROJECT_ROOT_DIR
        self.cleaned_files: List[Path] = []
        self.errors: List[str] = []
        
        # Configuration du logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
    
    def get_sensitive_patterns(self) -> List[str]:
        """
        Retourne les patterns de fichiers/répertoires sensibles à nettoyer.
        
        Returns:
            Liste des patterns de fichiers sensibles
        """
        return [
            # Logs de conversation qui peuvent contenir des données politiques
            "logs/rhetorical_analysis_demo_conversation.log",
            "logs/rhetorical_analysis_report.json",
            "logs/validation_tests/*political*",
            "logs/*complex*",
            "logs/*discourse*",
            "logs/*speech*",
            
            # Fichiers temporaires d'analyse
            "temp_extracts/extracts_decrypted_*.json",
            "_temp/analysis_*.json",
            "_temp/political_*.txt",
            
            # Caches pouvant contenir des données sensibles
            "text_cache/*",
            "argumentation_analysis/text_cache/*",
            
            # Fichiers de rapport pouvant contenir des extraits politiques
            "results/rhetorical_analysis_*.json",
            "results/*political*",
            "results/*complex*",
            
            # Fichiers de configuration temporaires non chiffrés
            "data/extract_sources.json",
            "extract_sources_updated.json",
            "scripts/extract_sources_updated.json",
            
            # Fichiers de debug avec données potentiellement sensibles
            "*debug*political*",
            "*analysis*temp*",
            
            # Fichiers de sauvegarde contenant potentiellement des données sensibles
            "**/backups/*political*",
            "**/backups/*complex*",
            
            # Archives temporaires
            "*.tmp",
            "*.temp",
            "*_temp_*"
        ]
    
    def get_log_retention_days(self) -> int:
        """
        Retourne le nombre de jours de rétention pour les logs.
        
        Returns:
            Nombre de jours de rétention (défaut: 7 jours)
        """
        return int(os.getenv("LOG_RETENTION_DAYS", "7"))
    
    def clean_old_logs(self) -> None:
        """
        Nettoie les anciens logs selon la politique de rétention.
        """
        logs_dir = self.project_root / "logs"
        if not logs_dir.exists():
            logger.info("Répertoire logs non trouvé, rien à nettoyer.")
            return
        
        retention_days = self.get_log_retention_days()
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        logger.info(f"Nettoyage des logs antérieurs au {cutoff_date.strftime('%Y-%m-%d')}")
        
        for log_file in logs_dir.rglob("*.log"):
            try:
                # Vérifier l'âge du fichier
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    if self.dry_run:
                        logger.info(f"[DRY-RUN] Suppression de l'ancien log: {log_file}")
                    else:
                        log_file.unlink()
                        logger.info(f"Ancien log supprimé: {log_file}")
                        self.cleaned_files.append(log_file)
                        
            except Exception as e:
                error_msg = f"Erreur lors du nettoyage de {log_file}: {e}"
                logger.error(error_msg)
                self.errors.append(error_msg)
    
    def clean_sensitive_files(self) -> None:
        """
        Nettoie les fichiers contenant potentiellement des données sensibles.
        """
        patterns = self.get_sensitive_patterns()
        logger.info(f"Nettoyage des fichiers sensibles ({len(patterns)} patterns)")
        
        for pattern in patterns:
            try:
                # Gestion des patterns avec globbing
                if "*" in pattern:
                    matching_files = list(self.project_root.glob(pattern))
                    for file_path in matching_files:
                        self._clean_file_or_dir(file_path)
                else:
                    # Fichier spécifique
                    file_path = self.project_root / pattern
                    if file_path.exists():
                        self._clean_file_or_dir(file_path)
                        
            except Exception as e:
                error_msg = f"Erreur lors du traitement du pattern '{pattern}': {e}"
                logger.error(error_msg)
                self.errors.append(error_msg)
    
    def _clean_file_or_dir(self, path: Path) -> None:
        """
        Nettoie un fichier ou répertoire spécifique.
        
        Args:
            path: Chemin vers le fichier ou répertoire à nettoyer
        """
        try:
            if path.is_file():
                if self.dry_run:
                    logger.info(f"[DRY-RUN] Suppression du fichier sensible: {path}")
                else:
                    path.unlink()
                    logger.info(f"Fichier sensible supprimé: {path}")
                    self.cleaned_files.append(path)
                    
            elif path.is_dir():
                if self.dry_run:
                    logger.info(f"[DRY-RUN] Suppression du répertoire sensible: {path}")
                else:
                    shutil.rmtree(path)
                    logger.info(f"Répertoire sensible supprimé: {path}")
                    self.cleaned_files.append(path)
                    
        except Exception as e:
            error_msg = f"Erreur lors de la suppression de {path}: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
    
    def anonymize_remaining_logs(self) -> None:
        """
        Anonymise les logs restants en remplaçant les données sensibles.
        """
        logs_dir = self.project_root / "logs"
        if not logs_dir.exists():
            return
        
        # Patterns de données sensibles à anonymiser
        sensitive_patterns = {
            # Noms de leaders politiques
            r'\b(Hitler|Staline|Mao|Churchill|Roosevelt|Trump|Biden|Macron|Poutine|Putin)\b': '[LEADER]',
            # Noms de pays sensibles dans certains contextes
            r'\b(Allemagne nazie|URSS|Reich)\b': '[HISTORICAL_ENTITY]',
            # Extraits de discours politiques longs
            r'"[^"]{200,}"': '"[LONG_POLITICAL_EXTRACT]"',
            # URLs potentiellement sensibles
            r'https?://[^\s]+political[^\s]*': '[POLITICAL_URL]',
            r'https?://[^\s]+discourse[^\s]*': '[DISCOURSE_URL]'
        }
        
        for log_file in logs_dir.rglob("*.log"):
            try:
                if self._should_anonymize_file(log_file):
                    self._anonymize_file(log_file, sensitive_patterns)
                    
            except Exception as e:
                error_msg = f"Erreur lors de l'anonymisation de {log_file}: {e}"
                logger.error(error_msg)
                self.errors.append(error_msg)
    
    def _should_anonymize_file(self, file_path: Path) -> bool:
        """
        Détermine si un fichier de log doit être anonymisé.
        
        Args:
            file_path: Chemin vers le fichier de log
            
        Returns:
            True si le fichier doit être anonymisé
        """
        # Anonymiser les logs récents qui pourraient contenir des données sensibles
        file_age_hours = (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).total_seconds() / 3600
        return file_age_hours < 24  # Anonymiser les logs de moins de 24h
    
    def _anonymize_file(self, file_path: Path, patterns: dict) -> None:
        """
        Anonymise un fichier en remplaçant les patterns sensibles.
        
        Args:
            file_path: Chemin vers le fichier à anonymiser
            patterns: Dictionnaire des patterns de remplacement
        """
        if self.dry_run:
            logger.info(f"[DRY-RUN] Anonymisation de: {file_path}")
            return
        
        try:
            # Lire le contenu
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Appliquer les patterns d'anonymisation
            import re
            original_size = len(content)
            for pattern, replacement in patterns.items():
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
            
            # Sauvegarder si des changements ont été effectués
            if len(content) != original_size:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Fichier anonymisé: {file_path}")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'anonymisation de {file_path}: {e}")
    
    def clean_all(self) -> None:
        """
        Effectue un nettoyage complet des données sensibles.
        """
        logger.info("=== DÉBUT DU NETTOYAGE DES DONNÉES SENSIBLES ===")
        if self.dry_run:
            logger.info("MODE SIMULATION ACTIVÉ - Aucune suppression réelle")
        
        # 1. Nettoyer les anciens logs
        self.clean_old_logs()
        
        # 2. Nettoyer les fichiers sensibles
        self.clean_sensitive_files()
        
        # 3. Anonymiser les logs restants
        self.anonymize_remaining_logs()
        
        # 4. Rapport final
        self.print_summary()
    
    def print_summary(self) -> None:
        """
        Affiche un résumé du nettoyage effectué.
        """
        logger.info("=== RÉSUMÉ DU NETTOYAGE ===")
        logger.info(f"Fichiers/répertoires nettoyés: {len(self.cleaned_files)}")
        logger.info(f"Erreurs rencontrées: {len(self.errors)}")
        
        if self.verbose and self.cleaned_files:
            logger.info("Fichiers nettoyés:")
            for file_path in self.cleaned_files:
                logger.info(f"  - {file_path}")
        
        if self.errors:
            logger.warning("Erreurs rencontrées:")
            for error in self.errors:
                logger.warning(f"  - {error}")
        
        status = "SIMULATION TERMINÉE" if self.dry_run else "NETTOYAGE TERMINÉ"
        logger.info(f"=== {status} ===")

def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(
        description="Nettoie automatiquement les traces sensibles générées lors de l'analyse de discours politiques."
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Mode simulation - affiche ce qui serait nettoyé sans effectuer de suppressions"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mode verbeux - affiche plus de détails"
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=7,
        help="Nombre de jours de rétention pour les logs (défaut: 7)"
    )
    
    args = parser.parse_args()
    
    # Configurer la rétention des logs via variable d'environnement
    os.environ["LOG_RETENTION_DAYS"] = str(args.retention_days)
    
    # Créer et exécuter le nettoyeur
    cleaner = SensitiveDataCleaner(dry_run=args.dry_run, verbose=args.verbose)
    cleaner.clean_all()
    
    # Code de sortie selon les erreurs
    exit_code = 1 if cleaner.errors else 0
    sys.exit(exit_code)

if __name__ == "__main__":
    main()