#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour adapter le code du projet pour utiliser pyjnius au lieu de JPype1.
Ce script recherche les importations et utilisations de JPype1 dans le code et les remplace par pyjnius.
"""

import project_core.core_from_scripts.auto_env
import os
import re
import sys
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("adapt_code_for_pyjnius")

# Chemin vers le répertoire racine du projet
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Motifs de recherche et de remplacement
PATTERNS = [
    # Importations
    (r'import jpype', r'import jnius'),
    (r'import jpype as jp', r'import jnius as jp'),
    (r'from jpype import', r'from jnius import'),
    
    # Initialisation de la JVM
    (r'jpype\.startJVM\((.*?)\)', r'# pyjnius initializes JVM automatically\n# Original: jpype.startJVM(\1)'),
    (r'jp\.startJVM\((.*?)\)', r'# pyjnius initializes JVM automatically\n# Original: jp.startJVM(\1)'),
    
    # Arrêt de la JVM
    (r'jpype\.shutdownJVM\(\)', r'# pyjnius handles JVM shutdown automatically\n# Original: jpype.shutdownJVM()'),
    (r'jp\.shutdownJVM\(\)', r'# pyjnius handles JVM shutdown automatically\n# Original: jp.shutdownJVM()'),
    
    # Conversion des types
    (r'jpype\.JArray', r'jnius.array'),
    (r'jp\.JArray', r'jp.array'),
    
    # Création de classes Java
    (r'jpype\.JClass\([\'"]([^\'"]+)[\'"]\)', r'jnius.autoclass("\1")'),
    (r'jp\.JClass\([\'"]([^\'"]+)[\'"]\)', r'jp.autoclass("\1")'),
    
    # Conversion des types primitifs
    (r'jpype\.java\.lang\.String', r'jnius.autoclass("java.lang.String")'),
    (r'jp\.java\.lang\.String', r'jp.autoclass("java.lang.String")'),
]

def should_process_file(file_path):
    """
    Détermine si un fichier doit être traité.
    
    Args:
        file_path: Chemin du fichier
        
    Returns:
        True si le fichier doit être traité, False sinon
    """
    # Extensions de fichiers à traiter
    EXTENSIONS = ['.py']
    
    # Répertoires à ignorer
    IGNORE_DIRS = ['venv', '.git', '__pycache__', 'build', 'dist', 'tests/mocks']
    
    # Vérifier l'extension
    if not any(str(file_path).endswith(ext) for ext in EXTENSIONS):
        return False
    
    # Vérifier si le fichier est dans un répertoire à ignorer
    for ignore_dir in IGNORE_DIRS:
        if ignore_dir in str(file_path):
            return False
    
    return True

def contains_jpype(content):
    """
    Vérifie si le contenu contient des références à JPype.
    
    Args:
        content: Contenu du fichier
        
    Returns:
        True si le contenu contient des références à JPype, False sinon
    """
    return 'jpype' in content.lower() or 'jp.' in content or 'jp ' in content

def adapt_file(file_path):
    """
    Adapte un fichier pour utiliser pyjnius au lieu de JPype1.
    
    Args:
        file_path: Chemin du fichier
        
    Returns:
        True si le fichier a été modifié, False sinon
    """
    try:
        # Lire le contenu du fichier
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier si le fichier contient des références à JPype
        if not contains_jpype(content):
            return False
        
        # Appliquer les motifs de recherche et de remplacement
        modified_content = content
        for pattern, replacement in PATTERNS:
            modified_content = re.sub(pattern, replacement, modified_content)
        
        # Si le contenu a été modifié, écrire le nouveau contenu
        if modified_content != content:
            # Ajouter un commentaire en haut du fichier
            header_comment = """# Ce fichier a été automatiquement adapté pour utiliser pyjnius au lieu de JPype1
# pour la compatibilité avec Python 3.12.
# Si vous rencontrez des problèmes, veuillez consulter le fichier README_PYTHON312_COMPATIBILITY.md
# dans le répertoire scripts/setup.

"""
            modified_content = header_comment + modified_content
            
            # Écrire le nouveau contenu
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            logger.info(f"Fichier adapté : {file_path}")
            return True
        
        return False
    except Exception as e:
        logger.error(f"Erreur lors de l'adaptation du fichier {file_path} : {e}")
        return False

def create_mock_module():
    """
    Crée un module mock pour JPype1 qui redirige vers pyjnius.
    Cela permet d'éviter de modifier tout le code qui utilise JPype1.
    
    Returns:
        True si le module a été créé, False sinon
    """
    try:
        mock_dir = os.path.join(PROJECT_ROOT, 'tests', 'mocks')
        os.makedirs(mock_dir, exist_ok=True)
        
        mock_file = os.path.join(mock_dir, 'jpype_to_pyjnius.py')
        
        content = """#!/usr/bin/env python
