#!/usr/bin/env python3
"""
Script pour extraire des versions de code jugées "prometteuses" à partir de
fichiers de log de conversation au format Markdown.

Une version est considérée comme prometteuse si les tests exécutés après une
modification du code montrent un succès partiel (entre 5 et 7 tests réussis).

Le script analyse les logs, identifie ces moments, et extrait le code
source correspondant pour recréer une arborescence de projet pour chaque
version prometteuse trouvée.
"""

import argparse
import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class PromisingVersionExtractor:
    """
    Extrait les versions de code prometteuses des logs de conversation.
    """
    def __init__(self, output_base_dir: str = ".temp/recovered"):
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Les extractions seront sauvegardées dans : {self.output_base_dir.resolve()}")

    def extract_from_logs(self, log_files: List[str]):
        """
        Orchestre l'extraction à partir d'une liste de fichiers de log.
        """
        total_snapshots = 0
        for i, log_file_path in enumerate(log_files):
            log_identifier = f"conv{i+1}"
            logger.info(f"--- Traitement du fichier de log : {log_file_path} ---")
            try:
                snapshots_found = self._process_single_log(Path(log_file_path), log_identifier)
                if snapshots_found:
                    logger.info(f"✓ {snapshots_found} snapshot(s) extrait(s) de {Path(log_file_path).name}")
                    total_snapshots += snapshots_found
                else:
                    logger.warning(f"Aucun snapshot prometteur trouvé dans {Path(log_file_path).name}")
            except Exception as e:
                logger.error(f"Erreur lors du traitement de {log_file_path}: {e}", exc_info=True)
        
        logger.info(f"--- Fin du traitement ---")
        if total_snapshots > 0:
            logger.info(f"🎉 Total de {total_snapshots} snapshot(s) prometteur(s) extrait(s) dans {self.output_base_dir.resolve()}")
        else:
            logger.info("Aucun snapshot prometteur n'a été trouvé dans les fichiers de log fournis.")

    def _process_single_log(self, log_file: Path, log_identifier: str) -> int:
        """
        Analyse un seul fichier de log pour en extraire les snapshots prometteurs.
        """
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Impossible de lire le fichier {log_file}: {e}")
            return 0

        code_block_regex = r"<(write_to_file|apply_diff)>(.*?)</\1>"
        pytest_summary_regex = r"={5,}\s*short test summary info\s*={5,}[\s\S]*?(\d+)\s+passed"

        # On recherche tous les blocs de code et les résultats de tests avec leur position de fin
        code_blocks = [(m.group(1), m.group(2), m.end(0)) for m in re.finditer(code_block_regex, content, re.DOTALL)]
        test_results = [(int(m.group(1)), m.start(0)) for m in re.finditer(pytest_summary_regex, content)]

        snapshots_created = 0
        for i, (passed_count, result_pos) in enumerate(test_results):
            if 5 <= passed_count <= 7:
                logger.info(f"Résultat prometteur trouvé dans {log_file.name} (pos {result_pos}): {passed_count} tests passés.")
                
                last_code_block_before_test: Optional[Tuple[str, str]] = None
                for tool, code_content, code_pos in code_blocks:
                    if code_pos < result_pos:
                        last_code_block_before_test = (tool, code_content.strip())
                    else:
                        # On a dépassé la position du test, le dernier bloc trouvé est le bon.
                        break 
                
                if last_code_block_before_test:
                    snapshots_created += 1
                    snapshot_name = f"{log_identifier}_snapshot{snapshots_created}"
                    self._create_snapshot(snapshot_name, last_code_block_before_test[0], last_code_block_before_test[1])
                else:
                    logger.warning(f"Aucun bloc de code (<write_to_file> ou <apply_diff>) trouvé avant le test prometteur à la position {result_pos}.")

        return snapshots_created

    def _create_snapshot(self, snapshot_name: str, tool: str, content_xml: str):
        """
        Crée l'arborescence et les fichiers pour un snapshot donné à partir du XML de l'outil.
        """
        snapshot_dir = self.output_base_dir / snapshot_name
        try:
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            
            path_match = re.search(r"<path>(.*?)</path>", content_xml, re.DOTALL)
            if not path_match:
                logger.error(f"  ! Chemin de fichier non trouvé dans le bloc {tool} pour {snapshot_name}.")
                return

            file_path_str = Path(path_match.group(1).strip())
            
            if tool == 'write_to_file':
                content_match = re.search(r"<content>(.*?)</content>", content_xml, re.DOTALL)
                if content_match:
                    file_content = content_match.group(1).strip()
                    target_path = snapshot_dir / file_path_str
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(file_content)
                    logger.info(f"  -> Fichier créé : {target_path}")
                else:
                    logger.error(f"  ! Contenu non trouvé pour write_to_file dans {snapshot_name}.")

            elif tool == 'apply_diff':
                diff_match = re.search(r"<diff>(.*?)</diff>", content_xml, re.DOTALL)
                if diff_match:
                    diff_content = diff_match.group(1).strip()
                    # On sauvegarde le diff dans un fichier pour analyse manuelle.
                    target_path = snapshot_dir / f"{file_path_str.name}.diff"
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(f"Original file path: {file_path_str}\n\n")
                        f.write(diff_content)
                    logger.info(f"  -> Diff sauvegardé : {target_path} (application manuelle requise)")
                else:
                    logger.error(f"  ! Contenu de diff non trouvé pour apply_diff dans {snapshot_name}.")

        except Exception as e:
            logger.error(f"Erreur lors de la création du snapshot {snapshot_name}: {e}", exc_info=True)


def main():
    """Point d'entrée principal du script."""
    parser = argparse.ArgumentParser(
        description="Extrait des versions de code prometteuses depuis des logs de conversation.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "log_files",
        nargs='+',
        help="Liste des chemins vers les fichiers de log (.md) à analyser."
    )
    parser.add_argument(
        "--output-dir",
        default=".temp/recovered",
        help="Répertoire de base pour sauvegarder les snapshots de code extraits."
    )
    
    args = parser.parse_args()

    extractor = PromisingVersionExtractor(output_base_dir=args.output_dir)
    extractor.extract_from_logs(args.log_files)


if __name__ == "__main__":
    main()