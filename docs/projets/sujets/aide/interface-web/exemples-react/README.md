# Exemples React pour l'API d'Argumentation

Ce dossier contient une collection complète d'exemples d'utilisation de l'API d'argumentation avec React, incluant tous les outils disponibles.

## 🚀 Démarrage rapide

1.  **Activez l'environnement du projet :**
    Avant de démarrer l'API, assurez-vous que votre environnement de projet est correctement activé. Par exemple, si vous utilisez le script fourni à la racine du projet :
    ```bash
    # Depuis la racine du projet
    ./activate_project_env.ps1
    ```

2.  **Démarrez l'API :**
    Une fois l'environnement activé, naviguez vers le répertoire de l'API et lancez-la :
    ```bash
    cd services/web_api
    python start_api.py
    ```
    L'API devrait maintenant être accessible (par défaut sur `http://localhost:5000`).

3.  **Intégrez les composants dans votre projet React :**
    ```jsx
    import Demo from './exemples-react/Demo'; // Assurez-vous que le chemin est correct
    import './exemples-react/Demo.css';

    function App() {
      return <Demo />;
    }
    ```

## 📦 Composants disponibles

### 🎯 Demo.jsx
**Interface de démonstration complète** qui présente tous les outils dans une interface unifiée.

**Fonctionnalités :**
- Navigation par onglets entre tous les outils
- Exemples pré-configurés pour chaque outil
- Résumé des résultats en temps réel
- Guide d'utilisation intégré

### 🔍 ArgumentAnalyzer.jsx
**Analyseur d'arguments complet** pour l'analyse de textes argumentatifs.

**Fonctionnalités :**
- Analyse complète avec détection de sophismes
- Évaluation de la structure argumentative
- Scores de qualité et cohérence
- Options avancées configurables

**Utilisation :**
```jsx
import ArgumentAnalyzer from './ArgumentAnalyzer';

<ArgumentAnalyzer 
  onAnalysisComplete={(results) => console.log(results)}
  showAdvancedOptions={true}
/>
```

### ✓ ValidationForm.jsx
**Validateur logique d'arguments** pour vérifier la validité et solidité.

**Fonctionnalités :**
- Validation de prémisses et conclusions
- Calcul de scores de validité et solidité
- Identification des problèmes logiques
- Suggestions d'amélioration

**Utilisation :**
```jsx
import ValidationForm from './ValidationForm';

<ValidationForm 
  onValidationComplete={(results) => console.log(results)}
  showArgumentType={true}
/>
```

### ⚠️ FallacyDetector.jsx
**Détecteur de sophismes** spécialisé dans l'identification des erreurs de raisonnement.

**Fonctionnalités :**
- Détection de sophismes formels et informels
- Classification par sévérité et catégorie
- Statistiques de distribution
- Options de filtrage avancées

**Utilisation :**
```jsx
import FallacyDetector from './FallacyDetector';

<FallacyDetector 
  onFallaciesDetected={(results) => console.log(results)}
  showAdvancedOptions={true}
/>
```

### 🏗️ FrameworkBuilder.jsx
**Constructeur de frameworks de Dung** pour créer et analyser des frameworks d'argumentation.

**Fonctionnalités :**
- Construction interactive de frameworks
- Calcul d'extensions selon différentes sémantiques
- Visualisation graphique
- Gestion des relations d'attaque et support

**Utilisation :**
```jsx
import FrameworkBuilder from './FrameworkBuilder';

<FrameworkBuilder 
  onFrameworkBuilt={(results) => console.log(results)}
  showVisualization={true}
  allowSemantics={['grounded', 'preferred', 'stable']}
/>
```

### 🔗 useArgumentationAPI.js (Hook)
**Hook React personnalisé** pour interagir avec l'API d'argumentation.

