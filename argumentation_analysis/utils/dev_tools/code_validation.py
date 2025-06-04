# project_core/dev_utils/code_validation.py
import ast
import tokenize
import io
import os # Ajout de l'import manquant
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

def analyze_directory_references(directory_to_scan: str, patterns_to_find: Dict[str, Any], file_extensions: Tuple[str, ...] = ('.py',)) -> Dict[str, Dict[str, Any]]:
    """
    Analyse les références à des motifs spécifiques (ex: chemins de répertoires) dans les fichiers d'un répertoire.

    Args:
        directory_to_scan (str): Répertoire racine à analyser.
        patterns_to_find (dict): Dictionnaire où les clés sont des noms de motifs
                                 et les valeurs sont des objets regex compilés.
        file_extensions (Tuple[str, ...]): Tuple des extensions de fichiers à analyser.

    Returns:
        dict: Statistiques et exemples d'utilisation pour chaque motif.
              Format: {pattern_name: {"count": 0, "files": {file_path: count}, "examples": [...]}}
    """
    results = {pattern_name: {"count": 0, "files": {}, "examples": []} for pattern_name in patterns_to_find}
    
    # Exclusions courantes pour l'analyse de code source
    excluded_dirs = {'.git', 'venv', '__pycache__', 'build', 'dist', 'docs', '_archives', 'htmlcov_demonstration', 'libs', 'node_modules', 'target'}
    # Ajouter d'autres répertoires spécifiques au projet si nécessaire
    
    logger.info(f"Analyse des références dans {directory_to_scan} pour les motifs: {list(patterns_to_find.keys())}")

    for root, dirs, files in os.walk(directory_to_scan):
        # Modification de la liste dirs en place pour éviter de parcourir les répertoires exclus
        dirs[:] = [d for d in dirs if d not in excluded_dirs and not d.endswith('.egg-info')]

        for file_name in files:
            if not file_name.endswith(file_extensions):
                continue

            file_path = os.path.join(root, file_name)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    for pattern_name, regex_pattern in patterns_to_find.items():
                        matches = regex_pattern.finditer(content)
                        
                        for match in matches:
                            results[pattern_name]["count"] += 1
                            
                            if file_path not in results[pattern_name]["files"]:
                                results[pattern_name]["files"][file_path] = 0
                            
                            results[pattern_name]["files"][file_path] += 1
                            
                            # Extraire la ligne contenant le match
                            # Compter les sauts de ligne avant le début du match pour obtenir le numéro de ligne
                            line_number = content.count('\n', 0, match.start()) + 1
                            
                            # Obtenir le contenu de la ligne
                            # Diviser le contenu en lignes, puis accéder à la ligne par son index (numéro de ligne - 1)
                            all_lines = content.splitlines()
                            line_content_str = all_lines[line_number - 1] if line_number <= len(all_lines) else "Ligne non trouvée"

                            # Ajouter l'exemple si moins de 5 exemples sont déjà stockés
                            if len(results[pattern_name]["examples"]) < 5: # Limiter le nombre d'exemples
                                results[pattern_name]["examples"].append({
                                    "file": file_path,
                                    "line": line_number,
                                    "content": line_content_str.strip()
                                })
            except FileNotFoundError:
                logger.warning(f"Fichier non trouvé pendant l'analyse des références: {file_path}")
            except UnicodeDecodeError:
                logger.warning(f"Erreur de décodage (non UTF-8) pour le fichier: {file_path}")
            except Exception as e:
                logger.error(f"Erreur lors de la lecture ou de l'analyse du fichier {file_path}: {e}", exc_info=True)
    
    for pattern_name, data in results.items():
        logger.info(f"Motif '{pattern_name}': {data['count']} références trouvées dans {len(data['files'])} fichier(s).")
        if data['examples']:
            logger.debug(f"  Exemples pour '{pattern_name}':")
            for ex in data['examples']:
                logger.debug(f"    {ex['file']}:{ex['line']} - {ex['content']}")
                
    return results


