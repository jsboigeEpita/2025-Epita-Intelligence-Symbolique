"""
Script de correction automatique des liens de documentation
Oracle Enhanced v2.1.0 - Auto-correction Documentation (Version Optimisée)
"""

import json
import re
import shutil
from pathlib import Path
from typing import Dict, List


class DocumentationAutoFixer:
    """Correcteur automatique de liens de documentation (optimisé)"""

    def __init__(self, analysis_data_file: str):
        with open(analysis_data_file, "r", encoding="utf-8") as f:
            self.analysis_data = json.load(f)

        self.fixes_applied = []
        self.manual_review_needed = []

        # Fichiers prioritaires à traiter en premier
        self.priority_patterns = [
            "README.md",
            "docs/",
            "GETTING_STARTED.md",
            "GUIDE_",
            "CHANGELOG",
            "INSTALL",
            "CONTRIBUTING",
        ]

    def filter_priority_broken_links(self) -> List[Dict]:
        """Filtre les liens brisés dans les fichiers prioritaires"""
        priority_links = []

        for broken_link in self.analysis_data["broken_links"]:
            source_file = broken_link.get("source_file", "")

            # Vérifier si c'est un fichier prioritaire
            if any(pattern in source_file for pattern in self.priority_patterns):
                priority_links.append(broken_link)

        # Limiter à 100 liens prioritaires pour traitement rapide
        return priority_links[:100]

    def analyze_simple_corrections(self, broken_links: List[Dict]) -> Dict:
        """Analyse les corrections simples possibles"""
        simple_corrections = {}

        for broken_link in broken_links:
            link = broken_link["link"]
            source_file = broken_link["source_file"]

            # Correction des liens relatifs cassés courants
            corrected_link = self.suggest_simple_correction(link, source_file)
            if corrected_link and corrected_link != link:
                simple_corrections[link] = {
                    "original": link,
                    "corrected": corrected_link,
                    "source_file": source_file,
                    "line_number": broken_link.get("line_number", 0),
                    "correction_type": "simple_path_fix",
                }

        return simple_corrections

    def suggest_simple_correction(self, link: str, source_file: str) -> str:
        """Suggère une correction simple pour un lien"""

        # Corrections courantes de chemins
        corrections = {
            # Liens vers docs
            "docs/README.md": "docs/README.md",
            "../docs/": "docs/",
            "./docs/": "docs/",
            # Liens vers examples
            "../examples/": "examples/",
            "./examples/": "examples/",
            # Liens vers scripts
            "../scripts/": "scripts/",
            "./scripts/": "scripts/",
            # Fichiers racine courants
            "GETTING_STARTED.md": "GETTING_STARTED.md",
            "README.md": "README.md",
            "CHANGELOG.md": "CHANGELOG_ORACLE_ENHANCED_V2_1_0.md",
        }

        # Vérifier les correspondances directes
        if link in corrections:
            if Path(corrections[link]).exists():
                return corrections[link]

        # Nettoyer les liens avec ../
        if link.startswith("../"):
            clean_link = link.replace("../", "")
            if Path(clean_link).exists():
                return clean_link

        # Nettoyer les liens avec ./
        if link.startswith("./"):
            clean_link = link.replace("./", "")
            if Path(clean_link).exists():
                return clean_link

        return None

    def apply_simple_corrections(self, corrections: Dict) -> Dict:
        """Applique les corrections simples identifiées"""
        results = {"files_modified": [], "corrections_applied": 0, "errors": []}

        # Grouper les corrections par fichier
        files_to_update = {}
        for link, correction_data in corrections.items():
            source_file = correction_data["source_file"]
            if source_file not in files_to_update:
                files_to_update[source_file] = []
            files_to_update[source_file].append(correction_data)

        # Appliquer les corrections fichier par fichier
        for file_path, file_corrections in files_to_update.items():
            try:
                success = self.update_file_links_batch(file_path, file_corrections)
                if success:
                    results["files_modified"].append(file_path)
                    results["corrections_applied"] += len(file_corrections)
                    print(
                        f"✅ Mis à jour: {file_path} ({len(file_corrections)} corrections)"
                    )

            except Exception as e:
                results["errors"].append({"file": file_path, "error": str(e)})
                print(f"❌ Erreur dans {file_path}: {e}")

        return results

    def update_file_links_batch(self, file_path: str, corrections: List[Dict]) -> bool:
        """Met à jour plusieurs liens dans un fichier en une fois"""
        file_full_path = Path(file_path)

        if not file_full_path.exists():
            print(f"⚠️ Fichier non trouvé: {file_path}")
            return False

        # Backup du fichier original
        backup_path = file_full_path.with_suffix(file_full_path.suffix + ".backup")
        shutil.copy2(file_full_path, backup_path)

        try:
            with open(file_full_path, "r", encoding="utf-8") as f:
                content = f.read()

            updated_content = content

            # Appliquer toutes les corrections
            for correction in corrections:
                old_link = correction["original"]
                new_link = correction["corrected"]

                # Remplacer les liens (Markdown et HTML)
                patterns = [
                    (rf"\[([^\]]+)\]\({re.escape(old_link)}\)", rf"[\1]({new_link})"),
                    (rf'href="{re.escape(old_link)}"', f'href="{new_link}"'),
                    (rf"`{re.escape(old_link)}`", f"`{new_link}`"),
                    (rf"{re.escape(old_link)}", new_link),  # Remplacement direct
                ]

                for pattern, replacement in patterns:
                    updated_content = re.sub(pattern, replacement, updated_content)

            # Sauvegarder le fichier mis à jour
            with open(file_full_path, "w", encoding="utf-8") as f:
                f.write(updated_content)

            # Supprimer le backup si succès
            backup_path.unlink()
            return True

        except Exception as e:
            # Restaurer le backup en cas d'erreur
            if backup_path.exists():
                shutil.copy2(backup_path, file_full_path)
                backup_path.unlink()
            raise e

    def generate_manual_review_report(self, remaining_links: List[Dict]) -> str:
        """Génère un rapport pour révision manuelle"""
        report_file = "logs/manual_review_needed.md"

        report = f"""# 📋 Corrections de Documentation - Révision Manuelle Requise
## Oracle Enhanced v2.1.0

Les liens suivants nécessitent une révision manuelle car ils ne peuvent pas être corrigés automatiquement.

## 🏆 Documents Prioritaires ({len(remaining_links)} liens)

"""

        for i, link_data in enumerate(
            remaining_links[:50], 1
        ):  # Limiter à 50 pour lisibilité
            report += f"""### {i}. ❌ `{link_data['link']}`
- **Fichier :** `{link_data['source_file']}` (ligne {link_data.get('line_number', 'N/A')})
- **Problème :** Lien brisé nécessitant révision manuelle
- **Chemin cible :** `{link_data.get('target_path', 'N/A')}`

"""

        if len(remaining_links) > 50:
            report += (
                f"\n... et {len(remaining_links) - 50} autres liens à réviser.\n\n"
            )

        report += """## 💡 Recommandations

1. **Vérifier l'existence** des fichiers cibles
2. **Mettre à jour les chemins** si les fichiers ont été déplacés
3. **Supprimer les liens** vers les fichiers supprimés
4. **Corriger les fautes de frappe** dans les noms de fichiers

---
*Rapport généré par Oracle Enhanced v2.1.0 Documentation Auto-Fixer*
"""

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        return report_file


