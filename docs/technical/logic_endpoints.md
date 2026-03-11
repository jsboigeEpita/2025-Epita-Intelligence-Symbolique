# Endpoints API pour les Opérations Logiques

Ce document décrit les endpoints API pour les opérations logiques.

## Vue d'ensemble

L'API expose plusieurs endpoints pour manipuler et raisonner sur des formules logiques. Ces endpoints permettent de :
- Convertir un texte en ensemble de croyances logiques
- Exécuter des requêtes logiques sur un ensemble de croyances
- Générer des requêtes logiques pertinentes
- Interpréter les résultats des requêtes

L'API prend en charge trois types de logiques :
- **Logique propositionnelle** (`propositional`)
- **Logique du premier ordre** (`first_order`)
- **Logique modale** (`modal`)

## Base URL

```
http://localhost:5000/api
```

## Endpoints

### Vérification de l'état de l'API

```
GET /health
```

Vérifie l'état de l'API et de ses services.

#### Réponse

```json
{
  "status": "healthy",
  "message": "API d'analyse argumentative opérationnelle",
  "version": "1.0.0",
  "services": {
    "analysis": true,
    "validation": true,
    "fallacy": true,
    "framework": true,
    "logic": true
  }
}
```

### Conversion de texte en ensemble de croyances

```
POST /logic/belief-set
```

Convertit un texte en ensemble de croyances logiques.

#### Corps de la requête

