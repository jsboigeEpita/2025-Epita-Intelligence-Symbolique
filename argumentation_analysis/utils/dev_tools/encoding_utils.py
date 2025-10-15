# project_core/dev_utils/encoding_utils.py
import logging
import os

# Configuration du logging pour ce module
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def fix_file_encoding(
    file_path: str, target_encoding: str = "utf-8", source_encodings: list = None
) -> bool:
    """
    Tente de lire un fichier en utilisant une liste d'encodages source possibles,
    puis le réécrit avec l'encodage cible spécifié (par défaut UTF-8).

    Args:
        file_path: Chemin du fichier à corriger.
        target_encoding: Encodage cible pour la réécriture du fichier.
        source_encodings: Liste optionnelle d'encodages source à essayer.
                          Si None, une liste par défaut sera utilisée.

    Returns:
        True si la conversion et l'écriture ont réussi, False sinon.
    """
    logger.info(
        f"Tentative de correction de l'encodage du fichier : {file_path} vers {target_encoding}"
    )

    if source_encodings is None:
        # Ordre important: utf-8 est strict. windows-1252 (alias cp1252) est un sur-ensemble de iso-8859-1.
        # Mettre windows-1252 avant latin-1/iso-8859-1 peut aider à mieux détecter les caractères spécifiques à Windows.
        source_encodings = ["utf-8", "windows-1252", "cp1252", "iso-8859-1", "latin-1"]

    # Nettoyer la liste pour éviter les doublons au cas où des alias sont passés
    cleaned_source_encodings = []
    seen_encodings = set()
    for enc in source_encodings:
        # Normaliser les noms d'encodage courants pour la déduplication
        norm_enc = enc.lower()
        if norm_enc == "latin1":
            norm_enc = "latin-1"
        if norm_enc == "iso8859-1":
            norm_enc = "iso-8859-1"

        if norm_enc not in seen_encodings:
            cleaned_source_encodings.append(enc)  # Garder le nom original pour `decode`
            seen_encodings.add(norm_enc)

    logger.debug(
        f"Encodages source à essayer (après nettoyage): {cleaned_source_encodings}"
    )

    try:
        with open(file_path, "rb") as f:
            raw_content = f.read()
    except FileNotFoundError:
        logger.error(f"Fichier non trouvé : {file_path}")
        return False
    except Exception as e:
        logger.error(
            f"Erreur lors de la lecture du fichier binaire {file_path}: {e}",
            exc_info=True,
        )
        return False

    decoded_content = None
    used_encoding = None

    for encoding in cleaned_source_encodings:  # Utiliser la liste nettoyée
        try:
            decoded_content = raw_content.decode(encoding)
            logger.info(f"Décodage réussi de {file_path} avec l'encodage : {encoding}")
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            logger.debug(f"Échec du décodage de {file_path} avec {encoding}.")
            continue
        except Exception as e:  # Autres erreurs potentielles de décodage
            logger.warning(
                f"Erreur inattendue lors du décodage de {file_path} avec {encoding}: {e}"
            )
            continue

    if decoded_content is None:
        logger.error(
            f"Impossible de décoder le fichier {file_path} avec les encodages connus: {cleaned_source_encodings}"
        )
        return False

    try:
        # Réencoder vers l'encodage cible
        encoded_content_target = decoded_content.encode(target_encoding)
    except Exception as e:
        logger.error(
            f"Erreur lors de l'encodage du contenu de {file_path} vers {target_encoding}: {e}",
            exc_info=True,
        )
        return False

    try:
        with open(file_path, "wb") as f:
            f.write(encoded_content_target)
        logger.info(
            f"Fichier corrigé et enregistré en {target_encoding} : {file_path} (décodé depuis {used_encoding})"
        )
        return True
    except Exception as e:
        logger.error(
            f"Erreur lors de l'écriture du fichier corrigé {file_path} en {target_encoding}: {e}",
            exc_info=True,
        )
        return False


