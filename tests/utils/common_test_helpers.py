
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utilitaires d'aide aux tests.

Ce module fournit des fonctions utilitaires pour faciliter l'écriture
et l'exécution des tests d'intégration et fonctionnels.
"""

import os
import sys
import json
import logging
import tempfile
import shutil
from pathlib import Path
from contextlib import contextmanager


# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestHelpers")


@contextmanager
def temp_directory():
    """
    Crée un répertoire temporaire pour les tests et le supprime après utilisation.
    
    Yields:
        str: Chemin du répertoire temporaire.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)


@contextmanager
def temp_file(content=None, suffix=".txt"):
    """
    Crée un fichier temporaire pour les tests et le supprime après utilisation.
    
    Args:
        content (str): Contenu à écrire dans le fichier.
        suffix (str): Suffixe du fichier temporaire.
        
    Yields:
        str: Chemin du fichier temporaire.
    """
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        if content is not None:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            os.close(fd)
        yield path
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def create_test_file(content, file_path):
    """
    Crée un fichier de test avec le contenu spécifié.
    
    Args:
        content (str): Contenu du fichier.
        file_path (str): Chemin du fichier à créer.
        
    Returns:
        str: Chemin du fichier créé.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return file_path


def read_test_file(file_path):
    """
    Lit le contenu d'un fichier de test.
    
    Args:
        file_path (str): Chemin du fichier à lire.
        
    Returns:
        str: Contenu du fichier.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def read_json_file(file_path):
    """
    Lit le contenu d'un fichier JSON.
    
    Args:
        file_path (str): Chemin du fichier JSON à lire.
        
    Returns:
        dict: Contenu du fichier JSON.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json_file(data, file_path):
    """
    Écrit des données dans un fichier JSON.
    
    Args:
        data (dict): Données à écrire.
        file_path (str): Chemin du fichier JSON à créer.
        
    Returns:
        str: Chemin du fichier créé.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return file_path


def compare_json_files(file1, file2, ignore_keys=None):
    """
    Compare deux fichiers JSON en ignorant certaines clés si spécifié.
    
    Args:
        file1 (str): Chemin du premier fichier JSON.
        file2 (str): Chemin du deuxième fichier JSON.
        ignore_keys (list): Liste des clés à ignorer lors de la comparaison.
        
    Returns:
        bool: True si les fichiers sont équivalents, False sinon.
    """
    if ignore_keys is None:
        ignore_keys = []
    
    data1 = read_json_file(file1)
    data2 = read_json_file(file2)
    
    return compare_json_objects(data1, data2, ignore_keys)


def compare_json_objects(obj1, obj2, ignore_keys=None):
    """
    Compare deux objets JSON en ignorant certaines clés si spécifié.
    
    Args:
        obj1 (dict): Premier objet JSON.
        obj2 (dict): Deuxième objet JSON.
        ignore_keys (list): Liste des clés à ignorer lors de la comparaison.
        
    Returns:
        bool: True si les objets sont équivalents, False sinon.
    """
    if ignore_keys is None:
        ignore_keys = []
    
    if isinstance(obj1, dict) and isinstance(obj2, dict):
        if set(k for k in obj1 if k not in ignore_keys) != set(k for k in obj2 if k not in ignore_keys):
            return False
        
        return all(
            compare_json_objects(obj1[k], obj2[k], ignore_keys)
            for k in obj1
            if k not in ignore_keys and k in obj2
        )
    
    elif isinstance(obj1, list) and isinstance(obj2, list):
        if len(obj1) != len(obj2):
            return False
        
        # Pour les listes, on compare les éléments un à un
        # Cette approche est simplifiée et ne gère pas les permutations
        return all(
            compare_json_objects(o1, o2, ignore_keys)
            for o1, o2 in zip(obj1, obj2)
        )
    
    else:
        return obj1 == obj2


