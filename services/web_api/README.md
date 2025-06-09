# Interfaces Web - Analyse Argumentative EPITA

Ce répertoire contient les deux interfaces utilisateur du système d'analyse argumentative.

## Structure des Interfaces

### 🔥 Interface Complète (5 onglets)
**Localisation :** `interface-web-argumentative/`

Interface React complète avec les 5 composants spécialisés :

1. **ArgumentAnalyzer** - Analyse d'arguments
2. **ValidationForm** - Validation logique
3. **FallacyDetector** - Détection de sophismes
4. **FrameworkBuilder** - Construction de frameworks
5. **LogicGraph** - Graphiques logiques

**Technologie :** React + Node.js + API REST
**Port :** 3000 (par défaut)
**API Backend :** services/web_api_from_libs/app.py

### 🚀 Interface Simple
**Localisation :** `interface-simple/`

Interface Flask simple et unifiée :

- Page unique avec toutes les fonctionnalités
- Interface responsive Bootstrap
- Analyse complète ou spécialisée
- Exemples intégrés

**Technologie :** Flask + HTML/CSS/JS
**Port :** 3000 (par défaut)
**Backend :** Intégré dans l'application Flask

## Utilisation

### Interface Complète (React)

```bash
# Installation des dépendances
cd services/web_api/interface-web-argumentative
npm install

# Démarrage du serveur de développement
npm start

# Démarrage de l'API backend (terminal séparé)
cd services/web_api_from_libs
python app.py
```

L'interface sera accessible sur : http://localhost:3000
L'API backend sur : http://localhost:5000

### Interface Simple (Flask)

```bash
# Démarrage direct
cd services/web_api/interface-simple
python app.py
```

L'interface sera accessible sur : http://localhost:3000

## Services Backend

### API Complète (`services/web_api_from_libs/`)

Services spécialisés :
- **AnalysisService** - Analyse argumentative générale
- **ValidationService** - Validation de logique formelle
- **FallacyService** - Détection automatique de sophismes
- **FrameworkService** - Analyse de frameworks argumentatifs
- **LogicService** - Logique formelle et modélisation

### Interface Simple

Backend intégré avec :
- ServiceManager (si disponible)
- Mode fallback pour tests
- API REST compatible

## Tests

### Interface Complète
```bash
cd services/web_api/interface-web-argumentative
npm test
```

### Interface Simple
```bash
cd services/web_api/interface-simple
python test_webapp.py
```

## Configuration

### Variables d'environnement

```bash
# Port d'écoute
PORT=3000

# Mode debug
DEBUG=True

# Clé secrète (production)
SECRET_KEY=your-secret-key

# Répertoire de résultats
RESULTS_DIR=../../results
```

## Développement

### Interface Complète
- Framework : React 18
- UI : Material-UI + Custom CSS
- State Management : React Hooks
- API Client : Axios
- Tests : Jest + React Testing Library

### Interface Simple
- Framework : Flask 2.x
- UI : Bootstrap 5 + Font Awesome
- Templates : Jinja2
- API : JSON REST
- Tests : unittest + requests

## Architecture

```
services/web_api/
├── interface-web-argumentative/     # Interface React complète
│   ├── src/
│   │   ├── components/              # 5 composants spécialisés
│   │   ├── services/               # Client API
│   │   └── App.js                  # Application principale
│   ├── public/
│   └── package.json
├── interface-simple/               # Interface Flask simple
│   ├── templates/
│   │   └── index.html
│   ├── app.py                      # Application Flask
│   └── test_webapp.py
└── README.md                       # Ce fichier
```

## Choix d'Interface

### Utilisez l'Interface Complète si :
- Vous voulez tester chaque service séparément
- Vous développez de nouvelles fonctionnalités
- Vous avez besoin de visualisations avancées
- Vous travaillez en équipe sur des composants

### Utilisez l'Interface Simple si :
- Vous voulez une démonstration rapide
- Vous testez l'intégration complète
- Vous déployez en production simple
- Vous voulez un prototype fonctionnel

## Support

Pour toute question ou problème :
1. Vérifiez les logs d'application
2. Testez avec les exemples intégrés
3. Consultez la documentation des services backend
4. Utilisez les outils de test fournis

---
**EPITA Intelligence Symbolique 2025**