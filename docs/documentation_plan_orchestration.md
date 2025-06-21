# Plan de Documentation : Paquets `orchestration` et `pipelines`

## 1. Objectif Général

Ce document décrit le plan de mise à jour de la documentation pour les paquets `argumentation_analysis/orchestration` et `argumentation_analysis/pipelines`. L'objectif est de clarifier l'architecture, le flux de données, les responsabilités de chaque module et la manière dont ils collaborent.

## 2. Analyse Architecturale Préliminaire

L'analyse initiale révèle deux systèmes complémentaires mais distincts :

*   **`orchestration`**: Gère la collaboration complexe et dynamique entre agents, notamment via une architecture hiérarchique (Stratégique, Tactique, Opérationnel). C'est le "cerveau" qui décide qui fait quoi et quand.
*   **`pipelines`**: Définit des flux de traitement de données plus statiques et séquentiels. C'est la "chaîne de montage" qui applique une série d'opérations sur les données.

Une confusion potentielle existe avec la présence d'un sous-paquet `orchestration` dans `pipelines`. Cela doit être clarifié.

---

## 3. Plan de Documentation pour `argumentation_analysis/orchestration`

### 3.1. Documentation de Haut Niveau (READMEs)

1.  **`orchestration/README.md`**:
    *   **Contenu** : Description générale du rôle du paquet. Expliquer la philosophie d'orchestration d'agents. Présenter les deux approches principales disponibles : le `main_orchestrator` (dans `engine`) et l'architecture `hierarchical`.
    *   **Diagramme** : Inclure un diagramme Mermaid (block-diagram) illustrant les concepts clés.

2.  **`orchestration/hierarchical/README.md`**:
    *   **Contenu** : Description détaillée de l'architecture à trois niveaux (Stratégique, Tactique, Opérationnel). Expliquer les responsabilités de chaque couche et le flux de contrôle (top-down) et de feedback (bottom-up).
    *   **Diagramme** : Inclure un diagramme de séquence ou un diagramme de flux illustrant une requête typique traversant les trois couches.

3.  **Documentation par couche hiérarchique**: Créer/mettre à jour les `README.md` dans chaque sous-répertoire :
    *   `hierarchical/strategic/README.md`: Rôle : planification à long terme, allocation des ressources macro.
    *   `hierarchical/tactical/README.md`: Rôle : coordination des agents, résolution de conflits, monitoring des tâches.
    *   `hierarchical/operational/README.md`: Rôle : exécution des tâches par les agents, gestion de l'état, communication directe avec les agents via les adaptateurs.

### 3.2. Documentation du Code (Docstrings)

La priorité sera mise sur les modules et classes suivants :

1.  **Interfaces (`orchestration/hierarchical/interfaces/`)**:
    *   **Fichiers** : `strategic_tactical.py`, `tactical_operational.py`.
    *   **Tâche** : Documenter chaque classe et méthode d'interface pour définir clairement les contrats entre les couches. Utiliser des types hints précis.

2.  **Managers de chaque couche**:
    *   **Fichiers** : `strategic/manager.py`, `tactical/manager.py`, `operational/manager.py`.
    *   **Tâche** : Documenter la classe `Manager` de chaque couche, en expliquant sa logique principale, ses états et ses interactions.

3.  **Adaptateurs (`orchestration/hierarchical/operational/adapters/`)**:
    *   **Fichiers** : `extract_agent_adapter.py`, `informal_agent_adapter.py`, etc.
    *   **Tâche** : Pour chaque adaptateur, documenter comment il traduit les commandes opérationnelles en actions spécifiques pour chaque agent et comment il remonte les résultats. C'est un point crucial pour l'extensibilité.

4.  **Orchestrateurs spécialisés**:
    *   **Fichiers** : `cluedo_orchestrator.py`, `conversation_orchestrator.py`, etc.
    *   **Tâche** : Ajouter un docstring de module expliquant le cas d'usage spécifique de l'orchestrateur. Documenter la classe principale, ses paramètres de configuration et sa logique de haut niveau.

---

## 4. Plan de Documentation pour `argumentation_analysis/pipelines`

### 4.1. Documentation de Haut Niveau (READMEs)

1.  **`pipelines/README.md`**: (À créer)
    *   **Contenu** : Décrire le rôle du paquet : fournir des séquences de traitement prédéfinies. Expliquer la différence avec le paquet `orchestration`. Clarifier la relation avec le sous-paquet `pipelines/orchestration`.
    *   **Diagramme** : Schéma illustrant une pipeline typique avec ses étapes.

2.  **`pipelines/orchestration/README.md`**: (À créer)
    *   **Contenu**: Expliquer pourquoi ce sous-paquet existe. Est-ce un framework d'orchestration spécifique aux pipelines ? Est-ce un lien vers le paquet principal ? Clarifier la redondance apparente des orchestrateurs spécialisés. **Action requise :** investiguer pour clarifier l'intention architecturale avant de documenter.

### 4.2. Documentation du Code (Docstrings)

1.  **Pipelines principaux**:
    *   **Fichiers** : `analysis_pipeline.py`, `embedding_pipeline.py`, `unified_pipeline.py`, `unified_text_analysis.py`.
    *   **Tâche** : Pour chaque fichier, ajouter un docstring de module décrivant l'objectif de la pipeline, ses étapes (processeurs), les données d'entrée attendues et les artefacts produits en sortie.

2.  **Processeurs d'analyse (`pipelines/orchestration/analysis/`)**:
    *   **Fichiers** : `processors.py`, `post_processors.py`.
    *   **Tâche** : Documenter chaque fonction ou classe de processeur : sa responsabilité unique, ses entrées, ses sorties.

3.  **Moteur d'exécution (`pipelines/orchestration/execution/`)**:
    *   **Fichiers** : `engine.py`, `strategies.py`.
    *   **Tâche** : Documenter le moteur d'exécution des pipelines, comment il charge et exécute les étapes, et comment les stratégies peuvent être utilisées pour modifier son comportement.

## 5. Prochaines Étapes

1.  **Valider ce plan** avec l'équipe.
2.  **Clarifier l'architecture** du sous-paquet `pipelines/orchestration`.
3.  **Commencer la rédaction** de la documentation en suivant les priorités définies.