# tests/dev_utils/test_encoding_utils.py
import pytest
import os
import tempfile
from pathlib import Path
import logging
from project_core.dev_utils.encoding_utils import fix_file_encoding, logger as encoding_utils_logger

# Fixture pour créer des fichiers temporaires avec différents encodages
@pytest.fixture
def temp_file_for_encoding_test(request):
    original_level = encoding_utils_logger.level
    if "debuglog" in request.keywords:
        encoding_utils_logger.setLevel(logging.DEBUG)
        print(f"\n[DEBUG LOGGING ENABLED FOR {request.node.name}]")

    temp_files = []

    def _create_temp_file(content, encoding=None, suffix=".txt", content_bytes=None):
        fd, path_str = tempfile.mkstemp(suffix=suffix, text=False) # text=False pour wb
        path = Path(path_str)
        
        if content_bytes is not None:
            with open(path, "wb") as f:
                f.write(content_bytes)
        elif encoding:
            with open(path, "w", encoding=encoding) as f:
                f.write(content)
        else: # Par défaut, écrire en utf-8 si non spécifié et pas bytes
             with open(path, "w", encoding="utf-8") as f:
                f.write(content)

        os.close(fd)
        temp_files.append(path)
        return path

    yield _create_temp_file

    encoding_utils_logger.setLevel(original_level)
    if "debuglog" in request.keywords:
        print(f"\n[DEBUG LOGGING RESTORED FOR {request.node.name}]")

    for f_path in temp_files:
        if f_path.exists():
            f_path.unlink()

@pytest.mark.debuglog
def test_fix_encoding_already_utf8(temp_file_for_encoding_test):
    """Teste un fichier déjà en UTF-8."""
    original_content = "Contenu accentué déjà en UTF-8: éàçùè"
    file_path = temp_file_for_encoding_test(original_content, encoding="utf-8")
    
    result = fix_file_encoding(str(file_path))
    assert result is True
    
    with open(file_path, "r", encoding="utf-8") as f:
        new_content = f.read()
    assert new_content == original_content

@pytest.mark.debuglog
def test_fix_encoding_latin1_to_utf8(temp_file_for_encoding_test):
    """Teste la conversion de Latin-1 vers UTF-8."""
    original_text = "Contenu accentué en Latin-1: éàçùè"
    latin1_bytes = original_text.encode("latin-1")
    file_path = temp_file_for_encoding_test(None, content_bytes=latin1_bytes)

    result = fix_file_encoding(str(file_path))
    assert result is True
    
    with open(file_path, "r", encoding="utf-8") as f:
        new_content = f.read()
    assert new_content == original_text

@pytest.mark.debuglog
def test_fix_encoding_cp1252_to_utf8(temp_file_for_encoding_test):
    """Teste la conversion de CP1252 (Windows-1252) vers UTF-8."""
    original_text = "Contenu accentué en CP1252: éàçùè €" # € est spécifique
    cp1252_bytes = original_text.encode("cp1252")
    file_path = temp_file_for_encoding_test(None, content_bytes=cp1252_bytes)

    result = fix_file_encoding(str(file_path))
    assert result is True
    
    with open(file_path, "r", encoding="utf-8") as f:
        new_content = f.read()
    assert new_content == original_text

@pytest.mark.debuglog
def test_fix_encoding_unknown_encoding(temp_file_for_encoding_test):
    """Teste un fichier avec un encodage non géré par la liste par défaut."""
    # Utiliser des bytes qui ne sont valides dans aucun des encodages courants testés
    # Exemple: une séquence de bytes invalide en UTF-8, Latin-1, CP1252
    # Une séquence de début de caractère multi-byte UTF-8 tronquée peut causer cela.
    # Ou des bytes spécifiques à des encodages non listés (ex: KOI8-R)
    unknown_bytes = b"\x9A\x7A\x80\xFF\xFE" # Séquence aléatoire, peu probable d'être valide
    file_path = temp_file_for_encoding_test(None, content_bytes=unknown_bytes)
    
    # On s'attend à ce que la fonction échoue à décoder et retourne False
    # Forcer l'utilisation d'un encodage qui ne fonctionnera pas avec unknown_bytes
    result = fix_file_encoding(str(file_path), source_encodings=['utf-8'])
    assert result is False
    # On peut aussi vérifier que le fichier n'a pas été modifié ou est resté tel quel
    with open(file_path, "rb") as f:
        final_bytes = f.read()
    assert final_bytes == unknown_bytes

@pytest.mark.debuglog
def test_fix_encoding_file_not_found():
    """Teste la gestion d'un fichier non trouvé."""
    result = fix_file_encoding("fichier_inexistant_pour_test_encodage.txt")
    assert result is False

@pytest.mark.debuglog
def test_fix_encoding_custom_source_encodings(temp_file_for_encoding_test):
    """Teste la spécification d'encodages source personnalisés."""
    original_text = "Текст на русском языке" # Texte en cyrillique
    koi8r_bytes = original_text.encode("koi8-r")
    file_path = temp_file_for_encoding_test(None, content_bytes=koi8r_bytes)

    # Sans koi8-r dans la liste et avec des encodages restrictifs, cela devrait échouer.
    result_fail = fix_file_encoding(str(file_path), source_encodings=['utf-8', 'ascii'])
    assert result_fail is False

    # Avec koi8-r dans la liste source
    result_success = fix_file_encoding(str(file_path), source_encodings=['koi8-r', 'utf-8'])
    assert result_success is True
    
    with open(file_path, "r", encoding="utf-8") as f:
        new_content = f.read()
    assert new_content == original_text

@pytest.mark.debuglog
def test_fix_encoding_custom_target_encoding(temp_file_for_encoding_test):
    """Teste la spécification d'un encodage cible différent."""
    original_text = "Contenu à convertir en Latin-1: éàçùè"
    utf8_bytes = original_text.encode("utf-8") # Source est UTF-8
    file_path = temp_file_for_encoding_test(None, content_bytes=utf8_bytes)

    result = fix_file_encoding(str(file_path), target_encoding="latin-1", source_encodings=['utf-8'])
    assert result is True
    
    # Lire en Latin-1 pour vérifier
    with open(file_path, "r", encoding="latin-1") as f:
        new_content_latin1 = f.read()
    assert new_content_latin1 == original_text

    # Vérifier que les bytes correspondent à l'encodage Latin-1
    with open(file_path, "rb") as f:
        final_bytes = f.read()
    assert final_bytes == original_text.encode("latin-1")

@pytest.mark.debuglog
def test_fix_encoding_empty_file(temp_file_for_encoding_test):
    """Teste la gestion d'un fichier vide."""
    file_path = temp_file_for_encoding_test("") # Fichier vide
    
    result = fix_file_encoding(str(file_path))
    assert result is True # Devrait réussir, rien à changer
    
    with open(file_path, "r", encoding="utf-8") as f:
        new_content = f.read()
    assert new_content == ""