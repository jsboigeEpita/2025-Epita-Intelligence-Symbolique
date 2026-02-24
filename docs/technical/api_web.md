# API Web Applicative

## Introduction

Le projet expose ses fonctionnalités d'analyse argumentative via une API web RESTful. Cette API permet d'intégrer facilement les capacités d'analyse dans diverses applications, notamment des interfaces web.

Elle est construite avec le framework Flask et son fichier principal d'initialisation et de routage (pour les fonctionnalités non logiques) se trouve dans [`argumentation_analysis/services/web_api/app.py`](../../argumentation_analysis/services/web_api/app.py:1). Les routes spécifiques aux fonctionnalités logiques sont définies dans [`argumentation_analysis/services/web_api/routes/logic_routes.py`](../../argumentation_analysis/services/web_api/routes/logic_routes.py:1).

## Principes Généraux

L'API suit les conventions RESTful standard :

*   **Format des Données :** Toutes les requêtes et réponses utilisent le format JSON.
*   **Encodage :** L'encodage UTF-8 est utilisé pour les chaînes de caractères.
*   **Méthodes HTTP :** Les méthodes HTTP standard (GET, POST) sont utilisées pour interagir avec les ressources.
*   **Codes de Statut HTTP :** L'API utilise les codes de statut HTTP pour indiquer le succès ou l'échec des requêtes (par exemple, `200 OK`, `400 Bad Request`, `500 Internal Server Error`).

## Points de Terminaison (Endpoints)

Voici la liste des principaux points de terminaison exposés par l'API.

### Endpoints Principaux

Ces endpoints sont définis dans [`argumentation_analysis/services/web_api/app.py`](../../argumentation_analysis/services/web_api/app.py:1).

#### 1. Vérification de l'état de l'API

*   **Méthode HTTP :** `GET`
*   **URL :** `/api/health`
*   **Objectif :** Permet de vérifier si l'API et ses services dépendants sont opérationnels.
*   **Requête :** Aucune.
*   **Réponse :**
    *   **Succès (200 OK) :** Un objet JSON indiquant le statut global de l'API, sa version, et le statut de chaque service individuel.
        ```json
        {
          "status": "healthy",
          "message": "API d'analyse argumentative opérationnelle",
          "version": "1.0.0",
          "services": {
            "analysis": true, // ou false
            "validation": true,
            "fallacy": true,
            "framework": true,
            "logic": true
          }
        }
        ```
    *   **Erreur (500 Internal Server Error) :** Si une erreur survient lors de la vérification.
        ```json
        {
          "error": "Erreur de health check",
          "message": "Description de l'erreur",
          "status_code": 500
        }
        ```

#### 2. Analyse Complète d'un Texte

*   **Méthode HTTP :** `POST`
*   **URL :** `/api/analyze`
*   **Objectif :** Effectue une analyse argumentative complète d'un texte fourni, incluant potentiellement la détection de sophismes, l'analyse structurelle et l'évaluation de la cohérence.
*   **Requête :**
    *   Corps JSON :
        ```json
        {
          "text": "Le texte argumentatif à analyser ici.",
          "options": {
            "detect_fallacies": true,
            "analyze_structure": true,
            "evaluate_coherence": true,
            "include_context": true,
            "severity_threshold": 0.5
          }
        }
        ```
    *   Champs :
        *   `text` (string, requis) : Le texte à analyser.
        *   `options` (object, optionnel) : Options pour l'analyse (voir [`AnalysisOptions`](../../argumentation_analysis/services/web_api/models/request_models.py:12) dans [`request_models.py`](../../argumentation_analysis/services/web_api/models/request_models.py:1)).
*   **Réponse :**
    *   **Succès (200 OK) :** Un objet JSON contenant les résultats de l'analyse (voir [`AnalysisResponse`](../../libs/web_api/models/response_models.py:44)).
    *   **Erreur (400 Bad Request) :** Si les données de la requête sont manquantes ou invalides.
        ```json
        {
          "error": "Données manquantes" / "Données invalides",
          "message": "Le body JSON est requis" / "Erreur de validation: ...",
          "status_code": 400
        }
        ```
    *   **Erreur (500 Internal Server Error) :** Si une erreur interne survient pendant l'analyse.
        ```json
        {
          "error": "Erreur d'analyse",
          "message": "Description de l'erreur",
          "status_code": 500
        }
        ```

