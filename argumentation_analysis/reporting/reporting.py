import jinja2
import os

def render_markdown_report(template_path: str, data: dict) -> str:
    """
    Charge un template Jinja2, le remplit avec les données fournies et retourne le contenu rendu.

    :param template_path: Chemin vers le fichier template.
    :param data: Dictionnaire contenant les données à insérer dans le template.
    :return: Une chaîne de caractères contenant le rapport en Markdown.
    """
    # Configuration de l'environnement Jinja2 pour charger les templates depuis le système de fichiers
    template_dir = os.path.dirname(template_path)
    template_loader = jinja2.FileSystemLoader(template_dir)
    jinja_env = jinja2.Environment(loader=template_loader, autoescape=True)

    # Chargement du template
    template_file = os.path.basename(template_path)
    template = jinja_env.get_template(template_file)

    # Rendu du template avec les données
    rendered_output = template.render(data)
    
    return rendered_output