# Cartographie Architecturale : Outils d'Analyse Rhétorique

## 1. Couche d'Ingestion de Données (Data Ingestion Layer)

L'analyse du code a révélé que le système d'ingestion de données est le point d'entrée pour le traitement de sources externes comme des pages web ou des documents. Les deux principaux services externes utilisés sont **Apache Tika** pour l'extraction de texte à partir de documents (PDF, Office) et **Jina Reader** pour la conversion de pages web en Markdown.

### 1.1. Implémentation et Composants

Nous avons identifié deux implémentations distinctes et parallèles pour la récupération de ces données, ce qui constitue un point central de l'architecture actuelle.

#### Composants Clés :
*   **`config/settings.py`**: Fichier central de configuration utilisant Pydantic `BaseSettings`. Il définit tous les points de terminaison, les timeouts et autres paramètres pour les services externes (Tika, Jina) et l'application elle-même.
*   **`services/fetch_service.py`**: Contient la classe `FetchService`, qui est une implémentation robuste et bien conçue pour la récupération de données. Elle intègre des patrons de conception avancés comme le **Circuit Breaker** et des **stratégies de réessai**, ce qui la rend résiliente aux pannes réseau. Elle utilise l'injection de dépendances (un `CacheService`) et une logique de "dispatcher" pour choisir la méthode de récupération appropriée.
*   **`ui/fetch_utils.py`**: Un module de fonctions utilitaires qui **duplique** une grande partie de la logique de `FetchService`. Il est directement utilisé par l'interface utilisateur.
*   **`ui/app.py`**: L'application principale de l'interface utilisateur (basée sur IPyWidgets) qui, dans sa version actuelle, s'appuie sur `ui/fetch_utils.py` pour ses opérations de récupération.
*   **`services/cache_service.py`** et **`ui/cache_utils.py`**: Des services de cache distincts, un pour le service principal et un pour l'UI, qui persistent le texte récupéré pour éviter des appels réseau répétés.

### 1.2. Diagramme Architectural : Flux Actuel vs Cible

Le diagramme ci-dessous illustre le flux de données actuel, mettant en évidence la redondance, et propose une architecture cible refactorisée.

```mermaid
graph TD
    subgraph "Couche UI"
        A[UI Widgets: app.py]
    end

    subgraph "Logique d'Accès aux Données"
        B(ui/fetch_utils.py)
        C{services/fetch_service.py}
    end

    subgraph "Services Externes"
        D[Service Apache Tika]
        E[Service Jina Reader]
    end

    subgraph "Infrastructure & Cache"
        F[CacheService]
        G[Fichiers Bruts (temp_downloads)]
    end
    
    subgraph "Configuration"
        H[config/settings.py]
    end

    %% Flux Actuel - Redondant
    A -- "1. Appel direct (actuel)" --> B
    B -- "2a. Logique redondante" --> D
    B -- "2b. Logique redondante" --> E
    B -- "Cache Fichier" --> F

    %% Flux Cible - Recommandé
    A -.->| "3. Appel recommandé (refactoring)" | C

    %% Dépendances du Service
    C -- "4. Utilise" --> F
    C -- "5a. Stratégie Tika" --> D
    C -- "5b. Stratégie Jina" --> E
    F -- "Cache Tika" --> G
    
    C -- "Lit config" --> H
    B -- "Lit config" --> H

    classDef redundant fill:#f99,stroke:#333,stroke-width:2px;
    classDef recommended fill:#bbf,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;
    classDef service fill:#9f9,stroke:#333,stroke-width:2px;
    class B,D,E redundant;
    class C service;
```

### 1.3. Analyse de la Dette Technique et Recommandation

**Problème :**

L'architecture actuelle souffre d'une **duplication de code significative**. L'interface utilisateur (`app.py`) utilise `ui/fetch_utils.py`, une implémentation ad-hoc et moins robuste, au lieu de s'appuyer sur le `FetchService` centralisé.

Cette redondance engendre plusieurs problèmes :
1.  **Double Maintenance** : Toute mise à jour de la logique de récupération (par exemple, un changement d'API, une amélioration de la gestion des erreurs) doit être effectuée à deux endroits, augmentant le risque d'incohérence.
2.  **Manque de Robustesse** : L'implémentation de l'UI ne bénéficie pas pleinement des mécanismes avancés (Circuit Breaker, etc.) présents dans `FetchService`.
3.  **Complexité Accrue** : La présence de deux chemins pour effectuer la même tâche rend le code plus difficile à comprendre et à maintenir.

**Recommandation (Architecture Cible) :**

Il est fortement recommandé de **refactoriser** l'application pour éliminer cette redondance.

1.  **Centraliser la Logique** : Modifier `ui/app.py` pour qu'il instancie et utilise exclusivement `FetchService` pour toutes les opérations de récupération de données.
2.  **Supprimer le Code Redondant** : Le module `ui/fetch_utils.py` devrait être soit supprimé, soit réduit à de simples fonctions d'adaptation si nécessaire, mais toute la logique métier doit résider dans `FetchService`.
3.  **Unifier le Caching** : Assurer que toute l'application utilise une instance unique du `CacheService` pour garantir la cohérence des données mises en cache.

Cette refactorisation simplifiera considérablement la base de code, améliorera la robustesse de l'application et réduira la charge de maintenance future.