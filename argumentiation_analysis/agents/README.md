# 🧠 Agents IA (`agents/`)

Ce répertoire contient les définitions spécifiques à chaque agent IA participant à l'analyse rhétorique collaborative. La structure a été réorganisée pour une meilleure modularité et maintenabilité.

[Retour au README Principal](../README.md)

## Point d'entrée pour instance VSCode dédiée

Ce README sert de point d'entrée pour une instance VSCode dédiée au développement et à la maintenance des agents IA. Cette approche multi-instance permet de travailler spécifiquement sur les agents sans avoir à gérer l'ensemble du projet.

## Structure

### Agents Principaux

* **[`core/`](./core/README.md)** : Répertoire contenant les agents principaux du système
  * **[`core/pm/`](./core/pm/README.md)** 🧑‍🏫 : Agent Project Manager - Orchestre l'analyse.
  * **[`core/informal/`](./core/informal/README.md)** 🧐 : Agent d'Analyse Informelle - Identifie arguments et sophismes.
  * **[`core/pl/`](./core/pl/README.md)** 📐 : Agent de Logique Propositionnelle - Gère la formalisation et l'interrogation logique via Tweety.
  * **[`core/extract/`](./core/extract/README.md)** 📑 : Agent d'Extraction - Gère l'extraction et la réparation des extraits de texte.

### Outils et Utilitaires

* **[`tools/`](./tools/README.md)** 🛠️ : Outils et utilitaires utilisés par les agents
  * **[`tools/optimization/`](./tools/optimization/README.md)** ⚙️ : Outils d'optimisation des agents
  * **[`tools/analysis/`](./tools/analysis/README.md)** 📊 : Outils d'analyse des résultats des agents
  * **[`tools/encryption/`](./tools/encryption/README.md)** 🔒 : Système d'encryption pour sécuriser les données sensibles

### Scripts d'Exécution

* **[`runners/`](./runners/README.md)** 🚀 : Scripts d'exécution pour les agents
  * **[`runners/test/`](./runners/test/README.md)** 🧪 : Scripts pour l'exécution des tests
  * **[`runners/deploy/`](./runners/deploy/README.md)** 📦 : Scripts de déploiement
  * **[`runners/integration/`](./runners/integration/README.md)** 🔄 : Scripts d'intégration

### Données et Bibliothèques

* **[`data/`](./data/)** 📁 : Données utilisées par les agents
* **[`libs/`](./libs/)** 📦 : Bibliothèques partagées

### Documentation et Traces

* **[`docs/`](./docs/README.md)** 📚 : Documentation du projet
  * **[`docs/reports/`](./docs/reports/README.md)** 📝 : Rapports d'analyse et de test

* **[`traces/`](./traces/README.md)** 📝 : Traces d'exécution des agents (séparées du code)
  * **[`traces/informal/`](./traces/informal/README.md)** 🧐 : Traces de l'agent d'analyse informelle
  * **[`traces/orchestration/`](./traces/orchestration/README.md)** 🎮 : Traces de l'orchestration

### Templates

* **[`templates/`](./templates/README.md)** 📋 : Templates pour nouveaux agents
  * **[`templates/student_template/`](./templates/student_template/README.md)** 🎓 : Template pour les étudiants

## Structure des Agents

Chaque sous-répertoire d'agent dans `core/` contient typiquement :
* `__init__.py`: Fichier vide ou avec des imports pour faciliter l'accès aux fonctions.
* `*_definitions.py`: Classes Plugin (si besoin), fonction `setup_*_kernel`, constante `*_INSTRUCTIONS`.
* `prompts.py`: Constantes contenant les prompts sémantiques pour l'agent.
* `*_agent.py`: Classe principale de l'agent avec ses méthodes spécifiques.
* `README.md`: Documentation spécifique à l'agent.

## Développement des agents

### Création d'un nouvel agent

Pour créer un nouvel agent, suivez ces étapes :

1. Utilisez le template étudiant comme base (`templates/student_template/`)
2. Créez un nouveau sous-répertoire dans `core/` avec le nom de l'agent (ex: `core/new_agent/`)
3. Copiez les fichiers du template et adaptez-les à votre agent
4. Implémentez les fonctionnalités spécifiques à l'agent
5. Mettez à jour l'orchestrateur principal pour intégrer le nouvel agent

### Test indépendant des agents

Pour tester un agent de manière indépendante, vous pouvez créer un script de test dans le répertoire `runners/test/[agent_name]/`. Exemple :

```python
# runners/test/new_agent/test_new_agent.py
import asyncio
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from dotenv import load_dotenv
load_dotenv(override=True)

from core.llm_service import create_llm_service
from agents.core.new_agent.new_agent_definitions import setup_new_agent

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
python agents/runners/test/new_agent/test_new_agent.py
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
- Créez des backups des fichiers avant de les modifier
- Documentez les modifications apportées aux agents dans des rapports dédiés
- Utilisez les outils d'optimisation pour améliorer les performances des agents

## Nouveaux Développements

### Optimisation des Agents

Le dossier `tools/optimization/` contient des outils pour analyser et améliorer les performances des agents :

- **Analyse de la taxonomie** : Visualisation et analyse de la structure de la taxonomie des sophismes.
- **Optimisation des prompts** : Amélioration des instructions et des prompts de l'agent.
- **Amélioration des performances** : Scripts pour améliorer les performances de l'agent.
- **Comparaison des versions** : Outils pour comparer différentes versions de l'agent.

### Tests à Grande Échelle

Les scripts dans `runners/integration/` permettent de tester l'orchestration des agents sur un grand nombre de textes, afin d'évaluer :

- La robustesse du système
- Les performances des agents
- La qualité des analyses produites
- Les temps d'exécution

Les résultats de ces tests sont documentés dans `docs/reports/`.

### Traces d'Exécution

Le dossier `traces/` contient les traces d'exécution des agents, permettant :

- D'analyser le comportement des agents
- D'identifier les points d'amélioration
- De comparer différentes versions des agents
- De documenter les performances sur différents types de textes