# 🧠 Agents IA (`agents/`)

Ce répertoire contient les définitions spécifiques à chaque agent IA participant à l'analyse rhétorique collaborative. L'objectif est que chaque agent ait son propre sous-répertoire pour une meilleure modularité.

[Retour au README Principal](../README.md)

## Structure

Chaque agent est organisé dans son propre sous-répertoire :

* **[`pm/`](./pm/README.md)** 🧑‍🏫 : Agent Project Manager - Orchestre l'analyse.
* **[`informal/`](./informal/README.md)** 🧐 : Agent d'Analyse Informelle - Identifie arguments et sophismes.
* **[`pl/`](./pl/README.md)** 📐 : Agent de Logique Propositionnelle - Gère la formalisation et l'interrogation logique via Tweety.
* **`(student_template/)`** : *(À créer)* Un template pour guider les étudiants dans l'ajout de leur propre agent.

Chaque sous-répertoire contient typiquement :
* `__init__.py`: Fichier vide.
* `*_definitions.py`: Classes Plugin (si besoin), fonction `setup_*_kernel`, constante `*_INSTRUCTIONS`.
* `prompts.py`: Constantes contenant les prompts sémantiques pour l'agent.