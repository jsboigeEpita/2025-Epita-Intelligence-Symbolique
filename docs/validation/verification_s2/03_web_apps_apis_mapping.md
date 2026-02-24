# Cartographie du Système : Web-Apps et APIs

Ce document détaille l'architecture des applications web et des API identifiées dans le projet, conformément à la Phase 1/3 de la campagne de vérification.

## 1. Points d'Entrée des Applications

Le système expose principalement deux applications web : une API FastAPI moderne et une application Flask plus complète servant également une interface utilisateur.

- **API FastAPI**
  - **Fichier :** [`api/main.py`](api/main.py)
  - **Description :** Point d'entrée pour une API RESTful basée sur FastAPI. Elle gère l'initialisation de l'environnement du projet, y compris la JVM, et expose des endpoints pour l'analyse d'arguments.

- **Application Web Flask**
  - **Fichier :** [`argumentation_analysis/services/web_api/app.py`](argumentation_analysis/services/web_api/app.py)
  - **Description :** Application web complète utilisant Flask. Elle sert à la fois une API REST et une interface utilisateur React. Comme l'API FastAPI, elle initialise la JVM au démarrage et est rendue compatible ASGI via `WsgiToAsgi`.

- **Autres Points d'Entrée Notables**
  - **Streamlit UI :** [`Arg_Semantic_Index/UI_streamlit.py`](Arg_Semantic_Index/UI_streamlit.py) - Une interface utilisateur simple pour interagir avec l'index sémantique.
  - **Démos :** Les scripts dans `argumentation_analysis/demos/` (ex: `run_demo.py`) servent de points d'entrée pour des démonstrations spécifiques.

## 2. Endpoints d'API

### 2.1 API FastAPI (`api/`)

Ce service est structuré autour de deux routeurs principaux avec des préfixes distincts.

**Routeur Principal (préfixe: `/api`)**

| Méthode | Route              | Description                                                                 |
| :------ | :----------------- | :-------------------------------------------------------------------------- |
| `POST`  | `/analyze`         | Analyse un texte simple pour extraire prémisses et conclusion (via Tweety). |
| `GET`   | `/status`          | Vérifie l'état de disponibilité des services d'analyse.                     |
| `GET`   | `/examples`        | Retourne une liste d'exemples de textes pour l'analyse.                     |
| `GET`   | `/health`          | Endpoint de santé simple pour confirmer que l'API est en cours d'exécution. |
| `GET`   | `/endpoints`       | Fournit une liste auto-générée de tous les endpoints disponibles.           |

**Routeur de Framework de Dung (préfixe: `/api/v1/framework`)**

| Méthode | Route      | Description                                                    |
| :------ | :--------- | :------------------------------------------------------------- |
| `POST`  | `/analyze` | Analyse un framework d'argumentation de Dung complet (graphe). |

### 2.2 Application Web Flask (`argumentation_analysis/services/web_api/`)

Cette application utilise des Blueprints pour organiser ses routes.

**Blueprint Principal (préfixe: `/api`)**

| Méthode | Route         | Description                                                          |
| :------ | :------------ | :------------------------------------------------------------------- |
| `GET`   | `/health`     | Health check détaillé incluant l'état de la JVM et des services.   |
| `POST`  | `/analyze`    | Analyse complète et asynchrone d'un texte argumentatif.            |
| `POST`  | `/validate`   | Valide la structure logique d'un argument fourni.                    |
| `POST`  | `/fallacies`  | Détecte les sophismes dans un texte.                                 |
| `POST`  | `/framework`  | Construit et analyse un framework d'argumentation de Dung.           |
| `GET`   | `/endpoints`  | Liste statique des principaux endpoints de l'API.                    |

**Blueprint Logique (préfixe: `/api/logic`)**

