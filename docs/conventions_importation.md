# Conventions d'Importation et Mécanismes de Redirection

## Table des matières

- [Introduction](#introduction)
- [Structure des importations](#structure-des-importations)
- [Mécanismes de redirection](#mécanismes-de-redirection)
- [Bonnes pratiques](#bonnes-pratiques)
- [Exemples concrets](#exemples-concrets)

## Introduction

Ce document décrit les conventions d'importation et les mécanismes de redirection utilisés dans le projet d'analyse argumentative. Ces conventions permettent de maintenir une structure de code cohérente et de faciliter la maintenance du projet.

## Structure des importations

### Importations au niveau du package principal

Le fichier `__init__.py` à la racine du package `argumentiation_analysis` expose les modules principaux pour faciliter leur accès:

```python
from . import core
from . import agents
from . import orchestration
from . import ui
from . import utils
from . import paths
```

Il expose également certaines fonctions couramment utilisées:

```python
from .core.llm_service import create_llm_service
from .core.jvm_setup import initialize_jvm
```

### Importations au niveau des sous-modules

Chaque sous-module (core, agents, services, etc.) possède son propre fichier `__init__.py` qui expose les classes et fonctions importantes du module. Par exemple, le module `core` expose:

```python
from .llm_service import create_llm_service
from .jvm_setup import initialize_jvm, download_tweety_jars
from .shared_state import SharedState
```

## Mécanismes de redirection

Le projet utilise des mécanismes de redirection pour maintenir la compatibilité avec le code existant tout en permettant une réorganisation de la structure interne. Ces mécanismes sont implémentés dans les fichiers `__init__.py` des modules concernés.

### Exemple: Module `agents/extract`

Le module `agents/extract` est un exemple de module de redirection. Son fichier `__init__.py` redirige vers le module `agents/core/extract`:

```python
from argumentiation_analysis.agents.core.extract.extract_agent import *
from argumentiation_analysis.agents.core.extract.extract_definitions import *
from argumentiation_analysis.agents.core.extract.prompts import *

# Exposer explicitement le module extract_agent
import argumentiation_analysis.agents.core.extract.extract_agent as extract_agent
```

Cela permet aux importations de la forme `from argumentiation_analysis.agents.extract import X` de fonctionner correctement, même si le code a été réorganisé.

## Bonnes pratiques

### Importations absolues vs relatives

- **Importations absolues**: Utilisez des importations absolues pour les modules externes ou les modules de haut niveau du projet.
  ```python
  from argumentiation_analysis.core import shared_state
  ```

- **Importations relatives**: Utilisez des importations relatives pour les modules proches dans la hiérarchie.
  ```python
  from . import shared_state
  from ..core import llm_service
  ```

### Gestion des erreurs d'importation

Les importations sont généralement entourées de blocs try/except pour éviter que l'échec d'une importation ne bloque l'ensemble du module:

```python
try:
    from . import shared_state
    from . import jvm_setup
except ImportError as e:
    import logging
    logging.warning(f"Certains sous-modules n'ont pas pu être importés: {e}")
```

### Exposition des API

Les modules exposent généralement une API claire via leur fichier `__init__.py`, en important et en réexportant les classes et fonctions importantes:

```python
# Dans le fichier __init__.py
from .module_a import ClassA, function_a
from .module_b import ClassB, function_b

__all__ = ['ClassA', 'function_a', 'ClassB', 'function_b']
```

## Exemples concrets

### Importation d'un agent

Pour utiliser l'agent d'extraction:

```python
# Méthode recommandée
from argumentiation_analysis.agents.extract import extract_agent

# Alternative (fonctionne grâce au mécanisme de redirection)
from argumentiation_analysis.agents.extract.extract_agent import ExtractAgent
```

### Utilisation des services

Pour utiliser les services partagés:

```python
from argumentiation_analysis.services.extract_service import ExtractService
from argumentiation_analysis.services.fetch_service import FetchService

# Création des services
extract_service = ExtractService()
fetch_service = FetchService()
```

### Accès aux chemins du projet

Pour accéder aux chemins définis dans le module `paths`:

```python
from argumentiation_analysis.paths import ROOT_DIR, CONFIG_DIR, DATA_DIR

# Utilisation des chemins
config_file = CONFIG_DIR / "settings.json"