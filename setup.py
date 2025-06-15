from setuptools import setup, find_packages
import os
import yaml # PyYAML doit être installé (ajoutez 'pyyaml' à environment.yml si besoin)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, 'requirements.txt')

def parse_requirements_txt(file_path):
    """
    Parse requirements.txt pour extraire les dépendances pour install_requires.
    """
    install_requires_list = []
    if not os.path.exists(file_path):
        print(f"AVERTISSEMENT: {file_path} non trouvé. Aucune dépendance ne sera lue.")
        return install_requires_list

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                install_requires_list.append(line)
    return install_requires_list

# Lire les dépendances depuis requirements.txt
dynamic_install_requires = parse_requirements_txt(ENV_FILE)

if not dynamic_install_requires:
    print("AVERTISSEMENT: La liste des dépendances dynamiques est vide. Vérifiez requirements.txt ou la logique de parsing.")
    # Vous pourriez vouloir un fallback vers une liste statique ici en cas d'échec critique.
    # Par exemple: dynamic_install_requires = ["numpy", "pandas"] # Liste minimale de secours

setup(
    name="argumentation_analysis_project",
    version="0.1.0",
    packages=find_packages(exclude=["tests", "tests.*", "docs", "docs.*", "notebooks", "notebooks.*", "venv", ".venv", "dist", "build", "*.egg-info", "_archives", "_archives.*", "examples", "examples.*", "config", "config.*", "services", "services.*", "tutorials", "tutorials.*", "libs", "libs.*", "results", "results.*", "src", "src.*"]),
    # package_dir={'': 'src'}, # Maintenu commenté comme dans HEAD
    install_requires=dynamic_install_requires,
    python_requires=">=3.8",
    description="Système d'analyse argumentative",
    author="EPITA",
    author_email="contact@epita.fr",
)