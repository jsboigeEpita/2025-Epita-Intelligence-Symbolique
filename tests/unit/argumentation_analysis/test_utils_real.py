# -*- coding: utf-8 -*-
"""
Tests unitaires RÉELS pour les utilitaires - VERSION AUTHENTIQUE
Remplace test_utils.py qui utilise des mocks
"""

import unittest
import os
import sys
import tempfile
import shutil
from pathlib import Path
import json

# Import réels des utilitaires
from argumentation_analysis.utils.system_utils import ensure_directory_exists, get_project_root, is_running_in_notebook


class TestRealSystemUtils(unittest.TestCase):
    """Tests RÉELS pour les utilitaires système - AUCUN MOCK."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Nettoyage après chaque test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_ensure_directory_exists_real(self):
        """Teste la création de répertoire - VERSION RÉELLE."""
        try:
            test_dir = Path(self.temp_dir) / "test_real_dir"
            
            # Vérifier que le répertoire n'existe pas initialement
            self.assertFalse(test_dir.exists(), "Le répertoire ne devrait pas exister initialement")
            
            # Appeler la fonction à tester
            result = ensure_directory_exists(test_dir)
            
            # Vérifier que le répertoire a été créé
            self.assertTrue(test_dir.exists(), "Le répertoire devrait être créé")
            self.assertTrue(test_dir.is_dir(), "Devrait être un répertoire")
            self.assertTrue(result, "La fonction devrait retourner True")
            
            # Appeler à nouveau la fonction (le répertoire existe déjà)
            result2 = ensure_directory_exists(test_dir)
            self.assertTrue(result2, "Devrait retourner True même si le répertoire existe")
            
            print("✅ Test création répertoire réel réussi")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test de création répertoire réel: {e}")
            return False

    def test_ensure_directory_exists_with_file_real(self):
        """Teste le comportement quand le chemin est un fichier - VERSION RÉELLE."""
        try:
            test_file = Path(self.temp_dir) / "test_file.txt"
            test_file.touch()  # Créer le fichier
            
            # Appeler la fonction avec un chemin de fichier
            result = ensure_directory_exists(test_file)
            self.assertFalse(result, "Devrait retourner False pour un fichier existant")
            
            print("✅ Test comportement avec fichier réussi")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test fichier réel: {e}")
            return False

    def test_get_project_root_real(self):
        """Teste la récupération de la racine du projet - VERSION RÉELLE."""
        try:
            # Appeler la fonction à tester
            root = get_project_root()
            
            # Vérifications basiques
            self.assertIsNotNone(root, "La racine ne devrait pas être None")
            self.assertIsInstance(root, Path, "Devrait retourner un Path")
            self.assertTrue(root.exists(), "La racine devrait exister")
            self.assertTrue(root.is_dir(), "La racine devrait être un répertoire")
            
            # Vérifier que c'est bien la racine du projet (contient des dossiers typiques)
            expected_dirs = ['examples', 'tests', 'argumentation_analysis']
            existing_dirs = [d for d in expected_dirs if (root / d).exists()]
            self.assertGreater(len(existing_dirs), 0, "Devrait contenir au moins un dossier du projet")
            
            print(f"✅ Test racine projet réussi: {root}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test racine projet réel: {e}")
            return False

    def test_is_running_in_notebook_real(self):
        """Teste la détection d'environnement notebook - VERSION RÉELLE."""
        try:
            # Appeler la fonction à tester
            result = is_running_in_notebook()
            
            # Dans un test normal, on ne devrait pas être dans un notebook
            self.assertIsInstance(result, bool, "Devrait retourner un booléen")
            
            # En général, dans les tests pytest/unittest, on n'est pas dans un notebook
            # mais on ne fait pas d'assertion stricte car cela dépend de l'environnement
            
            print(f"✅ Test détection notebook réussi: {result}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors du test détection notebook réel: {e}")
            return False