# -*- coding: utf-8 -*-

\"\"\"
Module mock pour rediriger JPype1 vers pyjnius.
Ce module est utilisé pour la compatibilité avec Python 3.12.
\"\"\"

import sys
import logging
import importlib.util

logger = logging.getLogger(__name__)

try:
    import jnius
    
    # Créer un module jpype qui redirige vers jnius
    class JPypeModule:
        def __init__(self):
            self.jnius = jnius
            
        def __getattr__(self, name):
            if name == 'startJVM':
                # pyjnius initialise la JVM automatiquement
                return lambda *args, **kwargs: None
            elif name == 'shutdownJVM':
                # pyjnius gère l'arrêt de la JVM automatiquement
                return lambda: None
            elif name == 'JClass':
                return lambda class_name: jnius.autoclass(class_name)
            elif name == 'JArray':
                return jnius.array
            elif name == 'java':
                # Créer un proxy pour jpype.java
                class JavaPackage:
                    def __getattr__(self, name):
                        if name == 'lang':
                            # Créer un proxy pour jpype.java.lang
                            class LangPackage:
                                def __getattr__(self, name):
                                    return jnius.autoclass(f"java.lang.{name}")
                            return LangPackage()
                        return jnius.autoclass(f"java.{name}")
                return JavaPackage()
            else:
                try:
                    return getattr(jnius, name)
                except AttributeError:
                    logger.warning(f"Attribut {name} non trouvé dans jnius")
                    # Retourner une fonction qui ne fait rien
                    return lambda *args, **kwargs: None
    
    # Installer le module mock
    sys.modules['jpype'] = JPypeModule()
    sys.modules['jpype.types'] = JPypeModule()
    sys.modules['jpype.imports'] = JPypeModule()
    
    logger.info("Module mock JPype1 installé avec succès (redirection vers pyjnius)")
    
except ImportError:
    logger.error("Impossible d'importer jnius. Veuillez installer pyjnius.")
    raise
"""
        
        with open(mock_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Module mock créé : {mock_file}")
        
        # Créer un fichier __init__.py dans le répertoire mocks
        init_file = os.path.join(mock_dir, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write("# Ce répertoire contient des modules mock pour la compatibilité\n")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la création du module mock : {e}")
        return False

def create_init_script():
    """
    Crée un script d'initialisation qui importe le module mock si nécessaire.
    
    Returns:
        True si le script a été créé, False sinon
    """
    try:
        script_dir = os.path.join(PROJECT_ROOT, 'scripts', 'setup')
        os.makedirs(script_dir, exist_ok=True)
        
        script_file = os.path.join(script_dir, 'init_jpype_compatibility.py')
        
        content = """#!/usr/bin/env python
# -*- coding: utf-8 -*-

\"\"\"
Script d'initialisation pour la compatibilité JPype1/pyjnius.
Ce script détecte la version de Python et importe le module mock si nécessaire.
\"\"\"

import sys
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("init_jpype_compatibility")

def init_compatibility():
    \"\"\"
    Initialise la compatibilité JPype1/pyjnius en fonction de la version de Python.
    \"\"\"
    # Vérifier la version de Python
    if sys.version_info.major == 3 and sys.version_info.minor >= 12:
        logger.info("Python 3.12 ou supérieur détecté, utilisation du module mock JPype1")
        try:
            # Importer le module mock
            from tests.mocks import jpype_to_pyjnius
            logger.info("Module mock JPype1 importé avec succès")
            return True
        except ImportError as e:
            logger.error(f"Erreur lors de l'importation du module mock JPype1 : {e}")
            return False
    else:
        logger.info(f"Python {sys.version_info.major}.{sys.version_info.minor} détecté, utilisation de JPype1 standard")
        return True

if __name__ == "__main__":
    init_compatibility()
"""
        
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Script d'initialisation créé : {script_file}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la création du script d'initialisation : {e}")
        return False

def update_conftest():
    """
    Met à jour le fichier conftest.py pour importer le module mock si nécessaire.
    
    Returns:
        True si le fichier a été mis à jour, False sinon
    """
    try:
        conftest_file = os.path.join(PROJECT_ROOT, 'conftest.py')
        
        if not os.path.exists(conftest_file):
            logger.warning(f"Le fichier {conftest_file} n'existe pas")
            return False
        
        with open(conftest_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier si le code d'initialisation est déjà présent
        if 'init_jpype_compatibility' in content:
            logger.info(f"Le fichier {conftest_file} contient déjà le code d'initialisation")
            return False
        
        # Ajouter le code d'initialisation
        import_code = """
