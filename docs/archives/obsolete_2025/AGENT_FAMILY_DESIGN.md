# Conception d'une Famille d'Agents de Détection de Sophismes

## 1. Introduction

Ce document présente la conception d'une famille d'agents spécialisés dans la détection de sophismes informels. Chaque agent, ou "archétype", utilise une stratégie opérationnelle distincte, tirant parti des différents workflows développés au cours de l'évolution du `InformalFallacyAgent` (voir [`PLUGIN_GENEALOGY.md`](PLUGIN_GENEALOGY.md:1)).

L'objectif est de créer un système flexible où l'on peut sélectionner l'agent le plus adapté à une tâche donnée, en fonction des besoins en matière de vitesse, de précision, de coût ou d'explicabilité.

## 2. Les Archétypes d'Agents

Nous proposons trois archétypes distincts, chacun avec ses propres forces et faiblesses.

### Archétype 1 : L'Auditeur Méthodique (Methodical Auditor)

*   **Description de la Stratégie :** Cet agent suit une approche séquentielle et déductive rigoureuse. Inspiré par le workflow "Progressive Focus", il commence son analyse à la racine de la taxonomie des sophismes et explore chaque branche de manière itérative, ne descendant que dans les chemins jugés pertinents. Chaque étape de son raisonnement est explicitement tracée.
*   **Plugins / Workflows Clés :**
    *   Utilise un workflow séquentiel contraint (`Forced Sequential Workflow`).
    *   S'appuie fortement sur des outils d'exploration de taxonomie (par ex. `TaxonomyDisplayPlugin`).
    *   N'utilise l'outil `identify_fallacies` qu'à la toute fin du processus, après une exploration complète.
*   **Forces :**
    *   **Haute Traçabilité :** Le parcours de l'agent est facile à suivre et à auditer.
    *   **Précision Maximale :** En évitant les sauts logiques, il est moins susceptible de faire des erreurs de classification.
    *   **Explicabilité :** Idéal pour générer des justifications détaillées pour chaque sophisme identifié.
*   **Faiblesses :**
    *   **Lenteur :** L'approche séquentielle en fait l'agent le plus lent.
    *   **Coût Potentiel :** Peut nécessiter de nombreux appels au modèle pour explorer la taxonomie en profondeur.

### Archétype 2 : L'Explorateur Parallèle (Parallel Explorer)

*   **Description de la Stratégie :** Cet agent est l'implémentation de la nouvelle architecture "map-reduce" sémantique. Il décompose le problème en sous-tâches indépendantes, lançant plusieurs "mini-analyses" en parallèle pour différentes catégories de sophismes. Les résultats sont ensuite agrégés par un composant de synthèse dédié.
*   **Plugins / Workflows Clés :**
    *   Orchestré par le `ParallelWorkflowManager`.
    *   Lance N instances de fonctions sémantiques d'exploration en parallèle.
    *   Utilise un `SynthesisPlugin` pour agréger et consolider les résultats des différentes branches.
*   **Forces :**
    *   **Vitesse :** C'est de loin l'approche la plus rapide pour une analyse complète.
    *   **Couverture Large :** Explore de nombreuses hypothèses simultanément, ce qui lui permet de détecter des sophismes variés.
    *   **Scalabilité :** L'architecture est conçue pour être scalable à un plus grand nombre de catégories de sophismes.
*   **Faiblesses :**
    *   **Moins Traçable :** Le raisonnement est distribué, ce qui le rend plus complexe à auditer qu'une approche séquentielle.
    *   **Dépendance à la Synthèse :** La qualité du résultat final dépend fortement de la capacité du plugin de synthèse à résoudre les conflits et à agréger les informations de manière cohérente.

### Archétype 3 : L'Assistant de Recherche (Research Assistant)

*   **Description de la Stratégie :** Cet agent est une réutilisation astucieuse de l'ancien workflow parallèle (`4d7132cc`). Son but n'est pas de réaliser une analyse de bout en bout, mais de servir d'outil de collecte d'informations rapide. Il récupère en parallèle les descriptions de plusieurs branches de la taxonomie pour les présenter de manière comparative.
*   **Plugins / Workflows Clés :**
    *   Utilise une version simplifiée du `FallacyWorkflowPlugin` original.
    *   Se concentre sur l'appel parallèle de la fonction `TaxonomyDisplayPlugin.display_branch`.
    *   **N'utilise pas** l'outil `identify_fallacies`. Son travail s'arrête à la présentation des informations.
*   **Forces :**
    *   **Collecte d'Information Rapide :** Excellent pour obtenir une vue d'ensemble de plusieurs concepts sans lancer une analyse complète.
    *   **Flexibilité :** Peut être utilisé comme un outil par un autre agent (par exemple, l'Auditeur Méthodique pourrait l'utiliser pour décider quelle branche explorer ensuite) ou par un utilisateur humain.
    *   **Faible Coût :** Les appels sont simples et peu coûteux.
*   **Faiblesses :**
    *   **Pas d'Analyse :** Ne fournit aucune conclusion, seulement des informations brutes.
    *   **Usage Spécifique :** Son utilité est limitée à des tâches de recherche et de comparaison.

## 3. Conclusion

Cette famille d'agents offre un éventail de stratégies pour aborder la détection de sophismes. Le choix de l'archétype à déployer pourra être configuré en fonction du contexte, permettant de passer d'une analyse rapide et globale à une investigation lente et méticuleuse selon les besoins.