#### 3. Validation Logique d'un Argument

*   **Méthode HTTP :** `POST`
*   **URL :** `/api/validate`
*   **Objectif :** Évalue la validité logique d'un argument donné par ses prémisses et sa conclusion.
*   **Requête :**
    *   Corps JSON :
        ```json
        {
          "premises": ["Prémisse 1.", "Si Prémisse 1 alors Prémisse 2."],
          "conclusion": "Donc, Prémisse 2.",
          "argument_type": "deductive"
        }
        ```
    *   Champs :
        *   `premises` (list[string], requis) : Liste des prémisses de l'argument.
        *   `conclusion` (string, requis) : Conclusion de l'argument.
        *   `argument_type` (string, optionnel) : Type d'argument (`deductive`, `inductive`, `abductive`). Défaut : `deductive`. (voir [`ValidationRequest`](../../argumentation_analysis/services/web_api/models/request_models.py:34))
*   **Réponse :**
    *   **Succès (200 OK) :** Un objet JSON avec le résultat de la validation (voir [`ValidationResponse`](../../libs/web_api/models/response_models.py:44)).
    *   **Erreur (400/500) :** Similaire à `/api/analyze`.

#### 4. Détection de Sophismes

*   **Méthode HTTP :** `POST`
*   **URL :** `/api/fallacies`
*   **Objectif :** Identifie les sophismes présents dans un texte.
*   **Requête :**
    *   Corps JSON :
        ```json
        {
          "text": "Ce politicien est mauvais car il a une drôle de tête.",
          "options": {
            "severity_threshold": 0.5,
            "include_context": true,
            "max_fallacies": 10,
            "categories": ["ad hominem"]
          }
        }
        ```
    *   Champs :
        *   `text` (string, requis) : Le texte à analyser pour les sophismes.
        *   `options` (object, optionnel) : Options pour la détection (voir [`FallacyOptions`](../../argumentation_analysis/services/web_api/models/request_models.py:65) et [`FallacyRequest`](../../argumentation_analysis/services/web_api/models/request_models.py:73)).
*   **Réponse :**
    *   **Succès (200 OK) :** Un objet JSON listant les sophismes détectés (voir [`FallacyResponse`](../../libs/web_api/models/response_models.py:44)).
    *   **Erreur (400/500) :** Similaire à `/api/analyze`.

#### 5. Construction d'un Framework de Dung

*   **Méthode HTTP :** `POST`
*   **URL :** `/api/framework`
*   **Objectif :** Construit un framework d'argumentation de Dung à partir d'un ensemble d'arguments et de leurs relations d'attaque/support.
*   **Requête :**
    *   Corps JSON :
        ```json
        {
          "arguments": [
            {
              "id": "A",
              "content": "L'IA va sauver le monde.",
              "attacks": ["B"]
            },
            {
              "id": "B",
              "content": "L'IA va causer notre perte.",
              "attacks": ["A"]
            }
          ],
          "options": {
            "compute_extensions": true,
            "semantics": "preferred",
            "include_visualization": true
          }
        }
        ```
    *   Champs :
        *   `arguments` (list[object], requis) : Liste des arguments, chacun avec `id`, `content`, `attacks` (optionnel), `supports` (optionnel). (voir [`Argument`](../../argumentation_analysis/services/web_api/models/request_models.py:86))
        *   `options` (object, optionnel) : Options pour la construction et l'analyse du framework (voir [`FrameworkOptions`](../../argumentation_analysis/services/web_api/models/request_models.py:108) et [`FrameworkRequest`](../../argumentation_analysis/services/web_api/models/request_models.py:116)).
