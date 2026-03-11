#!/usr/bin/env python3
"""
Script de vérification des erreurs F821 restantes après corrections Batch 1
Phase 1F : Analyse rapide des catégories restantes
"""

import json
from pathlib import Path

def check_f821_remaining():
    """Analyse les erreurs F821 restantes après corrections Batch 1"""
    
    report_path = Path("reports/f821_analysis.json")
    
    with open(report_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=" * 60)
    print("📊 Analyse F821 Restantes - Phase 1F")
    print("=" * 60)
    print()
    
    # Statistiques par catégorie
    print("📦 Répartition par catégorie :")
    print("-" * 60)
    
    by_category = data['by_category']
    
    for category, info in by_category.items():
        count = info['count']
        percentage = info['percentage']
        print(f"  {category:20} : {count:3} erreurs ({percentage:5.2f}%)")
    
    print()
    print("=" * 60)
    print("🎯 Priorités de correction :")
    print("-" * 60)
    
    # Catégorie 1 : missing_imports (déjà traités partiellement)
    missing_imports = by_category['missing_imports']
    print(f"\n1. IMPORTS MANQUANTS ({missing_imports['count']} erreurs)")
    print("   - Batch 1 traité : Optional, MagicMock (6 erreurs)")
    print(f"   - Restants : ~{missing_imports['count'] - 6} erreurs")
    print("   - Action : Analyser les imports restants")
    
    # Extraire les noms undefined de missing_imports
    import_names = {}
    for error in missing_imports['errors']:
        name = error['undefined_name']
        import_names[name] = import_names.get(name, 0) + 1
    
    print("\n   Top imports manquants :")
    sorted_imports = sorted(import_names.items(), key=lambda x: x[1], reverse=True)
    for name, count in sorted_imports[:10]:
        print(f"     - {name:25} : {count:2} occurrences")
    
    # Catégorie 2 : dead_code
    dead_code = by_category.get('dead_code', {'count': 0, 'errors': []})
    print(f"\n2. DEAD CODE ({dead_code['count']} erreurs)")
    print("   - Action : Nettoyer ou commenter le code mort")
    
    # Catégorie 3 : scope_issue
    scope_issue = by_category.get('scope_issue', {'count': 0, 'errors': []})
    print(f"\n3. SCOPE ISSUES ({scope_issue['count']} erreurs)")
    print("   - Action : Analyse manuelle de la portée des variables")
    
    # Catégorie 4 : unknown
    unknown = by_category['unknown']
    print(f"\n4. UNKNOWN ({unknown['count']} erreurs)")
    print("   - Action : Analyse manuelle approfondie")
    
    # Extraire les noms undefined de unknown
    unknown_names = {}
    for error in unknown['errors']:
        name = error['undefined_name']
        unknown_names[name] = unknown_names.get(name, 0) + 1
    
    print("\n   Top noms undefined (unknown) :")
    sorted_unknown = sorted(unknown_names.items(), key=lambda x: x[1], reverse=True)
    for name, count in sorted_unknown[:10]:
        print(f"     - {name:25} : {count:2} occurrences")
    
    print()
    print("=" * 60)
    print("💡 Recommandations :")
    print("-" * 60)
    print("1. Continuer avec missing_imports restants (automatisable)")
    print("2. Nettoyer dead_code (automatisable avec analyse)")
    print("3. Analyser unknown au cas par cas (manuel)")
    print("4. Résoudre scope_issue (manuel)")
    print("=" * 60)
    
    # Statistiques finales
    total_errors = data['summary']['total_f821_errors']
    batch1_fixed = 2  # Optional dans run_complete_test_and_analysis.py
    remaining = total_errors - batch1_fixed
    
    print()
    print("📈 Progression Phase 1F :")
    print("-" * 60)
    print(f"  Baseline initial     : {total_errors} erreurs F821")
    print(f"  Corrigées Batch 1    : {batch1_fixed} erreurs")
    print(f"  Restantes            : {remaining} erreurs")
    print(f"  Réduction            : {(batch1_fixed/total_errors)*100:.2f}%")
    print("=" * 60)

if __name__ == "__main__":
    check_f821_remaining()