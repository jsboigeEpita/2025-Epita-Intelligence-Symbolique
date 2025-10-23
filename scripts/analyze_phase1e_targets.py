#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script d'Analyse Phase 1E - Quick Wins Auto-Fixables
====================================================

Mission D-CI-06 Phase 1E
Analyse ciblée des erreurs auto-fixables:
- W293: 56 erreurs (whitespace lignes vides - RÉAPPARU)
- E128: 18 erreurs (continuation line under-indented)
- E999: 9 erreurs (SyntaxError CRITIQUE)
- E117: 8 erreurs (over-indented)
- E265: 7 erreurs (block comment)

Auteur: Roo Code Mode
Date: 2025-10-23
"""

import re
from pathlib import Path
from collections import defaultdict
import json


def parse_flake8_line(line):
    """
    Parse une ligne flake8 format: filepath:line:col: CODE message
    
    Returns:
        dict ou None si parsing échoue
    """
    # Format attendu: path/file.py:123:45: E128 continuation line under-indented
    match = re.match(r'^(.+?):(\d+):(\d+):\s+([A-Z]\d{3,4})\s+(.+)$', line)
    if match:
        return {
            'filepath': match.group(1),
            'line': int(match.group(2)),
            'col': int(match.group(3)),
            'code': match.group(4),
            'message': match.group(5).strip()
        }
    return None


def analyze_phase1e_targets():
    """
    Analyse les erreurs ciblées Phase 1E depuis flake8_report.txt
    """
    report_path = Path('flake8_report.txt')
    
    if not report_path.exists():
        print(f"❌ Fichier {report_path} introuvable!")
        return None
    
    # Codes ciblés Phase 1E
    target_codes = {
        'W293': 'blank line contains whitespace',
        'E128': 'continuation line under-indented for visual indent',
        'E999': 'SyntaxError',
        'E117': 'over-indented',
        'E265': 'block comment should start with \'# \''
    }
    
    # Structures de données
    errors_by_code = defaultdict(list)
    errors_by_file = defaultdict(lambda: defaultdict(list))
    total_errors = 0
    target_errors = 0
    
    # Lecture du rapport
    print(f"📖 Lecture de {report_path}...")
    with open(report_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            parsed = parse_flake8_line(line)
            if not parsed:
                continue
            
            total_errors += 1
            code = parsed['code']
            
            # Si code ciblé Phase 1E
            if code in target_codes:
                target_errors += 1
                errors_by_code[code].append(parsed)
                errors_by_file[parsed['filepath']][code].append(parsed)
    
    # Affichage résultats
    print(f"\n{'='*70}")
    print(f"📊 ANALYSE PHASE 1E - QUICK WINS AUTO-FIXABLES")
    print(f"{'='*70}\n")
    
    print(f"Total erreurs baseline: {total_errors}")
    print(f"Erreurs ciblées Phase 1E: {target_errors} ({target_errors/total_errors*100:.1f}%)\n")
    
    # Détail par code
    print(f"{'─'*70}")
    print(f"{'CODE':<8} {'COUNT':<8} {'%':<8} {'DESCRIPTION':<40}")
    print(f"{'─'*70}")
    
    for code in sorted(target_codes.keys()):
        count = len(errors_by_code[code])
        pct = (count / total_errors * 100) if total_errors > 0 else 0
        desc = target_codes[code][:40]
        
        # Emoji priorité
        if code == 'E999':
            priority = '🔴'  # CRITIQUE
        elif code in ['W293', 'E128']:
            priority = '🟡'  # Important
        else:
            priority = '🟢'  # Moyen
        
        print(f"{priority} {code:<6} {count:<8} {pct:<7.1f}% {desc:<40}")
    
    print(f"{'─'*70}\n")
    
    # Top 10 fichiers hot-spots
    print(f"📁 TOP 10 FICHIERS HOT-SPOTS (Erreurs Phase 1E)\n")
    
    file_totals = {}
    for filepath, codes_dict in errors_by_file.items():
        file_totals[filepath] = sum(len(errors) for errors in codes_dict.values())
    
    sorted_files = sorted(file_totals.items(), key=lambda x: x[1], reverse=True)[:10]
    
    print(f"{'RANK':<6} {'ERRORS':<8} {'FILEPATH':<55}")
    print(f"{'─'*70}")
    
    for rank, (filepath, count) in enumerate(sorted_files, 1):
        # Codes présents dans ce fichier
        codes_present = []
        for code in target_codes:
            if code in errors_by_file[filepath]:
                codes_present.append(f"{code}:{len(errors_by_file[filepath][code])}")
        
        codes_str = ' '.join(codes_present)
        filepath_short = filepath if len(filepath) <= 50 else '...' + filepath[-47:]
        
        print(f"{rank:<6} {count:<8} {filepath_short:<55}")
        print(f"       └─ {codes_str}")
    
    print(f"{'─'*70}\n")
    
    # Détail E999 (CRITIQUE)
    if errors_by_code['E999']:
        print(f"🔴 DÉTAIL E999 (SYNTAXERROR CRITIQUE) - {len(errors_by_code['E999'])} erreurs\n")
        print(f"{'FILE':<50} {'LINE':<6} {'MESSAGE':<30}")
        print(f"{'─'*70}")
        
        for err in errors_by_code['E999']:
            filepath_short = err['filepath'] if len(err['filepath']) <= 45 else '...' + err['filepath'][-42:]
            msg_short = err['message'][:28]
            print(f"{filepath_short:<50} {err['line']:<6} {msg_short:<30}")
        
        print(f"{'─'*70}\n")
    
    # Statistiques détaillées par code
    results = {
        'total_errors_baseline': total_errors,
        'target_errors_phase1e': target_errors,
        'reduction_potential_pct': (target_errors / total_errors * 100) if total_errors > 0 else 0,
        'errors_by_code': {},
        'hot_spots': [],
        'e999_critical': []
    }
    
    for code in target_codes:
        results['errors_by_code'][code] = {
            'count': len(errors_by_code[code]),
            'description': target_codes[code],
            'files': list(set(err['filepath'] for err in errors_by_code[code])),
            'errors': errors_by_code[code]
        }
    
    # Hot-spots (top 20 pour export JSON)
    for filepath, count in sorted_files[:20]:
        hot_spot = {
            'filepath': filepath,
            'total_errors': count,
            'errors_by_code': {}
        }
        for code in target_codes:
            if code in errors_by_file[filepath]:
                hot_spot['errors_by_code'][code] = len(errors_by_file[filepath][code])
        results['hot_spots'].append(hot_spot)
    
    # E999 critical details
    results['e999_critical'] = errors_by_code['E999']
    
    # Export JSON
    output_path = Path('reports/phase1e_analysis.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Rapport détaillé exporté: {output_path}\n")
    
    # Recommandations
    print(f"{'='*70}")
    print(f"🎯 RECOMMANDATIONS PHASE 1E")
    print(f"{'='*70}\n")
    
    print("1. 🔴 PRIORITAIRE: Traiter E999 (SyntaxError) EN PREMIER")
    print(f"   → {len(errors_by_code['E999'])} erreurs syntaxe Python critiques")
    print(f"   → Correction manuelle fichier par fichier\n")
    
    print("2. 🟡 IMPORTANT: Correction W293 (whitespace réapparu)")
    print(f"   → {len(errors_by_code['W293'])} erreurs")
    print(f"   → Réutiliser scripts/fix_whitespace_errors.py (Phase 1B)")
    print(f"   → Durée estimée: 2 minutes\n")
    
    print("3. 🟡 IMPORTANT: Correction E128/E117 (indentation)")
    print(f"   → E128: {len(errors_by_code['E128'])} erreurs")
    print(f"   → E117: {len(errors_by_code['E117'])} erreurs")
    print(f"   → Utiliser autopep8 --select=E128,E117 ou corrections manuelles\n")
    
    print("4. 🟢 MOYEN: Correction E265 (block comments)")
    print(f"   → {len(errors_by_code['E265'])} erreurs")
    print(f"   → Script regex simple: # ([^\s#]) → # \\1\n")
    
    print(f"{'='*70}\n")
    
    print(f"✅ Réduction potentielle Phase 1E: -{target_errors} erreurs (-{target_errors/total_errors*100:.1f}%)")
    print(f"📈 Objectif Phase 1E: {total_errors} → ~{total_errors - target_errors} erreurs\n")
    
    return results


if __name__ == '__main__':
    try:
        results = analyze_phase1e_targets()
        if results:
            print("✅ Analyse Phase 1E complétée avec succès!")
        else:
            print("❌ Échec de l'analyse Phase 1E")
            exit(1)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        exit(1)