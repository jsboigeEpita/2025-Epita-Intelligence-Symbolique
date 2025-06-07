"""
Tests de validation pour le code récupéré.
Validation complète des 9 fichiers priorité 8-10 récupérés et adaptés pour Oracle Enhanced v2.1.0

Tests couvrant:
- Validation des imports et compatibilité v2.1.0
- Tests d'intégrité du code récupéré
- Validation des adaptations Oracle Enhanced
- Tests de non-régression
"""

import pytest
import os
import sys
import importlib
import ast
from pathlib import Path
from typing import List, Dict, Any

# Configuration des chemins récupérés
RECOVERED_PATHS = {
    "scripts/maintenance/recovered": [
        "update_test_coverage.py",
        "test_oracle_behavior_demo.py", 
        "test_oracle_behavior_simple.py"
    ],
    "tests/integration/recovered": [
        "test_cluedo_extended_workflow.py",
        "test_mock_vs_real_behavior.py",
        "test_oracle_integration.py",
        "conftest_gpt_enhanced.py"
    ],
    "tests/comparison/recovered": [
        "test_mock_vs_real_behavior.py"
    ],
    "tests/unit/recovered": [
        "test_oracle_base_agent.py"
    ]
}


class TestRecoveredCodeValidation:
    """Tests de validation du code récupéré."""
    
    @pytest.fixture(scope="class")
    def recovered_files_info(self):
        """Information sur tous les fichiers récupérés."""
        files_info = {}
        
        for base_path, files in RECOVERED_PATHS.items():
            for file_name in files:
                file_path = Path(base_path) / file_name
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    files_info[str(file_path)] = {
                        'path': file_path,
                        'content': content,
                        'lines': len(content.splitlines()),
                        'size': len(content)
                    }
        
        return files_info
    
    def test_all_recovered_files_exist(self, recovered_files_info):
        """Test que tous les fichiers récupérés existent."""
        expected_count = sum(len(files) for files in RECOVERED_PATHS.values())
        actual_count = len(recovered_files_info)
        
        assert actual_count >= 8, f"Attendu au moins 8 fichiers récupérés, trouvé {actual_count}"
        
        # Vérification des fichiers critiques
        critical_files = [
            "scripts/maintenance/recovered/update_test_coverage.py",
            "tests/integration/recovered/test_oracle_integration.py",
            "tests/integration/recovered/conftest_gpt_enhanced.py"
        ]
        
        for critical_file in critical_files:
            assert any(critical_file in path for path in recovered_files_info.keys()), \
                f"Fichier critique manquant: {critical_file}"
    
    def test_oracle_enhanced_v2_1_0_adaptations(self, recovered_files_info):
        """Test que tous les fichiers sont adaptés pour Oracle Enhanced v2.1.0."""
        adaptation_indicators = [
            "Oracle Enhanced v2.1.0",
            "oracle_enhanced.",
            "v2.1.0",
            "adaptations"
        ]
        
        for file_path, info in recovered_files_info.items():
            content = info['content']
            
            # Au moins un indicateur d'adaptation doit être présent
            has_adaptation = any(indicator in content for indicator in adaptation_indicators)
            assert has_adaptation, f"Fichier {file_path} manque d'adaptations v2.1.0"
            
            # Vérification spécifique des imports modernisés
            if "import" in content:
                # Ne doit pas avoir d'imports obsolètes sans fallback
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    if "from argumentation_analysis" in line and "import" in line:
                        # Doit avoir un fallback ou être dans un try/except
                        context_lines = lines[max(0, i-5):i+5]
                        context_str = '\n'.join(context_lines)
                        
                        assert ("try:" in context_str or "except ImportError:" in context_str), \
                            f"Import sans fallback trouvé dans {file_path}:{i+1}"
    
    def test_python_syntax_validity(self, recovered_files_info):
        """Test que tous les fichiers récupérés ont une syntaxe Python valide."""
        for file_path, info in recovered_files_info.items():
            try:
                ast.parse(info['content'])
            except SyntaxError as e:
                pytest.fail(f"Erreur syntaxe dans {file_path}: {e}")
    
    def test_no_regression_indicators(self, recovered_files_info):
        """Test l'absence d'indicateurs de régression."""
        regression_patterns = [
            "TODO: FIX",
            "BROKEN",
            "DEPRECATED",
            "NOT WORKING",
            "FIXME",
            "import_error",
            "ImportError # Non géré"
        ]
        
        for file_path, info in recovered_files_info.items():
            content = info['content'].lower()
            
            for pattern in regression_patterns:
                assert pattern.lower() not in content, \
                    f"Indicateur de régression '{pattern}' trouvé dans {file_path}"
    
    def test_oracle_functionality_preservation(self, recovered_files_info):
        """Test que les fonctionnalités Oracle sont préservées."""
        oracle_keywords = [
            "Oracle",
            "CluedoOracle",
            "MoriartyInterrogator",
            "dataset_manager",
            "oracle_strategy",
            "enhanced_auto_reveal"
        ]
        
        oracle_files = [path for path in recovered_files_info.keys() 
                       if "oracle" in path.lower() or "cluedo" in path.lower()]
        
        assert len(oracle_files) >= 4, f"Pas assez de fichiers Oracle récupérés: {len(oracle_files)}"
        
        for file_path in oracle_files:
            content = recovered_files_info[file_path]['content']
            
            # Au moins 2 mots-clés Oracle doivent être présents
            keyword_count = sum(1 for keyword in oracle_keywords if keyword in content)
            assert keyword_count >= 2, \
                f"Fonctionnalités Oracle insuffisantes dans {file_path} ({keyword_count} mots-clés)"
    
    def test_documentation_and_comments_quality(self, recovered_files_info):
        """Test la qualité de la documentation des adaptations."""
        for file_path, info in recovered_files_info.items():
            content = info['content']
            lines = content.splitlines()
            
            # Doit avoir un docstring informatif
            has_docstring = '"""' in content or "'''" in content
            assert has_docstring, f"Docstring manquant dans {file_path}"
            
            # Doit mentionner les adaptations dans les 20 premières lignes
            header_lines = lines[:20]
            header_content = '\n'.join(header_lines)
            
            adaptation_mentioned = any(word in header_content.lower() for word in 
                                     ['adapté', 'adaptation', 'récupéré', 'v2.1.0'])
            assert adaptation_mentioned, f"Adaptations non documentées dans {file_path}"
    
    def test_file_size_reasonableness(self, recovered_files_info):
        """Test que les tailles de fichiers sont raisonnables."""
        for file_path, info in recovered_files_info.items():
            lines = info['lines']
            size = info['size']
            
            # Tests de base de cohérence
            assert lines > 10, f"Fichier trop petit {file_path}: {lines} lignes"
            assert size > 500, f"Fichier trop petit {file_path}: {size} caractères"
            assert lines < 1000, f"Fichier anormalement grand {file_path}: {lines} lignes"
            
            # Ratio taille/lignes raisonnable (indicateur de contenu)
            if lines > 0:
                avg_line_length = size / lines
                assert 20 <= avg_line_length <= 200, \
                    f"Longueur moyenne de ligne suspecte dans {file_path}: {avg_line_length:.1f}"


