# project_core/dev_utils/code_validation.py
import ast
import tokenize
import io
import logging
from typing import Tuple, List, Dict, Any # Ajout pour des types potentiels futurs

# Configuration du logging pour ce module
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def check_python_syntax(file_path: str) -> Tuple[bool, str, List[str]]:
    """
    Vérifie la syntaxe d'un fichier Python.
    
    Args:
        file_path: Chemin du fichier à vérifier.
        
    Returns:
        Tuple[bool, str, List[str]]: 
            - True si la syntaxe est correcte, False sinon.
            - Message de succès ou d'erreur.
            - Liste des lignes de contexte en cas d'erreur.
    """
    logger.debug(f"Vérification de la syntaxe du fichier : {file_path}")
    context_lines_on_error = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        message = "✅ La syntaxe du fichier est correcte."
        logger.info(f"{message} ({file_path})")
        return True, message, []
    except SyntaxError as e:
        message = f"❌ Erreur de syntaxe : {e}"
        logger.warning(f"{message} ({file_path})")
        logger.warning(f"   Ligne {e.lineno}, colonne {e.offset}: {e.text.strip() if e.text else ''}")
        
        lines = content.split('\n')
        start_line_ctx = max(0, e.lineno - 3) # 2 lignes avant
        end_line_ctx = min(len(lines), e.lineno + 2) # 2 lignes après (inclusif de la ligne d'erreur)
        
        for i in range(start_line_ctx, end_line_ctx):
            prefix = ">> " if i + 1 == e.lineno else "   "
            line_content = f"{prefix}{i + 1}: {lines[i]}"
            logger.debug(line_content) # Log pour le débogage
            context_lines_on_error.append(line_content)
        return False, message, context_lines_on_error
    except FileNotFoundError:
        message = f"❌ Fichier non trouvé : {file_path}"
        logger.error(message)
        return False, message, []
    except Exception as e:
        message = f"❌ Autre erreur lors de la vérification de syntaxe : {e}"
        logger.error(f"{message} ({file_path})", exc_info=True)
        return False, message, []

