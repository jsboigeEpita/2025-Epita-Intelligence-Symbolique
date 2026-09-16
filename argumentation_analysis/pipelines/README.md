# Paquet `pipelines`

## 1. Rôle et Philosophie

Le paquet `pipelines` est conçu pour exécuter des **séquences de traitement de données prédéfinies et linéaires**. Il représente la "chaîne de montage" du système, où une donnée d'entrée traverse une série d'étapes de transformation (processeurs) pour produire un résultat final.

Contrairement au paquet `orchestration`, qui gère une collaboration dynamique et complexe entre agents, le paquet `pipelines` est optimisé pour des flux de travail plus statiques et déterministes.

## 2. Distinction avec le paquet `orchestration`

| Caractéristique | **`pipelines`** | **`orchestration`** |
| :--- | :--- | :--- |
| **Logique** | Séquentielle, linéaire | Dynamique, événementielle, parallèle |
| **Flux** | "Chaîne de montage" | "Équipe d'experts" |
| **Flexibilité** | Faible (flux prédéfini) | Élevée (adaptation au contexte) |
| **Cas d'usage** | Traitement par lot, ETL, exécution d'une séquence d'analyses simple. | Analyse complexe multi-facettes, résolution de problèmes, dialogue. |

## 3. Relation avec `pipelines/orchestration`

Le sous-paquet `pipelines/orchestration` conserve uniquement un vocabulaire de configuration et des stratégies historiques sans appelant production. Son ancien moteur `execution/engine.py` et ses helpers `analysis/` ont été retirés dans #2113 : le chemin était orphelin et déjà refusé explicitement par `pipelines/unified_pipeline.py`. Il ne doit pas être confondu avec le paquet principal `orchestration`, qui porte le `WorkflowExecutor` vivant.

## 4. Schéma d'une Pipeline Typique

```mermaid
graph TD
    A[Donnée d'entrée] --> B{Processeur 1: Nettoyage};
    B --> C{Processeur 2: Extraction d'entités};
    C --> D{Processeur 3: Analyse de sentiments};
    D --> E[Artefact de sortie];