"""Configuration du projet d'argumentation Dung"""

import os

# Chemins
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
LIBS_DIR = os.path.join(PROJECT_ROOT, 'libs')
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
OUTPUTS_DIR = os.path.join(PROJECT_ROOT, 'outputs')
EXAMPLES_DIR = os.path.join(PROJECT_ROOT, 'examples')

# Créer les dossiers s'ils n'existent pas
for directory in [DATA_DIR, OUTPUTS_DIR, EXAMPLES_DIR]:
    os.makedirs(directory, exist_ok=True)

# Paramètres de visualisation
VISUALIZATION_CONFIG = {
    'figure_size': (12, 8),
    'node_size': 3000,
    'font_size': 12,
    'font_weight': 'bold',
    'arrow_size': 25,
    'accepted_color': 'lightgreen',
    'rejected_color': 'lightcoral',
    'neutral_color': 'skyblue',
    'edge_color': 'gray',
    'dpi': 100
}

# Paramètres de génération aléatoire
RANDOM_GENERATION_CONFIG = {
    'default_size': 5,
    'default_attack_probability': 0.3,
    'max_size': 50,
    'min_size': 2
}

# Configuration TweetyProject
TWEETY_CONFIG = {
    'jar_files': [
        'tweety-full-1.28.jar',
        'dung-1.27.jar',
        'commons-1.27.jar',
        'graphs-1.27.jar',
        'math-1.27.jar'
    ],
    'memory_limit': '2g'
}

# Configuration des tests
TEST_CONFIG = {
    'verbosity': 2,
    'performance_timeout': 10.0,
    'stress_test_size': 20,
    'benchmark_trials': 5
}

# Sémantiques supportées
SUPPORTED_SEMANTICS = [
    'grounded',
    'preferred', 
    'stable',
    'complete',
    'admissible',
    'ideal',
    'semi_stable'
]

# Formats d'export supportés
SUPPORTED_FORMATS = {
    'json': 'JavaScript Object Notation',
    'tgf': 'Trivial Graph Format',
    'dot': 'GraphViz DOT format',
    'csv': 'Comma Separated Values'
}

def get_project_info():
    """Retourne les informations du projet"""
    return {
        'name': 'Agent d\'Argumentation Abstraite de Dung',
        'version': '1.0.0',
        'supported_semantics': SUPPORTED_SEMANTICS,
        'supported_formats': list(SUPPORTED_FORMATS.keys()),
        'project_root': PROJECT_ROOT
    }

def validate_configuration():
    """Valide la configuration du projet"""
    errors = []
    
    # Vérifier les JAR files
    for jar_file in TWEETY_CONFIG['jar_files']:
        jar_path = os.path.join(LIBS_DIR, jar_file)
        if not os.path.exists(jar_path):
            errors.append(f"JAR file manquant: {jar_path}")
    
    # Vérifier les dossiers
    for directory in [LIBS_DIR, DATA_DIR, OUTPUTS_DIR]:
        if not os.path.exists(directory):
            errors.append(f"Dossier manquant: {directory}")
    
    return errors

if __name__ == "__main__":
    print("=== CONFIGURATION DU PROJET ===")
    info = get_project_info()
    for key, value in info.items():
        print(f"{key}: {value}")
    
    print("\n=== VALIDATION ===")
    errors = validate_configuration()
    if errors:
        print("Erreurs détectées:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✓ Configuration valide")