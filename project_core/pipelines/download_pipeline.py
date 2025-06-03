"""
Module pour les pipelines de téléchargement de fichiers, notamment les JARs.

Ce module fournit des fonctions pour orchestrer le téléchargement de fichiers
depuis des URLs distantes vers un répertoire local. Il est conçu pour être
robuste, gérer les erreurs de téléchargement et permettre la reprise ou
le forçage des téléchargements.

Le pipeline principal, `run_download_jars_pipeline`, est spécialisé dans
le téléchargement de fichiers JAR, mais peut être adapté pour d'autres types
de fichiers si nécessaire.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any

try:
    from project_core.utils.network_utils import download_file
except ImportError:
    # Gérer le cas où le script est exécuté dans un contexte où project_core n'est pas dans PYTHONPATH
    # Ceci est plus pour la robustesse, en utilisation normale, l'import devrait fonctionner.
    logging.error("Impossible d'importer download_file depuis project_core.utils.network_utils.")
    raise

def run_download_jars_pipeline(
    jars_to_download: List[Dict[str, Any]],
    destination_dir: Path,
    force_download: bool = False
) -> bool:
    """
    Exécute le pipeline de téléchargement pour une liste de fichiers JAR.

    Cette fonction orchestre le téléchargement de plusieurs fichiers JAR,
    en utilisant :func:`project_core.utils.network_utils.download_file` pour chaque JAR.
    Elle gère la vérification de l'existence des fichiers (si `force_download` est False),
    la création du répertoire de destination si nécessaire, et logue le succès ou
    l'échec de chaque téléchargement.

    :param jars_to_download: Une liste de dictionnaires, où chaque dictionnaire
                             contient les informations pour un JAR à télécharger.
                             Chaque dictionnaire doit avoir les clés :
                             - "name": (str) Nom du fichier local.
                             - "url": (str) URL de téléchargement.
                             - "expected_size": (int, optionnel) Taille attendue en octets.
                                                None si non vérifiée.
    :type jars_to_download: List[Dict[str, Any]]
    :param destination_dir: Le chemin du répertoire où les JARs seront téléchargés.
    :type destination_dir: pathlib.Path
    :param force_download: Si True, télécharge les fichiers même s'ils existent déjà.
                           Si False, saute le téléchargement si le fichier existe.
                           Par défaut à False.
    :type force_download: bool
    :return: True si tous les JARs configurés ont été traités avec succès
             (téléchargés ou déjà existants et `force_download` était False),
             False si au moins un téléchargement a échoué ou si une configuration
             de JAR était invalide.
    :rtype: bool
    :raises ImportError: Si `project_core.utils.network_utils.download_file`
                         ne peut pas être importé (ce qui interrompt l'exécution
                         avant l'appel de cette fonction si l'import initial échoue).
    :raises OSError: Peut être levée par `destination_dir.mkdir()` si la création
                     du répertoire échoue pour des raisons de permissions ou autres
                     problèmes système.
                     Peut également être levée par les opérations sur `Path` si les
                     chemins sont invalides ou inaccessibles.
    """
    # Vérification initiale des paramètres
    if not jars_to_download:
        logging.info("Aucun JAR n'est configuré pour le téléchargement dans le pipeline.")
        return True # Considéré comme un succès car il n'y avait rien à faire.

    # Création du répertoire de destination s'il n'existe pas.
    # Peut lever OSError en cas de problème (ex: permissions).
    try:
        destination_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logging.error(f"Impossible de créer le répertoire de destination {destination_dir}: {e}")
        raise # Propage l'exception car c'est une condition bloquante.
    
    logging.info(f"Début du pipeline de téléchargement des JARs vers {destination_dir}.")

    all_successful = True  # Indicateur global du succès de tous les téléchargements
    jars_processed_count = 0 # Compteur pour les JARs traités (téléchargés ou skippés car existants)

    # Itération sur chaque JAR à télécharger
    for jar_info in jars_to_download:
        jar_name = jar_info.get("name")
        jar_url = jar_info.get("url")
        expected_size = jar_info.get("expected_size") # Peut être None

        # Validation des informations minimales pour un JAR
        if not jar_name or not jar_url:
            logging.warning(f"Informations incomplètes pour un JAR (nom ou URL manquant): {jar_info}. Ce JAR est ignoré.")
            all_successful = False # Marquer comme échec partiel car une configuration est invalide
            continue # Passer au JAR suivant

        destination_file_path = destination_dir / jar_name

        # Vérification de l'existence du fichier et de l'option force_download
        if not force_download and destination_file_path.exists():
            # Si le fichier existe et qu'on ne force pas le téléchargement, on le saute.
            logging.info(f"Le fichier {jar_name} existe déjà dans {destination_dir} et force_download est False. Skip.")
            jars_processed_count += 1
            continue

        # Tentative de téléchargement du fichier
        logging.info(f"Téléchargement de {jar_name} depuis {jar_url} vers {destination_file_path}...")
        try:
            success = download_file(
                url=jar_url,
                destination_path=destination_file_path,
                expected_size=expected_size
            )
        except Exception as e: # Capture générique des erreurs de download_file
            logging.error(f"Une erreur inattendue est survenue lors du téléchargement de {jar_name}: {e}")
            success = False # Marquer ce téléchargement spécifique comme un échec

        if success:
            logging.info(f"✅ {jar_name} téléchargé avec succès dans {destination_file_path}.")
            jars_processed_count += 1
        else:
            logging.error(f"❌ Échec du téléchargement de {jar_name} depuis {jar_url}.")
            all_successful = False
            # Note: Le pipeline continue avec les autres JARs même en cas d'échec
            # d'un téléchargement individuel pour maximiser les chances de récupérer
            # les autres fichiers.

    # Log final basé sur le succès global et le nombre de JARs traités
    if all_successful:
        if jars_processed_count == len(jars_to_download):
            logging.info("✅ Tous les JARs configurés ont été traités avec succès.")
        elif jars_processed_count > 0 :
             logging.info(f"✅ {jars_processed_count}/{len(jars_to_download)} JARs traités avec succès (certains skippés car déjà présents ou configurations invalides ignorées).")
        elif not jars_to_download: # Cas où la liste initiale était vide
             logging.info("Aucun JAR n'était configuré pour le téléchargement.")
        else: # jars_to_download n'est pas vide, mais jars_processed_count est 0 et all_successful est True
              # Cela signifie que tous les JARs avaient des configurations invalides.
             logging.warning("Aucun JAR n'a été traité avec succès en raison de configurations invalides pour tous les éléments.")
    else:
        logging.error(f"❌ Échec du traitement d'un ou plusieurs JARs. {jars_processed_count}/{len(jars_to_download)} JARs traités avec un certain succès (téléchargés ou skippés).")

    return all_successful

if __name__ == '__main__':
    # Section pour des tests rapides du module (optionnel)
    # Configuration du logging pour les tests directs
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(module)s.%(funcName)s: %(message)s',
        datefmt='%H:%M:%S'
    )

    # Créer un répertoire de test temporaire
    test_dir = Path(__file__).parent.parent.parent / "temp_test_downloads"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Exemple de JARS (remplacer par des URLs valides pour tester réellement)
    # Pour un test réel, il faudrait des petites URLs valides.
    # Ici, on va simuler avec des URLs qui vont probablement échouer ou des fichiers très petits.
    # Utiliser des URLs de fichiers textes bruts de GitHub pour des tests simples.
    sample_jars = [
        {
            "name": "README_core.md", # Simule un JAR
            "url": "https://raw.githubusercontent.com/user/repo/main/README.md", # Mettre une URL réelle d'un petit fichier
            "expected_size": None
        },
        {
            "name": "non_existent.jar",
            "url": "https://example.com/non_existent.jar",
            "expected_size": None
        }
    ]
    # Remplacer l'URL du README par une URL valide pour un test de succès
    # Par exemple, l'URL brute d'un petit fichier texte sur GitHub.
    # Note: Pour que le test de succès fonctionne, l'URL doit être valide et accessible.
    # Exemple: "https://raw.githubusercontent.com/python/cpython/main/README.rst" (gros fichier)
    # Pour un petit fichier:
    # Trouvez une URL d'un petit fichier texte brut sur GitHub.
    # Par exemple, si vous avez un petit repo public:
    # sample_jars[0]["url"] = "URL_VERS_UN_PETIT_FICHIER_RAW_SUR_GITHUB"


    logging.info(f"Début du test de run_download_jars_pipeline dans {test_dir}")

    # Test 1: Téléchargement normal (s'attendre à un échec partiel si les URLs ne sont pas parfaites)
    logging.info("\n--- Test 1: Téléchargement normal ---")
    success1 = run_download_jars_pipeline(sample_jars, test_dir, force_download=True)
    logging.info(f"Résultat Test 1: {'Succès' if success1 else 'Échec'}")
    if (test_dir / sample_jars[0]["name"]).exists():
        logging.info(f"Fichier {sample_jars[0]['name']} existe après Test 1.")
    else:
        logging.warning(f"Fichier {sample_jars[0]['name']} NON TROUVÉ après Test 1 (vérifiez l'URL).")


    # Test 2: Pas de force, les fichiers (ou certains) devraient exister
    logging.info("\n--- Test 2: Sans force_download (devrait skipper si le premier a réussi) ---")
    success2 = run_download_jars_pipeline(sample_jars, test_dir, force_download=False)
    logging.info(f"Résultat Test 2: {'Succès' if success2 else 'Échec'}")

    # Test 3: Liste de JARs vide
    logging.info("\n--- Test 3: Liste de JARs vide ---")
    success3 = run_download_jars_pipeline([], test_dir)
    logging.info(f"Résultat Test 3 (liste vide): {'Succès' if success3 else 'Échec'}")

    logging.info(f"\nTests terminés. Vérifiez le contenu du répertoire: {test_dir}")
    logging.info("Nettoyage manuel du répertoire de test suggéré si nécessaire.")
    # Pour un vrai test, on supprimerait le répertoire à la fin.
    # import shutil
    # shutil.rmtree(test_dir)
    # logging.info(f"Répertoire de test {test_dir} supprimé.")