**Fonctionnalités :**
- Gestion complète de tous les endpoints (voir la [documentation de l'API Web](../../../../composants/api_web.md) pour le détail des endpoints)
- États de chargement et gestion d'erreurs
- Cache des résultats (si configuré et applicable)
- Configuration flexible

**Utilisation :**
```jsx
import { useArgumentationAPI } from './hooks/useArgumentationAPI';

function MyComponent() {
  const { 
    analyzeText, 
    validateArgument, 
    detectFallacies, 
    buildFramework,
    loading, 
    error 
  } = useArgumentationAPI();

  // Utilisation des différentes fonctions...
}
```

## 🛠️ Utilitaires

### 📊 formatters.js
**Fonctions de formatage** pour présenter les données de manière lisible.

**Fonctions disponibles :**
- `formatScore(score)` - Formatage des scores en pourcentages
- `formatProcessingTime(time)` - Formatage des temps de traitement
- `formatSeverityLevel(severity)` - Formatage des niveaux de sévérité
- `formatArgumentStatus(status)` - Formatage des statuts d'arguments
- Et bien d'autres...

### ✅ validators.js
**Fonctions de validation** pour vérifier les données avant envoi à l'API.

**Fonctions disponibles :**
- `validateArgumentText(text)` - Validation de textes d'arguments
- `validatePremises(premises)` - Validation de listes de prémisses
- `validateFrameworkArguments(args)` - Validation d'arguments de framework
- `validateApiUrl(url)` - Validation d'URLs d'API
- Et bien d'autres...

## 📁 Structure des fichiers

```
exemples-react/
├── Demo.jsx                    # Interface de démonstration complète
├── Demo.css                    # Styles pour la démo
├── ArgumentAnalyzer.jsx        # Analyseur d'arguments
├── ArgumentAnalyzer.css        # Styles de l'analyseur
├── ValidationForm.jsx          # Formulaire de validation
├── FallacyDetector.jsx         # Détecteur de sophismes
├── FallacyDetector.css         # Styles du détecteur
├── FrameworkBuilder.jsx        # Constructeur de frameworks
├── FrameworkBuilder.css        # Styles du constructeur
├── hooks/
│   └── useArgumentationAPI.js  # Hook pour l'API
├── utils/
│   ├── formatters.js           # Utilitaires de formatage
│   └── validators.js           # Utilitaires de validation
└── README.md                   # Cette documentation
```

## ⚙️ Installation et configuration

### Prérequis
- Node.js 16+ et npm/yarn
- API d'argumentation démarrée (par défaut sur `http://localhost:5000` après activation de l'environnement)

### Installation
```bash
# Installation des dépendances React
npm install react react-dom

# Optionnel : dépendances pour les graphiques (si utilisées par certains exemples)
npm install recharts d3
```

### Configuration
1.  **URL de l'API :** L'URL de base de l'API est configurée dans `hooks/useArgumentationAPI.js`. Modifiez la variable `baseURL` dans `API_CONFIG` si votre API n'est pas sur `http://localhost:5000`.
2.  **CORS :** Assurez-vous que l'API autorise les requêtes depuis le domaine et le port de votre application React (ex: `http://localhost:3000`).
3.  **Styles :** Importez les fichiers CSS nécessaires pour les composants que vous utilisez (ex: `Demo.css`, `ArgumentAnalyzer.css`, etc.).

## 🎨 Exemples d'utilisation

### Interface complète
```jsx
import React from 'react';
import Demo from './exemples-react/Demo'; // Ajustez le chemin si nécessaire
import './exemples-react/Demo.css';   // Ajustez le chemin si nécessaire

function App() {
  return (
    <div className="App">
      <Demo />
    </div>
  );
}
```

### Composants individuels
```jsx
import React, { useState } from 'react';
import ArgumentAnalyzer from './exemples-react/ArgumentAnalyzer'; // Ajustez les chemins
import FallacyDetector from './exemples-react/FallacyDetector';

function MyApp() {
  const [results, setResults] = useState({});

  return (
    <div>
      <ArgumentAnalyzer 
        onAnalysisComplete={(data) => setResults({...results, analysis: data})}
      />
      
      <FallacyDetector 
        onFallaciesDetected={(data) => setResults({...results, fallacies: data})}
      />
    </div>
  );
}
```

### Utilisation du hook
```jsx
import { useArgumentationAPI } from './exemples-react/hooks/useArgumentationAPI'; // Ajustez le chemin
import { formatScore, formatProcessingTime } from './exemples-react/utils/formatters'; // Ajustez le chemin
import { validateArgumentText } from './exemples-react/utils/validators'; // Ajustez le chemin

function CustomAnalyzer() {
  const { analyzeText, loading, error } = useArgumentationAPI();
  const [text, setText] = useState('');
  const [results, setResults] = useState(null);

  const handleAnalyze = async () => {
    // Validation avant envoi
    const validation = validateArgumentText(text);
    if (!validation.isValid) {
      alert('Texte invalide: ' + validation.errors.join(', '));
      return;
    }

    // Analyse
    const result = await analyzeText(text);
    setResults(result);
  };

  return (
    <div>
      <textarea 
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Saisissez votre argument..."
      />
      
      <button onClick={handleAnalyze} disabled={loading}>
        {loading ? 'Analyse...' : 'Analyser'}
      </button>

      {error && <div className="error">Erreur: {error}</div>}

      {results && (
        <div className="results">
          <h3>Résultats</h3>
          <p>Qualité: {formatScore(results.overall_quality)}</p>
          <p>Temps: {formatProcessingTime(results.processing_time)}</p>
          <p>Sophismes: {results.fallacy_count}</p>
        </div>
      )}
    </div>
  );
}
```

## 🔧 Personnalisation

### Thèmes et styles
Tous les composants utilisent des variables CSS pour faciliter la personnalisation :

```css
:root {
  --primary-color: #007bff;
  --success-color: #28a745;
  --warning-color: #ffc107;
  --danger-color: #dc3545;
  --border-radius: 8px;
  --box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
```

### Configuration de l'API

La configuration de l'API se fait principalement dans le hook [`useArgumentationAPI.js`](#useargumentationapijs-hook). Il est crucial de s'assurer que l'URL de base (`baseURL`) pointe vers votre instance de l'API d'argumentation.

Pour une compréhension détaillée des endpoints disponibles et des options de configuration avancées, référez-vous à :
- **Documentation de l'API Web :** [`../../../../composants/api_web.md`](../../../../composants/api_web.md)
- **Guide d'Intégration de l'API Web :** [`../../../../guides/integration_api_web.md`](../../../../guides/integration_api_web.md)

```javascript
// Dans useArgumentationAPI.js
const API_CONFIG = {
  baseURL: 'http://localhost:5000', // Assurez-vous que cette URL correspond à votre instance de l'API
  timeout: 30000, // Délai d'attente en millisecondes pour les requêtes
  retries: 3,       // Nombre de tentatives en cas d'échec réseau (pour les requêtes GET idempotentes)
  cache: true      // Activation du cache pour les requêtes GET (si implémenté dans le hook)
};
```

## 🐛 Dépannage

### Problèmes courants

1.  **Erreur CORS :**
    Vérifiez que l'API autorise les requêtes depuis l'origine de votre application React (ex: `http://localhost:3000`). Vous pouvez tester avec `curl` :
    ```bash
    # Remplacez http://localhost:3000 par l'origine de votre application React
    curl -I -H "Origin: http://localhost:3000" http://localhost:5000/health
    ```
    Recherchez l'en-tête `Access-Control-Allow-Origin` dans la réponse.

2.  **API non accessible :**
    Assurez-vous que l'API est démarrée et écoute sur l'URL et le port attendus.
    ```bash
    curl http://localhost:5000/health
    ```
    Cela devrait retourner une réponse de l'API (par exemple, un statut de santé).

3.  **Erreurs de validation des données :**
    - Utilisez les fonctions de validation fournies dans [`utils/validators.js`](#validatorsjs) avant d'envoyer des données à l'API.
    - Consultez la [documentation de l'API Web](../../../../composants/api_web.md) pour les formats de données attendus par chaque endpoint.

### Logs de débogage
Pour activer des logs plus détaillés dans la console lors des interactions avec l'API (si le hook `useArgumentationAPI.js` le supporte) :
```javascript
// Dans la console de votre navigateur
localStorage.setItem('DEBUG_API', 'true');
// Rafraîchissez la page
```

## 📚 Documentation Complète et Références Utiles

Pour une compréhension approfondie de l'API Web et du système global, veuillez consulter :

- **Documentation de l'API Web (Composant) :** [`../../../../composants/api_web.md`](../../../../composants/api_web.md) - Description détaillée du composant API Web, son architecture et ses endpoints.
- **Guide d'Intégration de l'API Web :** [`../../../../guides/integration_api_web.md`](../../../../guides/integration_api_web.md) - Instructions pas à pas pour intégrer l'API Web dans vos applications.
- **Guide du Développeur :** [`../../../../guides/guide_developpeur.md`](../../../../guides/guide_developpeur.md) - Informations générales pour les développeurs contribuant au projet.
- **Portail des Guides :** [`../../../../guides/README.md`](../../../../guides/README.md) - Point d'entrée vers tous les guides techniques et d'utilisation.
- **Architecture Globale :** [`../../../../architecture/architecture_globale.md`](../../../../architecture/architecture_globale.md) - Vue d'ensemble de l'architecture du système (pour contexte).

Les anciens liens spécifiques à ce dossier d'exemples ont été remplacés ou complétés par les références ci-dessus, qui sont plus actuelles et centralisées au sein de la documentation globale du projet.

## 🤝 Contribution

Pour contribuer à ces exemples :

1.  Fork le projet principal contenant ces exemples.
2.  Créez une branche pour votre fonctionnalité : `git checkout -b feature/nouvelle-fonctionnalite-react`
3.  Faites vos modifications et committez : `git commit -m 'Ajout nouvelle fonctionnalité aux exemples React'`
4.  Poussez votre branche : `git push origin feature/nouvelle-fonctionnalite-react`
5.  Ouvrez une Pull Request sur le dépôt principal.

## 📄 Licence

Ces exemples sont fournis sous licence MIT. Voir le fichier `LICENSE` à la racine du projet principal pour plus de détails.