def check_python_tokens(file_path: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    Vérifie les tokens d'un fichier Python pour détecter des problèmes potentiels.
    
    Args:
        file_path: Chemin du fichier à vérifier.
        
    Returns:
        Tuple[bool, str, List[Dict[str, Any]]]:
            - True si aucun token d'erreur n'est trouvé, False sinon.
            - Message de succès ou d'erreur.
            - Liste des tokens d'erreur trouvés (dictionnaires avec 'line', 'col', 'message').
    """
    logger.debug(f"Analyse des tokens du fichier : {file_path}")
    error_tokens_found = []
    try:
        with open(file_path, 'rb') as f: # tokenize.tokenize attend un flux binaire
            tokens = list(tokenize.tokenize(f.readline))
        
        has_error_token = False
        for token in tokens:
            if token.type == tokenize.ERRORTOKEN:
                has_error_token = True
                error_detail = {
                    "line": token.start[0],
                    "col": token.start[1],
                    "message": f"Token d'erreur: {token.string!r}"
                }
                error_tokens_found.append(error_detail)
                logger.warning(f"❌ Token d'erreur détecté à la ligne {token.start[0]}, colonne {token.start[1]} dans {file_path}: {token.string!r}")
        
        if has_error_token:
            message = f"❌ Des tokens d'erreur ont été détectés dans {file_path}."
            return False, message, error_tokens_found
        else:
            message = f"✅ Analyse des tokens terminée pour {file_path}. Aucun token d'erreur."
            logger.info(message)
            return True, message, []
            
    except FileNotFoundError:
        message = f"❌ Fichier non trouvé pour l'analyse des tokens : {file_path}"
        logger.error(message)
        return False, message, []
    except tokenize.TokenError as e: # Erreur spécifique de tokenization
        message = f"❌ Erreur de tokenization dans {file_path}: {e}"
        logger.error(message, exc_info=True)
        error_tokens_found.append({"line": e.args[1][0] if len(e.args) > 1 and isinstance(e.args[1], tuple) else 'N/A', 
                                   "col": e.args[1][1] if len(e.args) > 1 and isinstance(e.args[1], tuple) else 'N/A', 
                                   "message": str(e)})
        return False, message, error_tokens_found
    except Exception as e:
        message = f"❌ Autre erreur lors de l'analyse des tokens de {file_path}: {e}"
        logger.error(message, exc_info=True)
        return False, message, []

if __name__ == '__main__':
    # Section de test simple
    logger.setLevel(logging.DEBUG)
    
    # Créer un fichier de test valide
    valid_test_file = "temp_valid_code.py"
    with open(valid_test_file, "w", encoding="utf-8") as f:
        f.write("def hello():\n")
        f.write("    print('Hello, world!')\n")
        f.write("hello()\n")

    logger.info(f"\n--- Test avec fichier valide: {valid_test_file} ---")
    is_valid, msg, ctx = check_python_syntax(valid_test_file)
    logger.info(f"Syntaxe valide: {is_valid}, Message: {msg}")
    if not is_valid: logger.info(f"Contexte: {ctx}")
    
    tokens_ok, token_msg, err_tokens = check_python_tokens(valid_test_file)
    logger.info(f"Tokens OK: {tokens_ok}, Message: {token_msg}")
    if not tokens_ok: logger.info(f"Tokens d'erreur: {err_tokens}")

    # Créer un fichier de test avec erreur de syntaxe
    invalid_syntax_file = "temp_invalid_syntax.py"
    with open(invalid_syntax_file, "w", encoding="utf-8") as f:
        f.write("def hello_bad():\n")
        f.write("    print('Missing quote)\n") # Erreur ici

    logger.info(f"\n--- Test avec fichier syntaxe invalide: {invalid_syntax_file} ---")
    is_valid, msg, ctx = check_python_syntax(invalid_syntax_file)
    logger.info(f"Syntaxe valide: {is_valid}, Message: {msg}")
    if not is_valid: 
        logger.info("Contexte de l'erreur:")
        for line_ctx in ctx: logger.info(line_ctx)
        
    # Créer un fichier de test avec erreur de token (ex: caractère invalide hors chaîne/commentaire)
    # Note: ast.parse pourrait aussi attraper cela comme SyntaxError.
    # tokenize est plus bas niveau.
    invalid_token_file = "temp_invalid_token.py"
    with open(invalid_token_file, "w", encoding="utf-8") as f:
        f.write("a = 1\n")
        f.write("b = 2 @ 3 # Erreur de token si @ n'est pas un opérateur binaire valide ici\n") 
        # En Python moderne, @ est pour la multiplication de matrices, donc syntaxiquement valide
        # mais tokenize.ERRORTOKEN est plus pour des caractères illégaux ou des indentations incohérentes
        # que ast.parse pourrait ne pas signaler de la même manière.
        # Remplaçons par un exemple plus clair d'ERRORTOKEN
    with open(invalid_token_file, "w", encoding="utf-8") as f:
        f.write("a = 1\n")
        f.write("  b = 2 # Indentation inattendue pouvant causer ERRORTOKEN\n")
        # Ou un caractère vraiment invalide:
        # f.write("val = `test` # backticks sont invalides en Python 3\n")
        # Pour l'instant, l'indentation est un bon test pour tokenize.TokenError

    logger.info(f"\n--- Test avec fichier token invalide (indentation): {invalid_token_file} ---")
    # Note: check_python_syntax pourrait déjà échouer pour ce cas.
    is_valid_syntax_for_token_test, _, _ = check_python_syntax(invalid_token_file)
    if is_valid_syntax_for_token_test:
        tokens_ok, token_msg, err_tokens = check_python_tokens(invalid_token_file)
        logger.info(f"Tokens OK: {tokens_ok}, Message: {token_msg}")
        if not tokens_ok: logger.info(f"Tokens d'erreur: {err_tokens}")
    else:
        logger.info("Syntaxe déjà invalide, test de token non pertinent ou déjà couvert.")

    # Nettoyage des fichiers de test
    import os
    if os.path.exists(valid_test_file): os.remove(valid_test_file)
    if os.path.exists(invalid_syntax_file): os.remove(invalid_syntax_file)
    if os.path.exists(invalid_token_file): os.remove(invalid_token_file)