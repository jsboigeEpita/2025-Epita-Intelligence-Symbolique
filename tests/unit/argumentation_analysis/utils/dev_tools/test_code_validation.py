# tests/dev_utils/test_code_validation.py
import pytest
import os
import tempfile
from pathlib import Path
from argumentation_analysis.utils.dev_tools.code_validation import check_python_syntax, check_python_tokens

# Helper pour créer des fichiers temporaires
@pytest.fixture
def temp_python_file():
    """Crée un fichier Python temporaire et retourne son chemin."""
    temp_files = []
    def _create_temp_file(content: str, suffix=".py"):
        fd, path_str = tempfile.mkstemp(suffix=suffix, text=True)
        path = Path(path_str)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        os.close(fd)
        temp_files.append(path)
        return path
    
    yield _create_temp_file
    
    for f_path in temp_files:
        if f_path.exists():
            f_path.unlink()

# --- Tests pour check_python_syntax ---

def test_check_syntax_valid_file(temp_python_file):
    """Teste check_python_syntax avec un fichier Python valide."""
    valid_content = "a = 1\ndef my_func():\n    return a + 1\nprint(my_func())"
    file_path = temp_python_file(valid_content)
    is_valid, msg, context = check_python_syntax(str(file_path))
    assert is_valid is True
    assert "syntaxe du fichier est correcte" in msg
    assert not context

def test_check_syntax_invalid_file(temp_python_file):
    """Teste check_python_syntax avec un fichier Python invalide."""
    invalid_content = "a = 1\ndef my_func()\n    return a + 1" # Erreur de syntaxe (manque :)
    file_path = temp_python_file(invalid_content)
    is_valid, msg, context = check_python_syntax(str(file_path))
    assert is_valid is False
    assert "Erreur de syntaxe" in msg
    assert any("my_func()" in line for line in context), "Le contexte devrait inclure la ligne avec l'erreur"

def test_check_syntax_file_not_found():
    """Teste check_python_syntax avec un fichier inexistant."""
    is_valid, msg, context = check_python_syntax("fichier_inexistant_pour_test.py")
    assert is_valid is False
    assert "Fichier non trouvé" in msg
    assert not context

def test_check_syntax_empty_file(temp_python_file):
    """Teste check_python_syntax avec un fichier vide (syntaxe valide)."""
    file_path = temp_python_file("")
    is_valid, msg, context = check_python_syntax(str(file_path))
    assert is_valid is True
    assert "syntaxe du fichier est correcte" in msg
    assert not context

# --- Tests pour check_python_tokens ---

def test_check_tokens_valid_file(temp_python_file):
    """Teste check_python_tokens avec un fichier Python valide."""
    valid_content = "b = 'hello'\n# un commentaire"
    file_path = temp_python_file(valid_content)
    tokens_ok, msg, errors = check_python_tokens(str(file_path))
    assert tokens_ok is True
    assert "Aucun token d'erreur" in msg
    assert not errors

def test_check_tokens_with_indentation_error_token(temp_python_file):
    """
    Teste check_python_tokens avec une erreur d'indentation qui génère un TokenError.
    tokenize.tokenize lève TokenError pour des indentations incohérentes.
    """
    # Contenu qui cause un tokenize.TokenError (indentation inattendue)
    # Note: ast.parse pourrait aussi l'attraper comme IndentationError, une sous-classe de SyntaxError.
    # L'objectif ici est de voir si check_python_tokens gère bien TokenError.
    invalid_content = "def func():\n    pass\n print('dedent error')" # Dé-indentation incorrecte
    file_path = temp_python_file(invalid_content)
    
    # D'abord, vérifier si ast.parse le voit comme une erreur de syntaxe
    syntax_ok, _, _ = check_python_syntax(str(file_path))
    
    if syntax_ok:
        # Si ast.parse ne l'a pas vu (peu probable pour ce cas), alors tester check_tokens
        tokens_ok, msg, errors = check_python_tokens(str(file_path))
        assert tokens_ok is False, "check_python_tokens aurait dû trouver une erreur de token."
        assert "Erreur de tokenization" in msg or "tokens d'erreur ont été détectés" in msg
        assert len(errors) > 0
        assert any("indent" in err.get("message", "").lower() or "dedent" in err.get("message", "").lower() for err in errors)
    else:
        # Si ast.parse l'a déjà attrapé, on peut considérer que le test de token est couvert
        # ou on pourrait vouloir un cas où SEULEMENT tokenize.TokenError est levée.
        # Pour cet exemple, si la syntaxe est déjà invalide, on ne force pas le test de token.
        pytest.skip("Syntaxe déjà invalide, test de TokenError spécifique non exécuté pour ce cas.")


def test_check_tokens_file_not_found():
    """Teste check_python_tokens avec un fichier inexistant."""
    tokens_ok, msg, errors = check_python_tokens("fichier_inexistant_pour_test_tokens.py")
    assert tokens_ok is False
    assert "Fichier non trouvé" in msg
    assert not errors

def test_check_tokens_empty_file(temp_python_file):
    """Teste check_python_tokens avec un fichier vide."""
    file_path = temp_python_file("")
    tokens_ok, msg, errors = check_python_tokens(str(file_path))
    assert tokens_ok is True # Un fichier vide n'a pas de tokens d'erreur
    assert "Aucun token d'erreur" in msg
    assert not errors

# Exemple de contenu qui pourrait générer un ERRORTOKEN (difficile à produire sans SyntaxError)
# Les ERRORTOKEN sont typiquement pour des caractères illégaux qui ne forment pas un token valide.
# Souvent, ast.parse les attrapera aussi comme SyntaxError.
# def test_check_tokens_with_explicit_errortoken(temp_python_file):
#     # ` (backtick) est invalide en Python 3 et pourrait générer un ERRORTOKEN
#     # si ce n'est pas attrapé comme SyntaxError plus tôt.
#     # content_with_errortoken = "a = `1`" 
#     # file_path = temp_python_file(content_with_errortoken)
#     # tokens_ok, msg, errors = check_python_tokens(str(file_path))
#     # assert tokens_ok is False
#     # assert "Token d'erreur détecté" in msg # ou le message de TokenError
#     # assert len(errors) > 0
#     pass # Difficile de créer un cas isolé de ERRORTOKEN sans SyntaxError