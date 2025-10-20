"""
Script d'analyse de documentation obsolète - Version avec logging verbeux
Oracle Enhanced v2.1.0 - Reconstruction après crash
"""

import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime
import logging

# Configuration du logging avec timestamps
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class DocumentationAnalyzer:
    """Analyseur de documentation obsolète - Version robuste avec logging verbeux"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.doc_extensions = {".md", ".rst", ".txt", ".html"}
        self.results = {
            "analysis_timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "broken_links": [],
            "valid_links": [],
            "files_analyzed": 0,
            "total_links": 0,
        }

        # Répertoires à ignorer pour éviter l'enlisement
        self.ignore_dirs = {
            "libs/portable_jdk",
            ".git",
            "__pycache__",
            ".pytest_cache",
            "venv",
            "venv_test",
            ".vscode",
            ".vs",
            "migration_output",
            "_archives",
            "_temp",
            "argumentation_analysis_project.egg-info",
            "argumentation_analysis.egg-info",
        }

    def find_documentation_files(self, quick_scan=False) -> List[Path]:
        """Trouve les fichiers de documentation de manière optimisée"""
        logger.info("🔍 Début recherche fichiers documentation...")
        start_time = datetime.now()
        doc_files = []

        if quick_scan:
            logger.info("⚡ Mode QUICK SCAN activé")
            # Scan ultra-rapide - seulement les fichiers .md prioritaires
            priority_patterns = [
                "README.md",
                "docs/**/*.md",
                "CHANGELOG*.md",
                "GUIDE*.md",
            ]

            for pattern in priority_patterns:
                try:
                    logger.info(f"   Recherche pattern: {pattern}")
                    files = list(self.project_root.glob(pattern))
                    logger.info(f"   ✓ Trouvé {len(files)} fichiers pour {pattern}")
                    doc_files.extend(files)
                except Exception as e:
                    logger.warning(f"   ⚠ Erreur pattern {pattern}: {e}")
                    continue
        else:
            logger.info("🔬 Mode FULL ANALYSIS activé")
            # Scan sécurisé avec exclusions
            for ext in self.doc_extensions:
                logger.info(f"   Recherche fichiers {ext}...")
                ext_start = datetime.now()
                try:
                    ext_files = []
                    for file_path in self.project_root.rglob(f"*{ext}"):
                        # Vérifier si le fichier est dans un répertoire ignoré
                        if any(
                            ignore_dir in str(file_path)
                            for ignore_dir in self.ignore_dirs
                        ):
                            continue
                        ext_files.append(file_path)
                    doc_files.extend(ext_files)
                    ext_duration = (datetime.now() - ext_start).total_seconds()
                    logger.info(
                        f"   ✓ {len(ext_files)} fichiers {ext} trouvés en {ext_duration:.1f}s"
                    )
                except Exception as e:
                    logger.warning(f"   ⚠ Erreur recherche {ext}: {e}")
                    continue

        doc_files = list(set(doc_files))  # Éliminer les doublons
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"✅ Recherche terminée: {len(doc_files)} fichiers en {duration:.1f}s"
        )
        return doc_files

    def extract_links_from_file(self, file_path: Path) -> List[Tuple[str, int]]:
        """Extrait les liens d'un fichier de manière robuste"""
        links = []

        try:
            # Essayer plusieurs encodages
            content = None
            for encoding in ["utf-8", "latin-1", "cp1252"]:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue

            if content is None:
                return links

            # Pattern Markdown: [text](link)
            markdown_pattern = r"\[([^\]]+)\]\(([^)]+)\)"

            # Pattern HTML: <a href="link">
            html_pattern = r'<a\s+[^>]*href=["\']([^"\']+)["\']'

            lines = content.split("\n")
            for line_num, line in enumerate(lines, 1):
                # Extraire liens Markdown
                for match in re.finditer(markdown_pattern, line):
                    link = match.group(2)
                    # Ignorer les liens externes et ancres
                    if not link.startswith(("http://", "https://", "#", "mailto:")):
                        links.append((link, line_num))

                # Extraire liens HTML
                for match in re.finditer(html_pattern, line):
                    link = match.group(1)
                    if not link.startswith(("http://", "https://", "#", "mailto:")):
                        links.append((link, line_num))

        except Exception:
            pass

        return links

    def check_link_exists(self, link: str, source_file: Path) -> bool:
        """Vérifie qu'un lien pointe vers un fichier existant"""
        try:
            # Nettoyer le lien
            link = link.split("#")[0].strip()

            # Construire le chemin absolu
            if link.startswith("/"):
                target_path = self.project_root / link.lstrip("/")
            else:
                target_path = source_file.parent / link

            # Normaliser et résoudre le chemin
            target_path = target_path.resolve()

            return target_path.exists()
        except Exception:
            return False

    def analyze_documentation(self, quick_scan=False) -> Dict:
        """Analyse la documentation et détecte les liens brisés"""
        logger.info("=" * 70)
        logger.info("🚀 DÉMARRAGE ANALYSE DOCUMENTATION")
        logger.info("=" * 70)

        analysis_start = datetime.now()

        doc_files = self.find_documentation_files(quick_scan)
        logger.info(f"📊 {len(doc_files)} fichiers à analyser")

        self.results["files_analyzed"] = len(doc_files)

        logger.info("=" * 70)
        logger.info("🔗 EXTRACTION ET VÉRIFICATION LIENS")
        logger.info("=" * 70)

        for i, doc_file in enumerate(doc_files):
            try:
                # Log tous les 10 fichiers pour plus de feedback
                if i % 10 == 0:
                    progress_pct = i / len(doc_files) * 100
                    elapsed = (datetime.now() - analysis_start).total_seconds()
                    rate = i / elapsed if elapsed > 0 else 0
                    eta = (len(doc_files) - i) / rate if rate > 0 else 0

                    logger.info(
                        f"📈 Progression: {i+1}/{len(doc_files)} ({progress_pct:.1f}%) - "
                        f"Vitesse: {rate:.1f} fichiers/s - "
                        f"ETA: {eta/60:.1f} min"
                    )
                    logger.info(
                        f"   Liens trouvés: {self.results['total_links']} "
                        f"(Brisés: {len(self.results['broken_links'])}, "
                        f"Valides: {len(self.results['valid_links'])})"
                    )

                links = self.extract_links_from_file(doc_file)

                if links and i % 50 == 0:  # Log échantillon tous les 50 fichiers
                    logger.info(f"   📄 {doc_file.name}: {len(links)} liens détectés")

                for link, line_num in links:
                    self.results["total_links"] += 1

                    link_info = {
                        "link": link,
                        "source_file": str(doc_file.relative_to(self.project_root)),
                        "line_number": line_num,
                    }

                    if self.check_link_exists(link, doc_file):
                        self.results["valid_links"].append(link_info)
                    else:
                        self.results["broken_links"].append(link_info)

            except Exception as e:
                logger.warning(f"⚠ Erreur analyse {doc_file.name}: {e}")
                continue

        # Calculer les statistiques
        total_links = self.results["total_links"]
        broken_count = len(self.results["broken_links"])
        valid_count = len(self.results["valid_links"])

        self.results["summary"] = {
            "total_links": total_links,
            "broken_links": broken_count,
            "valid_links": valid_count,
            "broken_percentage": (broken_count / total_links * 100)
            if total_links > 0
            else 0,
        }

        duration = (datetime.now() - analysis_start).total_seconds()

        logger.info("=" * 70)
        logger.info("✅ ANALYSE TERMINÉE")
        logger.info("=" * 70)
        logger.info(f"⏱  Durée totale: {duration/60:.2f} minutes")
        logger.info(f"📊 Fichiers analysés: {self.results['files_analyzed']}")
        logger.info(f"🔗 Liens totaux: {total_links}")
        logger.info(
            f"❌ Liens brisés: {broken_count} ({(broken_count/total_links*100):.1f}%)"
        )
        logger.info(
            f"✓  Liens valides: {valid_count} ({(valid_count/total_links*100):.1f}%)"
        )
        logger.info("=" * 70)

        return self.results

    def generate_report(self, output_file: str = None) -> str:
        """Génère un rapport de documentation"""
        logger.info("📝 Génération du rapport...")

        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"logs/documentation_analysis_{timestamp}.md"

        # Créer le dossier si nécessaire
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        # Sauvegarder en JSON
        json_file = (
            output_file.replace(".md", ".json")
            if output_file.endswith(".md")
            else output_file
        )
        try:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ JSON sauvegardé: {json_file}")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde JSON: {e}")

        summary = self.results.get("summary", {})

        report = f"""# Rapport d'Analyse de Documentation
## Oracle Enhanced v2.1.0 - Reconstruction

**Date d'analyse :** {self.results['analysis_timestamp']}  
**Racine du projet :** `{self.results['project_root']}`

## Résumé

- **Fichiers analysés :** {self.results['files_analyzed']}
- **Liens totaux :** {summary.get('total_links', 0)}
- **Liens brisés :** {summary.get('broken_links', 0)} ({summary.get('broken_percentage', 0):.1f}%)
- **Liens valides :** {summary.get('valid_links', 0)}

## Liens Brisés (Top 20)

"""

        # Afficher les 20 premiers liens brisés
        broken_links = self.results["broken_links"][:20]

        if broken_links:
            for i, broken_link in enumerate(broken_links, 1):
                report += f"""### {i}. {broken_link['link']}
- **Fichier :** `{broken_link['source_file']}` (ligne {broken_link['line_number']})

"""
        else:
            report += "Aucun lien brisé détecté !\n\n"

        if len(self.results["broken_links"]) > 20:
            report += f"\n*... et {len(self.results['broken_links']) - 20} autres liens brisés*\n\n"

        report += """## Actions Recommandées

1. **Examiner les liens brisés** listés ci-dessus
2. **Corriger ou supprimer** les références obsolètes
3. **Re-exécuter l'analyse** après corrections

---
*Rapport généré par Oracle Enhanced v2.1.0 Documentation Analyzer (Version reconstruite)*
"""

        try:
            markdown_file = (
                output_file if output_file.endswith(".md") else output_file + ".md"
            )
            with open(markdown_file, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info(f"✅ Rapport Markdown sauvegardé: {markdown_file}")
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde rapport: {e}")

        return json_file


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Analyse de documentation obsolète (Version reconstruite)"
    )
    parser.add_argument(
        "--quick-scan", action="store_true", help="Analyse rapide (.md prioritaires)"
    )
    parser.add_argument("--full-analysis", action="store_true", help="Analyse complète")
    parser.add_argument("--output", help="Fichier de sortie")

    args = parser.parse_args()

    analyzer = DocumentationAnalyzer()

    # Mode d'analyse
    quick_mode = args.quick_scan or not args.full_analysis

    try:
        results = analyzer.analyze_documentation(quick_scan=quick_mode)
        analyzer.generate_report(args.output)

        return 0 if results["summary"].get("broken_links", 0) == 0 else 1

    except Exception as e:
        logger.error(f"❌ Erreur analyse: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    exit(main())