def check_project_python_files_encoding(project_root: str = ".") -> list:
    """
    Vérifie que tous les fichiers Python dans le répertoire du projet sont encodés en UTF-8.

    Args:
        project_root: Chemin racine du projet à analyser.

    Returns:
        Liste des chemins des fichiers qui ne sont pas encodés en UTF-8.
    """
    logger.info(
        f"Vérification de l'encodage UTF-8 des fichiers Python dans : {os.path.abspath(project_root)}"
    )
    non_utf8_files = []
    python_files_count = 0

    # Exclusions courantes
    excluded_dirs = {
        ".git",
        "venv",
        "__pycache__",
        "build",
        "dist",
        "docs",
        "_archives",
        "htmlcov_demonstration",
        "libs",
    }
    # Ajouter d'autres répertoires spécifiques au projet si nécessaire, ex: 'node_modules', 'target'

    for root, dirs, files in os.walk(project_root):
        # Modification de la liste dirs en place pour éviter de parcourir les répertoires exclus
        dirs[:] = [
            d for d in dirs if d not in excluded_dirs and not d.endswith(".egg-info")
        ]

        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                python_files_count += 1
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        f.read()  # Essayer de lire le contenu pour déclencher l'erreur
                except UnicodeDecodeError:
                    logger.warning(f"Fichier non-UTF-8 détecté : {file_path}")
                    non_utf8_files.append(file_path)
                except Exception as e:
                    logger.error(
                        f"Erreur inattendue lors de la lecture de {file_path}: {e}"
                    )
                    non_utf8_files.append(
                        file_path
                    )  # Le considérer comme problématique

    if non_utf8_files:
        logger.warning(
            f"{len(non_utf8_files)} fichier(s) Python sur {python_files_count} ne sont pas (ou n'ont pas pu être vérifiés comme étant) encodés en UTF-8."
        )
    else:
        logger.info(
            f"Tous les {python_files_count} fichiers Python vérifiés sont encodés en UTF-8."
        )

    return non_utf8_files


