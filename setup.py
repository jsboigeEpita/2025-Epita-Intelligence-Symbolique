from setuptools import setup, find_packages
import os

# Version du package
__version__ = "0.1.0"

# Fonction pour parser requirements.txt
def parse_requirements_txt(filename='requirements.txt'):
    """
    Assurez-vous que cette fonction ne lit que les noms des paquets,
    en ignorant les commentaires, les options et les marqueurs.
    """
    # Exclusions pour éviter les conflits de dépendances directes/indirectes
    # ou les paquets qui sont mieux gérés d'une autre manière.
    # Un bon exemple est `semantic-kernel` qui peut avoir une version très spécifique
    # nécessaire pour le projet mais qui pourrait entrer en conflit avec d'autres.
    # 'uvicorn[standard]' doit être simplifié en 'uvicorn'
    exclusions = [
        'semantic-kernel',
        'uvicorn[standard]'  # Le setup ne gère pas les extras comme ça, on met 'uvicorn' à la place
    ]

    # Paquets à ajouter explicitement au lieu de ceux exclus (si nécessaire)
    # par exemple, uvicorn sans l'extra.
    additions = {
        'uvicorn[standard]': 'uvicorn'
    }

    libs = {}
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            # Ignorer les commentaires, les lignes vides et les options
            if not line or line.startswith('#') or line.startswith('-'):
                continue

            # Retirer les commentaires en ligne
            if '#' in line:
                line = line.split('#', 1)[0].strip()

            # Normaliser le nom du paquet et retirer les extras pour les exclusions
            package_name_for_check = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
            
            # Gérer les exclusions de manière plus robuste
            if any(ex in line for ex in exclusions) and not "torch" in line:
                 # Vérifier si on doit ajouter une version modifiée du paquet
                for key, value in additions.items():
                    if key in line:
                        libs[value] = line.replace(key, value)
                continue # On saute la ligne originale

            # Vérifier que le paquet n'est pas déjà dans la liste
            # pour éviter les doublons si une substitution a déjà été faite.
            package_key = package_name_for_check
            if package_key not in libs:
                libs[package_key] = line

    return list(libs.values())

# Charger les dépendances depuis requirements.txt
try:
    dynamic_install_requires = parse_requirements_txt('requirements.txt')
except FileNotFoundError:
    print("AVERTISSEMENT: Le fichier 'requirements.txt' est introuvable. "
          "Installation sans dépendances.")
    dynamic_install_requires = []

# Configuration du package
setup(
    name="argumentation_analysis_project",
    version=__version__,
    author="Votre Nom ou Nom de l'Équipe",
    author_email="votre.email@example.com",
    description="Un projet d'analyse d'argumentation",
    long_description=open('README.md', encoding='utf-8').read() if os.path.exists('README.md') else '',
    long_description_content_type="text/markdown",
    url="https://github.com/votre_nom/votre_projet",
    packages=find_packages(
        exclude=["*.tests", "*.tests.*", "tests.*", "tests",
                 "docs", "examples", "scripts", "archived_scripts"]
    ),
    install_requires=dynamic_install_requires,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
    include_package_data=True,
    package_data={
        '': ['*.json', '*.yml', '*.css', '*.js', '*.html', '*.jinja', '*.txt'],
    },
    entry_points={
        'console_scripts': [
            'analyze_arguments=argumentation_analysis.main:main',
        ],
    },
    # Assurez-vous que les dépendances de test sont dans un fichier-extra
    # pour ne pas être installées en production.
    extras_require={
        'dev': [
            'pytest',
            'pytest-cov',
            'pytest-mock',
            # autres dépendances de développement
        ],
        'docs': [
            'sphinx',
            'sphinx_rtd_theme',
        ]
    },
    # Si votre projet inclut des données non-python, spécifiez-les ici
    # package_data={
    #     'argumentation_analysis': ['data/*.csv'],
    # }
)