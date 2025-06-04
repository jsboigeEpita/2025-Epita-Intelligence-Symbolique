#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Ce module fournit un pipeline pour la génération d'embeddings à partir de diverses sources de données.

Le pipeline principal, `run_embedding_generation_pipeline`, prend en entrée des
configurations de sources (soit via un fichier chiffré, une chaîne JSON, ou un
fichier JSON non chiffré), récupère le contenu textuel complet pour chaque source si
nécessaire, génère optionnellement des embeddings pour ces textes en utilisant un
modèle spécifié, et sauvegarde les configurations mises à jour (incluant les textes
récupérés) ainsi que les embeddings générés dans des fichiers séparés.

Il gère le chiffrement/déchiffrement des fichiers de configuration et la
sauvegarde des embeddings dans un répertoire structuré. Ce module respecte PEP 257
pour les docstrings et PEP 8 pour le style de code.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
import json
from typing import Optional, List, Dict, Any # Ajout pour Optional, List, Dict, Any

# Assurer que le répertoire racine du projet est dans sys.path
# Ceci est nécessaire si ce module est exécuté directement ou importé par des scripts
# qui ne sont pas dans la racine du projet.
try:
    SCRIPT_DIR = Path(__file__).resolve().parent
    PROJECT_ROOT = SCRIPT_DIR.parent.parent # argumentation_analysis -> project_root
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
except NameError: # __file__ n'est pas défini si exécuté dans un interpréteur interactif par exemple
    PROJECT_ROOT = Path.cwd() # Fallback au répertoire courant
    if str(PROJECT_ROOT) not in sys.path:
         sys.path.insert(0, str(PROJECT_ROOT))


from argumentation_analysis.utils.core_utils.logging_utils import setup_logging
from argumentation_analysis.utils.core_utils.file_utils import load_json_file, sanitize_filename, load_document_content
from argumentation_analysis.ui.file_operations import load_extract_definitions, save_extract_definitions
from argumentation_analysis.ui.utils import get_full_text_for_source
from argumentation_analysis.ui.config import ENCRYPTION_KEY as CONFIG_UI_ENCRYPTION_KEY
from argumentation_analysis.nlp.embedding_utils import get_embeddings_for_chunks, save_embeddings_data

logger = logging.getLogger(__name__)

