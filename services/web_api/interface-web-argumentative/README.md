# Interface Web Argumentative - Frontend React

## Vue d'ensemble

Interface utilisateur React pour l'analyse d'argumentation logique. Cette application web permet aux utilisateurs de saisir du texte logique, de le convertir en ensembles de croyances et de visualiser les résultats sous forme de graphiques interactifs.

## 🚀 Démarrage Rapide

### Méthode Recommandée
```powershell
# Depuis la racine du projet
.\start_web_application.ps1 -FrontendOnly
```

### Démarrage Manuel
```powershell
# Naviguer vers le répertoire frontend
cd services\web_api\interface-web-argumentative

# Installer les dépendances
npm install

# Lancer le serveur de développement
npm start
```

L'application sera accessible sur http://localhost:3000

## 🛠️ Technologies

- **React 18** : Framework UI principal
- **JavaScript ES6+** : Langage de programmation
- **CSS3** : Styling et animations
- **Fetch API** : Communication avec l'API backend
- **SVG** : Visualisation des graphiques logiques

## 📁 Structure du Projet

```
src/
├── components/
│   ├── LogicGraph.js          # Composant principal graphique
│   ├── LogicInput.js          # Formulaire de saisie
│   └── ErrorBoundary.js       # Gestion d'erreurs React
├── utils/
│   ├── api.js                 # Client API
│   ├── graphRenderer.js       # Rendu graphique SVG
│   └── constants.js           # Constantes application
├── styles/
│   ├── App.css               # Styles principaux
│   ├── LogicGraph.css        # Styles graphique
│   └── components.css        # Styles composants
├── App.js                    # Composant racine
└── index.js                  # Point d'entrée React
```

## 🧩 Composants Principaux

### `LogicGraph.js`
Composant central de l'application qui :
- Affiche le formulaire de saisie logique
- Communique avec l'API backend via `/api/logic/belief-set`
- Rend les graphiques SVG interactifs
- Gère les états de chargement et d'erreur

**Props & État :**
```javascript
const [inputText, setInputText] = useState('');
const [graphData, setGraphData] = useState(null);
const [loading, setLoading] = useState(false);
const [error, setError] = useState(null);
```

**Méthodes principales :**
```javascript
const handleSubmit = async (e) => {
  // Soumission vers l'API backend
  const response = await fetch('/api/logic/belief-set', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: inputText, logic_type: 'propositional' })
  });
};

const renderGraph = (beliefSet) => {
  // Rendu SVG du graphique logique
};
```

### `LogicInput.js`
Formulaire de saisie qui :
- Collecte le texte logique utilisateur
- Valide les entrées
- Transmet les données au composant parent

### `ErrorBoundary.js`
Composant de gestion d'erreurs React qui :
- Capture les erreurs JavaScript non gérées
- Affiche une interface d'erreur conviviale
- Permet la récupération d'erreur

## 🔗 Intégration API

### Configuration Backend
L'application frontend communique avec l'API Flask sur `http://localhost:5003`

**Endpoints utilisés :**
- `GET /api/health` : Vérification de connexion
- `POST /api/logic/belief-set` : Conversion texte → ensemble de croyances

### Format des Requêtes
```javascript
// Requête belief-set
const requestData = {
  text: "A -> B; B -> C",
  logic_type: "propositional",
  options: {
    include_explanation: true
  }
};
```

### Format des Réponses
```javascript
// Réponse belief-set
const responseData = {
  success: true,
  belief_set: {
    id: "bs_123456",
    logic_type: "propositional",
    content: "a=>b, b=>c",
    source_text: "A -> B; B -> C",
    creation_timestamp: "2025-06-06T20:15:00Z"
  },
  processing_time: 0.145
};
```

## 🎨 Interface Utilisateur

### Design System
- **Couleurs** : Palette moderne en bleu/gris
- **Typographie** : Police système avec fallbacks
- **Responsive** : Adaptation mobile et desktop
- **Accessibilité** : Support clavier et screen readers

