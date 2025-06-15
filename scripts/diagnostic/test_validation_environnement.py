import project_core.core_from_scripts.auto_env
#!/usr/bin/env python3
"""
Phase 4 - Validation configuration et environnement
"""

import sys
import os
print('=== VALIDATION ENVIRONNEMENT ===')

print(f'Python version: {sys.version.split()[0]}')
print(f'Plateforme: {sys.platform}')
print(f'Working directory: {os.getcwd()}')

# Vérification structure projet
required_dirs = [
    'argumentation_analysis',
    'argumentation_analysis/agents',
    'argumentation_analysis/orchestration',
    'tests',
    'config',
    'scripts',
    'libs',
    'docs'
]

structure_score = 0
total_dirs = len(required_dirs)

print('\n📁 Structure du projet:')
for dir_path in required_dirs:
    if os.path.exists(dir_path):
        print(f'✅ {dir_path}/')
        structure_score += 1
    else:
        print(f'❌ MANQUANT: {dir_path}/')

# Vérification fichiers critiques
critical_files = [
    'argumentation_analysis/__init__.py',
    'argumentation_analysis/agents/core/logic/fol_logic_agent.py',
    'argumentation_analysis/orchestration/real_llm_orchestrator.py',
    'config/__init__.py',
    'setup.py',
    '.env'
]

print('\n📄 Fichiers critiques:')
files_score = 0
total_files = len(critical_files)

for file_path in critical_files:
    if os.path.exists(file_path):
        print(f'✅ {file_path}')
        files_score += 1
    else:
        print(f'❌ MANQUANT: {file_path}')

# Test import modules critiques
print('\n🔌 Modules critiques:')
modules_score = 0
critical_modules = [
    ('FOLLogicAgent', 'argumentation_analysis.agents.core.logic.fol_logic_agent'),
    ('RealLLMOrchestrator', 'argumentation_analysis.orchestration.real_llm_orchestrator'),
]

for module_name, module_path in critical_modules:
    try:
        exec(f'from {module_path} import {module_name}')
        print(f'✅ {module_name}')
        modules_score += 1
    except Exception as e:
        print(f'❌ {module_name}: {str(e)[:50]}...')

# Calcul score global
structure_pct = (structure_score / total_dirs) * 100
files_pct = (files_score / total_files) * 100
modules_pct = (modules_score / len(critical_modules)) * 100

overall_score = (structure_pct + files_pct + modules_pct) / 3

print(f'\n📊 SCORES VALIDATION:')
print(f'Structure: {structure_pct:.1f}% ({structure_score}/{total_dirs})')
print(f'Fichiers: {files_pct:.1f}% ({files_score}/{total_files})')
print(f'Modules: {modules_pct:.1f}% ({modules_score}/{len(critical_modules)})')
print(f'Score global: {overall_score:.1f}%')

if overall_score >= 90:
    print('✅ ENVIRONNEMENT EXCELLENT')
elif overall_score >= 80:
    print('✅ ENVIRONNEMENT STABLE')
else:
    print('⚠️ ENVIRONNEMENT NÉCESSITE ATTENTION')

print('=== ENVIRONNEMENT VALIDÉ ===')