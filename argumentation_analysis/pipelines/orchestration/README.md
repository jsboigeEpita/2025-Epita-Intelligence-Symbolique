# Moteur d'Orchestration de Pipelines

## 1. Rôle et Intention

Ce paquet contient le **moteur d'exécution** pour le système de `pipelines`. Le terme "orchestration" est utilisé ici dans un sens beaucoup plus restreint que dans le paquet `orchestration` principal : il ne s'agit pas de coordonner des agents intelligents, mais d'**ordonnancer l'exécution séquentielle des étapes (processeurs) d'une pipeline**.

Ce paquet fournit un mini-framework pour :
- **Définir** des étapes de traitement (`analysis/processors.py`).
- **Configurer** des pipelines en assemblant ces étapes (`config/`).
- **Exécuter** une pipeline sur des données d'entrée (`execution/engine.py`).
- **Adapter** le comportement de l'exécution via des stratégies (`execution/strategies.py`).

## 2. Structure du Framework

-   **`core/`**: Définit les structures de données de base, comme les `PipelineData` qui encapsulent les données transitant d'une étape à l'autre.
-   **`analysis/`**: Contient les briques de traitement atomiques (les `processors` et `post_processors`). Chaque processeur est une fonction ou une classe qui effectue une seule tâche (ex: normaliser le texte, extraire les arguments).
-   **`config/`**: Contient les définitions des pipelines. Un fichier de configuration de pipeline est une liste ordonnée de processeurs à appliquer.
-   **`execution/`**: Contient le cœur du moteur. L'`engine.py` prend une configuration de pipeline et des données, et exécute chaque processeur dans l'ordre. Les `strategies.py` permettent de modifier ce comportement (ex: exécuter en mode "dry-run", gérer les erreurs différemment).
-   **`orchestrators/`**: Contient des orchestrateurs de haut niveau qui encapsulent la logique d'exécution d'une pipeline complète pour un cas d'usage donné (ex: `analysis_orchestrator.py` pour une analyse de texte complète).

En résumé, ce paquet est un système d'exécution de "chaînes de montage" où les machines sont les processeurs et les produits sont les données analysées.