| Méthode | Route               | Description                                           |
| :------ | :------------------ | :---------------------------------------------------- |
| `POST`  | `/belief-set`       | Convertit un texte en un ensemble de croyances logiques. |
| `POST`  | `/query`            | Exécute une requête sur un ensemble de croyances.     |
| `POST`  | `/generate-queries` | Suggère des requêtes pertinentes basées sur un texte. |

## 3. Composants Clés

### 3.1 Architecture Globale

```mermaid
graph TD
    subgraph "Clients"
        User[Utilisateur via Navigateur]
        Dev[Développeur via client API]
    end

    subgraph "Services Web"
        Flask[Application Flask (Web UI + API)]
        FastAPI[API FastAPI (Services spécialisés)]
    end

    subgraph "Logique Métier (Services)"
        AnalysisService["AnalysisService"]
        ValidationService["ValidationService"]
        FallacyService["FallacyService"]
        FrameworkService["FrameworkService"]
        LogicService["LogicService (Moteur logique)"]
        DungService["DungAnalysisService (Tweety)"]
    end

    subgraph "Dépendances Fondamentales"
        JVM["JVM (via JPype)"]
        TweetyLib["Bibliothèque Tweety"]
    end

    User --> Flask
    Dev --> Flask
    Dev --> FastAPI

    Flask --> AnalysisService
    Flask --> ValidationService
    Flask --> FallacyService
    Flask --> FrameworkService
    Flask --> LogicService

    FastAPI --> DungService

    DungService -- "utilise" --> JVM
    LogicService -- "utilise" --> JVM
    JVM -- "charge" --> TweetyLib
```

### 3.2 Modèles de Données (Pydantic)

- **`api/models.py`** : Définit les modèles pour l'API FastAPI, y compris `FrameworkAnalysisRequest` qui structure les données pour l'analyse de graphes d'arguments.
- **`argumentation_analysis/services/web_api/models/`** : Contient les modèles de requête (`request_models.py`) et de réponse (`response_models.py`) pour l'application Flask, couvrant toutes les fonctionnalités de l'API.

### 3.3 Services d'Analyse

- Les services (`AnalysisService`, `LogicService`, etc.) situés dans `argumentation_analysis/services/web_api/services/` encapsulent la logique métier.
- Ils dépendent fortement de la couche `argumentation_analysis.core` et `argumentation_analysis.agents` pour interagir avec la JVM et exécuter les analyses logiques.

## 4. Fichiers Statiques et Templates

- L'application Flask est configurée pour servir une application frontend React.
- **Répertoire du build React :** `argumentation_analysis/services/web_api/interface-web-argumentative/build`
- **Mécanisme :** La route `serve_react_app` dans `argumentation_analysis/services/web_api/app.py` sert le fichier `index.html` pour toutes les routes non-API, permettant à React de gérer le routage côté client.

## 5. Hypothèses de Workflow

### 5.1 Workflow Utilisateur (via UI)

1.  L'utilisateur accède à l'URL racine de l'application Flask.
2.  Le serveur Flask sert l'application React (`index.html` et les assets JS/CSS).
3.  L'interface utilisateur React permet à l'utilisateur de saisir du texte, de construire des graphes ou de soumettre des arguments.
4.  Les requêtes sont envoyées depuis le navigateur vers les endpoints de l'API Flask (`/api/...`).
5.  Le backend Flask traite la requête en utilisant les services appropriés, qui peuvent faire appel à la JVM.
6.  Le résultat est retourné au format JSON à l'interface React, qui l'affiche à l'utilisateur.

### 5.2 Workflow Développeur (via API)

1.  Un développeur envoie une requête HTTP à l'un des endpoints (soit sur l'API FastAPI, soit sur l'application Flask).
2.  La requête doit être formatée selon les modèles Pydantic définis (ex: `FrameworkAnalysisRequest`).
3.  Le serveur traite la requête et retourne une réponse JSON structurée. Ce workflow est utilisé pour l'intégration avec d'autres systèmes ou pour des tests automatisés.