# Agent d'Analyse Informelle

Ce répertoire contient les définitions et les prompts pour l'agent d'analyse informelle, qui est responsable de l'identification des arguments et de l'analyse des sophismes dans un texte.

## Fichiers

- `__init__.py` : Module d'initialisation
- `informal_definitions.py` : Définitions pour l'agent informel, incluant la classe `InformalAnalysisPlugin` et la fonction `setup_informal_kernel`
- `prompts.py` : Prompts utilisés par l'agent informel

## Fonctionnalités

L'agent d'analyse informelle offre les fonctionnalités suivantes :

1. **Identification des arguments** : Extraction des arguments principaux d'un texte
2. **Exploration de la taxonomie des sophismes** : Navigation dans la hiérarchie des sophismes
3. **Analyse des sophismes** : Identification et justification des sophismes dans les arguments
4. **Attribution de sophismes** : Association de sophismes spécifiques à des arguments identifiés

## Utilisation

L'agent est configuré via la fonction `setup_informal_kernel` qui ajoute une instance du plugin `InformalAnalysisPlugin` au kernel et configure les fonctions sémantiques nécessaires.

```python
from agents.core.informal.informal_definitions import setup_informal_kernel

# Configuration du kernel pour l'agent informel
setup_informal_kernel(kernel, llm_service)
```

## Taxonomie des sophismes

L'agent utilise une taxonomie externe des sophismes stockée dans un fichier CSV. Cette taxonomie est chargée via l'utilitaire `taxonomy_loader` du module `utils`.