def run_embedding_generation_pipeline(
    input_config_path: Optional[Path],
    json_string: Optional[str],
    input_json_file_path: Optional[Path],
    output_config_path: Path,
    generate_embeddings_model: Optional[str],
    force_overwrite: bool,
    log_level: str = "INFO",
    passphrase: Optional[str] = None
) -> None:
    """Exécute le pipeline de génération d'embeddings.

    Cette fonction orchestre le chargement des configurations de sources,
    la récupération du texte complet pour chaque source, la génération optionnelle
    d'embeddings, et la sauvegarde des configurations mises à jour et des embeddings.

    Le pipeline effectue les étapes suivantes :
    1.  Initialisation du logging.
    2.  Validation des chemins d'entrée et de sortie.
    3.  Chargement des définitions d'extraits depuis la source spécifiée
        (fichier chiffré, chaîne JSON, ou fichier JSON).
    4.  Pour chaque définition de source :
        a.  Récupération du texte complet si absent.
        b.  Si `generate_embeddings_model` est fourni et le texte complet est disponible,
            génération des embeddings pour le texte.
        c.  Sauvegarde des embeddings générés dans un fichier JSON dédié.
    5.  Sauvegarde des définitions d'extraits mises à jour (potentiellement avec
        les nouveaux textes complets) dans le fichier de configuration de sortie chiffré.

    :param input_config_path: Chemin vers le fichier de configuration chiffré
        d'entrée (.json.gz.enc). Peut être None si `json_string` ou
        `input_json_file_path` est fourni.
    :type input_config_path: Optional[Path]
    :param json_string: Chaîne JSON contenant les définitions d'extraits.
        Peut être None si `input_config_path` ou `input_json_file_path` est fourni.
    :type json_string: Optional[str]
    :param input_json_file_path: Chemin vers un fichier JSON non chiffré
        contenant les définitions d'extraits. Peut être None si `input_config_path`
        ou `json_string` est fourni.
    :type input_json_file_path: Optional[Path]
    :param output_config_path: Chemin vers le fichier de configuration chiffré de sortie.
        Ce fichier contiendra les définitions d'extraits mises à jour.
    :type output_config_path: Path
    :param generate_embeddings_model: Nom du modèle d'embedding à utiliser pour la
        génération. Si None, aucune génération d'embeddings n'est effectuée.
    :type generate_embeddings_model: Optional[str]
    :param force_overwrite: Si True, écrase le fichier de configuration de sortie
        s'il existe déjà.
    :type force_overwrite: bool
    :param log_level: Niveau de logging à utiliser (par exemple, "INFO", "DEBUG").
    :type log_level: str
    :param passphrase: Passphrase (OBSOLÈTE pour la dérivation de clé dans ce
        pipeline, mais conservé pour la signature de la fonction).
    :type passphrase: Optional[str]
    :return: None. La fonction termine par `sys.exit(1)` en cas d'erreur critique.
    :rtype: None
    :raises SystemExit: Si une erreur critique empêche la poursuite du pipeline
        (par exemple, fichier d'entrée manquant, clé de chiffrement absente,
        format de données incorrect).
    :raises json.JSONDecodeError: Si `json_string` est fourni et n'est pas un JSON valide.
    :raises FileNotFoundError: Si un chemin de fichier spécifié pour une source locale
        (via `input_json_file_path` ou dans `source_info['path']`) n'est pas trouvé.
    :raises Exception: D'autres exceptions peuvent être levées par les modules sous-jacents
        (opérations de fichiers, génération d'embeddings, etc.), par exemple
        des erreurs de permission ou des problèmes réseau lors de la récupération
        de contenu distant.
    """
    setup_logging(log_level)
    logger.info("Démarrage du pipeline de génération d'embeddings.")

    # Section 1: Validation des sources d'entrée et du fichier de sortie
    # Commentaire: Cette section valide les arguments d'entrée pour s'assurer
    # qu'au moins une source de configuration est fournie et que les chemins
    # de fichiers spécifiés sont valides et accessibles.
    if input_json_file_path:
        logger.info(f"Utilisation des définitions JSON fournies via fichier: {input_json_file_path}")
    elif json_string:
        logger.info("Utilisation des définitions JSON fournies via chaîne.")
    elif input_config_path:
        logger.info(f"Fichier d'entrée (chiffré): {input_config_path}")
    else:
        logger.error("Aucune source de configuration d'entrée spécifiée (ni --input-config, ni --json-string, ni --input-json-file). Arrêt.")
        sys.exit(1) # Erreur critique: aucune source d'entrée
    logger.info(f"Fichier de configuration de sortie: {output_config_path}")

    # Vérifier l'existence des fichiers d'entrée si spécifiés
    if input_json_file_path and not input_json_file_path.exists():
        logger.error(f"Le fichier d'entrée JSON {input_json_file_path} n'existe pas. Arrêt.")
        sys.exit(1) # Erreur critique: fichier d'entrée JSON manquant
    elif input_config_path and not input_config_path.exists() and not json_string and not input_json_file_path:
         logger.error(f"Le fichier d'entrée chiffré {input_config_path} n'existe pas et aucune autre source (chaîne JSON ou fichier JSON) n'est fournie. Arrêt.")
         sys.exit(1) # Erreur critique: fichier d'entrée chiffré manquant et pas d'alternative

    # Gérer le cas où le fichier de sortie existe déjà
    if output_config_path.exists() and not force_overwrite:
        logger.error(
            f"Le fichier de sortie {output_config_path} existe déjà. Utilisez --force pour l'écraser. Arrêt."
        )
        sys.exit(1) # Erreur critique: conflit de fichier de sortie non résolu
    elif output_config_path.exists() and force_overwrite:
        logger.warning(f"Le fichier de sortie {output_config_path} existe et sera écrasé (--force activé).")

    # S'assurer que le répertoire de sortie existe
    output_config_path.parent.mkdir(parents=True, exist_ok=True)

    # Section 2: Chargement des définitions d'extraits
    # Commentaire: Charge les définitions d'extraits à partir de la source prioritaire:
    # fichier JSON non chiffré, puis chaîne JSON, puis fichier de configuration chiffré.
    # Gère les erreurs de chargement et de format.
    extract_definitions: List[Dict[str, Any]] = []
    encryption_key_to_use = CONFIG_UI_ENCRYPTION_KEY # Clé de chiffrement depuis la configuration de l'UI
    if not encryption_key_to_use:
        logger.error("ENCRYPTION_KEY n'est pas disponible depuis argumentation_analysis.ui.config. Impossible de continuer pour les opérations chiffrées. Arrêt.")
        sys.exit(1) # Erreur critique: clé de chiffrement manquante
    
    # Log informatif sur la clé utilisée (tronquée pour la sécurité)
    logger.info(f"Utilisation de ENCRYPTION_KEY (commençant par '{encryption_key_to_use[:10].decode('utf-8', 'ignore')}') pour les opérations de chiffrement/déchiffrement.")

    # Logique de chargement prioritaire: fichier JSON > chaîne JSON > fichier config chiffré
    if input_json_file_path:
        try:
            logger.info(f"Chargement des définitions d'extraits depuis le fichier JSON non chiffré: {input_json_file_path}...")
            loaded_data = load_json_file(input_json_file_path)
            if isinstance(loaded_data, list):
                extract_definitions = loaded_data
            elif loaded_data is None: # load_json_file retourne None et logue en cas d'erreur
                logger.error(f"Échec du chargement du fichier JSON {input_json_file_path} (détails ci-dessus). Arrêt.")
                sys.exit(1) # Erreur critique: échec du chargement JSON
            else: # Le JSON est valide mais n'est pas une liste
                logger.error(f"Le contenu du fichier JSON {input_json_file_path} n'est pas une liste de définitions. Type trouvé: {type(loaded_data)}. Arrêt.")
                sys.exit(1) # Erreur critique: format JSON incorrect
            logger.info(f"{len(extract_definitions)} définitions d'extraits chargées depuis {input_json_file_path}.")
        except Exception as e: # Capture d'autres exceptions potentielles
            logger.error(f"Erreur inattendue lors du traitement du fichier JSON {input_json_file_path}: {e}. Arrêt.")
            sys.exit(1) # Erreur critique
    elif json_string:
        try:
            logger.info("Chargement des définitions d'extraits depuis la chaîne JSON fournie...")
            loaded_data = json.loads(json_string)
            if not isinstance(loaded_data, list):
                logger.error("La chaîne JSON fournie ne contient pas une liste de définitions. Arrêt.")
                sys.exit(1) # Erreur critique: format JSON incorrect
            extract_definitions = loaded_data
            logger.info(f"{len(extract_definitions)} définitions d'extraits chargées depuis la chaîne JSON.")
        except json.JSONDecodeError as e:
            logger.error(f"Erreur lors du décodage de la chaîne JSON: {e}. Arrêt.")
            sys.exit(1) # Erreur critique: JSON malformé
    elif input_config_path: # Traitement du fichier de configuration chiffré
        try:
            logger.info(f"Chargement et déchiffrement des définitions d'extraits depuis: {input_config_path}...")
            # Utilisation de la clé directement depuis ui.config
            loaded_defs = load_extract_definitions(
                config_file=input_config_path,
                b64_derived_key=encryption_key_to_use
            )
            # load_extract_definitions gère les erreurs internes et peut retourner une liste vide ou des valeurs par défaut.
            # Il est crucial de vérifier si le chargement a réussi.
            # Si le fichier n'existe pas, load_extract_definitions peut retourner une liste vide par défaut.
            # Ce cas est déjà géré par la vérification d'existence plus haut.
            extract_definitions = loaded_defs if loaded_defs is not None else []
            logger.info(f"{len(extract_definitions)} définitions d'extraits chargées et déchiffrées depuis {input_config_path}.")
        except Exception as e: # Erreur pendant le chargement/déchiffrement
            logger.error(f"Erreur majeure lors du chargement ou du déchiffrement de {input_config_path}: {e}. Arrêt.")
            sys.exit(1) # Erreur critique
    else:
        # Ce cas ne devrait pas être atteint grâce aux vérifications initiales, mais par sécurité :
        logger.error("Logique de chargement incohérente: aucune source de configuration n'a été traitée. Arrêt.")
        sys.exit(1)

    # Section 3: Traitement de chaque définition de source
    # Commentaire: Itère sur chaque définition de source. Pour chacune, tente de récupérer
    # le texte complet si absent, puis génère et sauvegarde les embeddings si un modèle
    # est spécifié et que le texte complet est disponible.
    updated_sources_count = 0
    sources_with_errors_count = 0

    for i, source_info in enumerate(extract_definitions):
        source_id = source_info.get('id', f"SourceNonIdentifiée_{i+1}") # ID par défaut si manquant
        logger.info(f"Traitement de la source: {source_id} (Type: {source_info.get('type', 'N/A')}, Chemin/URL: {source_info.get('path', 'N/A')})")

        full_text_content_retrieved_this_run: Optional[str] = None # Pour suivre si le texte a été récupéré dans cette exécution

        # Étape 3a: Récupération du texte complet si absent
        if source_info.get('full_text') and source_info['full_text'].strip():
            logger.info(f"  Le texte complet est déjà présent pour la source {source_id}.")
        else:
            logger.info(f"  Texte complet manquant pour la source {source_id}. Tentative de récupération...")
            try:
                # Déterminer la méthode de récupération (compatibilité avec 'source_type')
                fetch_method = source_info.get("fetch_method", source_info.get("source_type", "unknown"))
                
                if fetch_method == "file":
                    file_path_str = source_info.get("path")
                    if file_path_str:
                        document_path = Path(file_path_str)
                        # Résoudre le chemin relatif par rapport à la racine du projet si nécessaire
                        if not document_path.is_absolute():
                            document_path = (PROJECT_ROOT / file_path_str).resolve()
                        logger.info(f"  Récupération du contenu du fichier local: {document_path}")
                        full_text_content_retrieved_this_run = load_document_content(document_path)
                        if full_text_content_retrieved_this_run is None: # load_document_content logue déjà l'erreur
                             logger.warning(f"  load_document_content n'a pas pu lire {document_path} pour la source {source_id}.")
                    else:
                        logger.error(f"  Champ 'path' manquant pour la source locale de type 'file': {source_id}.")
                elif fetch_method in ["url", "api", "web_page"]: # Autres types gérés par get_full_text_for_source
                    logger.info(f"  Utilisation de get_full_text_for_source pour la source {source_id} (méthode: {fetch_method}).")
                    # `app_config` n'est pas directement disponible ici, on passe None.
                    # `get_full_text_for_source` devrait utiliser les valeurs par défaut de `ui.config`.
                    full_text_content_retrieved_this_run = get_full_text_for_source(source_info, app_config=None)
                else:
                    logger.warning(f"  Méthode de récupération '{fetch_method}' non reconnue pour la source {source_id}.")

                # Mettre à jour source_info si le texte a été récupéré
                if full_text_content_retrieved_this_run:
                    source_info['full_text'] = full_text_content_retrieved_this_run
                    logger.info(f"  Texte complet récupéré et mis à jour pour la source {source_id} (longueur: {len(full_text_content_retrieved_this_run)}).")
                    updated_sources_count += 1
                elif not (source_info.get('full_text') and source_info['full_text'].strip()): # Si toujours pas de texte
                    logger.warning(f"  Impossible de récupérer le texte complet pour la source {source_id} (méthode: {fetch_method}). 'full_text' reste vide ou inchangé.")
                    sources_with_errors_count += 1
            except FileNotFoundError as fnf_err:
                logger.error(f"  Fichier non trouvé lors de la récupération du texte pour la source {source_id}: {fnf_err}")
                sources_with_errors_count += 1
            except Exception as e: # Capturer les autres erreurs pendant la récupération
                logger.error(f"  Erreur générique lors de la récupération du texte pour la source {source_id}: {e}")
                sources_with_errors_count += 1
        
        # Étape 3b & 3c: Génération et sauvegarde des embeddings
        # Condition: modèle spécifié ET texte complet disponible (soit préexistant, soit récupéré)
        if generate_embeddings_model and (source_info.get('full_text') or '').strip():
            current_full_text_for_embedding = source_info['full_text']
            logger.info(f"  Tentative de génération d'embeddings pour la source {source_id} avec le modèle '{generate_embeddings_model}'...")
            try:
                # Simplification: le texte complet est traité comme un seul chunk.
                # Pour une application réelle, un découpage (chunking) plus sophistiqué serait nécessaire.
                text_chunks = [current_full_text_for_embedding]
                embeddings = get_embeddings_for_chunks(text_chunks, generate_embeddings_model)
                
                if embeddings and embeddings[0] is not None: # Vérifier si des embeddings ont été retournés et ne sont pas None
                    logger.info(f"    Embeddings générés: {len(embeddings)} vecteur(s). Dimension du premier: {len(embeddings[0])}.")
                    
                    # Préparation des données à sauvegarder
                    embeddings_data_to_save = {
                        "source_id": source_id,
                        "model_name": generate_embeddings_model,
                        "text_chunks": text_chunks, # Sauvegarde des chunks pour référence
                        "embeddings": embeddings    # Sauvegarde des vecteurs d'embedding
                    }
                    
                    # Définition du chemin de sortie pour les embeddings
                    base_output_dir = output_config_path.parent
                    embeddings_output_dir = base_output_dir / "embeddings_data" # Répertoire dédié pour les embeddings
                    embeddings_output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Nom de fichier sécurisé pour les embeddings
                    sanitized_source_id = sanitize_filename(str(source_id))
                    sanitized_model_name = sanitize_filename(str(generate_embeddings_model))
                    embedding_filename = f"embedding_{sanitized_source_id}_model_{sanitized_model_name}.json"
                    output_path_embeddings = embeddings_output_dir / embedding_filename
                    
                    logger.info(f"    Sauvegarde des embeddings pour la source {source_id} dans: {output_path_embeddings}")
                    if save_embeddings_data(embeddings_data_to_save, output_path_embeddings):
                        logger.info(f"    Embeddings pour {source_id} sauvegardés avec succès.")
                    else: # save_embeddings_data logue déjà l'échec
                        logger.error(f"    Échec de la sauvegarde des embeddings pour {source_id} (détails ci-dessus).")
                else:
                    logger.warning(f"    Aucun embedding valide n'a été généré ou retourné pour la source {source_id} avec le modèle '{generate_embeddings_model}'.")
            except Exception as emb_exc: # Erreur pendant la génération ou sauvegarde des embeddings
                logger.error(f"    Erreur lors de la génération/sauvegarde des embeddings pour la source {source_id} (modèle '{generate_embeddings_model}'): {emb_exc}")
                # Ne pas incrémenter sources_with_errors_count ici, car cela concerne la récupération du texte.
                # On pourrait avoir un compteur séparé pour les erreurs d'embedding.

    logger.info(f"Traitement des sources terminé. {updated_sources_count} sources ont eu leur texte complet mis à jour/récupéré. {sources_with_errors_count} erreurs lors de la récupération de texte.")

    # Section 4: Sauvegarde des définitions d'extraits mises à jour
    # Commentaire: Sauvegarde la liste complète des définitions d'extraits (potentiellement
    # enrichies avec les textes complets) dans le fichier de configuration de sortie chiffré.
    try:
        logger.info(f"Sauvegarde des définitions d'extraits (potentiellement mises à jour) dans {output_config_path}...")
        # `embed_full_text=True` assure que les textes complets (existants ou récupérés) sont inclus dans le fichier de sortie.
        save_success = save_extract_definitions(
            extract_definitions=extract_definitions,
            config_file=output_config_path,
            b64_derived_key=encryption_key_to_use,
            embed_full_text=True
        )
        if save_success:
            logger.info(f"Définitions d'extraits sauvegardées avec succès dans {output_config_path}.")
        else: # save_extract_definitions logue déjà l'échec
            logger.error(f"Échec de la sauvegarde des définitions dans {output_config_path} (détails ci-dessus).")
            # Envisager sys.exit(1) si cette sauvegarde est absolument critique.
    except Exception as e: # Erreur majeure pendant la sauvegarde finale
        logger.error(f"Erreur majeure lors de la tentative de sauvegarde des définitions dans {output_config_path}: {e}")
        sys.exit(1) # Erreur critique

    logger.info("Pipeline de génération d'embeddings terminé avec succès.")