# Initialisation de la compatibilité JPype1/pyjnius
import sys
try:
    from scripts.setup.init_jpype_compatibility import init_compatibility
    init_compatibility()
except ImportError:
    print("Avertissement: Module de compatibilité JPype1/pyjnius non trouvé")
"""
        
        # Trouver la position pour insérer le code
        import_pos = content.find('import')
        if import_pos == -1:
            # Si aucun import n'est trouvé, ajouter au début du fichier
            modified_content = import_code + content
        else:
            # Sinon, ajouter après le premier bloc d'imports
            end_of_imports = content.find('\n\n', import_pos)
            if end_of_imports == -1:
                end_of_imports = len(content)
            modified_content = content[:end_of_imports] + import_code + content[end_of_imports:]
        
        with open(conftest_file, 'w', encoding='utf-8') as f:
            f.write(modified_content)
        
        logger.info(f"Fichier {conftest_file} mis à jour")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du fichier {conftest_file} : {e}")
        return False

def main():
    """
    Fonction principale.
    """
    logger.info("Adaptation du code pour utiliser pyjnius au lieu de JPype1...")
    
    # Créer le module mock
    create_mock_module()
    
    # Créer le script d'initialisation
    create_init_script()
    
    # Mettre à jour le fichier conftest.py
    update_conftest()
    
    # Parcourir tous les fichiers Python du projet
    modified_files = 0
    for root, _, files in os.walk(PROJECT_ROOT):
        for file in files:
            if file.endswith('.py'):
                file_path = Path(os.path.join(root, file))
                if should_process_file(file_path):
                    if adapt_file(file_path):
                        modified_files += 1
    
    logger.info(f"Adaptation terminée. {modified_files} fichiers ont été modifiés.")
    
    # Créer un fichier README pour expliquer les modifications
    readme_file = os.path.join(PROJECT_ROOT, 'scripts', 'setup', 'README_JPYPE_TO_PYJNIUS.md')
    
    readme_content = """# Adaptation du code pour utiliser pyjnius au lieu de JPype1

## Contexte
JPype1 1.4.1 n'est pas compatible avec Python 3.12 en raison de changements dans la structure interne de Python.
Ce script adapte le code du projet pour utiliser pyjnius comme alternative à JPype1.

## Modifications apportées

1. **Module mock** : Un module mock a été créé dans `tests/mocks/jpype_to_pyjnius.py` qui redirige les appels à JPype1 vers pyjnius.
2. **Script d'initialisation** : Un script d'initialisation a été créé dans `scripts/setup/init_jpype_compatibility.py` qui détecte la version de Python et importe le module mock si nécessaire.
3. **Mise à jour de conftest.py** : Le fichier `conftest.py` a été mis à jour pour importer le module mock si nécessaire.
4. **Adaptation du code** : Les fichiers Python du projet ont été adaptés pour utiliser pyjnius au lieu de JPype1.

## Comment utiliser

Pour utiliser cette adaptation, il suffit d'importer le module d'initialisation au début de votre script :

```python
from scripts.setup.init_jpype_compatibility import init_compatibility
init_compatibility()
```

Ou, si vous préférez, vous pouvez utiliser directement pyjnius :

```python
import jnius
```

## Différences entre JPype1 et pyjnius

### Initialisation de la JVM

JPype1 :
```python
import jpype
jpype.startJVM(jpype.getDefaultJVMPath(), "-ea")
```

pyjnius :
```python
import jnius
# La JVM est initialisée automatiquement
```

### Création de classes Java

JPype1 :
```python
String = jpype.JClass("java.lang.String")
```

pyjnius :
```python
String = jnius.autoclass("java.lang.String")
```

### Tableaux Java

JPype1 :
```python
StringArray = jpype.JArray(jpype.JString)
```

pyjnius :
```python
StringArray = jnius.array("java.lang.String", 1)
```

### Arrêt de la JVM

JPype1 :
```python
jpype.shutdownJVM()
```

pyjnius :
```python
# La JVM est arrêtée automatiquement
```

## Problèmes connus

- Certaines fonctionnalités avancées de JPype1 peuvent ne pas être disponibles dans pyjnius.
- Les performances peuvent être légèrement différentes.
- Certaines adaptations manuelles peuvent être nécessaires pour des cas d'utilisation spécifiques.

Si vous rencontrez des problèmes, veuillez consulter la documentation de pyjnius : https://pyjnius.readthedocs.io/
"""
    
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    logger.info(f"Fichier README créé : {readme_file}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())