```json
{
  "text": "Si p est vrai, alors q est vrai. p est vrai.",
  "logic_type": "propositional",
  "options": {
    "include_explanation": true,
    "max_queries": 5,
    "timeout": 10.0
  }
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `text` | string | Texte à convertir |
| `logic_type` | string | Type de logique (`propositional`, `first_order`, `modal`) |
| `options` | object | Options de conversion (facultatif) |
| `options.include_explanation` | boolean | Inclure une explication détaillée |
| `options.max_queries` | integer | Nombre maximum de requêtes à générer |
| `options.timeout` | number | Timeout en secondes |

#### Réponse

```json
{
  "success": true,
  "conversion_timestamp": "2025-05-27T17:30:00.000Z",
  "belief_set": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "logic_type": "propositional",
    "content": "p => q\np",
    "source_text": "Si p est vrai, alors q est vrai. p est vrai.",
    "creation_timestamp": "2025-05-27T17:30:00.000Z"
  },
  "processing_time": 0.1,
  "conversion_options": {
    "include_explanation": true,
    "max_queries": 5,
    "timeout": 10.0
  }
}
```

### Exécution d'une requête logique

```
POST /logic/query
```

Exécute une requête logique sur un ensemble de croyances.

#### Corps de la requête

```json
{
  "belief_set_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "q",
  "logic_type": "propositional",
  "options": {
    "include_explanation": true,
    "timeout": 10.0
  }
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `belief_set_id` | string | ID de l'ensemble de croyances |
| `query` | string | Requête logique à exécuter |
| `logic_type` | string | Type de logique (`propositional`, `first_order`, `modal`) |
| `options` | object | Options d'exécution (facultatif) |
| `options.include_explanation` | boolean | Inclure une explication détaillée |
| `options.timeout` | number | Timeout en secondes |

#### Réponse

```json
{
  "success": true,
  "query_timestamp": "2025-05-27T17:30:00.000Z",
  "belief_set_id": "550e8400-e29b-41d4-a716-446655440000",
  "logic_type": "propositional",
  "result": {
    "query": "q",
    "result": true,
    "formatted_result": "Tweety Result: Query 'q' is ACCEPTED (True).",
    "explanation": "La requête 'q' est acceptée par l'ensemble de croyances. Cela signifie que la formule est une conséquence logique des axiomes définis dans l'ensemble de croyances."
  },
  "processing_time": 0.1,
  "query_options": {
    "include_explanation": true,
    "timeout": 10.0
  }
}
```

### Génération de requêtes logiques

```
POST /logic/generate-queries
```

Génère des requêtes logiques pertinentes pour un ensemble de croyances.

#### Corps de la requête

```json
{
  "belief_set_id": "550e8400-e29b-41d4-a716-446655440000",
  "text": "Si p est vrai, alors q est vrai. p est vrai.",
  "logic_type": "propositional",
  "options": {
    "max_queries": 5,
    "timeout": 10.0
  }
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `belief_set_id` | string | ID de l'ensemble de croyances |
| `text` | string | Texte source pour la génération de requêtes |
| `logic_type` | string | Type de logique (`propositional`, `first_order`, `modal`) |
| `options` | object | Options de génération (facultatif) |
| `options.max_queries` | integer | Nombre maximum de requêtes à générer |
| `options.timeout` | number | Timeout en secondes |

#### Réponse

```json
{
  "success": true,
  "generation_timestamp": "2025-05-27T17:30:00.000Z",
  "belief_set_id": "550e8400-e29b-41d4-a716-446655440000",
  "logic_type": "propositional",
  "queries": ["p", "q", "p => q", "p && q"],
  "processing_time": 0.1,
  "generation_options": {
    "max_queries": 5,
    "timeout": 10.0
  }
}
```

### Interprétation des résultats

```
POST /logic/interpret
```

Interprète les résultats de requêtes logiques.

#### Corps de la requête

```json
{
  "belief_set_id": "550e8400-e29b-41d4-a716-446655440000",
  "logic_type": "propositional",
  "text": "Si p est vrai, alors q est vrai. p est vrai.",
  "queries": ["p", "q", "p => q", "p && q"],
  "results": [
    {
      "query": "p",
      "result": true,
      "formatted_result": "Tweety Result: Query 'p' is ACCEPTED (True)."
    },
    {
      "query": "q",
      "result": true,
      "formatted_result": "Tweety Result: Query 'q' is ACCEPTED (True)."
    },
    {
      "query": "p => q",
      "result": true,
      "formatted_result": "Tweety Result: Query 'p => q' is ACCEPTED (True)."
    },
    {
      "query": "p && q",
      "result": true,
      "formatted_result": "Tweety Result: Query 'p && q' is ACCEPTED (True)."
    }
  ],
  "options": {
    "include_explanation": true
  }
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `belief_set_id` | string | ID de l'ensemble de croyances |
| `logic_type` | string | Type de logique (`propositional`, `first_order`, `modal`) |
| `text` | string | Texte source |
| `queries` | array | Liste des requêtes exécutées |
| `results` | array | Liste des résultats des requêtes |
| `options` | object | Options d'interprétation (facultatif) |
| `options.include_explanation` | boolean | Inclure une explication détaillée |

#### Réponse

```json
{
  "success": true,
  "interpretation_timestamp": "2025-05-27T17:30:00.000Z",
  "belief_set_id": "550e8400-e29b-41d4-a716-446655440000",
  "logic_type": "propositional",
  "queries": ["p", "q", "p => q", "p && q"],
  "results": [
    {
      "query": "p",
      "result": true,
      "formatted_result": "Tweety Result: Query 'p' is ACCEPTED (True)."
    },
    {
      "query": "q",
      "result": true,
      "formatted_result": "Tweety Result: Query 'q' is ACCEPTED (True)."
    },
    {
      "query": "p => q",
      "result": true,
      "formatted_result": "Tweety Result: Query 'p => q' is ACCEPTED (True)."
    },
    {
      "query": "p && q",
      "result": true,
      "formatted_result": "Tweety Result: Query 'p && q' is ACCEPTED (True)."
    }
  ],
  "interpretation": "D'après les axiomes, p est vrai et q est vrai par modus ponens. L'implication p => q est un axiome, et la conjonction p && q est vraie car p et q sont tous deux vrais.",
  "processing_time": 0.1,
  "interpretation_options": {
    "include_explanation": true
  }
}
```

## Codes d'erreur

| Code | Description |
|------|-------------|
| 400 | Requête invalide (données manquantes ou format incorrect) |
| 404 | Ressource non trouvée (ensemble de croyances inexistant) |
| 500 | Erreur interne du serveur |

## Exemples d'utilisation

### Exemple 1 : Logique propositionnelle

#### Conversion de texte en ensemble de croyances

```bash
curl -X POST http://localhost:5000/api/logic/belief-set \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Si p est vrai, alors q est vrai. p est vrai.",
    "logic_type": "propositional"
  }'
```

#### Exécution d'une requête

```bash
curl -X POST http://localhost:5000/api/logic/query \
  -H "Content-Type: application/json" \
  -d '{
    "belief_set_id": "550e8400-e29b-41d4-a716-446655440000",
    "query": "q",
    "logic_type": "propositional"
  }'
```

### Exemple 2 : Logique du premier ordre

#### Conversion de texte en ensemble de croyances

```bash
curl -X POST http://localhost:5000/api/logic/belief-set \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Tous les hommes sont mortels. Socrate est un homme.",
    "logic_type": "first_order"
  }'
```

#### Exécution d'une requête

```bash
curl -X POST http://localhost:5000/api/logic/query \
  -H "Content-Type: application/json" \
  -d '{
    "belief_set_id": "550e8400-e29b-41d4-a716-446655440000",
    "query": "Mortal(Socrates)",
    "logic_type": "first_order"
  }'
```

### Exemple 3 : Logique modale

#### Conversion de texte en ensemble de croyances

```bash
curl -X POST http://localhost:5000/api/logic/belief-set \
  -H "Content-Type: application/json" \
  -d '{
    "text": "S'il est nécessaire que p, alors p est vrai. Il est nécessaire que p.",
    "logic_type": "modal"
  }'
```

#### Exécution d'une requête

```bash
curl -X POST http://localhost:5000/api/logic/query \
  -H "Content-Type: application/json" \
  -d '{
    "belief_set_id": "550e8400-e29b-41d4-a716-446655440000",
    "query": "p",
    "logic_type": "modal"
  }'