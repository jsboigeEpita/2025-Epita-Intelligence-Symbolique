# -*- coding: utf-8 -*-
"""
Utilitaires réseau pour le projet.

Ce module fournit des fonctions pour effectuer des opérations réseau,
principalement le téléchargement de fichiers depuis des URLs.
Il gère les exceptions courantes et permet de vérifier l'intégrité
des fichiers téléchargés via leur taille.
"""
import logging
import os
from pathlib import Path
import requests
from typing import Optional

logger = logging.getLogger(__name__)

def download_file(url: str, destination_path: Path, expected_size: Optional[int] = None) -> bool:
    """
    Télécharge un fichier depuis une URL et le sauvegarde à destination_path.

    Gère les erreurs de requête HTTP, les problèmes d'écriture de fichier et
    vérifie optionnellement la taille du fichier téléchargé.

    :param url: L'URL du fichier à télécharger.
    :type url: str
    :param destination_path: Le chemin (objet Path) où sauvegarder le fichier.
                             Le répertoire parent sera créé s'il n'existe pas.
    :type destination_path: Path
    :param expected_size: La taille attendue du fichier en octets. Si fournie,
                          la taille du fichier téléchargé sera vérifiée.
    :type expected_size: Optional[int], optional
    :return: True si le téléchargement a réussi et si la taille (si vérifiée) correspond,
             False sinon.
    :rtype: bool
    :raises requests.exceptions.RequestException: Si une erreur liée à la requête HTTP survient
                                                  (ex: erreur réseau, code HTTP 4xx/5xx).
    :raises OSError: Si une erreur survient lors de l'écriture du fichier sur le disque
                     ou lors de la suppression d'un fichier partiel.
    """
    try:
        logger.info(f"Début du téléchargement de {url} vers {destination_path}")
        # S'assurer que le répertoire de destination existe
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()  # Lève une HTTPError pour les codes d'erreur HTTP (4xx ou 5xx)
            with open(destination_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): # 8KB chunks
                    if chunk: # Filtrer les keep-alive new chunks
                        f.write(chunk)
        
        actual_size = destination_path.stat().st_size
        logger.info(f"Fichier téléchargé : {destination_path} (Taille : {actual_size} octets)")

        if expected_size is not None:
            if actual_size == expected_size:
                logger.info(f"La taille du fichier téléchargé ({actual_size} octets) correspond à la taille attendue ({expected_size} octets).")
                return True
            else:
                logger.error(f"Erreur de taille : la taille du fichier téléchargé ({actual_size} octets) ne correspond pas à la taille attendue ({expected_size} octets).")
                # Optionnel : supprimer le fichier si la taille ne correspond pas pour éviter d'utiliser un fichier corrompu.
                # try:
                #     os.remove(destination_path)
                #     logger.info(f"Fichier {destination_path} supprimé en raison d'une taille incorrecte.")
                # except OSError as ose:
                #     logger.error(f"Impossible de supprimer le fichier {destination_path} après erreur de taille: {ose}")
                return False
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur de téléchargement (RequestException) depuis {url}: {e}")
        # Nettoyer si le fichier a été partiellement créé
        if destination_path.exists():
             try:
                os.remove(destination_path)
                logger.info(f"Fichier partiel {destination_path} supprimé après RequestException.")
             except OSError as ose: # Erreur lors de la suppression
                logger.error(f"Impossible de supprimer le fichier partiel {destination_path} après RequestException: {ose}")
        return False
    except OSError as e: # Erreurs liées au système de fichiers (écriture, suppression)
        logger.error(f"Erreur d'écriture ou de suppression du fichier {destination_path} (OSError): {e}")
        return False
    except Exception as e: # Capturer toute autre exception non prévue
        logger.error(f"Une erreur inattendue est survenue lors du téléchargement de {url}: {e}")
        if destination_path.exists():
             try:
                os.remove(destination_path)
                logger.info(f"Fichier partiel {destination_path} supprimé après erreur inattendue.")
             except OSError as ose:
                logger.error(f"Impossible de supprimer le fichier partiel {destination_path} après erreur inattendue: {ose}")
        return False

