# 🧐 Informal Analysis Agent (`agents/informal/`)

Agent spécialisé dans l'analyse informelle du discours : identification d'arguments et de sophismes courants.

[Retour au README Agents](../README.md)

## Rôle 📈

* **Identifier les arguments** principaux présents dans le texte source en utilisant une fonction sémantique (`InformalAnalyzer.semantic_IdentifyArguments`) et les enregistrer dans l'état partagé via `StateManager.add_identified_argument`.
* **Analyser les sophismes** :
    * Explorer une taxonomie externe de sophismes (fichier CSV issu du projet Argumentum, téléchargé et géré par le plugin) via la fonction native `InformalAnalyzer.explore_fallacy_hierarchy`.
    * Obtenir les détails (description, exemple...) d'un sophisme spécifique via son identifiant (PK) en utilisant `InformalAnalyzer.get_fallacy_details`.
    * Attribuer un sophisme identifié à un argument spécifique dans l'état partagé via `StateManager.add_identified_fallacy`.
* **Répondre** aux tâches assignées par le Project Manager en enregistrant un résumé de ses actions via `StateManager.add_answer`.

## Composants 🛠️

* **[`informal_definitions.py`](./informal_definitions.py)** :
    * Constantes (URL et chemin du CSV de taxonomie).
    * `InformalAnalysisPlugin`: Classe gérant :
        * Le téléchargement et le parsing (via Pandas) du CSV.
        * Le caching en mémoire du DataFrame Pandas résultant.
        * Les fonctions natives (`@kernel_function`) `explore_fallacy_hierarchy` et `get_fallacy_details` pour interagir avec la taxonomie.
    * `setup_informal_kernel`: Fonction de configuration du kernel SK.
    * `INFORMAL_AGENT_INSTRUCTIONS`: Instructions système détaillant le rôle, les outils (plugin, StateManager) et les workflows spécifiques (identifier args, explorer/détailler/attribuer sophisme).
* **[`prompts.py`](./prompts.py)** :
    * `prompt_identify_args_v*`: Prompt pour l'identification sémantique des arguments.

### Test du Plugin (Note)

Le notebook original contenait une cellule de test (commentée) pour valider le `InformalAnalysisPlugin` isolément (chargement CSV, exploration, détails, attribution simulée). Ce code n'a pas été migré ici mais pourrait être adapté dans un fichier de test séparé (ex: `tests/test_informal_plugin.py`).