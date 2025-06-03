# -*- coding: utf-8 -*-
"""
Utilitaires pour la manipulation de fichiers et de contenu Markdown.
"""

import logging
import re # Pour la recherche de section
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

def update_markdown_section(
    file_path: Path,
    section_header: str,
    new_content: str,
    ensure_header_level: Optional[int] = None,
    add_if_not_found: bool = True,
    replace_entire_section: bool = True
) -> bool:
    """
    Met à jour une section spécifique dans un fichier Markdown.

    La section est identifiée par son en-tête. Si la section est trouvée,
    son contenu existant peut être remplacé. Si elle n'est pas trouvée,
    la nouvelle section (en-tête + contenu) peut être ajoutée à la fin du fichier.

    Args:
        file_path (Path): Chemin vers le fichier Markdown.
        section_header (str): L'en-tête exact de la section à mettre à jour
                              (par exemple, "## Ma Section Spécifique").
                              Le niveau de l'en-tête (nombre de '#') est important.
        new_content (str): Le nouveau contenu (sans l'en-tête) à insérer pour la section.
        ensure_header_level (Optional[int]): Si fourni, s'assure que l'en-tête
                                             correspond à ce niveau (ex: 2 pour '##').
                                             Si la section est trouvée avec un niveau différent,
                                             elle ne sera pas mise à jour (pour éviter les erreurs).
                                             Si la section n'est pas trouvée et `add_if_not_found` est True,
                                             l'en-tête sera créé avec ce niveau.
        add_if_not_found (bool): Si True et que la section n'est pas trouvée,
                                 l'en-tête et le nouveau contenu sont ajoutés à la fin du fichier.
                                 Si False et non trouvée, le fichier n'est pas modifié.
        replace_entire_section (bool): Si True (défaut), tout le contenu de la section trouvée
                                       (de son en-tête jusqu'à l'en-tête suivant de même niveau ou supérieur,
                                       ou la fin du fichier) est remplacé par `section_header` + `new_content`.
                                       Si False, `new_content` est inséré juste après l'en-tête trouvé,
                                       conservant le contenu original de la section après l'insertion.

    Returns:
        bool: True si le fichier a été mis à jour, False sinon (par exemple, fichier non trouvé,
              section non trouvée et add_if_not_found est False, ou erreur d'écriture).
    """
    logger.info(f"Tentative de mise à jour de la section '{section_header}' dans le fichier {file_path}")

    if not file_path.exists() or not file_path.is_file():
        logger.error(f"Fichier Markdown non trouvé ou n'est pas un fichier: {file_path}")
        return False

    try:
        original_content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier Markdown {file_path}: {e}", exc_info=True)
        return False

    # Préparer le regex pour trouver l'en-tête de section.
    # Échapper les caractères spéciaux de Markdown dans section_header pour le regex.
    # Gérer les différents niveaux d'en-tête (par exemple, #, ##, ###)
    header_level_match = re.match(r'^(#+)\s+', section_header)
    if not header_level_match:
        logger.error(f"L'en-tête de section '{section_header}' ne commence pas par des '#'. Format invalide.")
        return False
    
    actual_header_level = len(header_level_match.group(1))
    header_text_to_match = re.escape(section_header[actual_header_level:].strip())
    
    if ensure_header_level is not None and actual_header_level != ensure_header_level:
        logger.warning(f"L'en-tête fourni '{section_header}' (niveau {actual_header_level}) "
                       f"ne correspond pas au niveau d'en-tête attendu {ensure_header_level}. Section non mise à jour.")
        # Si add_if_not_found est True, on pourrait vouloir forcer le niveau de l'en-tête ajouté.
        # Pour l'instant, on ne met pas à jour si le niveau de l'en-tête de recherche ne correspond pas.
        if not add_if_not_found: # Si on n'ajoute pas, et que le niveau ne correspond pas, c'est un échec.
             return False


    # Regex pour trouver l'en-tête et capturer son niveau
    # Ex: ^(#{2})\s+Mon En-tête\s*$ pour ## Mon En-tête
    # Le \s* à la fin permet des espaces après l'en-tête avant la fin de ligne.
    section_pattern_str = r"^(#{"+str(actual_header_level)+r"})\s+" + header_text_to_match + r"\s*$"
    section_pattern = re.compile(section_pattern_str, re.MULTILINE)
    
    match = section_pattern.search(original_content)
    
    updated_text = original_content

    if match:
        logger.info(f"Section '{section_header}' trouvée dans {file_path}.")
        start_index = match.start()
        
        if replace_entire_section:
            # Trouver la fin de la section : prochain en-tête de même niveau ou supérieur, ou fin du fichier.
            # Regex pour un en-tête de niveau actual_header_level ou moins (plus prioritaire, ex: # ou ## si on cherche ###)
            # (?:^#{1," + str(actual_header_level) + r"}\s+.*$)
            end_pattern_str = r"^(#{1," + str(actual_header_level) + r"}\s+.*)$"
            end_pattern = re.compile(end_pattern_str, re.MULTILINE)
            
            next_match = end_pattern.search(original_content, match.end())
            end_index = next_match.start() if next_match else len(original_content)
            
            # Construire le nouveau contenu de la section (en-tête + nouveau contenu)
            full_new_section_content = f"{section_header.strip()}\n\n{new_content.strip()}\n"
            
            # Remplacer l'ancienne section
            updated_text = original_content[:start_index] + full_new_section_content + original_content[end_index:]
            logger.debug(f"Section remplacée. Début: {start_index}, Fin: {end_index}")
        else: # Insérer après l'en-tête
            insert_point = match.end()
            # S'assurer qu'il y a un saut de ligne après l'en-tête avant d'insérer
            if original_content[insert_point:].startswith('\n'):
                insert_point += 1 # Après le premier \n
            else: # Ajouter un \n si ce n'est pas le cas (en-tête sur une ligne sans contenu direct après)
                new_content = "\n" + new_content
            
            updated_text = original_content[:insert_point] + new_content.strip() + "\n" + original_content[insert_point:]
            logger.debug(f"Contenu inséré après l'en-tête au point: {insert_point}")

    elif add_if_not_found:
        logger.info(f"Section '{section_header}' non trouvée. Ajout à la fin du fichier {file_path}.")
        # S'assurer qu'il y a des sauts de ligne avant d'ajouter la nouvelle section
        separator = "\n\n" if not original_content.endswith("\n\n") else ("\n" if not original_content.endswith("\n") else "")
        
        # Utiliser ensure_header_level pour l'en-tête ajouté si fourni, sinon le niveau de section_header
        header_to_add = section_header.strip()
        if ensure_header_level is not None and actual_header_level != ensure_header_level:
             header_to_add = ("#" * ensure_header_level) + " " + section_header[actual_header_level:].strip()
        
        full_new_section_content = f"{separator}{header_to_add}\n\n{new_content.strip()}\n"
        updated_text = original_content + full_new_section_content
    else:
        logger.info(f"Section '{section_header}' non trouvée et add_if_not_found est False. Fichier non modifié.")
        return False # Aucune modification effectuée

    if updated_text != original_content:
        try:
            file_path.write_text(updated_text, encoding='utf-8')
            logger.info(f"Fichier Markdown {file_path} mis à jour avec succès.")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'écriture des modifications dans {file_path}: {e}", exc_info=True)
            return False
    else:
        logger.info(f"Aucune modification n'était nécessaire pour le fichier {file_path} concernant la section '{section_header}'.")
        return False # Peut être True si on considère "pas de modif nécessaire" comme un succès. Pour l'instant False.