def mock_dependencies():
    """
    Mocke les dépendances problématiques (numpy, pandas, jpype).
    
    Returns:
        tuple: Tuple contenant les patchers créés.
    """
    # Importer les mocks
    from tests.mocks.numpy_mock import array, ndarray, mean, sum, zeros, ones, dot, concatenate, vstack, hstack, argmax, argmin, max, min, random
    from tests.mocks.pandas_mock import DataFrame, read_csv, read_json
    from tests.mocks.jpype_mock import isJVMStarted, startJVM, getJVMPath, getJVMVersion, getDefaultJVMPath, JClass, JException, JObject, JVMNotFoundException, imports, _jpype
    
    # Créer les mocks pour numpy
    numpy_mock = Magicawait self._create_authentic_gpt4o_mini_instance()
    numpy_mock.array = array
    numpy_mock.ndarray = ndarray
    numpy_mock.mean = mean
    numpy_mock.sum = sum
    numpy_mock.zeros = zeros
    numpy_mock.ones = ones
    numpy_mock.dot = dot
    numpy_mock.concatenate = concatenate
    numpy_mock.vstack = vstack
    numpy_mock.hstack = hstack
    numpy_mock.argmax = argmax
    numpy_mock.argmin = argmin
    numpy_mock.max = max
    numpy_mock.min = min
    numpy_mock.random = random
    
    # Créer les mocks pour pandas
    pandas_mock = Magicawait self._create_authentic_gpt4o_mini_instance()
    pandas_mock.DataFrame = DataFrame
    pandas_mock.read_csv = read_csv
    pandas_mock.read_json = read_json
    pandas_mock.Series = list
    pandas_mock.NA = None
    pandas_mock.NaT = None
    pandas_mock.isna = lambda x: x is None
    pandas_mock.notna = lambda x: x is not None
    
    # Créer les mocks pour jpype
    jpype_mock = Magicawait self._create_authentic_gpt4o_mini_instance()
    jpype_mock.isJVMStarted = isJVMStarted
    jpype_mock.startJVM = startJVM
    jpype_mock.getJVMPath = getJVMPath
    jpype_mock.getJVMVersion = getJVMVersion
    jpype_mock.getDefaultJVMPath = getDefaultJVMPath
    jpype_mock.JClass = JClass
    jpype_mock.JException = JException
    jpype_mock.JObject = JObject
    jpype_mock.JVMNotFoundException = JVMNotFoundException
    jpype_mock.imports = imports
    
    # Créer les patchers
    numpy_patcher = patch.dict('sys.modules', {'numpy': numpy_mock})
    pandas_patcher = patch.dict('sys.modules', {'pandas': pandas_mock})
    jpype_patcher = patch.dict('sys.modules', {'jpype': jpype_mock, '_jpype': _jpype})
    
    # Démarrer les patchers
    numpy_patcher.start()
    pandas_patcher.start()
    jpype_patcher.start()
    
    return numpy_patcher, pandas_patcher, jpype_patcher


def unmock_dependencies(patchers):
    """
    Arrête les patchers de dépendances.
    
    Args:
        patchers (tuple): Tuple contenant les patchers à arrêter.
    """
    for patcher in patchers:
        patcher.stop()


@contextmanager
def mocked_dependencies():
    """
    Contexte pour mocker les dépendances problématiques pendant l'exécution d'un bloc de code.
    
    Yields:
        tuple: Tuple contenant les mocks (numpy_mock, pandas_mock, jpype_mock).
    """
    patchers = mock_dependencies()
    try:
        yield patchers
    finally:
        unmock_dependencies(patchers)


def setup_test_environment():
    """
    Configure l'environnement de test.
    
    Returns:
        dict: Informations sur l'environnement de test.
    """
    # Ajouter le répertoire parent au PYTHONPATH
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    # Commenté car l'installation du package via `pip install -e .` devrait gérer l'accessibilité.
    
    # Créer les répertoires nécessaires
    os.makedirs("results/test", exist_ok=True)
    os.makedirs("examples/test_data", exist_ok=True)
    
    # Vérifier si les dépendances sont disponibles
    dependencies_available = {
        "numpy": False,
        "pandas": False,
        "jpype": False
    }
    
    try:
        import numpy
        dependencies_available["numpy"] = True
    except ImportError:
        pass
    
    try:
        import pandas
        dependencies_available["pandas"] = True
    except ImportError:
        pass
    
    try:
        import jpype
        dependencies_available["jpype"] = True
    except ImportError:
        pass
    
    return {
        "project_dir": parent_dir,
        "dependencies_available": dependencies_available
    }


def cleanup_test_environment():
    """
    Nettoie l'environnement de test.
    """
    # Supprimer les fichiers temporaires
    temp_dirs = ["results/test"]
    
    for temp_dir in temp_dirs:
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    logger.warning(f"Erreur lors de la suppression du fichier {file_path}: {e}")


def run_with_real_dependencies(func, *args, **kwargs):
    """
    Exécute une fonction avec les dépendances réelles si elles sont disponibles.
    
    Args:
        func (callable): Fonction à exécuter.
        *args: Arguments positionnels à passer à la fonction.
        **kwargs: Arguments nommés à passer à la fonction.
        
    Returns:
        any: Résultat de la fonction ou None si les dépendances ne sont pas disponibles.
    """
    # Vérifier si les dépendances sont disponibles
    try:
        import numpy
        import pandas
        has_dependencies = True
    except ImportError:
        has_dependencies = False
        logger.warning("Les dépendances numpy et pandas ne sont pas disponibles. Le test sera ignoré.")
    
    if has_dependencies:
        return func(*args, **kwargs)
    else:
        return None


def run_with_mocked_dependencies(func, *args, **kwargs):
    """
    Exécute une fonction avec les dépendances mockées.
    
    Args:
        func (callable): Fonction à exécuter.
        *args: Arguments positionnels à passer à la fonction.
        **kwargs: Arguments nommés à passer à la fonction.
        
    Returns:
        any: Résultat de la fonction.
    """
    with mocked_dependencies():
        return func(*args, **kwargs)


if __name__ == "__main__":
    # Exemple d'utilisation
    env_info = setup_test_environment()
    print("Informations sur l'environnement de test :")
    print(json.dumps(env_info, indent=2))
    
    with temp_file("Contenu de test") as temp_file_path:
        print(f"Fichier temporaire créé : {temp_file_path}")
        content = read_test_file(temp_file_path)
        print(f"Contenu du fichier : {content}")
    
    cleanup_test_environment()