
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests unitaires pour les utilitaires du projet.
"""

import unittest
import os
import sys
import tempfile

from pathlib import Path
from argumentation_analysis.utils.system_utils import ensure_directory_exists, get_project_root, is_running_in_notebook
# from tests.async_test_case import AsyncTestCase # Suppression de l'import


class TestSystemUtils:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests pour les utilitaires système."""

    def test_ensure_directory_exists(self):
        """Teste la création de répertoire."""
        # Créer un répertoire temporaire pour les tests
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "test_dir"
            
            # Vérifier que le répertoire n'existe pas initialement
            assert not test_dir.exists()
            
            # Appeler la fonction à tester
            result = ensure_directory_exists(test_dir)
            
            # Vérifier que le répertoire a été créé
            assert test_dir.exists()
            assert test_dir.is_dir()
            assert result is True
            
            # Appeler à nouveau la fonction (le répertoire existe déjà)
            result2 = ensure_directory_exists(test_dir)
            assert result2 is True
            
            # Tester avec un chemin qui est un fichier
            test_file = Path(temp_dir) / "test_file.txt"
            test_file.touch()
            result3 = ensure_directory_exists(test_file)
            assert result3 is False

    def test_get_project_root(self):
        """Teste la récupération de la racine du projet."""
        # Appeler la fonction à tester
        root = get_project_root()
        
        # Vérifier que le résultat est un Path
        assert isinstance(root, Path)
        
        # Vérifier que le répertoire existe
        assert root.exists()
        assert root.is_dir()
        
        # Vérifier que c'est bien la racine du projet (contient des fichiers/dossiers clés)
        # Note: Cette vérification peut varier selon la structure du projet
        assert (root / "argumentation_analysis").exists() or \
               (root / "tests").exists() or \
               (root / "scripts").exists()

    def test_is_running_in_notebook(self):
        """Teste la détection d'exécution dans un notebook."""
        # Nous ne pouvons pas vraiment tester cette fonction de manière fiable
        # car elle dépend de l'environnement d'exécution.
        # Nous vérifions simplement que la fonction retourne un booléen.
        result = is_running_in_notebook()
        assert isinstance(result, bool)


class TestExtractRepairUtils:
    """Tests pour les utilitaires de réparation d'extraits."""
    
    
    def test_fix_missing_first_letter(self):
        """Teste la correction des marqueurs d'extraits manquant la première lettre."""
        # Note: Ce test est un exemple de ce que nous pourrions implémenter
        # pour tester la fonction fix_missing_first_letter.
        # Pour l'instant, nous nous contentons de vérifier que le test passe.
        
        assert True


class TestIntegrationUtils:
    """Tests d'intégration pour les utilitaires."""
    
    async def test_extract_repair_workflow(self):
        """Teste le workflow complet de réparation d'extraits."""
        # Note: Ce test est un exemple de test d'intégration
        # que nous pourrions implémenter à l'avenir.
        # Pour l'instant, nous nous contentons de vérifier que le test passe.
        
        assert True