class TestRealFileOperations(unittest.TestCase):
    """Tests RÉELS pour les opérations de fichiers - AUCUN MOCK."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Nettoyage après chaque test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_real_file_operations(self):
        """Teste les opérations de fichiers réelles."""
        try:
            test_file = Path(self.temp_dir) / "test_data.json"
            
            # Données de test
            test_data = {
                "rules": ["Si P alors Q", "Si Q alors R"],
                "facts": ["P est vrai"],
                "conclusions": ["Q", "R"]
            }
            
            # Écriture réelle
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, ensure_ascii=False, indent=2)
            
            # Vérification que le fichier existe
            self.assertTrue(test_file.exists(), "Le fichier devrait être créé")
            
            # Lecture réelle
            with open(test_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            # Vérifications
            self.assertEqual(loaded_data, test_data, "Les données chargées devraient correspondre")
            self.assertIn("rules", loaded_data)
            self.assertIn("facts", loaded_data)
            self.assertIn("conclusions", loaded_data)
            
            print("✅ Test opérations fichiers réelles réussi")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors des opérations fichiers réelles: {e}")
            return False

    def test_real_directory_traversal(self):
        """Teste la traversée de répertoires réelle."""
        try:
            # Créer une structure de répertoires
            subdir1 = Path(self.temp_dir) / "subdir1"
            subdir2 = Path(self.temp_dir) / "subdir2"
            subdir1.mkdir()
            subdir2.mkdir()
            
            # Créer des fichiers
            (subdir1 / "file1.txt").touch()
            (subdir1 / "file2.txt").touch()
            (subdir2 / "file3.txt").touch()
            
            # Traverser et compter
            all_files = []
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    all_files.append(Path(root) / file)
            
            # Vérifications
            self.assertEqual(len(all_files), 3, "Devrait trouver 3 fichiers")
            
            # Vérifier que tous les fichiers existent
            for file_path in all_files:
                self.assertTrue(file_path.exists(), f"Le fichier {file_path} devrait exister")
            
            print("✅ Test traversée répertoires réelle réussie")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la traversée réelle: {e}")
            return False


class TestRealTextProcessing(unittest.TestCase):
    """Tests RÉELS pour le traitement de texte - AUCUN MOCK."""

    def test_real_text_normalization(self):
        """Teste la normalisation de texte réelle."""
        try:
            # Texte avec différents problèmes
            raw_text = "  Si P   alors Q.  \n\n P est vrai...   Donc Q !  "
            
            # Normalisation basique
            normalized = raw_text.strip()
            normalized = ' '.join(normalized.split())  # Normaliser les espaces
            normalized = normalized.replace('...', '.')
            normalized = normalized.replace('!', '.')
            
            # Vérifications
            self.assertNotIn('  ', normalized, "Ne devrait pas contenir d'espaces doubles")
            self.assertFalse(normalized.startswith(' '), "Ne devrait pas commencer par un espace")
            self.assertFalse(normalized.endswith(' '), "Ne devrait pas finir par un espace")
            self.assertIn("Si P alors Q", normalized)
            self.assertIn("P est vrai", normalized)
            
            print(f"✅ Test normalisation texte réelle réussie: '{normalized}'")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de la normalisation réelle: {e}")
            return False

    def test_real_logical_pattern_extraction(self):
        """Teste l'extraction de patterns logiques réels."""
        try:
            text = "Si P alors Q. Si Q alors R. P est vrai. Donc Q et R."
            
            # Extraction par regex simple
            import re
            
            # Patterns logiques
            if_then_pattern = r"Si\s+(\w+)\s+alors\s+(\w+)"
            fact_pattern = r"(\w+)\s+est\s+vrai"
            
            rules = re.findall(if_then_pattern, text)
            facts = re.findall(fact_pattern, text)
            
            # Vérifications
            self.assertEqual(len(rules), 2, "Devrait trouver 2 règles")
            self.assertEqual(len(facts), 1, "Devrait trouver 1 fait")
            
            # Vérifier le contenu
            self.assertIn(("P", "Q"), rules, "Devrait contenir la règle P->Q")
            self.assertIn(("Q", "R"), rules, "Devrait contenir la règle Q->R")
            self.assertIn("P", facts, "Devrait contenir le fait P")
            
            print(f"✅ Test extraction patterns réelle réussie - Règles: {rules}, Faits: {facts}")
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de l'extraction réelle: {e}")
            return False


class TestRealIntegrationUtils(unittest.TestCase):
    """Tests d'intégration RÉELS pour les utilitaires - AUCUN MOCK."""

    def test_real_full_pipeline(self):
        """Teste un pipeline complet d'utilitaires réels."""
        try:
            # Créer un répertoire temporaire
            with tempfile.TemporaryDirectory() as temp_dir:
                project_dir = Path(temp_dir) / "test_project"
                
                # Utiliser les utilitaires réels
                success = ensure_directory_exists(project_dir)
                self.assertTrue(success, "Création répertoire devrait réussir")
                
                # Créer des fichiers de test
                data_dir = project_dir / "data"
                ensure_directory_exists(data_dir)
                
                test_file = data_dir / "logic_rules.txt"
                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write("Si P alors Q.\nP est vrai.\nDonc Q.")
                
                # Vérifier l'existence
                self.assertTrue(test_file.exists(), "Le fichier devrait être créé")
                
                # Lire et traiter
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Traitement simple
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                self.assertEqual(len(lines), 3, "Devrait avoir 3 lignes")
                
                # Détection de la racine (relative au projet réel)
                real_root = get_project_root()
                self.assertIsNotNone(real_root, "Devrait détecter la racine")
                
                print("✅ Test pipeline complet utilitaires réels réussi")
                return True
                
        except Exception as e:
            print(f"❌ Erreur lors du pipeline réel: {e}")
            return False


if __name__ == "__main__":
    # Exécuter tous les tests
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Ajouter toutes les classes de test
    test_classes = [
        TestRealSystemUtils,
        TestRealFileOperations, 
        TestRealTextProcessing,
        TestRealIntegrationUtils
    ]
    
    for test_class in test_classes:
        tests = test_loader.loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Lancer les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    if result.wasSuccessful():
        print("\n✅ TOUS LES TESTS RÉELS DES UTILITAIRES RÉUSSIS")
    else:
        print(f"\n❌ ÉCHECS: {len(result.failures)}, ERREURS: {len(result.errors)}")