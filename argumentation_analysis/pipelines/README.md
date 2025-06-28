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

Le sous-paquet `pipelines/orchestration` contient le **moteur d'exécution** (`engine`) et la **logique de séquencement** (`processors`) spécifiques aux pipelines. Il ne doit pas être confondu avec le paquet principal `orchestration`. Ici, "orchestration" est utilisé dans un sens plus restreint : l'ordonnancement des étapes d'une pipeline, et non la coordination d'agents intelligents.

## 4. Schéma d'une Pipeline Typique

```mermaid
graph TD
    A[Donnée d'entrée] --> B{Processeur 1: Nettoyage};
    B --> C{Processeur 2: Extraction d'entités};
    C --> D{Processeur 3: Analyse de sentiments};
    D --> E[Artefact de sortie];