def main():
    """Exécute les corrections automatiques optimisées"""
    print("🚀 Démarrage Auto-Fixer Documentation Oracle Enhanced v2.1.0")

    fixer = DocumentationAutoFixer("logs/documentation_analysis_data.json")

    print("📋 Filtrage des liens prioritaires...")
    priority_links = fixer.filter_priority_broken_links()
    print(f"   🎯 {len(priority_links)} liens prioritaires identifiés")

    print("🔍 Analyse des corrections simples...")
    simple_corrections = fixer.analyze_simple_corrections(priority_links)
    print(f"   🤖 {len(simple_corrections)} corrections automatiques possibles")

    if simple_corrections:
        print("⚡ Application des corrections automatiques...")
        results = fixer.apply_simple_corrections(simple_corrections)
        print(f"   ✅ {results['corrections_applied']} corrections appliquées")
        print(f"   📁 {len(results['files_modified'])} fichiers modifiés")
        if results["errors"]:
            print(f"   ❌ {len(results['errors'])} erreurs")

    # Générer rapport de révision manuelle pour les liens restants
    remaining_links = [
        link for link in priority_links if link["link"] not in simple_corrections
    ]

    manual_report = fixer.generate_manual_review_report(remaining_links)
    print(f"📄 Rapport révision manuelle: {manual_report}")

    # Résumé final
    print(f"\n🎯 RÉSUMÉ:")
    print(f"   📊 Liens prioritaires traités: {len(priority_links)}")
    print(f"   🤖 Corrections automatiques: {len(simple_corrections)}")
    print(f"   👁️ Révision manuelle requise: {len(remaining_links)}")

    return {
        "priority_links": len(priority_links),
        "automatic_corrections": len(simple_corrections),
        "manual_review_needed": len(remaining_links),
    }


if __name__ == "__main__":
    main()
