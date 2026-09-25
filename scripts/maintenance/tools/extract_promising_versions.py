#!/usr/bin/env python3
"""
Script pour extraire des versions de code jugées "prometteuses" à partir de
fichiers de log de conversation au format Markdown.

Une version est considérée comme prometteuse si les tests exécutés après une
modification du code montrent un succès partiel (par défaut entre 5 et 7 tests
réussis, réglable par ``--min-passed`` / ``--max-passed``).

Pour chaque résultat prometteur, le script reconstruit l'état de **chaque
fichier** touché avant ce résultat, et pas seulement le dernier bloc de code :
le dernier contenu complet connu (``<write_to_file>``, ou le résultat d'un
``<read_file>``), plus les ``<apply_diff>`` venus après lui, sauvegardés à côté
(``<fichier>.diff``, application manuelle requise). Le contexte de conversation
qui précède le résultat est sauvegardé dans ``_CONVERSATION_CONTEXT.md``.
"""

import argparse
import logging
import re
from pathlib import Path, PurePath
from typing import Dict, List, Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

CODE_EVENT_REGEX = re.compile(
    r"<(read_file|write_to_file|apply_diff)>(.*?)</\1>", re.DOTALL
)
PYTEST_SUMMARY_REGEX = re.compile(
    r"={5,}\s*short test summary info\s*={5,}[\s\S]*?(\d+)\s+passed"
)
READ_RESULT_REGEX = re.compile(
    r"Result:[\s\S]*?<file>[\s\S]*?<content[^>]*>\n([\s\S]*?)</content>"
)
# Préfixe de numéro de ligne ajouté par read_file ("  12 | code").
LINE_NUMBER_PREFIX = re.compile(r"^\s*\d+\s*\| ?")
CONTEXT_CHARS = 4000