*   **Réponse :**
    *   **Succès (200 OK) :** Un objet JSON représentant le framework construit, potentiellement avec ses extensions sémantiques et une visualisation (voir [`FrameworkResponse`](../../libs/web_api/models/response_models.py:44)).
    *   **Erreur (400/500) :** Similaire à `/api/analyze`.

#### 6. Lister les Endpoints

*   **Méthode HTTP :** `GET`
*   **URL :** `/api/endpoints`
*   **Objectif :** Fournit une liste auto-documentée de tous les endpoints disponibles de l'API principale.
*   **Requête :** Aucune.
*   **Réponse :**
    *   **Succès (200 OK) :** Un objet JSON décrivant chaque endpoint, ses paramètres et sa réponse attendue.
        ```json
        {
          "api_name": "API d'Analyse Argumentative",
          "version": "1.0.0",
          "endpoints": {
            "GET /api/health": { /* ... */ },
            "POST /api/analyze": { /* ... */ }
            // etc.
          }
        }
        ```

### Endpoints Logiques

Ces endpoints sont préfixés par `/api/logic` et définis dans [`argumentation_analysis/services/web_api/routes/logic_routes.py`](../../argumentation_analysis/services/web_api/routes/logic_routes.py:1).

#### 1. Conversion Texte vers Ensemble de Croyances

*   **Méthode HTTP :** `POST`
*   **URL :** `/api/logic/belief-set`
*   **Objectif :** Convertit un texte en langage naturel en un ensemble structuré de croyances logiques.
*   **Requête :**
    *   Corps JSON :
        ```json
        {
          "text": "Socrate est un homme. Tous les hommes sont mortels.",
          "logic_type": "first_order",
          "options": {
            "include_explanation": true
          }
        }
        ```
    *   Champs :
        *   `text` (string, requis) : Texte à convertir.
        *   `logic_type` (string, requis) : Type de logique à utiliser (`propositional`, `first_order`, `modal`).
        *   `options` (object, optionnel) : Options pour la conversion (voir [`LogicOptions`](../../argumentation_analysis/services/web_api/models/request_models.py:154) et [`LogicBeliefSetRequest`](../../argumentation_analysis/services/web_api/models/request_models.py:161)).
*   **Réponse :**
    *   **Succès (200 OK) :** Un objet JSON représentant l'ensemble de croyances (voir [`LogicBeliefSetResponse`](../../services/web_api/models/response_models.py:1)).
    *   **Erreur (400/500) :** Similaire à `/api/analyze`, avec des messages d'erreur spécifiques à la conversion logique.

#### 2. Exécution d'une Requête Logique

*   **Méthode HTTP :** `POST`
*   **URL :** `/api/logic/query`
*   **Objectif :** Exécute une requête logique (par exemple, vérifier une conséquence) sur un ensemble de croyances préalablement défini.
*   **Requête :**
    *   Corps JSON :
        ```json
        {
          "belief_set_id": "some_belief_set_uuid",
          "query": "Mortel(Socrate)?",
          "logic_type": "first_order",
          "options": {
            "include_explanation": true,
            "timeout": 10.0
          }
        }
        ```
    *   Champs :
        *   `belief_set_id` (string, requis) : Identifiant de l'ensemble de croyances sur lequel exécuter la requête.
        *   `query` (string, requis) : La requête logique.
        *   `logic_type` (string, requis) : Type de logique.
        *   `options` (object, optionnel) : Options pour l'exécution (voir [`LogicOptions`](../../argumentation_analysis/services/web_api/models/request_models.py:154) et [`LogicQueryRequest`](../../argumentation_analysis/services/web_api/models/request_models.py:183)).
*   **Réponse :**
    *   **Succès (200 OK) :** Un objet JSON avec le résultat de la requête (voir [`LogicQueryResponse`](../../services/web_api/models/response_models.py:1)).
    *   **Erreur (400/500) :** Similaire à `/api/analyze`.

#### 3. Génération de Requêtes Logiques