if __name__ == "__main__":
    # Section de test simple pour les fonctions
    logger.setLevel(logging.DEBUG)  # Afficher plus de détails pour les tests

    # --- Tests pour fix_file_encoding ---
    logger.info("--- DÉBUT DES TESTS POUR fix_file_encoding ---")
    test_files_content_fix = {
        "test_fix_utf8.txt": "Contenu accentué en UTF-8: éàçùè",
        "test_fix_latin1.txt": "Contenu accentué en Latin-1: éàçùè".encode("latin-1"),
        "test_fix_cp1252.txt": "Contenu accentué en CP1252: éàçùè".encode("cp1252"),
    }

    temp_dir_fix = "temp_encoding_tests_fix"
    if not os.path.exists(temp_dir_fix):
        os.makedirs(temp_dir_fix)

    for filename, content in test_files_content_fix.items():
        file_path = os.path.join(temp_dir_fix, filename)
        logger.info(
            f"\n--- Création du fichier de test pour fix_file_encoding : {file_path} ---"
        )
        try:
            if isinstance(content, str):
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"Fichier {filename} (str) écrit en UTF-8.")
            else:  # bytes
                with open(file_path, "wb") as f:
                    f.write(content)
                original_encoding = (
                    "latin-1"
                    if "latin1" in filename
                    else "cp1252"
                    if "cp1252" in filename
                    else "unknown"
                )
                logger.info(
                    f"Fichier {filename} (bytes) écrit avec encodage brut (simulant {original_encoding})."
                )

            success = fix_file_encoding(file_path)
            if success:
                logger.info(
                    f"Correction de {filename} terminée. Vérification du contenu:"
                )
                with open(file_path, "r", encoding="utf-8") as f:
                    final_content = f.read()
                    logger.info(f"Contenu lu en UTF-8: {final_content}")
                    if "Contenu accentué" in final_content and "éàçùè" in final_content:
                        logger.info(f"Vérification pour {filename} : OK")
                    else:
                        logger.error(
                            f"Vérification pour {filename} : ÉCHEC. Contenu inattendu."
                        )
            else:
                logger.error(f"Échec de la correction pour {filename}.")
        except Exception as e:
            logger.error(f"Erreur lors du test de {filename}: {e}", exc_info=True)
        finally:
            if os.path.exists(file_path):
                logger.info(
                    f"Fichier de test {file_path} conservé pour inspection dans {temp_dir_fix}."
                )

    logger.info("\n--- Test fix_file_encoding avec un fichier inexistant ---")
    fix_file_encoding(os.path.join(temp_dir_fix, "fichier_inexistant_pour_test.txt"))
    logger.info("--- FIN DES TESTS POUR fix_file_encoding ---")

    # --- Tests pour check_project_python_files_encoding ---
    logger.info("\n--- DÉBUT DES TESTS POUR check_project_python_files_encoding ---")
    temp_dir_check = "temp_encoding_tests_check"
    if os.path.exists(temp_dir_check):  # Nettoyer les anciens tests
        import shutil

        shutil.rmtree(temp_dir_check)
    os.makedirs(temp_dir_check)

    # Créer des fichiers de test pour check_project_python_files_encoding
    # Fichier Python correctement encodé
    with open(
        os.path.join(temp_dir_check, "good_encoding.py"), "w", encoding="utf-8"
    ) as f:
        f.write("# Fichier UTF-8\nprint('éàç')\n")
    # Fichier Python mal encodé (simulé en latin-1)
    with open(
        os.path.join(temp_dir_check, "bad_encoding.py"), "w", encoding="latin-1"
    ) as f:
        f.write(
            "# Fichier Latin-1\nprint('éàç')\n"
        )  # Python lira ces bytes comme latin-1
    # Fichier non-Python
    with open(
        os.path.join(temp_dir_check, "not_python.txt"), "w", encoding="utf-8"
    ) as f:
        f.write("Ceci n'est pas un fichier Python.\n")

    # Créer un sous-répertoire pour tester la récursion et les exclusions
    os.makedirs(os.path.join(temp_dir_check, "subdir"))
    with open(
        os.path.join(temp_dir_check, "subdir", "good_subdir_encoding.py"),
        "w",
        encoding="utf-8",
    ) as f:
        f.write("# Fichier UTF-8 en sous-répertoire\nprint('éàç')\n")

    os.makedirs(os.path.join(temp_dir_check, "venv"))  # Répertoire à exclure
    with open(
        os.path.join(temp_dir_check, "venv", "excluded_file.py"),
        "w",
        encoding="latin-1",
    ) as f:
        f.write("# Devrait être ignoré\n")

    logger.info(
        f"Test de check_project_python_files_encoding sur le répertoire: {temp_dir_check}"
    )
    non_utf8 = check_project_python_files_encoding(temp_dir_check)

    expected_bad_file = os.path.join(temp_dir_check, "bad_encoding.py")
    if len(non_utf8) == 1 and os.path.abspath(non_utf8[0]) == os.path.abspath(
        expected_bad_file
    ):
        logger.info(
            f"Test check_project_python_files_encoding : OK. Fichier non-UTF-8 détecté comme prévu: {non_utf8[0]}"
        )
    else:
        logger.error(f"Test check_project_python_files_encoding : ÉCHEC.")
        logger.error(f"  Attendu: ['{expected_bad_file}']")
        logger.error(f"  Obtenu : {non_utf8}")

    logger.info(f"Répertoire temporaire {temp_dir_check} conservé pour inspection.")
    logger.info("--- FIN DES TESTS POUR check_project_python_files_encoding ---")

    logger.info(
        f"Les répertoires de test {temp_dir_fix} et {temp_dir_check} sont conservés pour inspection manuelle."
    )
