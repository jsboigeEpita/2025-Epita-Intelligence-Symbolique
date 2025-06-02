# project_core/dev_utils/encoding_utils.py
import logging
import os

# Configuration du logging pour ce module
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def fix_file_encoding(file_path: str, target_encoding: str = 'utf-8', source_encodings: list = None) -> bool:
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
    logger.info(f"Tentative de correction de l'encodage du fichier : {file_path} vers {target_encoding}")

    if source_encodings is None:
        # Ordre important: utf-8 est strict. windows-1252 (alias cp1252) est un sur-ensemble de iso-8859-1.
        # Mettre windows-1252 avant latin-1/iso-8859-1 peut aider à mieux détecter les caractères spécifiques à Windows.
        source_encodings = ['utf-8', 'windows-1252', 'cp1252', 'iso-8859-1', 'latin-1']
    
    # Nettoyer la liste pour éviter les doublons au cas où des alias sont passés
    cleaned_source_encodings = []
    seen_encodings = set()
    for enc in source_encodings:
        # Normaliser les noms d'encodage courants pour la déduplication
        norm_enc = enc.lower()
        if norm_enc == 'latin1': norm_enc = 'latin-1'
        if norm_enc == 'iso8859-1': norm_enc = 'iso-8859-1'
        
        if norm_enc not in seen_encodings:
            cleaned_source_encodings.append(enc) # Garder le nom original pour `decode`
            seen_encodings.add(norm_enc)
    
    logger.debug(f"Encodages source à essayer (après nettoyage): {cleaned_source_encodings}")

    try:
        with open(file_path, 'rb') as f:
            raw_content = f.read()
    except FileNotFoundError:
        logger.error(f"Fichier non trouvé : {file_path}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier binaire {file_path}: {e}", exc_info=True)
        return False

    decoded_content = None
    used_encoding = None

    for encoding in cleaned_source_encodings: # Utiliser la liste nettoyée
        try:
            decoded_content = raw_content.decode(encoding)
            logger.info(f"Décodage réussi de {file_path} avec l'encodage : {encoding}")
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            logger.debug(f"Échec du décodage de {file_path} avec {encoding}.")
            continue
        except Exception as e: # Autres erreurs potentielles de décodage
            logger.warning(f"Erreur inattendue lors du décodage de {file_path} avec {encoding}: {e}")
            continue

    if decoded_content is None:
        logger.error(f"Impossible de décoder le fichier {file_path} avec les encodages connus: {cleaned_source_encodings}")
        return False

    try:
        # Réencoder vers l'encodage cible
        encoded_content_target = decoded_content.encode(target_encoding)
    except Exception as e:
        logger.error(f"Erreur lors de l'encodage du contenu de {file_path} vers {target_encoding}: {e}", exc_info=True)
        return False

    try:
        with open(file_path, 'wb') as f:
            f.write(encoded_content_target)
        logger.info(f"Fichier corrigé et enregistré en {target_encoding} : {file_path} (décodé depuis {used_encoding})")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'écriture du fichier corrigé {file_path} en {target_encoding}: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    # Section de test simple pour la fonction
    logger.setLevel(logging.DEBUG)
    
    # Créer des fichiers de test
    test_files_content = {
        "test_utf8.txt": "Contenu accentué en UTF-8: éàçùè",
        "test_latin1.txt": "Contenu accentué en Latin-1: éàçùè".encode('latin-1'),
        "test_cp1252.txt": "Contenu accentué en CP1252: éàçùè".encode('cp1252'),
    }
    
    temp_dir = "temp_encoding_tests"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    for filename, content in test_files_content.items():
        file_path = os.path.join(temp_dir, filename)
        logger.info(f"\n--- Création du fichier de test : {file_path} ---")
        try:
            if isinstance(content, str):
                with open(file_path, "w", encoding="utf-8") as f: # Écrire le fichier source UTF-8 en UTF-8
                    f.write(content)
                logger.info(f"Fichier {filename} (str) écrit en UTF-8.")
            else: # bytes
                with open(file_path, "wb") as f:
                    f.write(content)
                # Déterminer l'encodage d'origine pour l'affichage
                original_encoding = "latin-1" if "latin1" in filename else "cp1252" if "cp1252" in filename else "unknown"
                logger.info(f"Fichier {filename} (bytes) écrit avec encodage brut (simulant {original_encoding}).")

            success = fix_file_encoding(file_path)
            if success:
                logger.info(f"Correction de {filename} terminée. Vérification du contenu:")
                with open(file_path, "r", encoding="utf-8") as f:
                    final_content = f.read()
                    logger.info(f"Contenu lu en UTF-8: {final_content}")
                    # Vérification simple
                    if "Contenu accentué" in final_content and "éàçùè" in final_content:
                        logger.info(f"Vérification pour {filename} : OK")
                    else:
                        logger.error(f"Vérification pour {filename} : ÉCHEC. Contenu inattendu.")
            else:
                logger.error(f"Échec de la correction pour {filename}.")
        except Exception as e:
            logger.error(f"Erreur lors du test de {filename}: {e}", exc_info=True)
        finally:
            # Nettoyage
            if os.path.exists(file_path):
                # os.remove(file_path)
                logger.info(f"Fichier de test {file_path} conservé pour inspection.")


    # Test avec un fichier qui n'existe pas
    logger.info("\n--- Test avec un fichier inexistant ---")
    fix_file_encoding("fichier_inexistant_pour_test.txt")

    # Nettoyage du répertoire temporaire
    # import shutil
    # if os.path.exists(temp_dir):
    #     shutil.rmtree(temp_dir)
    #     logger.info(f"Répertoire temporaire {temp_dir} supprimé.")
    logger.info(f"Répertoire temporaire {temp_dir} conservé pour inspection.")