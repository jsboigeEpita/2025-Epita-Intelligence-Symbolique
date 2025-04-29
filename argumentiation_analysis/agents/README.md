# 🧠 Agents IA (`agents/`)

Ce répertoire contient les définitions spécifiques à chaque agent IA participant à l'analyse rhétorique collaborative. L'objectif est que chaque agent ait son propre sous-répertoire pour une meilleure modularité.

[Retour au README Principal](../README.md)

## Point d'entrée pour instance VSCode dédiée

Ce README sert de point d'entrée pour une instance VSCode dédiée au développement et à la maintenance des agents IA. Cette approche multi-instance permet de travailler spécifiquement sur les agents sans avoir à gérer l'ensemble du projet.

## Structure

Chaque agent est organisé dans son propre sous-répertoire :

* **[`pm/`](./pm/README.md)** 🧑‍🏫 : Agent Project Manager - Orchestre l'analyse.
* **[`informal/`](./informal/README.md)** 🧐 : Agent d'Analyse Informelle - Identifie arguments et sophismes.
* **[`pl/`](./pl/README.md)** 📐 : Agent de Logique Propositionnelle - Gère la formalisation et l'interrogation logique via Tweety.
* **[`extract/`](./extract/README.md)** 📑 : Agent d'Extraction - Gère l'extraction et la réparation des extraits de texte.
* **`(student_template/)`** : *(À créer)* Un template pour guider les étudiants dans l'ajout de leur propre agent.

Chaque sous-répertoire contient typiquement :
* `__init__.py`: Fichier vide ou avec des imports pour faciliter l'accès aux fonctions.
* `*_definitions.py`: Classes Plugin (si besoin), fonction `setup_*_kernel`, constante `*_INSTRUCTIONS`.
* `prompts.py`: Constantes contenant les prompts sémantiques pour l'agent.
* `*_agent.py`: Classe principale de l'agent avec ses méthodes spécifiques.

## Développement des agents

### Création d'un nouvel agent

Pour créer un nouvel agent, suivez ces étapes :

1. Créez un nouveau sous-répertoire avec le nom de l'agent (ex: `new_agent/`)
2. Créez les fichiers de base :
   - `__init__.py`
   - `new_agent_definitions.py`
   - `prompts.py`
   - `new_agent.py`
3. Implémentez les fonctionnalités spécifiques à l'agent
4. Mettez à jour l'orchestrateur principal pour intégrer le nouvel agent

### Test indépendant des agents

Pour tester un agent de manière indépendante, vous pouvez créer un script de test dans son sous-répertoire. Exemple :

```python
# test_new_agent.py
import asyncio
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from dotenv import load_dotenv
load_dotenv(override=True)

from core.llm_service import create_llm_service
from new_agent.new_agent_definitions import setup_new_agent

async def test_agent():
    # Créer le service LLM
    llm_service = create_llm_service()
    
    # Initialiser l'agent
    kernel, agent = await setup_new_agent(llm_service)
    
    # Tester une fonctionnalité spécifique
    result = await agent.some_function("Texte de test")
    print(f"Résultat: {result}")

if __name__ == "__main__":
    asyncio.run(test_agent())
```

Exécutez le test avec :
```bash
python agents/new_agent/test_new_agent.py
```

## Intégration avec l'orchestrateur principal

Pour intégrer un nouvel agent dans l'analyse complète, vous devez :

1. Ajouter l'importation de l'agent dans `orchestration/analysis_runner.py`
2. Initialiser l'agent dans la fonction `setup_agents()`
3. Ajouter l'agent à la liste des agents disponibles
4. Mettre à jour la logique d'orchestration pour utiliser le nouvel agent

## Développement avec l'approche multi-instance

1. Ouvrez ce répertoire (`agents/`) comme dossier racine dans une instance VSCode dédiée
2. Travaillez sur les agents sans être distrait par les autres parties du projet
3. Testez vos modifications avec les scripts de test indépendants
4. Une fois les modifications validées, intégrez-les dans le projet principal

## Bonnes pratiques

- Gardez les prompts dans des fichiers séparés pour faciliter leur maintenance
- Documentez clairement les fonctionnalités et les paramètres de chaque agent
- Utilisez des tests unitaires pour valider le comportement des agents
- Suivez une structure cohérente pour tous les agents
- Utilisez des noms explicites pour les fonctions et les variables