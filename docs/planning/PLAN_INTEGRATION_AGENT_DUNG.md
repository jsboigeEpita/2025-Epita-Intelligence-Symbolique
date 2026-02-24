# Plan d'Intégration et de Refactorisation : Agent d'Argumentation de Dung

_Version 2 - Ce document remplace et annule toutes les versions précédentes. Il prend en compte les découvertes architecturales faites durant l'analyse._

## 1. Contexte et Découverte d'un Problème Architectural

La tâche initiale était d'intégrer l'agent d'argumentation de Dung (`abs_arg_dung/`) dans le système existant. L'analyse a révélé une architecture inattendue : la fonctionnalité de "framework" de l'interface utilisateur React n'était pas gérée par le backend principal (FastAPI dans `api/`), mais par un **service Flask autonome et non documenté** situé dans `services/web_api_from_libs/`.

Ce service duplique la logique, introduit une complexité inutile, des problèmes de configuration (le port était incorrect) et rend la maintenance difficile.

**Ce plan ne se contente donc plus d'intégrer, il vise à corriger cette architecture déviante.**

L'objectif est de :
1.  **Intégrer correctement** l'agent `abs_arg_dung` dans le backend principal FastAPI.
2.  **Reconnecter** l'interface utilisateur React à ce nouvel endpoint, propre et centralisé.
3.  **Planifier la dépréciation** et la suppression du service Flask redondant.

## 2. Architecture Cible Proposée

L'architecture cible centralise la logique d'argumentation dans le backend FastAPI, éliminant ainsi le service Flask isolé.

### 2.1. Création d'un Service d'Argumentation Centralisé

Un nouveau service sera ajouté au sein de l'application FastAPI principale.

-   **Fichier** : `api/services.py`
-   **Nouvelle Classe** : `DungAnalysisAgent`
    -   **Responsabilités** :
        -   Gérer le cycle de vie de la JVM via JPype pour interagir avec l'agent `abs_arg_dung`.
        -   Exposer une méthode `analyze_framework_async(request_data)` qui enveloppera l'appel bloquant à l'agent dans `asyncio.to_thread`.
        -   Gérer la transformation des données entre les modèles Pydantic de l'API et les objets requis par l'agent.

### 2.2. Exposition via un Nouvel Endpoint API

Un nouvel endpoint sera créé pour exposer cette fonctionnalité.

-   **Fichier** : `api/endpoints.py`
-   **Nouvel Endpoint** : `POST /api/v1/framework/analyze`
    -   **Responsabilités** :
        -   Recevoir les requêtes de l'interface utilisateur.
        -   Valider les données d'entrée à l'aide d'un modèle Pydantic (dans `api/models.py`).
        -   Appeler la méthode `analyze_framework_async` du `DungAnalysisAgent`.
        -   Retourner le résultat au client.

### 2.3. Modification de l'Interface Utilisateur React

Le frontend sera reconfiguré pour utiliser ce nouvel endpoint centralisé.

-   **Fichier** : `services/web_api/interface-web-argumentative/src/services/api.js`
-   **Modification** :
    -   L'URL de base de l'API sera modifiée pour pointer vers le backend FastAPI principal (dont le port devra être confirmé, mais probablement `8000` par défaut pour FastAPI).
    -   La fonction qui appelle `/api/framework` sera modifiée pour appeler le nouvel endpoint `POST /api/v1/framework/analyze`.

## 3. Diagramme de l'Architecture Cible

```mermaid
graph TD
    subgraph "Navigateur Utilisateur"
        Frontend[React SPA<br>(interface-web-argumentative)]
    end

    subgraph "Infrastructure Backend Centralisée"
        APIFast[Backend Principal FastAPI<br>(api/)]
    end
    
    subgraph "Services Externes / Bibliothèques"
        Tweety[JVM / TweetyProject via JPype]
    end

    subgraph "Composants à Supprimer"
        style Composants à Supprimer fill:#ffcccc,stroke:#333,stroke-width:2px
        APIFlask(Backend Flask<br>services/web_api_from_libs)
    end

    Frontend -->|Appels API<br>POST /api/v1/framework/analyze| APIFast;
    
    APIFast -->|Appel de service| DungAgent[DungAnalysisAgent<br>(dans api/services.py)];
    DungAgent -->|Appel via JPype| Tweety;

```

## 4. Plan d'Implémentation Technique

1.  **Phase 1 : Backend**
    -   Ajouter la classe `DungAnalysisAgent` dans [`api/services.py`](api/services.py).
    -   Ajouter les modèles de requête/réponse nécessaires dans [`api/models.py`](api/models.py).
    -   Ajouter la route `POST /api/v1/framework/analyze` dans [`api/endpoints.py`](api/endpoints.py).
    -   Enregistrer le nouveau routeur dans l'application principale [`api/main.py`](api/main.py).

2.  **Phase 2 : Frontend**
    -   Identifier le port et l'URL du backend FastAPI principal.
    -   Mettre à jour le fichier [`services/web_api/interface-web-argumentative/src/services/api.js`](services/web_api/interface-web-argumentative/src/services/api.js) pour qu'il pointe vers le nouvel endpoint.

3.  **Phase 3 : Nettoyage**
    -   Mettre à jour le `README.md` du service `services/web_api_from_libs` pour le marquer comme **DÉPRÉCIÉ** et indiquer qu'il ne doit plus être utilisé.
    -   (Action future) Supprimer complètement le répertoire `services/web_api_from_libs`.

## 5. Livrables et Étapes Suivantes

Ce plan d'architecture et de refactorisation constitue le livrable principal. Une fois validé, la prochaine étape sera de passer en mode `code` pour exécuter le plan d'implémentation ci-dessus.