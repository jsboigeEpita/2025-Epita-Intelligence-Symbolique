# Exemples React pour l'API d'Argumentation

Ce dossier contient une collection complète d'exemples d'utilisation de l'API d'argumentation avec React, incluant tous les outils disponibles.

## 🚀 Démarrage rapide

1. **Démarrez l'API :**
   ```bash
   cd services/web_api
   python start_api.py
   ```

2. **Intégrez les composants dans votre projet React :**
   ```jsx
   import Demo from './exemples-react/Demo';
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
- Gestion complète de tous les endpoints
- États de chargement et gestion d'erreurs
- Cache des résultats
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
- API d'argumentation démarrée sur `http://localhost:5000`

### Installation
```bash
# Installation des dépendances React
npm install react react-dom

# Optionnel : dépendances pour les graphiques
npm install recharts d3
```

### Configuration
1. **URL de l'API :** Modifiez `BASE_URL` dans `hooks/useArgumentationAPI.js`
2. **CORS :** Assurez-vous que l'API autorise les requêtes depuis votre domaine
3. **Styles :** Importez les fichiers CSS nécessaires

## 🎨 Exemples d'utilisation

### Interface complète
```jsx
import React from 'react';
import Demo from './exemples-react/Demo';
import './exemples-react/Demo.css';

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
import ArgumentAnalyzer from './exemples-react/ArgumentAnalyzer';
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
import { useArgumentationAPI } from './exemples-react/hooks/useArgumentationAPI';
import { formatScore, formatProcessingTime } from './exemples-react/utils/formatters';
import { validateArgumentText } from './exemples-react/utils/validators';

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
```javascript
// Dans useArgumentationAPI.js
const API_CONFIG = {
  baseURL: 'http://localhost:5000',
  timeout: 30000,
  retries: 3,
  cache: true
};
```

## 🐛 Dépannage

### Problèmes courants

1. **Erreur CORS :**
   ```bash
   # Vérifiez que l'API autorise votre domaine
   curl -H "Origin: http://localhost:3000" http://localhost:5000/health
   ```

2. **API non accessible :**
   ```bash
   # Testez la connectivité
   curl http://localhost:5000/health
   ```

3. **Erreurs de validation :**
   - Utilisez les fonctions de `validators.js`
   - Vérifiez les formats de données dans la documentation API

### Logs de débogage
```javascript
// Activez les logs détaillés
localStorage.setItem('DEBUG_API', 'true');
```

## 📚 Documentation complète

- **[Guide d'utilisation](../GUIDE_UTILISATION_API.md)** - Documentation complète de l'API
- **[Démarrage rapide](../DEMARRAGE_RAPIDE.md)** - Guide de démarrage étape par étape  
- **[Dépannage](../TROUBLESHOOTING.md)** - Solutions aux problèmes courants

## 🤝 Contribution

Pour contribuer à ces exemples :

1. Fork le projet
2. Créez une branche : `git checkout -b feature/nouvelle-fonctionnalite`
3. Committez : `git commit -m 'Ajout nouvelle fonctionnalité'`
4. Push : `git push origin feature/nouvelle-fonctionnalite`
5. Ouvrez une Pull Request

## 📄 Licence

Ces exemples sont fournis sous licence MIT. Voir le fichier LICENSE pour plus de détails.