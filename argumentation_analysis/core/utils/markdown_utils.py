# -*- coding: utf-8 -*-
"""
Utilitaires pour la manipulation de Markdown et sa conversion en HTML.
"""
from pathlib import Path
from typing import Optional
import logging
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
