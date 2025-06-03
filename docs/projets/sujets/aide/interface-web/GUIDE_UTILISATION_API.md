# Guide d'Utilisation de l'API d'Analyse Argumentative

## 📋 Table des matières

1. [Introduction](#introduction)
2. [Installation et Configuration](#installation-et-configuration)
3. [Démarrage de l'API](#démarrage-de-lapi)
4. [Endpoints Disponibles](#endpoints-disponibles)
5. [Exemples d'Utilisation](#exemples-dutilisation)
6. [Intégration avec React](#intégration-avec-react)
7. [Gestion des Erreurs](#gestion-des-erreurs)
8. [Bonnes Pratiques](#bonnes-pratiques)

## Introduction

L'API d'Analyse Argumentative vous permet d'intégrer facilement les fonctionnalités d'analyse de textes argumentatifs dans votre interface web React. Cette API expose quatre services principaux :

- **Analyse complète** : Détection de sophismes + analyse de structure
- **Validation d'arguments** : Vérification de la logique d'un argument
- **Détection de sophismes** : Identification spécifique des erreurs de raisonnement
- **Framework de Dung** : Construction et analyse de frameworks argumentatifs

## Installation et Configuration

### Prérequis

- Python 3.8+
- Node.js 16+ (pour React)
- Git

### Installation de l'API

```bash
# 1. Naviguer vers le répertoire de l'API
cd services/web_api

# 2. Installer les dépendances Python
pip install -r requirements.txt

# 3. Vérifier l'installation
python start_api.py --no-check
```

### Variables d'environnement

Créez un fichier `.env` dans `services/web_api/` :

```env
# Configuration du serveur
PORT=5000
DEBUG=True
HOST=127.0.0.1

# Configuration CORS (pour React)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Logging
LOG_LEVEL=INFO
```

## Démarrage de l'API

### Méthode recommandée (avec script)

```bash
# Démarrage standard
python start_api.py

# Avec options personnalisées
python start_api.py --port 8080 --debug --host 0.0.0.0

# Mode silencieux
python start_api.py --quiet
```

### Méthode alternative (directe)

```bash
python app.py
```

### Vérification du démarrage

Une fois l'API démarrée, vérifiez qu'elle fonctionne :

```bash
curl http://localhost:5000/api/health
```

Réponse attendue :
```json
{
  "status": "healthy",
  "message": "API d'analyse argumentative opérationnelle",
  "version": "1.0.0",
  "services": {
    "analysis": true,
    "validation": true,
    "fallacy": true,
    "framework": true
  }
}
```

## Endpoints Disponibles

### 🔍 Health Check
- **URL** : `GET /api/health`
- **Description** : Vérifie l'état de l'API
- **Paramètres** : Aucun
- **Réponse** : Status de l'API et des services

### 📊 Analyse Complète
- **URL** : `POST /api/analyze`
- **Description** : Analyse complète d'un texte argumentatif
- **Content-Type** : `application/json`

**Corps de la requête :**
```json
{
  "text": "Votre texte à analyser",
  "options": {
    "detect_fallacies": true,
    "analyze_structure": true,
    "evaluate_coherence": true,
    "severity_threshold": 0.5,
    "include_context": true
  }
}
```

### ✅ Validation d'Argument
- **URL** : `POST /api/validate`
- **Description** : Valide la logique d'un argument
- **Content-Type** : `application/json`

**Corps de la requête :**
```json
{
  "premises": [
    "Tous les hommes sont mortels",
    "Socrate est un homme"
  ],
  "conclusion": "Socrate est mortel",
  "argument_type": "deductive"
}

Pour un exemple de test de cet endpoint, consultez la fonction [`test_analyze_endpoint`](libs/web_api/test_api.py:38) dans le script [`libs/web_api/test_api.py`](libs/web_api/test_api.py:0).
```

### 🚫 Détection de Sophismes
- **URL** : `POST /api/fallacies`
- **Description** : Détecte spécifiquement les sophismes
- **Content-Type** : `application/json`

**Corps de la requête :**
```json
{
  "text": "Texte à analyser pour les sophismes",
  "options": {
    "severity_threshold": 0.3,
    "include_context": true,
    "max_fallacies": 10,
    "categories": ["informal"]
  }

Pour un exemple de test de cet endpoint, consultez la fonction [`test_fallacies_endpoint`](libs/web_api/test_api.py:109) dans le script [`libs/web_api/test_api.py`](libs/web_api/test_api.py:0).

Pour un exemple de test de cet endpoint, consultez la fonction [`test_validate_endpoint`](libs/web_api/test_api.py:74) dans le script [`libs/web_api/test_api.py`](libs/web_api/test_api.py:0).
}
```

### 🕸️ Framework de Dung
- **URL** : `POST /api/framework`
- **Description** : Construit un framework argumentatif
- **Content-Type** : `application/json`

**Corps de la requête :**
```json
{
  "arguments": [
    {
      "id": "arg1",
      "content": "Il faut réduire les impôts",
      "attacks": ["arg2"]
    },
    {
      "id": "arg2",
      "content": "Réduire les impôts diminue les services publics",
      "attacks": ["arg1"]
    }
  ],
  "options": {
    "compute_extensions": true,
    "semantics": "preferred",
    "include_visualization": true
  }

Pour un exemple de test de cet endpoint, consultez la fonction [`test_framework_endpoint`](libs/web_api/test_api.py:143) dans le script [`libs/web_api/test_api.py`](libs/web_api/test_api.py:0).
}
```

### 📋 Liste des Endpoints
- **URL** : `GET /api/endpoints`
- **Description** : Documentation de tous les endpoints
- **Paramètres** : Aucun

## Exemples d'Utilisation

### Exemple 1 : Analyse complète avec curl

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Tous les politiciens sont corrompus. Jean est politicien. Donc Jean est corrompu.",
    "options": {
      "detect_fallacies": true,
      "analyze_structure": true,
      "evaluate_coherence": true
    }
  }'
```

### Exemple 2 : Validation d'argument avec JavaScript

```javascript
const validateArgument = async () => {
  const response = await fetch('http://localhost:5000/api/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      premises: [
        "Tous les hommes sont mortels",
        "Socrate est un homme"
      ],
      conclusion: "Socrate est mortel",
      argument_type: "deductive"
    })
  });
  
  const result = await response.json();
  console.log('Résultat de validation:', result);
};
```

### Exemple 3 : Détection de sophismes avec Python

```python
import requests

def detect_fallacies(text):
    url = "http://localhost:5000/api/fallacies"
    data = {
        "text": text,
        "options": {
            "severity_threshold": 0.3,
            "include_context": True
        }
    }
    
    response = requests.post(url, json=data)
    return response.json()

# Utilisation
result = detect_fallacies("Vous ne pouvez pas critiquer ce projet car vous n'êtes pas expert.")
print(f"Sophismes détectés: {result['fallacy_count']}")
```

### Exemple 4 : Script Python d'intégration API (Agents Logiques)

Bien que ciblant une API pour agents logiques avec des endpoints spécifiques (par exemple, `/api/logic/belief-set`), le script [`examples/logic_agents/api_integration_example.py`](examples/logic_agents/api_integration_example.py:0) fournit un exemple complet de classe client Python pour interagir avec une API REST, gérer l'authentification, et structurer les appels. Il peut servir de source d'inspiration pour construire votre propre client.

### Exemple 5 : Tutoriel interactif avec Jupyter Notebook (Agents Logiques)

De même, le notebook [`examples/notebooks/api_logic_tutorial.ipynb`](examples/notebooks/api_logic_tutorial.ipynb:0) illustre comment interagir avec une API pour agents logiques de manière interactive. Il montre la configuration, la création d'un client API, et l'exécution de requêtes pas à pas, ce qui peut être utile pour comprendre le flux général d'interaction avec une API.

## Intégration avec React

### Service API React

Créez un service pour encapsuler les appels API :

```javascript
// services/argumentationAPI.js
class ArgumentationAPI {
  constructor(baseURL = 'http://localhost:5000') {
    this.baseURL = baseURL;
  }

  async analyzeText(text, options = {}) {
    const response = await fetch(`${this.baseURL}/api/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text, options })
    });
    
    if (!response.ok) {
      throw new Error(`Erreur API: ${response.status}`);
    }
    
    return response.json();
  }

  async validateArgument(premises, conclusion, argumentType = 'deductive') {
    const response = await fetch(`${this.baseURL}/api/validate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        premises,
        conclusion,
        argument_type: argumentType
      })
    });
    
    if (!response.ok) {
      throw new Error(`Erreur API: ${response.status}`);
    }
    
    return response.json();
  }

  async detectFallacies(text, options = {}) {
    const response = await fetch(`${this.baseURL}/api/fallacies`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text, options })
    });
    
    if (!response.ok) {
      throw new Error(`Erreur API: ${response.status}`);
    }
    
    return response.json();
  }

  async buildFramework(arguments, options = {}) {
    const response = await fetch(`${this.baseURL}/api/framework`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ arguments, options })
    });
    
    if (!response.ok) {
      throw new Error(`Erreur API: ${response.status}`);
    }
    
    return response.json();
  }

  async checkHealth() {
    const response = await fetch(`${this.baseURL}/api/health`);
    return response.json();
  }
}

