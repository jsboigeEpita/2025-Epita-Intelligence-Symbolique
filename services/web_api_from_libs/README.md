# API Web d'Analyse Argumentative

Cette API Flask expose les fonctionnalités du moteur d'analyse argumentative pour permettre aux étudiants de créer facilement des interfaces web React.

## 🚀 Démarrage rapide

### Installation

```bash
# Naviguer vers le répertoire de l'API
cd services/web_api_from_libs

# Installer les dépendances
pip install -r requirements.txt

# Démarrer le serveur de développement
python app.py
```

L'API sera disponible sur `http://localhost:5000`

### Configuration

Variables d'environnement disponibles :
- `PORT` : Port du serveur (défaut: 5000)
- `DEBUG` : Mode debug (défaut: True)

## 📚 Endpoints

### 🔍 Health Check

**GET** `/api/health`

Vérifie l'état de l'API et de ses services.

```bash
curl http://localhost:5000/api/health
```

**Réponse :**
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

### 📊 Analyse complète

**POST** `/api/analyze`

Analyse complète d'un texte argumentatif incluant détection de sophismes, analyse de structure et évaluation de cohérence.

**Requête :**
```json
{
  "text": "Tous les politiciens sont corrompus. Jean est politicien. Donc Jean est corrompu.",
  "options": {
    "detect_fallacies": true,
    "analyze_structure": true,
    "evaluate_coherence": true,
    "severity_threshold": 0.5,
    "include_context": true
  }
}
```

**Exemple avec curl :**
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

**Réponse :**
```json
{
  "success": true,
  "text_analyzed": "Tous les politiciens sont corrompus...",
  "analysis_timestamp": "2025-05-27T10:30:00",
  "fallacies": [
    {
      "type": "hasty_generalization",
      "name": "Généralisation hâtive",
      "description": "Tirer une conclusion générale à partir d'exemples insuffisants",
      "severity": 0.6,
      "confidence": 0.8,
      "location": {"start": 0, "end": 35},
      "context": "Tous les politiciens sont corrompus",
      "explanation": "L'affirmation généralise sur tous les politiciens"
    }
  ],
  "argument_structure": {
    "premises": ["Tous les politiciens sont corrompus", "Jean est politicien"],
    "conclusion": "Donc Jean est corrompu",
    "argument_type": "deductive",
    "strength": 0.7,
    "coherence": 0.8
  },
  "overall_quality": 0.4,
  "coherence_score": 0.8,
  "fallacy_count": 1,
  "processing_time": 0.15
}
```

### ✅ Validation d'argument

**POST** `/api/validate`

Valide la logique d'un argument en analysant la relation entre prémisses et conclusion.

**Requête :**
```json
{
  "premises": [
    "Tous les hommes sont mortels",
    "Socrate est un homme"
  ],
  "conclusion": "Socrate est mortel",
  "argument_type": "deductive"
}
```

**Exemple avec curl :**
```bash
curl -X POST http://localhost:5000/api/validate \
  -H "Content-Type: application/json" \
  -d '{
    "premises": ["Tous les hommes sont mortels", "Socrate est un homme"],
    "conclusion": "Socrate est mortel",
    "argument_type": "deductive"
  }'
```

**Réponse :**
```json
{
  "success": true,
  "validation_timestamp": "2025-05-27T10:30:00",
  "premises": ["Tous les hommes sont mortels", "Socrate est un homme"],
  "conclusion": "Socrate est mortel",
  "argument_type": "deductive",
  "result": {
    "is_valid": true,
    "validity_score": 0.9,
    "soundness_score": 0.85,
    "premise_analysis": [
      {
        "index": 0,
        "text": "Tous les hommes sont mortels",
        "clarity_score": 0.8,
        "specificity_score": 0.7,
        "credibility_score": 0.9,
        "strength": 0.8
      }
    ],
    "issues": [],
    "suggestions": ["Votre argument semble bien structuré"]
  },
  "processing_time": 0.08
}
```

