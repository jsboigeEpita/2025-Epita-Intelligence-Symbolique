"""
Service de gestion des définitions d'extraits pour l'analyse d'argumentation.

Ce module fournit un service centralisé pour le chargement, la sauvegarde et la gestion
des définitions d'extraits, avec prise en charge du chiffrement et de la validation.
"""

import json
import logging
from pathlib import (
    Path,
)  # Import déjà présent, mais je le laisse pour la clarté du diff
from typing import List, Dict, Any, Tuple, Optional, Union

# Imports absolus pour les tests
import sys
import os

# from pathlib import Path # Redondant, déjà importé plus haut

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from argumentation_analysis.models.extract_definition import (
    ExtractDefinitions,
    SourceDefinition,
    Extract,
)
from argumentation_analysis.services.crypto_service import CryptoService

# Configuration du logging
logger = logging.getLogger("Services.DefinitionService")


class DefinitionService:
    """Service pour la gestion des définitions d'extraits."""

    def __init__(
        self,
        crypto_service: CryptoService,
        config_file: Union[str, Path],  # Modifié pour refléter la réalité potentielle
        fallback_file: Optional[
            Union[str, Path]
        ] = None,  # Modifié pour refléter la réalité potentielle
        default_definitions: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialise le service de définitions.

        :param crypto_service: L'instance du service de chiffrement à utiliser.
        :type crypto_service: CryptoService
        :param config_file: Chemin vers le fichier de configuration principal
                            (peut être chiffré ou JSON brut).
        :type config_file: Union[str, Path]
        :param fallback_file: Chemin optionnel vers un fichier de configuration JSON
                              de secours, utilisé si le fichier principal échoue.
        :type fallback_file: Optional[Union[str, Path]]
        :param default_definitions: Liste optionnelle de dictionnaires de définitions
                                    à utiliser si aucun fichier ne peut être chargé.
        :type default_definitions: Optional[List[Dict[str, Any]]]
        """
        self.crypto_service = crypto_service
        self.config_file = config_file  # Peut être une chaîne ou un Path
        self.fallback_file = fallback_file  # Peut être une chaîne ou un Path
        self.default_definitions = default_definitions or []
        self.logger = logger

        self.logger.info(
            f"Service de définitions initialisé avec fichier principal: {config_file}"
        )
        if fallback_file:
            self.logger.info(f"Fichier de secours configuré: {fallback_file}")

    def load_definitions(self) -> Tuple[ExtractDefinitions, Optional[str]]:
        """
        Charge les définitions d'extraits à partir du fichier de configuration.

        Tente de charger depuis le fichier principal (`self.config_file`).
        Si chiffré et `crypto_service` activé, déchiffre et décompresse.
        Si le fichier principal échoue ou n'existe pas, tente de charger depuis
        `self.fallback_file` (JSON brut). Si tout échoue, utilise
        `self.default_definitions`.

        :return: Un tuple contenant un objet `ExtractDefinitions` et un message d'erreur optionnel.
        :rtype: Tuple[ExtractDefinitions, Optional[str]]
        """
        definitions_list = []
        error_message = None

        # S'assurer que config_file est un Path pour les opérations
        config_file_path = Path(self.config_file)

        # Essayer de charger depuis le fichier principal
        if config_file_path.exists():
            try:
                if self.crypto_service.is_encryption_enabled():
                    # Fichier chiffré
                    with open(config_file_path, "rb") as f:
                        encrypted_data = f.read()

                    definitions_list = self.crypto_service.decrypt_and_decompress_json(
                        encrypted_data
                    )

                    if definitions_list:
                        self.logger.info(
                            f"[OK] Définitions chargées depuis le fichier chiffré {config_file_path.name}"
                        )
                    else:
                        error_message = (
                            f"Échec du déchiffrement de {config_file_path.name}"
                        )
                        self.logger.error(error_message)
                else:
                    # Fichier JSON non chiffré
                    with open(config_file_path, "r", encoding="utf-8") as f:
                        definitions_list = json.load(f)

                    self.logger.info(
                        f"[OK] Définitions chargées depuis {config_file_path.name}"
                    )
            except Exception as e:
                error_message = (
                    f"Erreur lors du chargement de {config_file_path.name}: {str(e)}"
                )
                self.logger.error(error_message)
        else:
            error_message = f"Le fichier {config_file_path.name} n'existe pas"
            self.logger.warning(error_message)

        # Si échec ou pas de définitions, essayer le fichier de secours
        fallback_file_path = Path(self.fallback_file) if self.fallback_file else None
        if (
            (not definitions_list or error_message)
            and fallback_file_path
            and fallback_file_path.exists()
        ):
            try:
                with open(fallback_file_path, "r", encoding="utf-8") as f:
                    definitions_list = json.load(f)

                self.logger.info(
                    f"[OK] Définitions chargées depuis le fichier de secours {fallback_file_path.name}"
                )
                error_message = None  # Erreur principale gérée, le secours a fonctionné
            except Exception as e:
                # Conserver le message d'erreur original si existant, sinon utiliser celui du fallback
                new_fallback_error = f"Erreur lors du chargement du fichier de secours {fallback_file_path.name}: {str(e)}"
                if error_message:
                    self.logger.error(
                        f"{error_message}. {new_fallback_error}"
                    )  # Log les deux erreurs
                else:
                    error_message = new_fallback_error  # L'erreur principale devient celle du fallback
                    self.logger.error(error_message)

        # Si toujours rien, utiliser les définitions par défaut
        if not definitions_list:
            definitions_list = self.default_definitions
            log_message = "Aucune définition trouvée ou erreur de chargement persistante, utilisation des définitions par défaut."
            if error_message:  # Si une erreur précédente a été loggée
                self.logger.warning(
                    f"{log_message} (Erreur précédente: {error_message})"
                )
                # Mettre à jour le message d'erreur pour refléter l'utilisation des définitions par défaut
                error_message = f"Utilisation des définitions par défaut. (Erreur précédente: {error_message})"
            else:  # Si aucune définition n'a été trouvée sans erreur explicite
                error_message = "Aucune définition trouvée, utilisation des définitions par défaut."  # Pour info interne
                self.logger.warning(log_message)

            self.logger.info(
                f"Utilisation des définitions par défaut ({len(definitions_list)} sources)"
            )

        # Convertir en modèle ExtractDefinitions
        # Gérer le cas où definitions_list pourrait être None ou pas une liste après toutes les tentatives
        if not isinstance(definitions_list, list):
            self.logger.error(
                f"Les données finales pour les définitions ne sont pas une liste (type: {type(definitions_list)}). Initialisation avec des définitions vides."
            )
            definitions_list = []
            if not error_message:  # S'il n'y a pas déjà une erreur plus spécifique
                error_message = "Les données de définition finales étaient invalides."

        extract_definitions = ExtractDefinitions.from_dict_list(definitions_list)

        if (
            error_message
        ):  # Log final de l'erreur si une s'est produite et n'a pas été résolue par un fallback
            self.logger.info(
                f"Processus de chargement des définitions terminé avec message: {error_message}"
            )

        return extract_definitions, error_message

    def save_definitions(
        self, definitions: ExtractDefinitions
    ) -> Tuple[bool, Optional[str]]:
        """
        Sauvegarde les définitions d'extraits dans le fichier de configuration.

        Convertit l'objet `ExtractDefinitions` en liste de dictionnaires.
        Si le chiffrement est activé via `crypto_service`, chiffre et compresse
        les données avant de les écrire dans `self.config_file`. Sinon, sauvegarde
        en JSON brut. En cas d'échec, tente de sauvegarder dans `self.fallback_file`
        (en JSON brut uniquement).

        :param definitions: L'objet `ExtractDefinitions` à sauvegarder.
        :type definitions: ExtractDefinitions
        :return: Un tuple contenant un booléen indiquant le succès de l'opération
                 et un message d'erreur optionnel en cas d'échec.
        :rtype: Tuple[bool, Optional[str]]
        """
        success = False
        error_message = None

        # Convertir en liste de dictionnaires
        definitions_list = definitions.to_dict_list()

        # S'assurer que config_file est un Path pour les opérations
        config_file_path = Path(self.config_file)

        # Essayer de sauvegarder dans le fichier principal
        try:
            config_file_path.parent.mkdir(parents=True, exist_ok=True)

            if self.crypto_service.is_encryption_enabled():
                # Fichier chiffré
                encrypted_data = self.crypto_service.encrypt_and_compress_json(
                    definitions_list
                )

                if encrypted_data:
                    with open(config_file_path, "wb") as f:
                        f.write(encrypted_data)

                    self.logger.info(
                        f"[OK] Définitions sauvegardées dans le fichier chiffré {config_file_path.name}"
                    )
                    success = True
                else:
                    error_message = "Échec du chiffrement des définitions"
                    self.logger.error(error_message)
            else:
                # Fichier JSON non chiffré
                with open(config_file_path, "w", encoding="utf-8") as f:
                    json.dump(definitions_list, f, indent=2, ensure_ascii=False)

                self.logger.info(
                    f"[OK] Définitions sauvegardées dans {config_file_path.name}"
                )
                success = True
        except Exception as e:
            error_message = (
                f"Erreur lors de la sauvegarde dans {config_file_path.name}: {str(e)}"
            )
            self.logger.error(error_message)

        # Si échec, essayer le fichier de secours
        fallback_file_path = Path(self.fallback_file) if self.fallback_file else None
        if not success and fallback_file_path:
            try:
                fallback_file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(fallback_file_path, "w", encoding="utf-8") as f:
                    json.dump(definitions_list, f, indent=2, ensure_ascii=False)

                self.logger.info(
                    f"[OK] Définitions sauvegardées dans le fichier de secours {fallback_file_path.name}"
                )
                success = True
                error_message = (
                    None  # Effacer le message d'erreur précédent si le secours réussit
                )
            except Exception as e:
                # Conserver le message d'erreur original si celui-ci est plus pertinent,
                # sinon mettre à jour avec l'erreur du fallback.
                new_error_message = f"Erreur lors de la sauvegarde dans le fichier de secours {fallback_file_path.name}: {str(e)}"
                if (
                    error_message is None
                ):  # S'il n'y avait pas d'erreur avant (improbable ici mais par sécurité)
                    error_message = new_error_message
                else:  # Ajouter la nouvelle erreur à la précédente
                    error_message += f" | {new_error_message}"
                self.logger.error(new_error_message)

        return success, error_message

    def export_definitions_to_json(
        self, definitions: ExtractDefinitions, output_path: Union[str, Path]
    ) -> Tuple[bool, str]:
        """
        Exporte les définitions d'extraits vers un fichier JSON non chiffré.

        :param definitions: L'objet `ExtractDefinitions` à exporter.
        :type definitions: ExtractDefinitions
        :param output_path: Le chemin du fichier de sortie JSON (chaîne ou Path).
        :type output_path: Union[str, Path]
        :return: Un tuple contenant un booléen indiquant le succès de l'exportation
                 et un message (succès ou erreur).
        :rtype: Tuple[bool, str]
        """
        output_file_path = Path(output_path)
        try:
            # Convertir en liste de dictionnaires
            definitions_list = definitions.to_dict_list()

            # Créer le répertoire parent si nécessaire
            output_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Écrire dans le fichier
            with open(output_file_path, "w", encoding="utf-8") as f:
                json.dump(definitions_list, f, indent=2, ensure_ascii=False)

            self.logger.info(f"[OK] Définitions exportées vers {output_file_path}")
            return True, f"[OK] Définitions exportées vers {output_file_path}"
        except Exception as e:
            error_message = (
                f"❌ Erreur lors de l'exportation vers {output_file_path}: {str(e)}"
            )
            self.logger.error(error_message)
            return False, error_message

    def import_definitions_from_json(
        self, input_path: Union[str, Path]
    ) -> Tuple[bool, Union[ExtractDefinitions, str]]:
        """
        Importe les définitions d'extraits depuis un fichier JSON non chiffré.

        :param input_path: Le chemin du fichier d'entrée JSON (chaîne ou Path).
        :type input_path: Union[str, Path]
        :return: Un tuple contenant un booléen indiquant le succès de l'importation
                 et soit l'objet `ExtractDefinitions` importé, soit un message d'erreur (str).
        :rtype: Tuple[bool, Union[ExtractDefinitions, str]]
        """
        input_file_path = Path(input_path)
        try:
            # Vérifier que le fichier existe
            if not input_file_path.exists():
                error_message = f"❌ Le fichier {input_file_path} n'existe pas"
                self.logger.error(error_message)
                return False, error_message

            # Lire le fichier
            with open(input_file_path, "r", encoding="utf-8") as f:
                definitions_list = json.load(f)

            # Convertir en modèle ExtractDefinitions
            extract_definitions = ExtractDefinitions.from_dict_list(definitions_list)

            self.logger.info(f"[OK] Définitions importées depuis {input_file_path}")
            return True, extract_definitions
        except json.JSONDecodeError as e:
            error_message = f"❌ Erreur de format JSON dans {input_file_path}: {str(e)}"
            self.logger.error(error_message)
            return False, error_message
        except Exception as e:
            error_message = (
                f"❌ Erreur lors de l'importation depuis {input_file_path}: {str(e)}"
            )
            self.logger.error(error_message)
            return False, error_message

    def validate_definitions(
        self, definitions: ExtractDefinitions
    ) -> Tuple[bool, List[str]]:
        """
        Valide la structure et les champs requis des définitions d'extraits.

        Vérifie la présence des champs obligatoires pour chaque source et chaque extrait
        au sein des sources (par exemple, `source_name`, `extract_name`, `start_marker`, `end_marker`).

        :param definitions: L'objet `ExtractDefinitions` à valider.
        :type definitions: ExtractDefinitions
        :return: Un tuple contenant un booléen indiquant si les définitions sont valides
                 et une liste des messages d'erreur trouvés.
        :rtype: Tuple[bool, List[str]]
        """
        errors = []

        # Vérifier chaque source
        for i, source in enumerate(definitions.sources):
            # Vérifier les champs obligatoires de la source
            if not source.source_name:
                errors.append(f"Source #{i+1}: Nom de source manquant")

            if not source.source_type:
                errors.append(
                    f"Source '{source.source_name or f'#{i+1}'}': Type de source manquant"
                )

            if not source.schema:
                errors.append(
                    f"Source '{source.source_name or f'#{i+1}'}': Schéma manquant"
                )

            # host_parts peut être vide pour certains types de source (ex: local file)
            # if not source.host_parts:
            #     errors.append(f"Source '{source.source_name or f'#{i+1}'}': Parties d'hôte manquantes")

            if not source.path:
                errors.append(
                    f"Source '{source.source_name or f'#{i+1}'}': Chemin manquant"
                )

            # Vérifier chaque extrait
            for j, extract in enumerate(source.extracts):
                # Vérifier les champs obligatoires de l'extrait
                if not extract.extract_name:
                    errors.append(
                        f"Source '{source.source_name or f'#{i+1}'}', Extrait #{j+1}: Nom d'extrait manquant"
                    )

                if not extract.start_marker:
                    errors.append(
                        f"Source '{source.source_name or f'#{i+1}'}', Extrait '{extract.extract_name or f'#{j+1}'}': Marqueur de début manquant"
                    )

                if not extract.end_marker:
                    errors.append(
                        f"Source '{source.source_name or f'#{i+1}'}', Extrait '{extract.extract_name or f'#{j+1}'}': Marqueur de fin manquant"
                    )

        return len(errors) == 0, errors
