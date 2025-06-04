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

Le fichier `__init__.py` à la racine du package `argumentation_analysis` utilise la variable `__all__` pour définir les sous-packages qui sont considérés comme faisant partie de l'API publique du package principal.

```python
# argumentation_analysis/__init__.py
__all__ = [
    "agents",
    "analytics",
    "core",
    "models",
    "nlp",
    "orchestration",
    "pipelines",
    "reporting",
    "scripts",
    "services",
    "service_setup",
    "ui",
    "utils",
]
```

Les modules spécifiques comme `paths.py` ou les fonctions utilitaires comme `create_llm_service` (du module `core.llm_service`) ne sont généralement pas ré-exportés à ce niveau et doivent être importés directement depuis leur module d'origine.

Par exemple:
```python
from argumentation_analysis.paths import ROOT_DIR
from argumentation_analysis.core.llm_service import create_llm_service
```

### Importations au niveau des sous-modules

Chaque sous-module (par exemple, `core`, `agents`, `services`) possède son propre fichier `__init__.py`. La manière dont ces fichiers exposent les classes et fonctions importantes du module peut varier :
*   Certains peuvent être minimes et ne servir qu'à marquer le répertoire comme un package. Dans ce cas, les importations se font directement depuis les fichiers spécifiques du sous-module.
*   D'autres peuvent importer et ré-exporter explicitement des éléments pour simplifier l'accès.

Par exemple, le fichier `argumentation_analysis/core/__init__.py` est actuellement minimal. Pour utiliser des éléments de `core`, vous importeriez directement depuis le module concerné :

```python
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.core.jvm_setup import initialize_jvm, download_tweety_jars
from argumentation_analysis.core.shared_state import SharedState
```

À l'inverse, le fichier `argumentation_analysis/services/__init__.py` expose explicitement les services :

```python
# argumentation_analysis/services/__init__.py
from .cache_service import CacheService
from .crypto_service import CryptoService
from .definition_service import DefinitionService
from .extract_service import ExtractService
from .fetch_service import FetchService

# __all__ peut aussi être utilisé ici si souhaité
# __all__ = ["CacheService", "CryptoService", "DefinitionService", "ExtractService", "FetchService"]
```
Cela permet des importations comme :
```python
from argumentation_analysis.services import ExtractService
```

## Mécanismes de redirection

Le projet utilise des mécanismes de redirection pour maintenir la compatibilité avec le code existant tout en permettant une réorganisation de la structure interne. Ces mécanismes sont implémentés dans les fichiers `__init__.py` des modules concernés.

### Exemple: Module `agents/extract`

Le module `agents/extract` est un exemple de module de redirection. Son fichier `__init__.py` redirige vers le module `agents/core/extract` en utilisant des importations relatives et la manipulation de `sys.modules` pour créer un alias.

```python
# argumentation_analysis/agents/extract/__init__.py
try:
    # Utiliser des imports relatifs
    from ..core.extract.extract_agent import *
    from ..core.extract.extract_definitions import *
    from ..core.extract.prompts import *
    
    from ..core.extract.extract_agent import ExtractAgent
    
    # Créer un alias pour le module extract_agent
    import sys
    from ..core.extract import extract_agent as core_extract_agent_module
    sys.modules['argumentation_analysis.agents.extract.extract_agent'] = core_extract_agent_module
except ImportError as e:
    # ... gestion des erreurs avec mocks ...
    pass
```

Cela permet aux importations de la forme `from argumentation_analysis.agents.extract import X` ou `from argumentation_analysis.agents.extract.extract_agent import Y` de fonctionner correctement, même si le code a été réorganisé dans `agents/core/extract`.

## Bonnes pratiques

### Importations absolues vs relatives

- **Importations absolues**: Utilisez des importations absolues pour les modules externes ou les modules de haut niveau du projet (c'est-à-dire, depuis la racine `argumentation_analysis`).
  ```python
  from argumentation_analysis.core import shared_state # Si shared_state est exposé par core/__init__.py
  from argumentation_analysis.core.shared_state import SharedState # Plus typique si core/__init__.py est minimal
  import requests # Module externe
  ```

- **Importations relatives**: Utilisez des importations relatives pour les modules proches dans la hiérarchie (au sein du même sous-package ou entre sous-packages frères si la structure le justifie clairement).
  ```python
  # Dans un module de argumentation_analysis/agents/core/
  from . import another_core_module # Module dans le même répertoire
  from ..utils import some_utility # Module dans argumentation_analysis/agents/utils/
  from ...core import llm_service # Module dans argumentation_analysis/core/
  ```

### Gestion des erreurs d'importation

Les importations sont généralement entourées de blocs `try/except ImportError` pour gérer les dépendances optionnelles ou pour éviter que l'échec d'une importation (par exemple, lors de tests ou de configurations partielles) ne bloque l'ensemble du module.

```python
try:
    from . import optional_dependency
except ImportError as e:
    import logging
    logging.debug(f"Dépendance optionnelle non disponible: {e}")
    optional_dependency = None # ou un mock
```

### Exposition des API

Les modules peuvent exposer une API via leur fichier `__init__.py`. Cela peut se faire par des importations directes des classes et fonctions à exposer, ou en utilisant la variable `__all__` pour définir explicitement l'interface publique. La pratique actuelle dans le projet varie selon les sous-modules.

```python
# Dans le fichier __init__.py d'un sous-module

# Méthode 1: Importations directes
from .module_a import ClassA, function_a
from .module_b import ClassB, function_b
# ClassA, function_a, etc. sont maintenant accessibles via le package

# Méthode 2: Utilisation de __all__ (souvent combinée avec des imports)
from .module_a import ClassA, function_a
from .module_b import ClassB, function_b
__all__ = ['ClassA', 'function_a', 'ClassB', 'function_b']
```

## Exemples concrets

### Importation d'un agent

Pour utiliser l'agent d'extraction, grâce au mécanisme de redirection dans `argumentation_analysis/agents/extract/__init__.py`:

```python
# Méthode recommandée (utilise l'alias créé dans agents/extract/__init__.py)
from argumentation_analysis.agents.extract import extract_agent
extract_instance = extract_agent.ExtractAgent()

# Alternative (import direct de la classe, fonctionne aussi grâce au `*` import)
from argumentation_analysis.agents.extract import ExtractAgent
extract_instance_alt = ExtractAgent()

# Importation directe depuis l'emplacement réel (moins recommandé si une redirection existe)
# from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
```

### Utilisation des services

Les services sont généralement exposés par le fichier `argumentation_analysis/services/__init__.py`:

```python
from argumentation_analysis.services import ExtractService, FetchService
# ou directement si le __init__.py n'exporte pas:
# from argumentation_analysis.services.extract_service import ExtractService
# from argumentation_analysis.services.fetch_service import FetchService


# Création des services (nécessite les dépendances appropriées, ex: CacheService pour FetchService)
# cache_service = CacheService(...)
# fetch_service = FetchService(cache_service=cache_service)
# extract_service = ExtractService()
```

### Accès aux chemins du projet

Le module `paths.py` définit les chemins importants du projet:

```python
from argumentation_analysis.paths import ROOT_DIR, CONFIG_DIR, DATA_DIR

# Utilisation des chemins
config_file_path = CONFIG_DIR / "settings.json"
data_file_path = DATA_DIR / "my_data.csv"