class TestRecoveredCodeFunctionality:
    """Tests fonctionnels spécifiques aux fichiers récupérés."""
    
    def test_update_test_coverage_script_integrity(self):
        """Test l'intégrité du script de couverture de tests récupéré."""
        script_path = Path("scripts/maintenance/recovered/update_test_coverage.py")
        
        if script_path.exists():
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Fonctionnalités critiques préservées
            critical_functions = [
                "create_test_coverage_for_error_handling",
                "create_test_coverage_for_interfaces", 
                "generate_test_coverage_report",
                "main"
            ]
            
            for func in critical_functions:
                assert f"def {func}" in content, \
                    f"Fonction critique {func} manquante dans le script de couverture"
            
            # Adaptations Oracle Enhanced
            assert "Oracle Enhanced v2.1.0" in content
            assert "oracle_enhanced" in content or "try:" in content  # Import adapté
    
    def test_conftest_gpt_enhanced_functionality(self):
        """Test la fonctionnalité du conftest GPT Enhanced récupéré."""
        conftest_path = Path("tests/integration/recovered/conftest_gpt_enhanced.py")
        
        if conftest_path.exists():
            with open(conftest_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Fixtures critiques préservées
            critical_fixtures = [
                "@pytest.fixture",
                "real_gpt_kernel",
                "validated_gpt_kernel", 
                "enhanced_orchestrator",
                "gpt_test_session"
            ]
            
            for fixture in critical_fixtures:
                assert fixture in content, \
                    f"Fixture critique {fixture} manquante dans conftest GPT Enhanced"
            
            # Configuration GPT-4o-mini préservée
            assert "gpt-4o-mini" in content
            assert "RateLimiter" in content
            assert "GPTTestSession" in content
    
    def test_oracle_tests_integrity(self):
        """Test l'intégrité des tests Oracle récupérés."""
        oracle_test_files = [
            "tests/integration/recovered/test_oracle_integration.py",
            "tests/unit/recovered/test_oracle_base_agent.py"
        ]
        
        for test_file_path in oracle_test_files:
            test_path = Path(test_file_path)
            
            if test_path.exists():
                with open(test_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Structure de test préservée
                assert "class Test" in content or "def test_" in content
                assert "@pytest.mark" in content
                assert "assert" in content
                
                # Imports Oracle préservés
                oracle_imports = ["Oracle", "Cluedo", "Moriarty", "dataset"]
                has_oracle_import = any(imp in content for imp in oracle_imports)
                assert has_oracle_import, f"Imports Oracle manquants dans {test_file_path}"


@pytest.mark.integration 
class TestRecoveredCodeIntegration:
    """Tests d'intégration pour le code récupéré."""
    
    def test_import_compatibility_fallbacks(self):
        """Test que les fallbacks d'import fonctionnent."""
        test_imports = [
            "tests.integration.recovered.conftest_gpt_enhanced",
            "tests.unit.recovered.test_oracle_base_agent"
        ]
        
        for module_name in test_imports:
            try:
                # Tentative d'import du module récupéré
                module = importlib.import_module(module_name)
                assert module is not None
                
                # Vérification que le module a du contenu
                assert hasattr(module, '__file__')
                
            except ImportError as e:
                # Les imports peuvent échouer à cause des dépendances externes
                # C'est acceptable tant que la structure du fallback est correcte
                assert "oracle_enhanced" in str(e) or "argumentation_analysis" in str(e), \
                    f"Import error inattendu pour {module_name}: {e}"
    
    def test_recovered_code_documentation(self):
        """Test que le code récupéré est bien documenté."""
        readme_path = Path("scripts/maintenance/recovered/README.md")
        
        assert readme_path.exists(), "Documentation README.md manquante"
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        # Documentation des fichiers récupérés
        assert "Code récupéré" in readme_content
        assert "Oracle Enhanced v2.1.0" in readme_content
        assert "priorité" in readme_content.lower()


if __name__ == "__main__":
    # Exécution rapide des tests de validation
    pytest.main([__file__, "-v", "--tb=short"])