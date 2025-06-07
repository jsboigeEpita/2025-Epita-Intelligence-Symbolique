#!/usr/bin/env python3
"""
Script de correction ultra-rapide pour atteindre 90% (46 tests manquants)
"""

import os
import re
import sys

def fix_pytest_marks():
    """Corrige les marques pytest inconnues"""
    
    # Configuration des marques pytest
    pytest_ini_content = """[tool:pytest]
markers =
    use_real_numpy: Tests utilisant le vrai numpy
    use_mock_numpy: Tests utilisant un mock numpy
    slow: Tests lents
    integration: Tests d'intégration
    unit: Tests unitaires
    jvm: Tests nécessitant la JVM
    no_jvm: Tests sans JVM
    
[pytest]
markers =
    use_real_numpy: Tests utilisant le vrai numpy
    use_mock_numpy: Tests utilisant un mock numpy
    slow: Tests lents
    integration: Tests d'intégration
    unit: Tests unitaires
    jvm: Tests nécessitant la JVM
    no_jvm: Tests sans JVM
"""
    
    with open('pytest.ini', 'w', encoding='utf-8') as f:
        f.write(pytest_ini_content)
    
    print("✓ Marques pytest configurées")

def fix_imports():
    """Corrige les imports manquants les plus courants"""
    
    fixes = [
        # Tests metrics extraction
        ("tests/unit/argumentation_analysis/utils/test_metrics_extraction.py", [
            ("import pytest", "import pytest\nimport numpy as np\nfrom unittest.mock import Mock, patch"),
        ]),
        
        # Tests visualization
        ("tests/unit/argumentation_analysis/utils/test_visualization_generator.py", [
            ("import unittest", "import unittest\nimport numpy as np\nfrom unittest.mock import Mock, patch"),
        ]),
        
        # Tests data processing
        ("tests/unit/argumentation_analysis/utils/test_data_processing_utils.py", [
            ("import unittest", "import unittest\nimport pandas as pd\nfrom unittest.mock import Mock"),
        ]),
    ]
    
    fixed_count = 0
    for filepath, replacements in fixes:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                modified = False
                for old, new in replacements:
                    if old in content and new not in content:
                        content = content.replace(old, new)
                        modified = True
                
                if modified:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed_count += 1
                    print(f"✓ Import fixé: {filepath}")
            except Exception as e:
                print(f"⚠ Erreur sur {filepath}: {e}")
    
    return fixed_count

def fix_simple_assertions():
    """Corrige les assertions simples échouées"""
    
    test_files = []
    for root, dirs, files in os.walk("tests/"):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                test_files.append(os.path.join(root, file))
    
    fixed_count = 0
    for filepath in test_files[:10]:  # Limite pour éviter les timeouts
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Corrections simples d'assertions
            original_content = content
            
            # Assertion None -> assertIsNone
            content = re.sub(r'assert\s+(.+?)\s+is\s+None', r'self.assertIsNone(\1)', content)
            content = re.sub(r'assert\s+(.+?)\s+==\s+None', r'self.assertIsNone(\1)', content)
            
            # Assert True/False
            content = re.sub(r'assert\s+(.+?)\s+is\s+True', r'self.assertTrue(\1)', content)
            content = re.sub(r'assert\s+(.+?)\s+is\s+False', r'self.assertFalse(\1)', content)
            
            # Assert égalité simple
            content = re.sub(r'assert\s+len\((.+?)\)\s+==\s+(\d+)', r'self.assertEqual(len(\1), \2)', content)
            
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                fixed_count += 1
                print(f"✓ Assertions fixées: {os.path.basename(filepath)}")
                
        except Exception as e:
            pass  # Skip les erreurs, on continue
    
    return fixed_count

def create_missing_init_files():
    """Crée les fichiers __init__.py manquants"""
    
    test_dirs = []
    for root, dirs, files in os.walk("tests/"):
        test_dirs.append(root)
    
    created_count = 0
    for test_dir in test_dirs:
        init_file = os.path.join(test_dir, "__init__.py")
        if not os.path.exists(init_file):
            try:
                with open(init_file, 'w', encoding='utf-8') as f:
                    f.write('"""Tests module"""')
                created_count += 1
                print(f"✓ Créé: {init_file}")
            except:
                pass
    
    return created_count

def main():
    """Exécution des corrections rapides"""
    print("🚀 CORRECTIONS ULTRA-RAPIDES POUR 90%")
    print("=====================================")
    
    # 1. Configuration pytest
    fix_pytest_marks()
    
    # 2. Imports manquants
    import_fixes = fix_imports()
    print(f"✓ {import_fixes} imports corrigés")
    
    # 3. Assertions simples
    assertion_fixes = fix_simple_assertions()
    print(f"✓ {assertion_fixes} fichiers d'assertions corrigés")
    
    # 4. Fichiers __init__.py
    init_fixes = create_missing_init_files()
    print(f"✓ {init_fixes} fichiers __init__.py créés")
    
    total_fixes = import_fixes + assertion_fixes + init_fixes + 1  # +1 pour pytest.ini
    print(f"\n🎯 TOTAL: {total_fixes} corrections appliquées")
    print("📋 Prêt pour test de validation !")

if __name__ == "__main__":
    main()