export default new ArgumentationAPI();
```

### Hook React personnalisé

```javascript
// hooks/useArgumentationAPI.js
import { useState, useCallback } from 'react';
import argumentationAPI from '../services/argumentationAPI';

export const useArgumentationAPI = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const analyzeText = useCallback(async (text, options) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await argumentationAPI.analyzeText(text, options);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const validateArgument = useCallback(async (premises, conclusion, type) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await argumentationAPI.validateArgument(premises, conclusion, type);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    analyzeText,
    validateArgument,
    loading,
    error
  };
};
```

### Composant React d'exemple

```jsx
// components/ArgumentAnalyzer.jsx
import React, { useState } from 'react';
import { useArgumentationAPI } from '../hooks/useArgumentationAPI';

const ArgumentAnalyzer = () => {
  const [text, setText] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const { analyzeText, loading, error } = useArgumentationAPI();

  const handleAnalyze = async () => {
    if (!text.trim()) return;
    
    try {
      const result = await analyzeText(text, {
        detect_fallacies: true,
        analyze_structure: true,
        evaluate_coherence: true
      });
      setAnalysis(result);
    } catch (err) {
      console.error('Erreur d\'analyse:', err);
    }
  };

  return (
    <div className="argument-analyzer">
      <h2>Analyseur d'Arguments</h2>
      
      <div className="input-section">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Entrez votre argument ici..."
          rows={6}
          cols={80}
          className="text-input"
        />
        <br />
        <button 
          onClick={handleAnalyze} 
          disabled={loading || !text.trim()}
          className="analyze-button"
        >
          {loading ? 'Analyse en cours...' : 'Analyser'}
        </button>
      </div>

      {error && (
        <div className="error-message">
          Erreur: {error}
        </div>
      )}

      {analysis && (
        <div className="results-section">
          <h3>Résultats de l'analyse</h3>
          
          <div className="metrics">
            <p><strong>Qualité globale:</strong> {(analysis.overall_quality * 100).toFixed(1)}%</p>
            <p><strong>Score de cohérence:</strong> {(analysis.coherence_score * 100).toFixed(1)}%</p>
            <p><strong>Sophismes détectés:</strong> {analysis.fallacy_count}</p>
          </div>

          {analysis.fallacies.length > 0 && (
            <div className="fallacies-section">
              <h4>Sophismes détectés</h4>
              {analysis.fallacies.map((fallacy, index) => (
                <div key={index} className="fallacy-item">
                  <h5>{fallacy.name}</h5>
                  <p>{fallacy.description}</p>
                  <p><strong>Sévérité:</strong> {(fallacy.severity * 100).toFixed(1)}%</p>
                  {fallacy.explanation && (
                    <p><strong>Explication:</strong> {fallacy.explanation}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {analysis.argument_structure && (
            <div className="structure-section">
              <h4>Structure de l'argument</h4>
              <p><strong>Type:</strong> {analysis.argument_structure.argument_type}</p>
              <p><strong>Force:</strong> {(analysis.argument_structure.strength * 100).toFixed(1)}%</p>
              
              <div className="premises">
                <h5>Prémisses:</h5>
                <ul>
                  {analysis.argument_structure.premises.map((premise, index) => (
                    <li key={index}>{premise}</li>
                  ))}
                </ul>
              </div>
              
              <div className="conclusion">
                <h5>Conclusion:</h5>
                <p>{analysis.argument_structure.conclusion}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ArgumentAnalyzer;
```

## Gestion des Erreurs

### Types d'erreurs courantes

1. **Erreurs de validation (400)** : Données de requête invalides
2. **Erreurs internes (500)** : Problèmes côté serveur
3. **Erreurs de réseau** : Problèmes de connexion

### Gestion des erreurs en JavaScript

```javascript
const handleAPICall = async (apiFunction, ...args) => {
  try {
    const result = await apiFunction(...args);
    return { success: true, data: result };
  } catch (error) {
    console.error('Erreur API:', error);
    
    if (error.message.includes('400')) {
      return { 
        success: false, 
        error: 'Données invalides. Vérifiez votre requête.' 
      };
    } else if (error.message.includes('500')) {
      return { 
        success: false, 
        error: 'Erreur serveur. Réessayez plus tard.' 
      };
    } else {
      return { 
        success: false, 
        error: 'Erreur de connexion. Vérifiez que l\'API est démarrée.' 
      };
    }
  }
};
```

### Composant de gestion d'erreurs

```jsx
const ErrorBoundary = ({ children }) => {
  const [hasError, setHasError] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const handleError = (error) => {
      setHasError(true);
      setError(error);
    };

    window.addEventListener('unhandledrejection', handleError);
    return () => window.removeEventListener('unhandledrejection', handleError);
  }, []);

  if (hasError) {
    return (
      <div className="error-boundary">
        <h2>Une erreur s'est produite</h2>
        <p>{error?.message || 'Erreur inconnue'}</p>
        <button onClick={() => setHasError(false)}>
          Réessayer
        </button>
      </div>
    );
  }

  return children;
};
```

## Bonnes Pratiques

### 1. Configuration de l'environnement

- Utilisez des variables d'environnement pour les URLs
- Séparez les configurations de développement et production
- Activez CORS uniquement pour les domaines autorisés

### 2. Performance

- Implémentez un cache pour les requêtes fréquentes
- Utilisez la pagination pour les grandes listes
- Limitez la taille des textes analysés

### 3. Sécurité

- Validez toujours les données côté client ET serveur
- Implémentez une limitation de taux (rate limiting)
- Sanitisez les entrées utilisateur

### 4. UX/UI

- Affichez des indicateurs de chargement
- Fournissez des messages d'erreur clairs
- Implémentez une fonctionnalité de retry automatique

### 5. Tests

```javascript
// Exemple de test avec Jest
describe('ArgumentationAPI', () => {
  test('should analyze text successfully', async () => {
    const mockResponse = {
      success: true,
      fallacy_count: 1,
      overall_quality: 0.7
    };
    
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })
    );

    const result = await argumentationAPI.analyzeText('Test text');
    expect(result.success).toBe(true);
    expect(result.fallacy_count).toBe(1);
  });
});
```

Pour des exemples concrets de tests d'intégration pour l'API d'analyse argumentative, vous pouvez consulter le script [`libs/web_api/test_api.py`](libs/web_api/test_api.py:0). Ce script utilise la bibliothèque `requests` pour envoyer des requêtes aux différents endpoints et vérifier leurs réponses.

### 6. Monitoring

- Loggez les erreurs importantes
- Surveillez les temps de réponse
- Trackez l'utilisation des endpoints

## Support et Ressources

- **Documentation complète** : Consultez le README.md de l'API
- **Exemples de code** :
  - Pour l'intégration React : Voir le dossier `exemples-react/` (mentionné précédemment dans ce guide).
  - Pour des tests d'API en Python : [`libs/web_api/test_api.py`](libs/web_api/test_api.py:0).
  - Pour un exemple de client API Python (pour une API d'agents logiques, mais illustratif) : [`examples/logic_agents/api_integration_example.py`](examples/logic_agents/api_integration_example.py:0).
  - Pour un tutoriel d'utilisation d'API avec Jupyter Notebook (pour une API d'agents logiques, mais illustratif) : [`examples/notebooks/api_logic_tutorial.ipynb`](examples/notebooks/api_logic_tutorial.ipynb:0).
- **Troubleshooting** : Consultez `TROUBLESHOOTING.md`
- **Démarrage rapide** : Suivez `DEMARRAGE_RAPIDE.md`

## Changelog

- **v1.0.0** : Version initiale avec tous les endpoints de base
- Support complet de CORS pour React
- Script de démarrage amélioré
- Documentation complète

---

*Ce guide est maintenu par l'équipe du projet d'Intelligence Symbolique EPITA 2025.*