# -*- coding: utf-8 -*-
"""
Script d'analyse spécialisé pour les erreurs F821 (noms non définis) - Phase 1A
Mission D-CI-06 Phase 6

Ce script analyse en profondeur les erreurs F821 pour faciliter leur correction
par catégorisation et priorisation.

Fonctionnalités:
- Extraction de toutes les erreurs F821
- Catégorisation automatique par type de problème
- Analyse par répertoire et fichier
- Identification des patterns récurrents
- Priorisation des corrections
- Exclusion du répertoire libs/ (bibliothèques externes)

Usage:
    python scripts/analyze_f821_errors.py

Output:
    reports/f821_analysis.json - Analyse JSON structurée
"""
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

# Constantes
REPORT_FILE = 'flake8_report.txt'
OUTPUT_JSON = 'reports/f821_analysis.json'
LIBS_DIR = 'libs/'  # Répertoire à exclure

# Patterns pour catégorisation
IMPORT_KEYWORDS = ['import', 'from', 'module', 'package']
DYNAMIC_PATTERNS = [
    r'__\w+__',  # Attributs magic __name__, __file__, etc.
    r'getattr',
    r'setattr',
    r'hasattr',
    r'exec',
    r'eval',
]


def similarity_ratio(a, b):
    """Calcule le ratio de similarité entre deux chaînes."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def extract_undefined_name(error_message):
    """
    Extrait le nom non défini du message d'erreur F821.
    
    Message type: "undefined name 'Symbol'"
    """
    match = re.search(r"undefined name ['\"]([^'\"]+)['\"]", error_message)
    return match.group(1) if match else None


def categorize_f821_error(file_path, line_num, error_msg, line_content=None):
    """
    Catégorise une erreur F821 selon son type probable.
    
    Retourne un dict avec:
        - category: str (missing_imports, typo, dead_code, scope_issue, dynamic, unknown)
        - confidence: str (high, medium, low)
        - reason: str (justification de la catégorie)
    """
    undefined_name = extract_undefined_name(error_msg)
    if not undefined_name:
        return {
            "category": "unknown",
            "confidence": "low",
            "reason": "Impossible d'extraire le nom non défini"
        }
    
    # Heuristiques de catégorisation
    
    # 1. Imports manquants (haute confiance)
    if any(keyword in error_msg.lower() for keyword in IMPORT_KEYWORDS):
        return {
            "category": "missing_imports",
            "confidence": "medium",
            "reason": f"Message mentionne import/module"
        }
    
    # Nom commence par majuscule = probablement une classe à importer
    if undefined_name[0].isupper() and len(undefined_name) > 2:
        return {
            "category": "missing_imports",
            "confidence": "high",
            "reason": f"'{undefined_name}' commence par majuscule (classe probable)"
        }
    
    # 2. Attributs dynamiques (moyenne confiance)
    for pattern in DYNAMIC_PATTERNS:
        if re.search(pattern, undefined_name) or (line_content and re.search(pattern, line_content)):
            return {
                "category": "dynamic",
                "confidence": "medium",
                "reason": f"Pattern dynamique détecté: {pattern}"
            }
    
    # 3. Variables privées/protégées (scope issue probable)
    if undefined_name.startswith('_'):
        return {
            "category": "scope_issue",
            "confidence": "medium",
            "reason": f"Variable privée/protégée '{undefined_name}'"
        }
    
    # 4. Dead code (fichiers tests, exemples)
    if 'test' in file_path.lower() or 'example' in file_path.lower():
        return {
            "category": "dead_code",
            "confidence": "low",
            "reason": "Dans fichier test/exemple (peut être obsolète)"
        }
    
    # 5. Typos possibles (noms courts avec similarité)
    if len(undefined_name) <= 6:
        return {
            "category": "typo",
            "confidence": "low",
            "reason": f"Nom court '{undefined_name}' (typo possible)"
        }
    
    # Défaut: incertain
    return {
        "category": "unknown",
        "confidence": "low",
        "reason": "Nécessite analyse manuelle"
    }


def analyze_f821_errors(report_path):
    """
    Analyse toutes les erreurs F821 du rapport flake8.
    
    Returns:
        dict: Analyse structurée avec catégories, statistiques, priorités
    """
    if not os.path.exists(report_path):
        print(f"❌ Erreur: Le fichier '{report_path}' n'existe pas.")
        return None
    
    print(f"📊 Analyse des erreurs F821 depuis {report_path}...")
    
    f821_errors = []
    f821_by_category = defaultdict(list)
    f821_by_directory = defaultdict(int)
    f821_by_file = defaultdict(int)
    undefined_names = Counter()
    
    excluded_count = 0
    total_f821 = 0
    
    with open(report_path, 'r', encoding='utf-8') as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            
            # Parser format flake8: file:line:col: code message
            parts = line.split(':', 3)
            if len(parts) < 4:
                continue
            
            file_path = parts[0].strip()
            line_num = parts[1].strip()
            col_num = parts[2].strip()
            error_info = parts[3].strip()
            
            # Filtrer uniquement F821
            if not error_info.startswith('F821 '):
                continue
            
            # Exclure libs/
            if file_path.startswith(LIBS_DIR):
                excluded_count += 1
                continue
            
            total_f821 += 1
            error_msg = error_info[5:]  # Enlever "F821 "
            
            # Extraire nom non défini
            undefined_name = extract_undefined_name(error_msg)
            if undefined_name:
                undefined_names[undefined_name] += 1
            
            # Catégoriser
            categorization = categorize_f821_error(file_path, line_num, error_msg)
            
            # Construire entrée d'erreur
            error_entry = {
                "file": file_path,
                "line": int(line_num),
                "column": int(col_num),
                "message": error_msg,
                "undefined_name": undefined_name,
                "category": categorization["category"],
                "confidence": categorization["confidence"],
                "reason": categorization["reason"]
            }
            
            f821_errors.append(error_entry)
            f821_by_category[categorization["category"]].append(error_entry)
            
            # Stats par répertoire
            dir_name = file_path.split('/')[0] if '/' in file_path else file_path.split('\\')[0]
            f821_by_directory[dir_name] += 1
            f821_by_file[file_path] += 1
    
    print(f"✅ Analyse terminée: {total_f821} erreurs F821 trouvées (hors libs/)")
    print(f"   📂 Exclues (libs/): {excluded_count}")
    
    # Priorisation des corrections
    priority_order = []
    
    # Priorité 1: Imports manquants (facile, haute valeur)
    if "missing_imports" in f821_by_category:
        priority_order.append({
            "priority": 1,
            "category": "missing_imports",
            "count": len(f821_by_category["missing_imports"]),
            "difficulty": "facile",
            "value": "haute",
            "strategy": "Identifier module source et ajouter import"
        })
    
    # Priorité 2: Typos (facile, moyenne valeur)
    if "typo" in f821_by_category:
        priority_order.append({
            "priority": 2,
            "category": "typo",
            "count": len(f821_by_category["typo"]),
            "difficulty": "facile",
            "value": "moyenne",
            "strategy": "Corriger orthographe avec similarité"
        })
    
    # Priorité 3: Dead code (moyen, faible valeur)
    if "dead_code" in f821_by_category:
        priority_order.append({
            "priority": 3,
            "category": "dead_code",
            "count": len(f821_by_category["dead_code"]),
            "difficulty": "moyen",
            "value": "faible",
            "strategy": "Commenter ou marquer TODO"
        })
    
    # Priorité 4: Scope issues (difficile, moyenne valeur)
    if "scope_issue" in f821_by_category:
        priority_order.append({
            "priority": 4,
            "category": "scope_issue",
            "count": len(f821_by_category["scope_issue"]),
            "difficulty": "difficile",
            "value": "moyenne",
            "strategy": "Révision manuelle du scope"
        })
    
    # Priorité 5: Dynamique (difficile, faible valeur - noqa)
    if "dynamic" in f821_by_category:
        priority_order.append({
            "priority": 5,
            "category": "dynamic",
            "count": len(f821_by_category["dynamic"]),
            "difficulty": "difficile",
            "value": "faible",
            "strategy": "Ajouter # noqa: F821 avec justification"
        })
    
    # Priorité 6: Inconnus (à analyser manuellement)
    if "unknown" in f821_by_category:
        priority_order.append({
            "priority": 6,
            "category": "unknown",
            "count": len(f821_by_category["unknown"]),
            "difficulty": "variable",
            "value": "variable",
            "strategy": "Analyse manuelle cas par cas"
        })
    
    # Top 10 noms non définis les plus fréquents
    top_undefined = undefined_names.most_common(10)
    
    # Statistiques par répertoire (top 10)
    top_directories = sorted(f821_by_directory.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Fichiers hotspots (>10 erreurs F821)
    hotspots = sorted(
        [(file, count) for file, count in f821_by_file.items() if count > 10],
        key=lambda x: x[1],
        reverse=True
    )
    
    return {
        "analysis_date": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total_f821_errors": total_f821,
            "excluded_libs": excluded_count,
            "categories_count": len(f821_by_category),
            "files_affected": len(f821_by_file),
            "directories_affected": len(f821_by_directory)
        },
        "by_category": {
            category: {
                "count": len(errors),
                "percentage": round((len(errors) / total_f821) * 100, 2) if total_f821 > 0 else 0,
                "errors": errors[:50]  # Limiter à 50 exemples par catégorie
            }
            for category, errors in f821_by_category.items()
        },
        "by_directory": dict(top_directories),
        "priority_order": priority_order,
        "top_undefined_names": [
            {"name": name, "count": count} for name, count in top_undefined
        ],
        "hotspots": [
            {"file": file, "f821_count": count} for file, count in hotspots
        ],
        "all_errors": f821_errors  # Pour référence complète
    }


def save_analysis_to_json(analysis_data, output_path):
    """Sauvegarde l'analyse dans un fichier JSON."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Analyse sauvegardée: {output_path}")