### Composants UI
- **Zone de saisie** : Textarea avec validation
- **Boutons** : États hover, focus, disabled
- **Graphiques** : SVG interactifs avec zoom
- **Messages** : Notifications succès/erreur
- **Loading** : Indicateurs de chargement

## 🧪 Tests

### Tests Automatisés avec Playwright
Les tests fonctionnels se trouvent dans `tests/functional/test_logic_graph.py`

**Scénarios testés :**
1. **Test de base** : Conversion texte simple → graphique
2. **Test de validation** : Gestion des entrées invalides  
3. **Test de performance** : Temps de réponse < 2s

### Tests Manuels
```powershell
# Lancer les tests Playwright
pytest tests/functional/test_logic_graph.py -v

# Test spécifique
pytest tests/functional/test_logic_graph.py::test_logic_graph_conversion -v
```

### Tests Unitaires React
```powershell
# Tests composants React (si configurés)
npm test

# Tests en mode watch
npm test -- --watch
```

## 🚀 Build et Déploiement

### Build de Production
```powershell
# Build optimisé
npm run build

# Le build sera dans le dossier build/
```

### Déploiement
Les fichiers statiques peuvent être servis par :
- **Serveur web** : Apache, Nginx
- **CDN** : Cloudflare, AWS CloudFront  
- **Plateforme** : Vercel, Netlify

### Configuration Environnement
```javascript
// Variables d'environnement (si utilisées)
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5003';
```

## 🐛 Résolution de Problèmes

### Erreurs Communes

#### Serveur de développement ne démarre pas
```
Error: EADDRINUSE :::3000
```
**Solution :** Port 3000 occupé, changer de port avec `PORT=3001 npm start`

#### Erreur de connexion API
```
TypeError: Failed to fetch
```
**Solutions :**
1. Vérifier que l'API backend est lancée (`http://localhost:5003/api/health`)
2. Vérifier la configuration CORS de l'API
3. Vérifier les URLs dans le code frontend

#### Graphique ne s'affiche pas
```
Error: Cannot read property 'content' of undefined
```
**Solution :** Vérifier que l'API retourne `response.belief_set` avec la structure attendue

### Mode Debug
```javascript
// Activer les logs de debug
console.log('API Response:', response);
console.log('Graph Data:', graphData);
```

## 📊 Performance

### Optimisations
- **Code splitting** : Chargement lazy des composants
- **Memoization** : React.memo pour les composants coûteux
- **Debouncing** : Limitation des appels API lors de la saisie

### Métriques
- **Temps de chargement initial** : < 2s
- **Temps de réponse API** : < 1s
- **Taille du bundle** : < 500KB (gzippé)

## 🔄 Workflow de Développement

### Scripts NPM
```json
{
  "start": "react-scripts start",      // Serveur dev
  "build": "react-scripts build",      // Build production  
  "test": "react-scripts test",        // Tests unitaires
  "eject": "react-scripts eject"       // Éjection config
}
```

### Hot Reload
Le serveur de développement supporte le rechargement automatique lors des modifications de code.

## 📚 Documentation Supplémentaire

- **[Guide Application Web](../../../docs/WEB_APPLICATION_GUIDE.md)** : Guide complet d'utilisation
- **[API Backend](../../argumentation_analysis/services/web_api/README.md)** : Documentation API
- **[Tests Fonctionnels](../../../docs/guides/testing/functional_tests.md)** : Tests Playwright
- **[Architecture Générale](../../../docs/ARCHITECTURE.md)** : Vue d'ensemble système

## 🤝 Contribution

### Standards de Code
- **ESLint** : Linting JavaScript
- **Prettier** : Formatage automatique
- **Conventions** : camelCase pour variables, PascalCase pour composants

### Git Workflow
```powershell
# Créer une branche feature
git checkout -b feature/new-component

# Commits atomiques
git commit -m "feat: add new graph rendering feature"

# Push et pull request
git push origin feature/new-component
```

---

*Dernière mise à jour : 2025-06-06*  
*Version Frontend : 1.0.0*  
*Compatible avec API Backend v1.0.0*
