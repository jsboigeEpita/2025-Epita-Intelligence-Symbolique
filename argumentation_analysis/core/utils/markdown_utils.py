# -*- coding: utf-8 -*-
"""
Utilitaires pour la manipulation de Markdown et sa conversion en HTML.
"""

from pathlib import Path
from typing import Optional
import logging
import re
import markdown  # type: ignore

# Importation des fonctions de chargement nécessaires
from .file_loaders import load_text_file

# Logger spécifique pour ce module
markdown_logger = logging.getLogger("App.ProjectCore.MarkdownUtils")
if not markdown_logger.handlers and not markdown_logger.propagate:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    markdown_logger.addHandler(handler)
    markdown_logger.setLevel(logging.INFO)


def save_markdown_to_html(markdown_content: str, output_path: Path) -> bool:
    """
    Convertit une chaîne de contenu Markdown en HTML et sauvegarde le résultat dans un fichier.
    Le document HTML généré inclut un style CSS de base pour une meilleure lisibilité.
    Les extensions Markdown 'tables' et 'fenced_code' sont activées.
    Crée les répertoires parents si nécessaire.
    """
    markdown_logger.info(
        f"Conversion du Markdown en HTML et sauvegarde vers {output_path}"
    )
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        html_content = markdown.markdown(
            markdown_content, extensions=["tables", "fenced_code"]
        )

        html_document = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{output_path.stem}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #2c3e50;
                    margin-top: 24px;
                    margin-bottom: 16px;
                }}
                h1 {{
                    font-size: 2.5em;
                    border-bottom: 1px solid #eaecef;
                    padding-bottom: 0.3em;
                }}
                h2 {{
                    font-size: 2em;
                    border-bottom: 1px solid #eaecef;
                    padding-bottom: 0.3em;
                }}
                h3 {{
                    font-size: 1.5em;
                }}
                h4 {{
                    font-size: 1.25em;
                }}
                p, ul, ol {{
                    margin-bottom: 16px;
                }}
                a {{
                    color: #0366d6;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                pre {{
                    background-color: #f6f8fa;
                    border-radius: 3px;
                    padding: 16px;
                    overflow: auto;
                }}
                code {{
                    background-color: #f6f8fa;
                    border-radius: 3px;
                    padding: 0.2em 0.4em;
                    font-family: SFMono-Regular, Consolas, Liberation Mono, Menlo, monospace;
                }}
                blockquote {{
                    border-left: 4px solid #dfe2e5;
                    padding: 0 1em;
                    color: #6a737d;
                    margin-left: 0;
                    margin-right: 0;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin-bottom: 16px;
                }}
                table, th, td {{
                    border: 1px solid #dfe2e5;
                }}
                th, td {{
                    padding: 8px 16px;
                    text-align: left;
                }}
                th {{
                    background-color: #f6f8fa;
                }}
                tr:nth-child(even) {{
                    background-color: #f6f8fa;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        with open(output_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(html_document)
        markdown_logger.info(
            f"[OK] Contenu HTML sauvegardé avec succès dans {output_path}"
        )
        return True
    except Exception as e:
        markdown_logger.error(
            f"❌ Erreur lors de la conversion Markdown en HTML ou de la sauvegarde dans {output_path}: {e}",
            exc_info=True,
        )
        return False


def convert_markdown_file_to_html(
    markdown_file_path: Path,
    output_html_path: Path,
    visualization_dir: Optional[Path] = None,
) -> bool:
    """
    Lit un fichier Markdown, le convertit en HTML et le sauvegarde.
    Utilise la fonction save_markdown_to_html pour la conversion et la sauvegarde.
    """
    markdown_logger.info(
        f"Tentative de conversion du fichier Markdown {markdown_file_path} en HTML vers {output_html_path}."
    )

    markdown_content = load_text_file(
        markdown_file_path
    )  # Utilise la fonction importée
    if markdown_content is None:
        markdown_logger.error(
            f"Impossible de lire le contenu du fichier Markdown: {markdown_file_path}"
        )
        return False

    if visualization_dir:
        markdown_logger.debug(
            f"Le répertoire de visualisations {visualization_dir} est fourni mais non utilisé activement dans cette version de la conversion."
        )

    return save_markdown_to_html(markdown_content, output_html_path)


markdown_logger.info("Utilitaires Markdown (MarkdownUtils) définis.")


# #2536 F821: récupérée de project_core/utils/markdown_utils.py (supprimée au
# refactor 9ddcbdd8a alors que deux scripts de scripts/reporting/ l'appellent).
def update_markdown_section(
    file_path: Path,
    section_header: str,
    new_content: str,
    ensure_header_level: Optional[int] = None,
    add_if_not_found: bool = True,
    replace_entire_section: bool = True,
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
    markdown_logger.info(
        f"Tentative de mise à jour de la section '{section_header}' dans le fichier {file_path}"
    )

    if not file_path.exists() or not file_path.is_file():
        markdown_logger.error(
            f"Fichier Markdown non trouvé ou n'est pas un fichier: {file_path}"
        )
        return False

    try:
        original_content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        markdown_logger.error(
            f"Erreur lors de la lecture du fichier Markdown {file_path}: {e}",
            exc_info=True,
        )
        return False

    # Préparer le regex pour trouver l'en-tête de section.
    # Échapper les caractères spéciaux de Markdown dans section_header pour le regex.
    # Gérer les différents niveaux d'en-tête (par exemple, #, ##, ###)
    header_level_match = re.match(r"^(#+)\s+", section_header)
    if not header_level_match:
        markdown_logger.error(
            f"L'en-tête de section '{section_header}' ne commence pas par des '#'. Format invalide."
        )
        return False

    actual_header_level = len(header_level_match.group(1))
    header_text_to_match = re.escape(section_header[actual_header_level:].strip())

    if ensure_header_level is not None and actual_header_level != ensure_header_level:
        markdown_logger.warning(
            f"L'en-tête fourni '{section_header}' (niveau {actual_header_level}) "
            f"ne correspond pas au niveau d'en-tête attendu {ensure_header_level}. Section non mise à jour."
        )
        # Si add_if_not_found est True, on pourrait vouloir forcer le niveau de l'en-tête ajouté.
        # Pour l'instant, on ne met pas à jour si le niveau de l'en-tête de recherche ne correspond pas.
        if (
            not add_if_not_found
        ):  # Si on n'ajoute pas, et que le niveau ne correspond pas, c'est un échec.
            return False

    # Regex pour trouver l'en-tête et capturer son niveau
    # Ex: ^(#{2})\s+Mon En-tête\s*$ pour ## Mon En-tête
    # Le \s* à la fin permet des espaces après l'en-tête avant la fin de ligne.
    section_pattern_str = (
        r"^(#{" + str(actual_header_level) + r"})\s+" + header_text_to_match + r"\s*$"
    )
    section_pattern = re.compile(section_pattern_str, re.MULTILINE)

    match = section_pattern.search(original_content)

    updated_text = original_content

    if match:
        markdown_logger.info(f"Section '{section_header}' trouvée dans {file_path}.")
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
            full_new_section_content = (
                f"{section_header.strip()}\n\n{new_content.strip()}\n"
            )

            # Remplacer l'ancienne section
            updated_text = (
                original_content[:start_index]
                + full_new_section_content
                + original_content[end_index:]
            )
            markdown_logger.debug(
                f"Section remplacée. Début: {start_index}, Fin: {end_index}"
            )
        else:  # Insérer après l'en-tête
            insert_point = match.end()
            # S'assurer qu'il y a un saut de ligne après l'en-tête avant d'insérer
            if original_content[insert_point:].startswith("\n"):
                insert_point += 1  # Après le premier \n
            else:  # Ajouter un \n si ce n'est pas le cas (en-tête sur une ligne sans contenu direct après)
                new_content = "\n" + new_content

            updated_text = (
                original_content[:insert_point]
                + new_content.strip()
                + "\n"
                + original_content[insert_point:]
            )
            markdown_logger.debug(
                f"Contenu inséré après l'en-tête au point: {insert_point}"
            )

    elif add_if_not_found:
        markdown_logger.info(
            f"Section '{section_header}' non trouvée. Ajout à la fin du fichier {file_path}."
        )
        # S'assurer qu'il y a des sauts de ligne avant d'ajouter la nouvelle section
        separator = (
            "\n\n"
            if not original_content.endswith("\n\n")
            else ("\n" if not original_content.endswith("\n") else "")
        )

        # Utiliser ensure_header_level pour l'en-tête ajouté si fourni, sinon le niveau de section_header
        header_to_add = section_header.strip()
        if (
            ensure_header_level is not None
            and actual_header_level != ensure_header_level
        ):
            header_to_add = (
                ("#" * ensure_header_level)
                + " "
                + section_header[actual_header_level:].strip()
            )

        full_new_section_content = (
            f"{separator}{header_to_add}\n\n{new_content.strip()}\n"
        )
        updated_text = original_content + full_new_section_content
    else:
        markdown_logger.info(
            f"Section '{section_header}' non trouvée et add_if_not_found est False. Fichier non modifié."
        )
        return False  # Aucune modification effectuée

    if updated_text != original_content:
        try:
            file_path.write_text(updated_text, encoding="utf-8")
            markdown_logger.info(
                f"Fichier Markdown {file_path} mis à jour avec succès."
            )
            return True
        except Exception as e:
            markdown_logger.error(
                f"Erreur lors de l'écriture des modifications dans {file_path}: {e}",
                exc_info=True,
            )
            return False
    else:
        markdown_logger.info(
            f"Aucune modification n'était nécessaire pour le fichier {file_path} concernant la section '{section_header}'."
        )
        return False  # Peut être True si on considère "pas de modif nécessaire" comme un succès. Pour l'instant False.