def print_summary(analysis_data):
    """Affiche un résumé console de l'analyse."""
    summary = analysis_data["summary"]
    
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ ANALYSE F821 - Phase 1A")
    print("=" * 60)
    print(f"Total erreurs F821 (hors libs/): {summary['total_f821_errors']}")
    print(f"Erreurs exclues (libs/):         {summary['excluded_libs']}")
    print(f"Fichiers affectés:               {summary['files_affected']}")
    print(f"Répertoires affectés:            {summary['directories_affected']}")
    
    print("\n📂 Distribution par Catégorie:")
    print("-" * 60)
    for category_info in analysis_data["priority_order"]:
        print(f"  P{category_info['priority']} - {category_info['category'].upper()}: "
              f"{category_info['count']} erreurs "
              f"({category_info['difficulty']}, valeur {category_info['value']})")
        print(f"      → Stratégie: {category_info['strategy']}")
    
    print("\n🔝 Top 5 Noms Non Définis:")
    print("-" * 60)
    for item in analysis_data["top_undefined_names"][:5]:
        print(f"  - '{item['name']}': {item['count']} occurrences")
    
    print("\n🔥 Hotspots (fichiers >10 erreurs F821):")
    print("-" * 60)
    for hotspot in analysis_data["hotspots"][:5]:
        print(f"  - {hotspot['file']}: {hotspot['f821_count']} erreurs")
    
    print("\n" + "=" * 60)
    print(f"✅ Fichier JSON complet: {OUTPUT_JSON}")
    print("=" * 60 + "\n")


def main():
    """Point d'entrée principal."""
    print("🚀 Démarrage analyse F821 - Mission D-CI-06 Phase 1A\n")
    
    analysis_data = analyze_f821_errors(REPORT_FILE)
    
    if analysis_data:
        save_analysis_to_json(analysis_data, OUTPUT_JSON)
        print_summary(analysis_data)
        
        print("📋 Prochaines étapes:")
        print("  1. Examiner reports/f821_analysis.json pour détails")
        print("  2. Commencer corrections par ordre de priorité")
        print("  3. Tests après chaque batch (pytest + flake8)")
        print("  4. Commits atomiques tous les 50-100 corrections\n")
        
        return 0
    else:
        print("❌ Échec de l'analyse")
        return 1


if __name__ == '__main__':
    exit(main())