### 🚫 Détection de sophismes

**POST** `/api/fallacies`

Détecte spécifiquement les sophismes dans un texte.

**Requête :**
```json
{
  "text": "Vous ne pouvez pas critiquer ce projet car vous n'êtes pas expert en la matière.",
  "options": {
    "severity_threshold": 0.3,
    "include_context": true,
    "max_fallacies": 10,
    "categories": ["informal"]
  }
}
```

**Exemple avec curl :**
```bash
curl -X POST http://localhost:5000/api/fallacies \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Vous ne pouvez pas critiquer ce projet car vous n'\''êtes pas expert en la matière.",
    "options": {
      "severity_threshold": 0.3,
      "include_context": true
    }
  }'
```

**Réponse :**
```json
{
  "success": true,
  "text_analyzed": "Vous ne pouvez pas critiquer...",
  "detection_timestamp": "2025-05-27T10:30:00",
  "fallacies": [
    {
      "type": "appeal_to_authority",
      "name": "Appel à l'autorité",
      "description": "Invoquer une autorité non pertinente ou fallacieuse",
      "severity": 0.5,
      "confidence": 0.7,
      "context": "vous n'êtes pas expert",
      "explanation": "Rejeter un argument basé sur l'absence d'expertise"
    }
  ],
  "fallacy_count": 1,
  "severity_distribution": {
    "low": 0,
    "medium": 1,
    "high": 0
  },
  "category_distribution": {
    "informal": 1
  },
  "processing_time": 0.12
}
```

### 🕸️ Framework de Dung

**POST** `/api/framework`

Construit un framework d'argumentation de Dung et calcule ses extensions.

**Requête :**
```json
{
  "arguments": [
    {
      "id": "arg1",
      "content": "Il faut réduire les impôts pour stimuler l'économie",
      "attacks": ["arg2"]
    },
    {
      "id": "arg2", 
      "content": "Réduire les impôts diminue les services publics",
      "attacks": ["arg1"]
    },
    {
      "id": "arg3",
      "content": "Les services publics sont essentiels au bien-être social",
      "supports": ["arg2"]
    }
  ],
  "options": {
    "compute_extensions": true,
    "semantics": "preferred",
    "include_visualization": true
  }
}
```

**Exemple avec curl :**
```bash
curl -X POST http://localhost:5000/api/framework \
  -H "Content-Type: application/json" \
  -d '{
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
      "semantics": "preferred"
    }
  }'
```

**Réponse :**
```json
{
  "success": true,
  "framework_timestamp": "2025-05-27T10:30:00",
  "arguments": [
    {
      "id": "arg1",
      "content": "Il faut réduire les impôts",
      "status": "undecided",
      "attacks": ["arg2"],
      "attacked_by": ["arg2"]
    }
  ],
  "attack_relations": [
    {
      "attacker": "arg1",
      "target": "arg2",
      "type": "attack"
    }
  ],
  "extensions": [
    {
      "type": "preferred",
      "arguments": [],
      "is_complete": true,
      "is_preferred": true
    }
  ],
  "semantics_used": "preferred",
  "argument_count": 2,
  "attack_count": 2,
  "extension_count": 1,
  "processing_time": 0.05
}
```

### 📋 Liste des endpoints

**GET** `/api/endpoints`

Retourne la documentation de tous les endpoints disponibles.

```bash
curl http://localhost:5000/api/endpoints
```

## 🔧 Intégration avec React

### Exemple d'utilisation en JavaScript

```javascript
// Service d'API
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
    return response.json();
  }
}

// Utilisation
const api = new ArgumentationAPI();

// Analyse d'un texte
api.analyzeText("Votre texte ici")
  .then(result => {
    console.log('Sophismes détectés:', result.fallacies);
    console.log('Structure:', result.argument_structure);
  });
```

### Composant React exemple

