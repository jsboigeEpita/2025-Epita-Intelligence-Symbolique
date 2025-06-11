# Guide d'Utilisation de l'API d'Analyse Argumentative

## 📋 Table des matières

1.  [Introduction](#introduction)
2.  [Prérequis et Installation](#prérequis-et-installation)
3.  [Démarrage de l'API](#démarrage-de-lapi)
4.  [Endpoints Disponibles](#endpoints-disponibles)
5.  [Exemples d'Utilisation](#exemples-dutilisation)
6.  [Intégration avec React](#intégration-avec-react)
7.  [Gestion des Erreurs](#gestion-des-erreurs)
8.  [Bonnes Pratiques](#bonnes-pratiques)
9.  [Support et Ressources](#support-et-ressources)
10. [Changelog](#changelog)

## Introduction

L'API d'Analyse Argumentative vous permet d'intégrer facilement les fonctionnalités d'analyse de textes argumentatifs dans votre interface web. Cette API expose plusieurs services principaux, détaillés dans la documentation du composant [`API Web`](../../../../composants/api_web.md:1) et le [`Guide d'Intégration de l'API Web`](../../../../guides/integration_api_web.md:1). Les services incluent typiquement :

-   **Analyse complète** : Par exemple, détection de sophismes combinée à une analyse de structure.
-   **Validation d'arguments** : Vérification de la logique d'un argument.
-   **Détection de sophismes** : Identification spécifique des erreurs de raisonnement.
-   **Framework de Dung** : Construction et analyse de frameworks argumentatifs.

Pour une compréhension globale de l'architecture du système, consultez le document sur l'[`Architecture Globale`](../../../../architecture/architecture_globale.md:1).

## Prérequis et Installation

### Prérequis

-   Python 3.8+ (voir le [`Guide Développeur`](../../../../guides/guide_developpeur.md:1) pour la gestion de l'environnement Python)
-   Node.js 16+ (pour les projets d'interface utilisateur comme React)
-   Git

### Activation de l'environnement de projet

Avant toute installation ou exécution, assurez-vous que votre environnement de projet est correctement configuré et activé. Utilisez le script fourni à la racine du projet :
```powershell
.\setup_project_env.ps1
```
Ce script gère notamment la configuration de JPype pour la communication avec la JVM, un aspect crucial détaillé dans la section sur la gestion de la JVM de [`argumentation_analysis/core/jvm_setup.py`](../../../../../argumentation_analysis/core/jvm_setup.py:0).

### Installation de l'API

L'API Web est un composant du projet principal. Ses dépendances sont gérées dans le cadre de l'installation globale du projet.
1.  Clonez le dépôt du projet si ce n'est pas déjà fait.
2.  Naviguez vers le répertoire racine du projet.
3.  Suivez les instructions d'installation principales du projet, généralement via :
    ```bash
    pip install -r requirements.txt
    # ou
    pip install .
    ```
    Consultez le [`Guide Développeur`](../../../../guides/guide_developpeur.md:1) pour les instructions d'installation détaillées.

L'API elle-même se trouve dans le répertoire [`libs/web_api/`](../../../../../libs/web_api/:0).

### Variables d'environnement

Créez un fichier `.env` à la racine du répertoire de l'API (`libs/web_api/.env`) ou configurez ces variables dans votre environnement système :
```env
# Configuration du serveur
PORT=5000
DEBUG=True
HOST=127.0.0.1

# Configuration CORS (ajustez selon les besoins de votre client React)
CORS_ORIGINS=http://localhost:3000,http://localhost:3001 

# Logging
LOG_LEVEL=INFO
```
Pour plus de détails sur la configuration, référez-vous au [`README de l'API Web`](../../../../../libs/web_api/README.md:0).

## Démarrage de l'API

### Méthode recommandée (depuis `libs/web_api`)

Assurez-vous que votre environnement de projet est activé (voir ci-dessus).
```bash
# 1. Naviguer vers le répertoire de l'API
cd libs/web_api

# 2. Démarrage standard (utilise les variables d'environnement)
python app.py 
# ou si un script de démarrage dédié existe (vérifier le README de libs/web_api)
# python start_api.py 

# Exemple avec options personnalisées (si supporté par app.py ou start_api.py)
# python app.py --port 8080 --debug --host 0.0.0.0
```
Consultez le [`README de l'API Web`](../../../../../libs/web_api/README.md:0) pour les commandes de démarrage exactes et les options disponibles.

### Vérification du démarrage

Une fois l'API démarrée (par défaut sur `http://localhost:5000`), vérifiez son état :
```bash
curl http://localhost:5000/api/health
```
Réponse attendue (la version et les services peuvent varier) :
```json
{
  "status": "healthy",
  "message": "API d'analyse argumentative opérationnelle",
  "version": "vérifiez_la_version_actuelle", 
  "services": {
    "analysis": true,
    "validation": true,
    "fallacy": true,
    "framework": true
  }
}
```

## Endpoints Disponibles

La liste exhaustive et les détails des endpoints sont disponibles dans la documentation du composant [`API Web`](../../../../composants/api_web.md:1) et le [`Guide d'Intégration de l'API Web`](../../../../guides/integration_api_web.md:1). Voici un aperçu des endpoints courants :

### 🔍 Health Check
-   **URL** : `GET /api/health`
-   **Description** : Vérifie l'état de l'API.
-   **Réponse** : Statut de l'API et des services.

### 📊 Analyse Complète
-   **URL** : `POST /api/analyze`
-   **Description** : Analyse complète d'un texte argumentatif.
-   **Content-Type** : `application/json`
-   **Corps de la requête (exemple) :**
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
-   **URL** : `POST /api/validate`
-   **Description** : Valide la logique d'un argument.
-   **Content-Type** : `application/json`
-   **Corps de la requête (exemple) :**
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
    Pour un exemple de test de cet endpoint, consultez la fonction [`test_validate_endpoint`](../../../../../libs/web_api/test_api.py:74) dans le script [`libs/web_api/test_api.py`](../../../../../libs/web_api/test_api.py:0).

### 🚫 Détection de Sophismes
-   **URL** : `POST /api/fallacies`
-   **Description** : Détecte spécifiquement les sophismes.
-   **Content-Type** : `application/json`
-   **Corps de la requête (exemple) :**
    ```json
    {
      "text": "Texte à analyser pour les sophismes",
      "options": {
        "severity_threshold": 0.3,
        "include_context": true,
        "max_fallacies": 10,
        "categories": ["informal"] 
      }
    }
    ```
    Pour un exemple de test de cet endpoint, consultez la fonction [`test_fallacies_endpoint`](../../../../../libs/web_api/test_api.py:109) dans le script [`libs/web_api/test_api.py`](../../../../../libs/web_api/test_api.py:0).

### 🕸️ Framework de Dung
-   **URL** : `POST /api/framework`
-   **Description** : Construit et analyse un framework argumentatif.
-   **Content-Type** : `application/json`
-   **Corps de la requête (exemple) :**
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
    }
    ```
    Pour un exemple de test de cet endpoint, consultez la fonction [`test_framework_endpoint`](../../../../../libs/web_api/test_api.py:143) dans le script [`libs/web_api/test_api.py`](../../../../../libs/web_api/test_api.py:0).

### 📋 Liste des Endpoints (Documentation)
-   **URL** : `GET /api/endpoints` (ou un endpoint similaire, vérifiez la documentation de l'[`API Web`](../../../../composants/api_web.md:1))
-   **Description** : Fournit une documentation (souvent au format OpenAPI/Swagger) de tous les endpoints disponibles.

## Exemples d'Utilisation

Consultez le [`Guide d'Intégration de l'API Web`](../../../../guides/integration_api_web.md:1) pour des exemples détaillés. Les exemples ci-dessous illustrent des interactions basiques.

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

### Exemple 2 : Validation d'argument avec JavaScript (Fetch API)
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

### Exemple 3 : Détection de sophismes avec Python (requests)
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
print(f"Sophismes détectés: {result.get('fallacy_count', 'N/A')}") # Utiliser .get pour éviter les KeyError
```

### Inspiration pour Clients API Avancés
Bien que ciblant une API pour agents logiques, les exemples suivants peuvent inspirer la création de clients API plus robustes :
-   Script Python d'intégration : [`examples/logic_agents/api_integration_example.py`](../../../../../examples/logic_agents/api_integration_example.py:0)
-   Tutoriel interactif Jupyter Notebook : [`examples/notebooks/api_logic_tutorial.ipynb`](../../../../../examples/notebooks/api_logic_tutorial.ipynb:0)
    (Voir aussi le [`Guide d'utilisation des agents logiques`](../../../../guides/utilisation_agents_logiques.md:1) pour le contexte de ces exemples.)

## Intégration avec React

Pour une intégration React, il est recommandé de structurer votre code avec des services API, des hooks personnalisés, et des composants. Des exemples de code pour une telle structure sont disponibles dans le répertoire [`docs/projets/sujets/aide/interface-web/exemples-react/`](./exemples-react/README.md:0).

Voici un aperçu conceptuel (adaptez les chemins et la logique à votre projet) :

### Service API React (Concept)
```javascript
// Adaptez ce chemin : src/services/argumentationAPI.js
class ArgumentationAPI {
  constructor(baseURL = process.env.REACT_APP_API_URL || 'http://localhost:5000') { // Utiliser une variable d'env
    this.baseURL = baseURL;
  }

  async _fetchAPI(endpoint, options = {}) {
    const response = await fetch(`${this.baseURL}${endpoint}`, options);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Erreur API sans détails JSON.' }));
      throw new Error(`Erreur API (${response.status}): ${errorData.message || response.statusText}`);
    }
    return response.json();
  }

  async analyzeText(text, options = {}) {
    return this._fetchAPI('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, options })
    });
  }

  async validateArgument(premises, conclusion, argumentType = 'deductive') {
    return this._fetchAPI('/api/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ premises, conclusion, argument_type: argumentType })
    });
  }
  
  // ... autres méthodes pour fallacies, framework, health ...

  async checkHealth() {
    return this._fetchAPI('/api/health');
  }
}

export default new ArgumentationAPI();
```

### Hook React personnalisé (Concept)
```javascript
// Adaptez ce chemin : src/hooks/useArgumentationAPI.js
import { useState, useCallback } from 'react';
import argumentationAPI from '../services/argumentationAPI'; // Adaptez le chemin

export const useArgumentationAPI = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const callAPI = useCallback(async (apiMethod, ...args) => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiMethod(...args);
      return result;
    } catch (err) {
      setError(err.message);
      throw err; // Permet au composant appelant de gérer aussi
    } finally {
      setLoading(false);
    }
  }, []);

  // Exposer des fonctions spécifiques
  const analyzeText = useCallback((text, options) => 
    callAPI(argumentationAPI.analyzeText.bind(argumentationAPI), text, options), [callAPI]);
  
  const validateArgument = useCallback((premises, conclusion, type) =>
    callAPI(argumentationAPI.validateArgument.bind(argumentationAPI), premises, conclusion, type), [callAPI]);

  // ... autres fonctions ...

  return {
    analyzeText,
    validateArgument,
    // ... autres fonctions ...
    loading,
    error
  };
};
```

### Composant React d'exemple (Concept)
Le composant `ArgumentAnalyzer.jsx` fourni précédemment est un bon point de départ. Assurez-vous que les champs de `analysis` (ex: `overall_quality`, `fallacy_count`, `fallacies`, `argument_structure`) correspondent à la réponse réelle de votre API, telle que définie dans la documentation du composant [`API Web`](../../../../composants/api_web.md:1).

Consultez les exemples complets dans [`docs/projets/sujets/aide/interface-web/exemples-react/`](./exemples-react/README.md:0).

## Gestion des Erreurs

### Types d'erreurs courantes
1.  **Erreurs de validation (HTTP 400, 422)** : Données de requête invalides ou manquantes.
2.  **Erreurs d'authentification/autorisation (HTTP 401, 403)** : Si l'API implémente de tels mécanismes.
3.  **Erreurs "Non trouvé" (HTTP 404)** : Endpoint incorrect.
4.  **Erreurs internes du serveur (HTTP 500)** : Problèmes côté serveur.
5.  **Erreurs de réseau** : Problèmes de connexion, timeouts.

### Gestion des erreurs en JavaScript (amélioration)
```javascript
const handleAPICall = async (apiFunction, ...args) => {
  try {
    const result = await apiFunction(...args);
    return { success: true, data: result };
  } catch (error) {
    console.error('Erreur API détaillée:', error); // Log l'objet erreur complet
    let errorMessage = 'Une erreur est survenue.';
    if (error.message) { // L'erreur peut provenir du throw new Error(...)
        if (error.message.includes('API (400)') || error.message.includes('API (422)')) {
            errorMessage = 'Données invalides. Vérifiez votre requête.';
        } else if (error.message.includes('API (401)') || error.message.includes('API (403)')) {
            errorMessage = 'Accès non autorisé.';
        } else if (error.message.includes('API (404)')) {
            errorMessage = 'Service non trouvé.';
        } else if (error.message.includes('API (5')) { // Commence par 5xx
            errorMessage = 'Erreur serveur. Réessayez plus tard.';
        } else if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
            errorMessage = 'Erreur de connexion. Vérifiez que l\'API est démarrée et accessible.';
        } else {
            errorMessage = error.message; // Message d'erreur plus générique de l'API
        }
    }
    return { success: false, error: errorMessage };
  }
};
```
L'utilisation d'un `ErrorBoundary` React, comme montré précédemment, est également une bonne pratique pour capturer les erreurs non gérées dans le rendu des composants.

## Bonnes Pratiques

Consultez le [`Guide Développeur`](../../../../guides/guide_developpeur.md:1) pour des bonnes pratiques générales.

### 1. Configuration de l'environnement
-   Utilisez des variables d'environnement (ex: via `.env` et `process.env` en React) pour les URLs de l'API et autres configurations sensibles.
-   Séparez les configurations pour les environnements de développement, test, et production.
-   Configurez CORS sur le serveur API (`libs/web_api/`) pour autoriser uniquement les domaines de vos applications clientes.

### 2. Performance
-   Envisagez la mise en cache côté client pour les données qui ne changent pas fréquemment.
-   Utilisez la pagination si l'API renvoie de grandes listes de données (vérifiez si les endpoints de l'API la supportent).
-   Optimisez la taille des textes envoyés pour analyse si cela impacte la performance.
-   Utilisez des techniques de "lazy loading" ou de "code splitting" dans votre application React.

### 3. Sécurité
-   Validez et nettoyez (sanitize) toujours les entrées utilisateur côté client avant l'envoi et impérativement côté serveur (l'API doit le faire).
-   Si l'API le requiert, gérez de manière sécurisée les jetons d'authentification.
-   Soyez conscient des risques d'attaques XSS si vous affichez du contenu provenant de l'API sans le nettoyer correctement.
-   Le serveur API devrait implémenter une limitation de taux (rate limiting).

### 4. UX/UI
-   Affichez des indicateurs de chargement clairs pendant les appels API.
-   Fournissez des messages d'erreur conviviaux et informatifs à l'utilisateur.
-   Envisagez une fonctionnalité de "réessayer" pour les erreurs réseau ou serveur temporaires.

### 5. Tests
-   Écrivez des tests unitaires pour vos services API, hooks et composants React (ex: avec Jest et React Testing Library).
    ```javascript
    // Exemple de test avec Jest et MSW (Mock Service Worker) pour mocker les appels API
    // Voir la documentation de MSW pour une configuration complète.
    import { rest } from 'msw';
    import { setupServer } from 'msw/node';
    import argumentationAPI from '../services/argumentationAPI'; // Adaptez

    const server = setupServer(
      rest.post('http://localhost:5000/api/analyze', (req, res, ctx) => {
        return res(ctx.json({ success: true, fallacy_count: 1, overall_quality: 0.7 }));
      })
    );

    beforeAll(() => server.listen());
    afterEach(() => server.resetHandlers());
    afterAll(() => server.close());

    describe('ArgumentationAPI Service', () => {
      test('analyzeText should return data on success', async () => {
        const result = await argumentationAPI.analyzeText('Test text');
        expect(result.success).toBe(true);
        expect(result.fallacy_count).toBe(1);
      });
    });
    ```
-   Pour des exemples de tests d'intégration Python pour l'API elle-même, consultez [`libs/web_api/test_api.py`](../../../../../libs/web_api/test_api.py:0).

### 6. Monitoring et Logging
-   Utilisez des outils de logging côté client (ex: Sentry, LogRocket) pour capturer les erreurs en production.
-   Le serveur API devrait avoir son propre système de logging et de monitoring.

## Support et Ressources

-   **Portail des Guides Officiels** : [`docs/guides/README.md`](../../../../guides/README.md:1) (point d'entrée principal pour la documentation).
-   **Documentation de l'API Web (Composant)** : [`docs/composants/api_web.md`](../../../../composants/api_web.md:1) (détails techniques de l'API).
-   **Guide d'Intégration de l'API Web** : [`docs/guides/integration_api_web.md`](../../../../guides/integration_api_web.md:1).
-   **Guide Développeur Général** : [`docs/guides/guide_developpeur.md`](../../../../guides/guide_developpeur.md:1).
-   **README de l'API Web (Code)** : [`libs/web_api/README.md`](../../../../../libs/web_api/README.md:0) (informations spécifiques au code de l'API).
-   **Exemples de code React** : [`docs/projets/sujets/aide/interface-web/exemples-react/`](./exemples-react/README.md:0).
-   **Tests d'API en Python** : [`libs/web_api/test_api.py`](../../../../../libs/web_api/test_api.py:0).
-   **Autres guides pertinents** :
    -   [`Guide d'utilisation des agents logiques`](../../../../guides/utilisation_agents_logiques.md:1)
    -   Consultez le portail des guides pour d'autres logiques formelles si nécessaire.
-   **Démarrage Rapide pour l'Interface Web** : [`DEMARRAGE_RAPIDE.md`](./DEMARRAGE_RAPIDE.md:0).
-   **Troubleshooting (si disponible)** : Recherchez un fichier `TROUBLESHOOTING.md` dans les répertoires pertinents.

## Changelog

-   **vX.Y.Z** : (Consultez le changelog principal du projet ou le [`README de l'API Web`](../../../../../libs/web_api/README.md:0) pour les versions).
-   Ce document est régulièrement mis à jour pour refléter les évolutions de l'API et des bonnes pratiques.

---

*Ce guide est maintenu par l'équipe du projet d'Intelligence Symbolique EPITA 2025.*