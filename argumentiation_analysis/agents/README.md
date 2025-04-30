# 🧠 Agents IA (`agents/`)

Ce répertoire contient les définitions spécifiques à chaque agent IA participant à l'analyse rhétorique collaborative. L'objectif est que chaque agent ait son propre sous-répertoire pour une meilleure modularité.

[Retour au README Principal](../README.md)

## Point d'entrée pour instance VSCode dédiée

Ce README sert de point d'entrée pour une instance VSCode dédiée au développement et à la maintenance des agents IA. Cette approche multi-instance permet de travailler spécifiquement sur les agents sans avoir à gérer l'ensemble du projet.

## Structure

### Agents Principaux

Chaque agent est organisé dans son propre sous-répertoire :

* **[`pm/`](./pm/README.md)** 🧑‍🏫 : Agent Project Manager - Orchestre l'analyse.
* **[`informal/`](./informal/README.md)** 🧐 : Agent d'Analyse Informelle - Identifie arguments et sophismes.
* **[`pl/`](./pl/README.md)** 📐 : Agent de Logique Propositionnelle - Gère la formalisation et l'interrogation logique via Tweety.
* **[`extract/`](./extract/README.md)** 📑 : Agent d'Extraction - Gère l'extraction et la réparation des extraits de texte.
* **`(student_template/)`** : *(À créer)* Un template pour guider les étudiants dans l'ajout de leur propre agent.

### Fichiers de Test et d'Optimisation

* **[`test_informal_agent.py`](./test_informal_agent.py)** : Script de test pour l'agent d'analyse informelle.
* **[`test_orchestration_scale.py`](./test_orchestration_scale.py)** : Script de test pour l'orchestration à grande échelle.
* **[`rapport_test_orchestration_echelle.md`](./rapport_test_orchestration_echelle.md)** : Rapport sur les tests d'orchestration à grande échelle.

### Utilitaires pour les Agents

* **[`utils/`](./utils/)** : Utilitaires spécifiques aux agents.
  * **[`utils/informal_optimization/`](./utils/informal_optimization/README.md)** : Outils pour l'optimisation de l'agent d'analyse informelle.
    * **[`analyze_taxonomy_usage.py`](./utils/informal_optimization/analyze_taxonomy_usage.py)** : Analyse l'utilisation de la taxonomie des sophismes.
    * **[`improve_informal_agent.py`](./utils/informal_optimization/improve_informal_agent.py)** : Améliore les performances de l'agent informel.
    * **[`optimize_informal_agent.py`](./utils/informal_optimization/optimize_informal_agent.py)** : Optimise les prompts et définitions de l'agent informel.
    * **[`documentation.md`](./utils/informal_optimization/documentation.md)** : Documentation sur l'optimisation de l'agent informel.
    * **[`taxonomy_analysis/`](./utils/informal_optimization/taxonomy_analysis/)** : Visualisations et analyses de la taxonomie des sophismes.
      * **[`rapport_analyse_taxonomie.md`](./utils/informal_optimization/taxonomy_analysis/rapport_analyse_taxonomie.md)** : Rapport d'analyse de la taxonomie des sophismes.

### Traces d'Exécution

* **[`traces_informal_agent/`](./traces_informal_agent/)** : Traces d'exécution de l'agent d'analyse informelle.
  * Contient plusieurs fichiers JSON avec les résultats d'analyse de l'agent informel.

### Structure des Agents

Chaque sous-répertoire d'agent contient typiquement :
* `__init__.py`: Fichier vide ou avec des imports pour faciliter l'accès aux fonctions.
* `*_definitions.py`: Classes Plugin (si besoin), fonction `setup_*_kernel`, constante `*_INSTRUCTIONS`.
* `prompts.py`: Constantes contenant les prompts sémantiques pour l'agent.
* `*_agent.py`: Classe principale de l'agent avec ses méthodes spécifiques.
* `README.md`: Documentation spécifique à l'agent.

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
- Créez des backups des fichiers avant de les modifier (voir `utils/informal_optimization/backups/`)
- Documentez les modifications apportées aux agents dans des rapports dédiés
- Utilisez les outils d'optimisation pour améliorer les performances des agents

## Nouveaux Développements

### Optimisation de l'Agent Informel

Le dossier `utils/informal_optimization/` contient des outils pour analyser et améliorer les performances de l'agent d'analyse informelle :

- **Analyse de la taxonomie** : Visualisation et analyse de la structure de la taxonomie des sophismes.
- **Optimisation des prompts** : Amélioration des instructions et des prompts de l'agent.
- **Sauvegarde automatique** : Création de backups avant modification des fichiers.
- **Rapports d'analyse** : Documentation des améliorations apportées.

### Tests à Grande Échelle

Le fichier `test_orchestration_scale.py` permet de tester l'orchestration des agents sur un grand nombre de textes, afin d'évaluer :

- La robustesse du système
- Les performances des agents
- La qualité des analyses produites
- Les temps d'exécution

Les résultats de ces tests sont documentés dans `rapport_test_orchestration_echelle.md`.

### Traces d'Exécution

Le dossier `traces_informal_agent/` contient les traces d'exécution de l'agent d'analyse informelle, permettant :

- D'analyser le comportement de l'agent
- D'identifier les points d'amélioration
- De comparer différentes versions de l'agent
- De documenter les performances sur différents types de textes