*   **Méthode HTTP :** `POST`
*   **URL :** `/api/logic/generate-queries`
*   **Objectif :** Génère des requêtes logiques pertinentes à partir d'un ensemble de croyances et/ou d'un texte source.
*   **Requête :**
    *   Corps JSON :
        ```json
        {
          "belief_set_id": "some_belief_set_uuid",
          "text": "Considérant que Socrate est un homme et que tous les hommes sont mortels, que pouvons-nous déduire d'autre ?",
          "logic_type": "first_order",
          "options": {
            "max_queries": 5
          }
        }
        ```
    *   Champs :
        *   `belief_set_id` (string, requis) : Identifiant de l'ensemble de croyances.
        *   `text` (string, requis) : Texte source pour guider la génération.
        *   `logic_type` (string, requis) : Type de logique.
        *   `options` (object, optionnel) : Options pour la génération (voir [`LogicOptions`](../../argumentation_analysis/services/web_api/models/request_models.py:154) et [`LogicGenerateQueriesRequest`](../../argumentation_analysis/services/web_api/models/request_models.py:213)).
*   **Réponse :**
    *   **Succès (200 OK) :** Un objet JSON listant les requêtes générées (voir [`LogicGenerateQueriesResponse`](../../services/web_api/models/response_models.py:1)).
    *   **Erreur (400/500) :** Similaire à `/api/analyze`.

## Authentification/Autorisation

Actuellement, l'API est ouverte et ne met pas en œuvre de mécanismes d'authentification ou d'autorisation spécifiques. La protection de l'API, si nécessaire, est supposée être gérée par des mécanismes externes (par exemple, un pare-feu, un proxy inverse, une gateway API).

## Gestion des Erreurs

Les erreurs sont signalées via :

*   **Codes de Statut HTTP :**
    *   `400 Bad Request` : Indique un problème avec la requête du client (par exemple, JSON malformé, données manquantes, paramètres invalides).
    *   `500 Internal Server Error` : Indique une erreur côté serveur lors du traitement de la requête.
*   **Corps de Réponse JSON :** En cas d'erreur, la réponse contiendra un objet JSON avec la structure suivante (voir [`ErrorResponse`](../../libs/web_api/models/response_models.py:45)) :
    ```json
    {
      "error": "Type d'erreur concis (ex: Données invalides)",
      "message": "Description détaillée de l'erreur.",
      "status_code": 400 // ou 500, etc.
    }
    ```
    Le gestionnaire d'erreur global est défini dans la fonction [`handle_error`](../../argumentation_analysis/services/web_api/app.py:79) de [`app.py`](../../argumentation_analysis/services/web_api/app.py:1).

## Exemple d'Utilisation (Analyse de Texte)

Voici un exemple simple d'interaction avec l'endpoint `/api/analyze` en utilisant `curl` :

```bash
curl -X POST -H "Content-Type: application/json" -d '{
  "text": "Les chats sont meilleurs que les chiens car ils sont plus indépendants. De plus, ils ronronnent, ce qui est apaisant.",
  "options": {
    "detect_fallacies": true,
    "analyze_structure": false
  }
}' http://localhost:5000/api/analyze
```

La réponse attendue (structure simplifiée) serait :

```json
{
  "original_text": "Les chats sont meilleurs que les chiens car ils sont plus indépendants. De plus, ils ronronnent, ce qui est apaisant.",
  "analysis_summary": {
    "overall_sentiment": "positif",
    "key_claims": [
      "Les chats sont meilleurs que les chiens.",
      "Les chats sont plus indépendants.",
      "Le ronronnement des chats est apaisant."
    ]
  },
  "fallacies": [
    {
      "fallacy_type": "Généralisation hâtive",
      "explanation": "L'affirmation que les chats sont 'meilleurs' est subjective et non étayée universellement.",
      "severity": 0.6,
      "context": "Les chats sont meilleurs que les chiens"
    }
  ],
  "structure": null, // Car analyze_structure était false
  "coherence": null // Car evaluate_coherence était sur sa valeur par défaut (true) mais dépend d'autres analyses
}