if __name__ == '__main__':
    # Configuration du parser d'arguments pour une exécution en ligne de commande.
    # Cela permet de tester le pipeline ou de l'utiliser comme un outil standalone.
    parser = argparse.ArgumentParser(
        description="Pipeline de génération d'embeddings pour les sources de texte."
    )
    parser.add_argument(
        "--input-config", type=Path, default=None,
        help="Chemin vers le fichier de configuration chiffré d'entrée (.json.gz.enc)."
    )
    parser.add_argument(
        "--json-string", type=str, default=None,
        help="Chaîne JSON contenant les définitions d'extraits."
    )
    parser.add_argument(
        "--input-json-file", type=Path, default=None,
        help="Chemin vers un fichier JSON non chiffré contenant les définitions d'extraits."
    )
    parser.add_argument(
        "--output-config", type=Path, required=True,
        help="Chemin vers le fichier de configuration chiffré de sortie."
    )
    parser.add_argument(
        "--generate-embeddings", type=str, metavar="MODEL_NAME", default=None,
        help="Nom du modèle d'embedding à utiliser."
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Écrase le fichier de sortie s'il existe déjà."
    )
    parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Niveau de verbosité du logging."
    )
    # L'argument passphrase n'est plus utilisé pour la dérivation de clé dans le pipeline lui-même,
    # mais on le garde pour une éventuelle compatibilité si le script lanceur le passe.
    parser.add_argument(
        "--passphrase", type=str, default=None,
        help="Passphrase (OBSOLÈTE pour la dérivation de clé dans ce pipeline)."
    )

    args = parser.parse_args()

    run_embedding_generation_pipeline(
        input_config_path=args.input_config,
        json_string=args.json_string,
        input_json_file_path=args.input_json_file,
        output_config_path=args.output_config,
        generate_embeddings_model=args.generate_embeddings,
        force_overwrite=args.force,
        log_level=args.log_level,
        passphrase=args.passphrase # Passé même si non utilisé activement pour la clé
    )