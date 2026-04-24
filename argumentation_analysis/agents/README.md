# 🧠 Agents IA (`agents/`)

Ce répertoire contient les définitions spécifiques à chaque agent IA participant à l'analyse rhétorique collaborative. La structure est organisée pour une modularité et maintenabilité optimales.

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

## Guide de Contribution pour Étudiants

Cette section explique comment contribuer efficacement au développement des agents en tant qu'étudiant, que vous travailliez seul ou en groupe.

### Choix d'un agent à développer ou améliorer

Voici quelques suggestions pour choisir un agent sur lequel travailler :

1. **Amélioration d'un agent existant** :
   - Agent Informal : Améliorer la détection des sophismes
   - Agent PL : Finaliser l'intégration avec Tweety
   - Agent Extract : Améliorer la robustesse de l'extraction

2. **Création d'un nouvel agent** :
   - Agent FOL (First Order Logic) : Étendre l'analyse à la logique du premier ordre
   - Agent Modal : Ajouter des capacités d'analyse en logique modale
   - Agent Résumé : Créer un agent capable de résumer les analyses

### Création d'un nouvel agent

Pour créer un nouvel agent, suivez ces étapes :

1. **Utilisez le template étudiant comme base** :
   - Explorez le contenu du dossier `templates/student_template/`
   - Comprenez la structure et les fichiers nécessaires

2. **Créez un nouveau sous-répertoire** :
   ```bash
   mkdir -p core/nom_de_votre_agent
   ```

3. **Copiez les fichiers du template** :
   ```bash
   cp templates/student_template/* core/nom_de_votre_agent/
   ```

4. **Adaptez les fichiers à votre agent** :
   - Renommez les fichiers selon la convention (ex: `nom_agent_definitions.py`)
   - Modifiez le contenu pour implémenter les fonctionnalités spécifiques
   - Mettez à jour le README.md avec la documentation de votre agent

5. **Intégrez votre agent dans l'orchestrateur** :
   - Modifiez `orchestration/analysis_runner.py` pour inclure votre agent
   - Ajoutez les importations nécessaires
   - Mettez à jour la fonction `setup_agents()`

### Test indépendant des agents

Les tests des agents se trouvent dans `tests/unit/agents/` et `tests/unit/argumentation_analysis/`. Pour tester un agent :

```bash
# Test unitaire standard
pytest tests/unit/agents/test_nom_agent.py -v
```

### Workflow de contribution en groupe

#### Pour les groupes de 2 étudiants

1. **Répartissez les tâches** :
   - Un étudiant peut travailler sur la logique principale de l'agent
   - L'autre peut se concentrer sur les tests et l'intégration

2. **Utilisez des branches Git dédiées** :
   ```bash
   # Étudiant 1
   git checkout -b feature/agent-logique

   # Étudiant 2
   git checkout -b feature/agent-tests
   ```

3. **Synchronisez régulièrement votre travail** :
   - Faites des commits fréquents
   - Poussez vos branches vers votre fork
   - Faites des revues de code mutuelles

#### Pour les groupes de 3-4 étudiants

1. **Divisez le travail en modules** :
   - Un étudiant pour la structure de base de l'agent
   - Un étudiant pour les prompts et définitions
   - Un étudiant pour les tests
   - Un étudiant pour l'intégration et la documentation

2. **Créez une branche par fonctionnalité** :
   ```bash
   git checkout -b feature/agent-structure
   git checkout -b feature/agent-prompts
   git checkout -b feature/agent-tests
   git checkout -b feature/agent-integration
   ```

3. **Utilisez les issues GitHub** pour suivre l'avancement :
   - Créez une issue pour chaque tâche
   - Assignez les issues aux membres du groupe
   - Référencez les issues dans vos commits

4. **Organisez des réunions régulières** pour synchroniser le travail

### Soumission de votre travail

Une fois votre agent développé et testé, soumettez-le au dépôt principal :

1. **Assurez-vous que tous les tests passent** :
   ```bash
   python -m tests.run_tests
   ```

2. **Mettez à jour la documentation** :
   - Complétez le README.md de votre agent
   - Ajoutez des exemples d'utilisation
   - Documentez les limitations connues

3. **Créez une Pull Request** :
   - Poussez votre branche vers votre fork
   - Créez une PR vers le dépôt principal
   - Remplissez le template de PR avec une description détaillée

4. **Répondez aux commentaires** des mainteneurs du projet

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

Les scripts dans `scripts/` et les tests d'intégration dans `tests/integration/` permettent de tester l'orchestration des agents sur un grand nombre de textes, afin d'évaluer :

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

## Ressources pour les étudiants

### Documentation de référence
- [Documentation Semantic Kernel](https://learn.microsoft.com/fr-fr/semantic-kernel/)
- [Documentation Tweety Project](https://tweetyproject.org/doc/)
- [Guide des prompts efficaces](https://platform.openai.com/docs/guides/prompt-engineering)

### Tutoriels et exemples
- Explorez les agents existants pour comprendre leur fonctionnement
- Consultez les traces d'exécution dans le dossier `traces/` pour voir des exemples concrets
- Utilisez les scripts de test comme point de départ pour vos propres tests

### Aide et support
- N'hésitez pas à créer des issues GitHub pour poser des questions
- Consultez la documentation existante avant de demander de l'aide
- Partagez vos découvertes et solutions avec les autres étudiants