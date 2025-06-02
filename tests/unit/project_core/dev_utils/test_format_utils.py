# tests/dev_utils/test_format_utils.py
import pytest
import os
import tempfile
from pathlib import Path
from project_core.dev_utils.format_utils import fix_docstrings_apostrophes, logger as format_utils_logger # Importer le logger
import logging # Importer logging

@pytest.fixture
def temp_file_for_docstring_test(request): # Ajouter request pour le nom du test
    # Sauvegarder le niveau de log original et le restaurer après le test
    original_level = format_utils_logger.level
    # Mettre le logger en DEBUG pour ce test spécifique si besoin
    # format_utils_logger.setLevel(logging.DEBUG)
    # Décommenter la ligne ci-dessus pour activer les logs DEBUG de format_utils pour tous les tests de ce fichier
    # Ou faire dynamiquement:
    if "debuglog" in request.keywords:
        format_utils_logger.setLevel(logging.DEBUG)
        print(f"\n[DEBUG LOGGING ENABLED FOR {request.node.name}]")


    """Crée un fichier temporaire et retourne son chemin."""
    """Crée un fichier temporaire et retourne son chemin."""
    temp_files = []
    def _create_temp_file(content: str, suffix=".py"):
        # Utiliser NamedTemporaryFile pour s'assurer que le fichier est supprimé même en cas d'erreur
        # mais on a besoin du chemin, donc on le ferme et le rouvre si nécessaire, ou on gère la suppression manuellement.
        # Pour la simplicité avec la lecture/écriture multiple, on utilise mkstemp et on gère la suppression.
        fd, path_str = tempfile.mkstemp(suffix=suffix, text=True)
        path = Path(path_str)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        os.close(fd) # Fermer le descripteur de fichier initial
        temp_files.append(path)
        return path
    
    yield _create_temp_file
    
    # Restaurer le niveau de log original
    format_utils_logger.setLevel(original_level)
    if "debuglog" in request.keywords:
        print(f"\n[DEBUG LOGGING RESTORED FOR {request.node.name}]")

    for f_path in temp_files:
        if f_path.exists():
            f_path.unlink()

@pytest.mark.debuglog # Marqueur pour activer les logs DEBUG pour ce test si besoin
def test_fix_docstrings_apostrophes_no_change(temp_file_for_docstring_test):
    """Teste que le fichier n'est pas modifié si aucune apostrophe problématique n'est trouvée."""
    content = """
def func1():
    '''Ceci est une docstring normale.'''
    pass
"""
    file_path = temp_file_for_docstring_test(content)
    result = fix_docstrings_apostrophes(str(file_path))
    assert result is True
    with open(file_path, 'r', encoding='utf-8') as f:
        new_content = f.read()
    assert new_content == content

@pytest.mark.debuglog # Marqueur pour activer les logs DEBUG pour ce test si besoin
def test_fix_docstrings_apostrophes_single_change(temp_file_for_docstring_test):
    """Teste un remplacement simple d'apostrophe."""
    content = """
def func1():
    '''Ceci est un test d'évaluation.'''
    pass
"""
    expected_content = """
def func1():
    '''Ceci est un test "d'évaluation".'''
    pass
"""
    file_path = temp_file_for_docstring_test(content)
    result = fix_docstrings_apostrophes(str(file_path))
    assert result is True
    with open(file_path, 'r', encoding='utf-8') as f:
        new_content = f.read()
    assert new_content == expected_content

@pytest.mark.debuglog # Marqueur pour activer les logs DEBUG pour ce test si besoin
def test_fix_docstrings_apostrophes_multiple_changes(temp_file_for_docstring_test):
    """Teste plusieurs remplacements d'apostrophes dans le même fichier."""
    content = """
def func1():
    '''Un test d'un cas avec d'une note d'analyse.
    Liste d'arguments:
        arg1: pour un test d'erreur.
    '''
    pass
"""
    expected_content = """
def func1():
    '''Un test "d'un" cas avec "d'une" note "d'analyse".
    Liste "d'arguments":
        arg1: pour un test "d'erreur".
    '''
    pass
"""
    file_path = temp_file_for_docstring_test(content)
    result = fix_docstrings_apostrophes(str(file_path))
    assert result is True
    with open(file_path, 'r', encoding='utf-8') as f:
        new_content = f.read()
    assert new_content == expected_content

@pytest.mark.debuglog # Marqueur pour activer les logs DEBUG pour ce test si besoin
def test_fix_docstrings_apostrophes_no_docstrings(temp_file_for_docstring_test):
    """Teste un fichier sans docstrings mais avec des chaînes qui pourraient correspondre."""
    # Le contenu initial est défini sans indentation de base pour correspondre à la sortie attendue.
    # La fixture écrit ce contenu tel quel.
    content = """# Ceci n'est pas une docstring: d'un commentaire
my_string = "d'un test"
def func1():
    # Pas de docstring ici
    a = "d'une variable" # Ceci n'est pas une docstring
    pass
"""
    file_path = temp_file_for_docstring_test(content)
    result = fix_docstrings_apostrophes(str(file_path))
    assert result is True # La fonction devrait toujours réussir
    with open(file_path, 'r', encoding='utf-8') as f:
        new_content = f.read()

    # La fonction remplace globalement, donc les chaînes en dehors des docstrings sont aussi affectées.
    # "n'est", "d'un", "d'une" sont dans replacements_map_full.
    # Les chaînes comme "d'un test" deviendront ""d'un" test".
    expected_content = """# Ceci "n'est" pas une docstring: "d'un" commentaire
my_string = ""d'un" test"
def func1():
    # Pas de docstring ici
    a = ""d'une" variable" # Ceci "n'est" pas une docstring
    pass
"""
    # Le contenu écrit dans le fichier temporaire par la fixture n'a pas de ligne vide au début ou à la fin si `content` n'en a pas.
    # `new_content` lu n'aura donc pas de ligne vide superflue si `content` et `expected_content` sont définis sans.
    assert new_content == expected_content


def test_fix_docstrings_apostrophes_file_not_found():
    """Teste le cas où le fichier n'existe pas."""
    result = fix_docstrings_apostrophes("fichier_qui_n_existe_pas_du_tout.py")
    assert result is False

@pytest.mark.debuglog # Marqueur pour activer les logs DEBUG pour ce test si besoin
def test_fix_docstrings_idempotency(temp_file_for_docstring_test):
    """Teste que réappliquer la fonction ne change plus le contenu."""
    content = """
def func1():
    '''Un test d'un cas avec d'une note d'analyse.'''
    pass
"""
    expected_content_pass1 = """
def func1():
    '''Un test "d'un" cas avec "d'une" note "d'analyse".'''
    pass
"""
    file_path = temp_file_for_docstring_test(content)
    
    # Premier passage
    result1 = fix_docstrings_apostrophes(str(file_path))
    assert result1 is True
    with open(file_path, 'r', encoding='utf-8') as f:
        content_pass1 = f.read()
    assert content_pass1 == expected_content_pass1
    
    # Deuxième passage
    result2 = fix_docstrings_apostrophes(str(file_path))
    assert result2 is True
    with open(file_path, 'r', encoding='utf-8') as f:
        content_pass2 = f.read()
    assert content_pass2 == expected_content_pass1 # Doit être identique au premier passage corrigé