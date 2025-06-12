from setuptools import setup, find_packages
import os
import yaml # PyYAML doit être installé (ajoutez 'pyyaml' à environment.yml si besoin)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, 'environment.yml')

def parse_environment_yml(file_path):
    """
    Parse environment.yml pour extraire les dépendances pour install_requires.
    """
    install_requires_list = []
    if not os.path.exists(file_path):
        print(f"AVERTISSEMENT: {file_path} non trouvé. Aucune dépendance ne sera lue.")
        return install_requires_list

    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            env_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"ERREUR: Impossible de parser {file_path}. Erreur YAML: {e}")
            return install_requires_list # Retourne une liste vide en cas d'erreur de parsing

    # Traitement de la section 'dependencies' principale
    if 'dependencies' in env_data and isinstance(env_data['dependencies'], list):
        for dep in env_data['dependencies']:
            if isinstance(dep, str):
                dep_cleaned = dep.split('#')[0].strip() # Enlever les commentaires en ligne
                if not dep_cleaned: # Ignorer les lignes vides ou de commentaires purs
                    continue
                if dep_cleaned.startswith('python=') or dep_cleaned == 'pip':
                    continue
                
                # Normalisations spécifiques Conda -> Pip
                if dep_cleaned == 'pytorch':
                    install_requires_list.append('torch')
                # elif dep_cleaned.startswith('python-dotenv'): # python-dotenv est le même nom pour pip
                #     install_requires_list.append('python-dotenv')
                else:
                    install_requires_list.append(dep_cleaned)

    # Traitement de la section 'pip' (au niveau racine du YAML)
    if 'pip' in env_data and isinstance(env_data['pip'], list):
        for pip_dep in env_data['pip']:
            if isinstance(pip_dep, str):
                pip_dep_cleaned = pip_dep.split('#')[0].strip() # Enlever les commentaires en ligne
                if pip_dep_cleaned: # S'assurer que ce n'est pas une ligne vide
                    install_requires_list.append(pip_dep_cleaned)
    
    # Optionnel: déduplication tout en préservant l'ordre approximatif pour la lisibilité
    # Cependant, setuptools gère les doublons, donc ce n'est pas strictement nécessaire.
    # seen = set()
    # unique_install_requires = [x for x in install_requires_list if not (x in seen or seen.add(x))]
    # return unique_install_requires
    return install_requires_list

# Lire les dépendances depuis environment.yml
dynamic_install_requires = parse_environment_yml(ENV_FILE)

if not dynamic_install_requires:
    print("AVERTISSEMENT: La liste des dépendances dynamiques est vide. Vérifiez environment.yml ou la logique de parsing.")
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