```jsx
import React, { useState } from 'react';

function ArgumentAnalyzer() {
  const [text, setText] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyzeText = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:5000/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text,
          options: {
            detect_fallacies: true,
            analyze_structure: true,
            evaluate_coherence: true
          }
        })
      });
      const result = await response.json();
      setAnalysis(result);
    } catch (error) {
      console.error('Erreur:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Entrez votre argument ici..."
        rows={4}
        cols={50}
      />
      <br />
      <button onClick={analyzeText} disabled={loading}>
        {loading ? 'Analyse...' : 'Analyser'}
      </button>
      
      {analysis && (
        <div>
          <h3>Résultats</h3>
          <p>Qualité globale: {(analysis.overall_quality * 100).toFixed(1)}%</p>
          <p>Sophismes détectés: {analysis.fallacy_count}</p>
          
          {analysis.fallacies.map((fallacy, index) => (
            <div key={index} style={{border: '1px solid #ccc', padding: '10px', margin: '5px'}}>
              <strong>{fallacy.name}</strong>
              <p>{fallacy.description}</p>
              <p>Sévérité: {(fallacy.severity * 100).toFixed(1)}%</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ArgumentAnalyzer;
```

## 🛠️ Développement

### Structure du projet

```
services/web_api_from_libs/
├── app.py                 # Serveur Flask principal
├── requirements.txt       # Dépendances
├── README.md             # Documentation
├── models/               # Modèles de données (Pydantic)
│   ├── __init__.py
│   ├── request_models.py # Modèles des requêtes entrantes
│   └── response_models.py# Modèles des réponses sortantes
└── services/             # Logique métier
    ├── __init__.py
    ├── analysis_service.py    # Service pour l'analyse complète
    ├── validation_service.py  # Service pour la validation d'arguments
    ├── fallacy_service.py     # Service pour la détection de sophismes
    └── framework_service.py   # Service pour le framework de Dung
```

### Tests

```bash
# Installer les dépendances de test
pip install pytest pytest-flask requests

# Lancer les tests
pytest

# Tests avec couverture
pytest --cov=services/web_api_from_libs
```

### Déploiement

Pour déployer en production :

1. Configurer les variables d'environnement :
   ```bash
   export DEBUG=False
   export PORT=8000
   ```

2. Utiliser un serveur WSGI comme Gunicorn :
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8000 app:app
   ```

## 🔍 Gestion d'erreurs

L'API retourne des erreurs standardisées :

```json
{
  "error": "Type d'erreur",
  "message": "Description détaillée",
  "status_code": 400,
  "timestamp": "2025-05-27T10:30:00",
  "details": {}
}
```

Codes d'erreur courants :
- `400` : Données de requête invalides
- `500` : Erreur interne du serveur

## 📈 Performance

- Temps de réponse typique : 50-200ms
- Support de CORS pour les appels cross-origin
- Gestion des timeouts et erreurs réseau
- Logging détaillé pour le debugging

## 🤝 Contribution

Pour contribuer au développement :

1. Respecter la structure des modèles Pydantic
2. Ajouter des tests pour les nouvelles fonctionnalités
3. Documenter les nouveaux endpoints
4. Suivre les conventions de nommage Python

## 📄 Licence

Ce projet fait partie du système d'analyse argumentative EPITA 2025.
## ⚠️ Problèmes d'Architecture Connus

### Dépendances Circulaires et Imports Relatifs

L'application (`app.py`) utilise des imports qui dépendent d'un autre service (`services/web_api/`) situé au même niveau dans l'arborescence du projet.

**Exemples :**
```python
from argumentation_analysis.services.web_api.services.logic_service import LogicService
from services.web_api.models.response_models import LogicBeliefSetResponse
```

Ces imports sont rendus possibles par une manipulation du `sys.path` dans `app.py`. Cette approche est fragile et non standard. Elle peut causer des problèmes lors de l'exécution et des tests.

**Recommandation :**
Une refactorisation future devrait viser à extraire les modèles et services partagés dans une librairie commune installable afin de supprimer ces dépendances directes et complexes entre les services.