if __name__ == '__main__':
    # Section de test simple pour la fonction download_file
    # Configure le logging basic pour voir les messages d'information et d'erreur
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] %(module)s.%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # --- Test 1: Téléchargement réussi d'un petit fichier ---
    # test_url_small = "https://raw.githubusercontent.com/psf/requests/main/README.md"
    # test_dest_path_small = Path("_test_downloaded_readme.md")
    # # Pour obtenir la taille attendue, on peut télécharger une fois et vérifier, ou utiliser un outil.
    # # Par exemple, `curl -sI https://raw.githubusercontent.com/psf/requests/main/README.md | grep -i content-length`
    # # Pour cet exemple, nous allons la laisser à None pour ne pas faire échouer le test si elle change.
    # test_expected_size_small = None
    
    # logger.info(f"--- Test 1: Téléchargement de {test_url_small} ---")
    # success_small = download_file(test_url_small, test_dest_path_small, test_expected_size_small)
    # if success_small:
    #     logger.info(f"Test 1 réussi. Fichier sauvegardé à {test_dest_path_small} (Taille: {test_dest_path_small.stat().st_size})")
    #     # os.remove(test_dest_path_small) # Nettoyer après le test
    #     # logger.info(f"Fichier de test {test_dest_path_small} supprimé.")
    # else:
    #     logger.error("Test 1 (petit fichier) échoué.")

    # --- Test 2: URL invalide ---
    # logger.info(f"--- Test 2: Téléchargement avec URL invalide ---")
    # invalid_url = "http://invalid.url.thisdoesnotexist/nonexistentfile.zip"
    # invalid_dest_path = Path("_test_invalid_download.zip")
    # success_invalid = download_file(invalid_url, invalid_dest_path)
    # if not success_invalid:
    #     logger.info("Test 2 (URL invalide) a correctement échoué.")
    #     if invalid_dest_path.exists():
    #         logger.error(f"ERREUR: Le fichier {invalid_dest_path} ne devrait pas exister après un échec de téléchargement.")
    #         # os.remove(invalid_dest_path)
    # else:
    #     logger.error("Test 2 (URL invalide) n'a pas échoué comme attendu.")

    # --- Test 3: Taille de fichier incorrecte ---
    # test_url_size_check = "https://raw.githubusercontent.com/psf/requests/main/README.md" # Même URL que test 1
    # test_dest_path_size_check = Path("_test_downloaded_readme_size_check.md")
    # incorrect_expected_size = 10 # Taille manifestement incorrecte
    
    # logger.info(f"--- Test 3: Vérification de taille incorrecte pour {test_url_size_check} ---")
    # success_size_check = download_file(test_url_size_check, test_dest_path_size_check, incorrect_expected_size)
    # if not success_size_check:
    #     logger.info(f"Test 3 (taille incorrecte) a correctement échoué. Fichier à {test_dest_path_size_check} (Taille: {test_dest_path_size_check.stat().st_size if test_dest_path_size_check.exists() else 'N/A'})")
    #     # if test_dest_path_size_check.exists():
    #         # os.remove(test_dest_path_size_check)
    #         # logger.info(f"Fichier de test {test_dest_path_size_check} supprimé.")
    # else:
    #     logger.error("Test 3 (taille incorrecte) n'a pas échoué comme attendu.")
    #     # if test_dest_path_size_check.exists():
    #         # os.remove(test_dest_path_size_check)


    # --- Test 4: Pas de permission d'écriture (plus difficile à simuler de manière portable) ---
    # Pourrait être testé en essayant d'écrire dans un répertoire protégé.
    # logger.info(f"--- Test 4: Tentative d'écriture dans un répertoire sans permission (simulé) ---")
    # no_permission_path = Path("/root/_test_no_permission.txt") # Unix-like, échouera probablement
    # if os.name == 'nt': # Windows
    #     no_permission_path = Path("C:/Windows/System32/config/_test_no_permission.txt") # Devrait échouer
    
    # success_permission = download_file(test_url_small, no_permission_path)
    # if not success_permission:
    #     logger.info(f"Test 4 (pas de permission) a correctement échoué.")
    # else:
    #     logger.error(f"Test 4 (pas de permission) n'a pas échoué comme attendu. Fichier créé à {no_permission_path} ?")

    logger.info("Tous les tests (commentés) de network_utils sont terminés.")
    pass # Les tests sont commentés pour éviter exécution automatique et dépendances externes non garanties