class PromisingVersionExtractor:
    """
    Extrait les versions de code prometteuses des logs de conversation,
    en reconstruisant l'état des fichiers et en sauvegardant le contexte.
    """

    def __init__(
        self,
        output_base_dir: str = ".temp/recovered",
        min_passed: int = 5,
        max_passed: int = 7,
    ):
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(parents=True, exist_ok=True)
        self.min_passed = min_passed
        self.max_passed = max_passed
        logger.info(
            f"Les extractions seront sauvegardées dans : {self.output_base_dir.resolve()}"
        )

    def extract_from_logs(self, log_files: List[str]):
        """
        Orchestre l'extraction à partir d'une liste de fichiers de log.
        """
        total_snapshots = 0
        for i, log_file_path in enumerate(log_files):
            log_identifier = f"conv{i+1}"
            logger.info(f"--- Traitement du fichier de log : {log_file_path} ---")
            try:
                snapshots_found = self._process_single_log(
                    Path(log_file_path), log_identifier
                )
                if snapshots_found:
                    logger.info(
                        f"✓ {snapshots_found} snapshot(s) extrait(s) de {Path(log_file_path).name}"
                    )
                    total_snapshots += snapshots_found
                else:
                    logger.warning(
                        f"Aucun snapshot prometteur trouvé dans {Path(log_file_path).name}"
                    )
            except Exception as e:
                logger.error(
                    f"Erreur lors du traitement de {log_file_path}: {e}", exc_info=True
                )

        logger.info(f"--- Fin du traitement ---")
        if total_snapshots > 0:
            logger.info(
                f"🎉 Total de {total_snapshots} snapshot(s) prometteur(s) extrait(s) dans {self.output_base_dir.resolve()}"
            )
        else:
            logger.info(
                "Aucun snapshot prometteur n'a été trouvé dans les fichiers de log fournis."
            )

    @staticmethod
    def _get_line_number(content: str, position: int) -> int:
        """Trouve le numéro de ligne à partir de la position d'un caractère."""
        return content.count("\n", 0, position) + 1

    @staticmethod
    def _snapshot_relative_path(file_path_str: str) -> Optional[PurePath]:
        """
        Chemin relatif sous le dossier du snapshot, ou None si le chemin est
        inutilisable : générique (``...``, un motif de regex recopié), ou qui
        remonterait hors du snapshot (``..``). Un chemin absolu perd sa racine.
        """
        if "..." in file_path_str or "(.*?)" in file_path_str:
            return None
        path = PurePath(file_path_str)
        parts = [p for p in path.parts if p not in (path.anchor, "")]
        if not parts or ".." in parts:
            return None
        return PurePath(*parts)

    def _process_single_log(self, log_file: Path, log_identifier: str) -> int:
        """
        Analyse un seul fichier de log pour en extraire les snapshots prometteurs.
        """
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Impossible de lire le fichier {log_file}: {e}")
            return 0

        code_events = [
            (m.start(0), m.end(0), m.group(1), m.group(2))
            for m in CODE_EVENT_REGEX.finditer(content)
        ]

        snapshots_created = 0
        for m in PYTEST_SUMMARY_REGEX.finditer(content):
            passed_count, result_pos = int(m.group(1)), m.start(0)
            if not self.min_passed <= passed_count <= self.max_passed:
                continue
            line_num = self._get_line_number(content, result_pos)
            logger.info(
                f"Résultat prometteur trouvé dans {log_file.name} (ligne ~{line_num}): {passed_count} tests passés."
            )

            before = [e for e in code_events if e[1] <= result_pos]
            files, diffs = self._file_states(content, before, result_pos)
            if not files and not diffs:
                logger.warning(
                    f"Aucun bloc de code (<write_to_file>, <read_file> ou <apply_diff>) trouvé avant le test prometteur à la ligne ~{line_num}."
                )
                continue

            snapshots_created += 1
            snapshot_name = f"{log_identifier}_snapshot{snapshots_created}_L{line_num}_passed{passed_count}"
            context = (
                content[max(0, result_pos - CONTEXT_CHARS) : result_pos]
                + "\n\n"
                + m.group(0)
            )
            self._create_snapshot(snapshot_name, files, diffs, context)

        return snapshots_created

    def _file_states(self, content: str, events: list, limit: int):
        """
        Remonte les événements de code, du plus récent au plus ancien, et rend
        pour chaque fichier son dernier contenu complet connu et les diffs
        appliqués après lui (dans l'ordre chronologique).
        """
        files: Dict[PurePath, str] = {}
        diffs: Dict[PurePath, List[str]] = {}
        closed = set()
        for index in range(len(events) - 1, -1, -1):
            start, end, tool, xml = events[index]
            path_match = re.search(r"<path>(.*?)</path>", xml, re.DOTALL)
            if not path_match:
                continue
            rel = self._snapshot_relative_path(path_match.group(1).strip())
            if rel is None or rel in closed:
                continue

            if tool == "apply_diff":
                diff_match = re.search(r"<diff>(.*?)</diff>", xml, re.DOTALL)
                if diff_match:
                    diffs.setdefault(rel, []).insert(0, diff_match.group(1).strip())
                continue

            full_content = None
            if tool == "write_to_file":
                content_match = re.search(r"<content>(.*?)</content>", xml, re.DOTALL)
                if content_match:
                    full_content = content_match.group(1).strip()
            elif tool == "read_file":
                # Le résultat suit l'appel, avant l'événement de code suivant.
                window_end = events[index + 1][0] if index + 1 < len(events) else limit
                result_match = READ_RESULT_REGEX.search(content[end:window_end])
                if result_match:
                    full_content = "\n".join(
                        LINE_NUMBER_PREFIX.sub("", line)
                        for line in result_match.group(1).splitlines()
                    )
            if full_content is not None:
                files[rel] = full_content
                closed.add(rel)
        return files, diffs

    def _create_snapshot(
        self,
        snapshot_name: str,
        files: Dict[PurePath, str],
        diffs: Dict[PurePath, List[str]],
        context: str,
    ):
        """
        Écrit le snapshot : les fichiers reconstruits, un ``.diff`` par fichier
        qui a des diffs postérieurs à son dernier contenu complet, et le contexte.
        """
        snapshot_dir = self.output_base_dir / snapshot_name
        try:
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Création du snapshot : {snapshot_name}")

            for rel, file_content in files.items():
                target_path = snapshot_dir / rel
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(file_content)
                logger.info(f"  -> Fichier restauré : {target_path}")

            for rel, blocks in diffs.items():
                target_path = snapshot_dir / f"{rel}.diff"
                target_path.parent.mkdir(parents=True, exist_ok=True)
                base = (
                    "le contenu restauré"
                    if rel in files
                    else "aucun contenu complet trouvé"
                )
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(f"Original file path: {rel}\nBase: {base}\n")
                    for n, block in enumerate(blocks, 1):
                        f.write(f"\n--- apply_diff {n}/{len(blocks)} ---\n{block}\n")
                logger.info(
                    f"  -> Diff sauvegardé : {target_path} (application manuelle requise)"
                )

            context_path = snapshot_dir / "_CONVERSATION_CONTEXT.md"
            with open(context_path, "w", encoding="utf-8") as f:
                f.write(context)
            logger.info(f"  -> Contexte sauvegardé : {context_path}")

        except Exception as e:
            logger.error(
                f"Erreur lors de la création du snapshot {snapshot_name}: {e}",
                exc_info=True,
            )


def main():
    """Point d'entrée principal du script."""
    parser = argparse.ArgumentParser(
        description="Extrait des versions de code prometteuses depuis des logs de conversation.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "log_files",
        nargs="+",
        help="Liste des chemins vers les fichiers de log (.md) à analyser.",
    )
    parser.add_argument(
        "--output-dir",
        default=".temp/recovered",
        help="Répertoire de base pour sauvegarder les snapshots de code extraits.",
    )
    parser.add_argument(
        "--min-passed",
        type=int,
        default=5,
        help="Nombre minimal de tests réussis pour qu'un résultat soit prometteur.",
    )
    parser.add_argument(
        "--max-passed",
        type=int,
        default=7,
        help="Nombre maximal de tests réussis pour qu'un résultat soit prometteur.",
    )

    args = parser.parse_args()

    extractor = PromisingVersionExtractor(
        output_base_dir=args.output_dir,
        min_passed=args.min_passed,
        max_passed=args.max_passed,
    )
    extractor.extract_from_logs(args.log_files)


if __name__ == "__main__":
    main()
