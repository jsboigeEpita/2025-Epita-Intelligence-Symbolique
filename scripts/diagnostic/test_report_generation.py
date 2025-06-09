#!/usr/bin/env python3
"""Test simple du générateur de rapports récupéré"""

# ===== ONE-LINER AUTO-ACTIVATEUR =====
import scripts.core.auto_env  # Auto-activation environnement intelligent
# =====================================

import sys
import os
# Ajout de la racine du projet au PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print('=== TEST GÉNÉRATEUR RAPPORTS RÉCUPÉRÉ ===')
try:
    from argumentation_analysis.utils.report_generation import generate_unified_report
    from argumentation_analysis.config.unified_config import UnifiedConfig
    
    config = UnifiedConfig()
    result = generate_unified_report({'test': 'data'}, config)
    print('✅ Report Generation System Functional')
    print(f'Type résultat: {type(result)}')
    if hasattr(result, '__len__'):
        print(f'Longueur résultat: {len(result)}')
    print(f'Contenu (extrait): {str(result)[:200]}...')
except Exception as e:
    print(f'❌ Erreur génération rapport: {e}')
    import traceback
    traceback.print_exc()