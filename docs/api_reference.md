# Documentation de Référence API

Cette documentation fournit une référence complète pour l'API du système d'analyse argumentative. Elle est destinée aux développeurs qui souhaitent intégrer le système dans leurs applications ou créer des interfaces utilisateur personnalisées.

## Table des matières

- [Documentation de Référence API](#documentation-de-référence-api)
  - [Table des matières](#table-des-matières)
  - [Introduction](#introduction)
  - [Authentification](#authentification)
    - [Obtention d'un jeton](#obtention-dun-jeton)
    - [Utilisation du jeton](#utilisation-du-jeton)
  - [Points de terminaison (Endpoints)](#points-de-terminaison-endpoints)
    - [Analyse de texte](#analyse-de-texte)
      - [`POST /api/analyze`](#post-apianalyze)
    - [Détection de sophismes](#détection-de-sophismes)
      - [`POST /api/fallacies`](#post-apifallacies)
    - [Validation d'arguments](#validation-darguments)
      - [`POST /api/validate`](#post-apivalidate)
    - [Construction de frameworks](#construction-de-frameworks)
      - [`POST /api/framework`](#post-apiframework)
    - [Documentation des endpoints](#documentation-des-endpoints)
      - [`GET /api/endpoints`](#get-apiendpoints)
  - [Modèles de données](#modèles-de-données)
    - [Argument](#argument)
    - [Fallacy (Sophisme)](#fallacy-sophisme)
    - [Framework](#framework)
  - [Codes d'erreur](#codes-derreur)
    - [Exemples d'erreurs](#exemples-derreurs)
  - [Limites et quotas](#limites-et-quotas)
  - [Exemples d'intégration](#exemples-dintégration)
    - [JavaScript (avec fetch)](#javascript-avec-fetch)
    - [Python (avec requests)](#python-avec-requests)
    - [React (avec axios)](#react-avec-axios)

## Introduction

L'API REST du système d'analyse argumentative est implémentée avec Flask et expose toutes les fonctionnalités d'analyse via des endpoints HTTP. Elle permet d'analyser des textes argumentatifs, de détecter des sophismes, de valider des arguments et de construire des frameworks d'argumentation.

L'API est accessible à l'adresse `http://localhost:5000` lorsqu'elle est exécutée localement, ou à l'URL de déploiement spécifiée dans la configuration.

## Authentification

L'API utilise l'authentification par jeton (token) pour sécuriser l'accès aux endpoints. Pour utiliser l'API, vous devez inclure un jeton d'authentification dans l'en-tête de vos requêtes HTTP.

### Obtention d'un jeton

Pour obtenir un jeton d'authentification, envoyez une requête POST à l'endpoint `/api/auth/token` avec vos identifiants :

```http
POST /api/auth/token
Content-Type: application/json

{
  "username": "votre_nom_utilisateur",
  "password": "votre_mot_de_passe"
}
```

La réponse contiendra votre jeton d'authentification :

```json
{
  "token": "votre_jeton_authentification",
  "expires_at": "2025-06-27T16:25:00Z"
}
```

### Utilisation du jeton

Incluez le jeton dans l'en-tête `Authorization` de vos requêtes HTTP :

```http
GET /api/analyze
Authorization: Bearer votre_jeton_authentification
```

## Points de terminaison (Endpoints)

### Analyse de texte

#### `POST /api/analyze`

Effectue une analyse complète d'un texte argumentatif.

**Paramètres de requête :**

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `text` | string | Oui | Le texte à analyser |
| `options` | object | Non | Options d'analyse (voir ci-dessous) |

**Options d'analyse :**

```json
{
  "detect_fallacies": true,
  "validate_arguments": true,
  "extract_framework": false,
  "language": "fr",
  "detail_level": "high"
}
```

**Exemple de requête :**

```http
POST /api/analyze
Content-Type: application/json
Authorization: Bearer votre_jeton_authentification

{
  "text": "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel.",
  "options": {
    "detect_fallacies": true,
    "validate_arguments": true,
    "detail_level": "high"
  }
}
```

**Exemple de réponse :**

```json
{
  "analysis_id": "a1b2c3d4",
  "timestamp": "2025-05-27T16:25:00Z",
  "text": "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel.",
  "arguments": [
    {
      "id": "arg1",
      "text": "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel.",
      "premises": [
        "Tous les hommes sont mortels",
        "Socrate est un homme"
      ],
      "conclusion": "Socrate est mortel",
      "structure": "deductive",
      "validity": true,
      "fallacies": []
    }
  ],
  "overall_quality": 0.95,
  "execution_time": 0.35
}
```

### Détection de sophismes

#### `POST /api/fallacies`

Analyse un texte pour détecter les sophismes et erreurs de raisonnement.

**Paramètres de requête :**

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `text` | string | Oui | Le texte à analyser |
| `fallacy_types` | array | Non | Types de sophismes à détecter (si vide, tous les types sont détectés) |
| `sensitivity` | string | Non | Sensibilité de la détection ("low", "medium", "high") |

**Exemple de requête :**

```http
POST /api/fallacies
Content-Type: application/json
Authorization: Bearer votre_jeton_authentification

{
  "text": "Si nous autorisons le mariage homosexuel, bientôt les gens voudront épouser leurs animaux de compagnie.",
  "fallacy_types": ["slippery_slope", "false_equivalence"],
  "sensitivity": "medium"
}
```

**Exemple de réponse :**

```json
{
  "analysis_id": "f1e2d3c4",
  "timestamp": "2025-05-27T16:26:00Z",
  "text": "Si nous autorisons le mariage homosexuel, bientôt les gens voudront épouser leurs animaux de compagnie.",
  "fallacies": [
    {
      "type": "slippery_slope",
      "confidence": 0.92,
      "span": [0, 85],
      "explanation": "Ce raisonnement suggère à tort qu'une action mènera inévitablement à une chaîne d'événements indésirables sans démontrer le lien causal entre ces événements."
    }
  ],
  "execution_time": 0.28
}
```

### Validation d'arguments

#### `POST /api/validate`

Valide la structure logique d'un argument.

**Paramètres de requête :**

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `premises` | array | Oui | Liste des prémisses de l'argument |
| `conclusion` | string | Oui | Conclusion de l'argument |
| `formalization` | string | Non | Type de formalisation à utiliser ("propositional", "predicate", "default") |

**Exemple de requête :**

```http
POST /api/validate
Content-Type: application/json
Authorization: Bearer votre_jeton_authentification

{
  "premises": [
    "Si il pleut, alors la route est mouillée",
    "Il pleut"
  ],
  "conclusion": "La route est mouillée",
  "formalization": "propositional"
}
```

**Exemple de réponse :**

```json
{
  "validation_id": "v1a2l3i4d",
  "timestamp": "2025-05-27T16:27:00Z",
  "valid": true,
  "formalization": {
    "type": "propositional",
    "premises": [
      "P → Q",
      "P"
    ],
    "conclusion": "Q",
    "rule": "modus_ponens"
  },
  "explanation": "L'argument est valide selon la règle du modus ponens. Si la première prémisse établit que P implique Q, et que la seconde prémisse affirme P, alors Q s'ensuit nécessairement.",
  "execution_time": 0.15
}
```

### Construction de frameworks

#### `POST /api/framework`

Construit un framework d'argumentation de Dung à partir d'un ensemble d'arguments et d'attaques.

**Paramètres de requête :**

| Paramètre | Type | Requis | Description |
|-----------|------|--------|-------------|
| `arguments` | array | Oui | Liste des arguments |
| `attacks` | array | Oui | Liste des relations d'attaque entre arguments |
| `semantics` | string | Non | Sémantique à utiliser pour l'évaluation ("grounded", "preferred", "stable", "complete") |

**Exemple de requête :**

```http
POST /api/framework
Content-Type: application/json
Authorization: Bearer votre_jeton_authentification

{
  "arguments": ["a", "b", "c", "d"],
  "attacks": [
    {"from": "a", "to": "b"},
    {"from": "b", "to": "c"},
    {"from": "c", "to": "d"},
    {"from": "d", "to": "c"}
  ],
  "semantics": "grounded"
}
```

**Exemple de réponse :**

```json
{
  "framework_id": "f1r2a3m4e",
  "timestamp": "2025-05-27T16:28:00Z",
  "arguments": ["a", "b", "c", "d"],
  "attacks": [
    {"from": "a", "to": "b"},
    {"from": "b", "to": "c"},
    {"from": "c", "to": "d"},
    {"from": "d", "to": "c"}
  ],
  "extensions": {
    "grounded": ["a"],
    "preferred": [["a", "c"], ["a", "d"]],
    "stable": [["a", "c"], ["a", "d"]],
    "complete": [["a"], ["a", "c"], ["a", "d"]]
  },
  "visualization_url": "/api/framework/f1r2a3m4e/visualization",
  "execution_time": 0.22
}
```

### Documentation des endpoints

#### `GET /api/endpoints`

Retourne la liste de tous les endpoints disponibles avec leur documentation.

**Exemple de requête :**

```http
GET /api/endpoints
Authorization: Bearer votre_jeton_authentification
```

**Exemple de réponse :**

```json
{
  "endpoints": [
    {
      "path": "/api/analyze",
      "method": "POST",
      "description": "Effectue une analyse complète d'un texte argumentatif",
      "parameters": [
        {
          "name": "text",
          "type": "string",
          "required": true,
          "description": "Le texte à analyser"
        },
        {
          "name": "options",
          "type": "object",
          "required": false,
          "description": "Options d'analyse"
        }
      ],
      "example_request": "...",
      "example_response": "..."
    },
    // Autres endpoints...
  ]
}
```

## Modèles de données

### Argument

```json
{
  "id": "string",
  "text": "string",
  "premises": ["string"],
  "conclusion": "string",
  "structure": "string (deductive, inductive, abductive)",
  "validity": "boolean",
  "fallacies": [
    {
      "type": "string",
      "confidence": "number",
      "span": ["number", "number"],
      "explanation": "string"
    }
  ]
}
```

### Fallacy (Sophisme)

```json
{
  "type": "string",
  "confidence": "number",
  "span": ["number", "number"],
  "explanation": "string"
}
```

### Framework

```json
{
  "arguments": ["string"],
  "attacks": [
    {
      "from": "string",
      "to": "string"
    }
  ],
  "extensions": {
    "grounded": ["string"],
    "preferred": [["string"]],
    "stable": [["string"]],
    "complete": [["string"]]
  }
}
```

## Codes d'erreur

| Code | Message | Description |
|------|---------|-------------|
| 400 | Bad Request | La requête est mal formée ou contient des paramètres invalides |
| 401 | Unauthorized | Authentification requise ou jeton invalide |
| 403 | Forbidden | Accès refusé à la ressource demandée |
| 404 | Not Found | La ressource demandée n'existe pas |
| 429 | Too Many Requests | Limite de requêtes dépassée |
| 500 | Internal Server Error | Erreur interne du serveur |
| 503 | Service Unavailable | Service temporairement indisponible |

### Exemples d'erreurs

```json
{
  "error": {
    "code": 400,
    "message": "Bad Request",
    "details": "Le paramètre 'text' est requis"
  }
}
```

```json
{
  "error": {
    "code": 401,
    "message": "Unauthorized",
    "details": "Jeton d'authentification invalide ou expiré"
  }
}
```

## Limites et quotas

L'API impose certaines limites pour garantir la stabilité et la disponibilité du service :

| Ressource | Limite |
|-----------|--------|
| Requêtes par minute | 60 |
| Requêtes par jour | 1000 |
| Taille maximale du texte | 10 000 caractères |
| Nombre maximum d'arguments | 100 |
| Temps de traitement maximum | 30 secondes |

En cas de dépassement de ces limites, l'API retournera une erreur 429 (Too Many Requests).

## Exemples d'intégration

### JavaScript (avec fetch)

```javascript
// Fonction pour analyser un texte
async function analyzeText(text, options = {}) {
  const token = localStorage.getItem('api_token');
  
  try {
    const response = await fetch('http://localhost:5000/api/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        text,
        options
      })
    });
    
    if (!response.ok) {
      throw new Error(`Erreur HTTP: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Erreur lors de l\'analyse:', error);
    throw error;
  }
}

// Exemple d'utilisation
analyzeText("Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel.")
  .then(result => {
    console.log('Résultat de l\'analyse:', result);
  })
  .catch(error => {
    console.error('Échec de l\'analyse:', error);
  });
```

### Python (avec requests)

```python
import requests

def analyze_text(text, options=None, api_url="http://localhost:5000", token=None):
    """
    Analyse un texte argumentatif via l'API.
    
    Args:
        text (str): Le texte à analyser
        options (dict, optional): Options d'analyse
        api_url (str): URL de base de l'API
        token (str): Jeton d'authentification
        
    Returns:
        dict: Résultat de l'analyse
    """
    if options is None:
        options = {}
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    data = {
        'text': text,
        'options': options
    }
    
    response = requests.post(f"{api_url}/api/analyze", json=data, headers=headers)
    response.raise_for_status()  # Lève une exception en cas d'erreur HTTP
    
    return response.json()

# Exemple d'utilisation
try:
    result = analyze_text(
        "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel.",
        options={'detect_fallacies': True, 'validate_arguments': True},
        token="votre_jeton_authentification"
    )
    print("Résultat de l'analyse:", result)
except requests.exceptions.RequestException as e:
    print(f"Erreur lors de l'analyse: {e}")
```

### React (avec axios)

```jsx
import React, { useState } from 'react';
import axios from 'axios';

const ArgumentAnalyzer = () => {
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const analyzeText = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('api_token');
      
      const response = await axios.post('http://localhost:5000/api/analyze', {
        text,
        options: {
          detect_fallacies: true,
          validate_arguments: true
        }
      }, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Une erreur est survenue');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="argument-analyzer">
      <h2>Analyseur d'arguments</h2>
      
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Entrez votre texte argumentatif ici..."
        rows={5}
        cols={50}
      />
      
      <button onClick={analyzeText} disabled={loading || !text}>
        {loading ? 'Analyse en cours...' : 'Analyser'}
      </button>
      
      {error && (
        <div className="error">
          <p>Erreur: {error.message || error}</p>
        </div>
      )}
      
      {result && (
        <div className="result">
          <h3>Résultat de l'analyse</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};

export default ArgumentAnalyzer;
```

---

Pour plus d'informations sur l'utilisation de l'API, consultez les exemples complets dans le dossier [`docs/projets/sujets/aide/interface-web/exemples-react/`](../projets/sujets/aide/interface-web/exemples-react/).

---

*Dernière mise à jour : 27/05/2025*