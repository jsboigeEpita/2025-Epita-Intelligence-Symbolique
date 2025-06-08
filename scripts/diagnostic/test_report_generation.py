#!/usr/bin/env python3
"""Test simple du générateur de rapports récupéré"""

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