if __name__ == '__main__':
    # Section de test simple
    logger.setLevel(logging.DEBUG)
    
    # --- Tests pour check_python_syntax et check_python_tokens ---
    logger.info("--- DÉBUT DES TESTS POUR check_python_syntax ET check_python_tokens ---")
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

    invalid_syntax_file = "temp_invalid_syntax.py"
    with open(invalid_syntax_file, "w", encoding="utf-8") as f:
        f.write("def hello_bad():\n")
        f.write("    print('Missing quote)\n")

    logger.info(f"\n--- Test avec fichier syntaxe invalide: {invalid_syntax_file} ---")
    is_valid, msg, ctx = check_python_syntax(invalid_syntax_file)
    logger.info(f"Syntaxe valide: {is_valid}, Message: {msg}")
    if not is_valid:
        logger.info("Contexte de l'erreur:")
        for line_ctx in ctx: logger.info(line_ctx)
        
    invalid_token_file = "temp_invalid_token.py"
    with open(invalid_token_file, "w", encoding="utf-8") as f:
        f.write("a = 1\n")
        f.write("  b = 2 # Indentation inattendue\n")

    logger.info(f"\n--- Test avec fichier token invalide (indentation): {invalid_token_file} ---")
    is_valid_syntax_for_token_test, _, _ = check_python_syntax(invalid_token_file)
    if is_valid_syntax_for_token_test: # Devrait être False à cause de l'indentation
        tokens_ok, token_msg, err_tokens = check_python_tokens(invalid_token_file)
        logger.info(f"Tokens OK: {tokens_ok}, Message: {token_msg}")
        if not tokens_ok: logger.info(f"Tokens d'erreur: {err_tokens}")
    else:
        logger.info("Syntaxe déjà invalide pour le test de token, ce qui est attendu pour une mauvaise indentation.")
    logger.info("--- FIN DES TESTS POUR check_python_syntax ET check_python_tokens ---")

    # --- Tests pour analyze_directory_references ---
    logger.info("\n--- DÉBUT DES TESTS POUR analyze_directory_references ---")
    import re
    import os
    import shutil # Pour supprimer le répertoire de test

    temp_dir_analyze = "temp_analyze_dir_usage"
    if os.path.exists(temp_dir_analyze):
        shutil.rmtree(temp_dir_analyze)
    os.makedirs(temp_dir_analyze)
    os.makedirs(os.path.join(temp_dir_analyze, "subdir"))

    # Créer des fichiers de test
    with open(os.path.join(temp_dir_analyze, "file1.py"), "w", encoding="utf-8") as f:
        f.write("path_to_config = 'config/settings.json'\n")
        f.write("data_file = 'data/input.csv'\n")
        f.write("another_config = 'config/other.yaml'\n")

    with open(os.path.join(temp_dir_analyze, "subdir", "file2.py"), "w", encoding="utf-8") as f:
        f.write("import os\n")
        f.write("data_path = os.path.join('data', 'subdir_data.txt')\n")
        f.write("print('no config here')\n")
    
    with open(os.path.join(temp_dir_analyze, "file3.txt"), "w", encoding="utf-8") as f:
        f.write("config/ignored.txt\n") # Ne devrait pas être analysé (mauvaise extension)

    test_patterns = {
        "config_refs": re.compile(r'config/'),
        "data_refs": re.compile(r'data/'),
        "non_existent_refs": re.compile(r'non_existent_path/')
    }

    analysis_results = analyze_directory_references(temp_dir_analyze, test_patterns)

    # Vérifications basiques des résultats
    if analysis_results["config_refs"]["count"] == 2 and \
       len(analysis_results["config_refs"]["files"]) == 1 and \
       analysis_results["data_refs"]["count"] == 2 and \
       len(analysis_results["data_refs"]["files"]) == 2 and \
       analysis_results["non_existent_refs"]["count"] == 0:
        logger.info("Test analyze_directory_references : OK (comptes de base)")
    else:
        logger.error(f"Test analyze_directory_references : ÉCHEC (comptes de base). Résultats: {analysis_results}")

    logger.info(f"Résultats détaillés de l'analyse des références de répertoires:")
    for pattern_name, data in analysis_results.items():
        logger.info(f"  Motif '{pattern_name}':")
        logger.info(f"    Comptes: {data['count']}")
        logger.info(f"    Fichiers: {list(data['files'].keys())}")
        logger.info(f"    Exemples (max 5):")
        for ex in data['examples']:
            logger.info(f"      {ex['file']}:{ex['line']} - {ex['content']}")
    
    logger.info("--- FIN DES TESTS POUR analyze_directory_references ---")

    # Nettoyage final
    logger.info("\n--- Nettoyage des fichiers et répertoires de test ---")
    if os.path.exists(valid_test_file): os.remove(valid_test_file)
    if os.path.exists(invalid_syntax_file): os.remove(invalid_syntax_file)
    if os.path.exists(invalid_token_file): os.remove(invalid_token_file)
    if os.path.exists(temp_dir_analyze): shutil.rmtree(temp_dir_analyze)
    logger.info("Nettoyage terminé.")