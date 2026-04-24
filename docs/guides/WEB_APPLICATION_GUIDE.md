# Guide de l'Application Web d'Analyse Argumentative

## Vue d'ensemble

L'application web d'analyse argumentative est composée de deux parties principales :
- **Backend Flask** : API REST pour l'analyse de logique propositionnelle
- **Frontend React** : Interface utilisateur graphique pour la visualisation et l'interaction

## 🚀 Démarrage Rapide

### Prérequis
- Python 3.13+ avec l'environnement conda `projet-is`
- Node.js 16+ et npm
- Variables d'environnement configurées (voir `.env`)

### Lancement Simple
```powershell
# Lancer backend et frontend ensemble
.\start_web_application.ps1

# Lancer uniquement le backend
.\start_web_application.ps1 -BackendOnly

# Lancer uniquement le frontend  
.\start_web_application.ps1 -FrontendOnly
```

### Accès aux Services
- **Interface Frontend** : http://localhost:3000
- **API Backend** : http://localhost:5003
- **Health Check** : http://localhost:5003/api/health

## 🏗️ Architecture

### Backend Flask
**Localisation** : `argumentation_analysis/services/web_api/`

#### Composants Principaux
- **`app.py`** : Application Flask principale avec routes API
- **`services/logic_service.py`** : Service de traitement logique
- **`models/`** : Modèles Pydantic pour requêtes/réponses
- **`start_api.py`** : Script de démarrage du serveur

#### Endpoints API Principaux
- `POST /api/logic/belief-set` : Conversion texte → ensemble de croyances
- `POST /api/logic/query` : Exécution de requêtes logiques
- `GET /api/health` : Vérification de l'état du serveur

### Frontend React
**Localisation** : `services/web_api/interface-web-argumentative/`

#### Composants Principaux
- **`src/App.js`** : Application React principale
- **`src/components/LogicGraph.js`** : Composant de visualisation logique
- **`src/services/api.js`** : Client API pour communication backend
- **`public/`** : Assets statiques

#### Fonctionnalités
- ✅ Conversion de texte en graphiques logiques
- ✅ Visualisation SVG des ensembles de croyances
- ✅ Gestion d'erreurs avec affichage utilisateur
- ✅ Interface responsive et moderne

## 🧪 Tests et Validation

### Tests Fonctionnels Playwright
**Localisation** : `tests/functional/test_logic_graph.py`

Les tests automatisés vérifient :
1. **Génération réussie de graphiques** (`test_successful_graph_visualization`)
2. **Gestion des erreurs API** (`test_logic_graph_api_error`) 
3. **Fonctionnalité de réinitialisation** (`test_logic_graph_reset_button`)

#### Exécution des Tests
```powershell
# Tests complets avec démarrage automatique des serveurs
.\scripts\run_all_and_test.ps1

# Tests uniquement (serveurs déjà en cours)
pytest tests/functional/test_logic_graph.py -v
```

### Validation Manuelle
1. Accéder à http://localhost:3000
2. Aller dans l'onglet "Logic Graph"
3. Saisir : `A -> B; B -> C`
4. Cliquer "Generate Graph"
5. Vérifier l'affichage du SVG et des informations

## 🔧 Configuration et Personnalisation

### Variables d'Environnement
```bash
# Backend
FLASK_ENV=development
FLASK_DEBUG=true

# Services de logique
USE_REAL_JPYPE=true
JAVA_HOME=./libs/portable_jdk/jdk-17.0.11+9

# Base de données (si applicable)
PYTHONPATH=./
```

### Ports par Défaut
- **Backend Flask** : 5003
- **Frontend React** : 3000
- **Tests Playwright** : Utilise les ports ci-dessus

### Personnalisation Frontend
Modifier `services/web_api/interface-web-argumentative/src/services/api.js` :
```javascript
const API_BASE_URL = 'http://localhost:5003'; // Changer l'URL du backend
```

## 📊 Monitoring et Debugging

### Logs Backend
- Localisation : Console PowerShell ou `logs/`
- Niveau de log : Configurable via `FLASK_DEBUG`
- Format : Timestamp, niveau, message

### Logs Frontend  
- Console navigateur (F12)
- Erreurs réseau dans l'onglet Network
- State React via React Developer Tools

### Health Checks
```powershell
# Vérifier backend
Invoke-RestMethod -Uri "http://localhost:5003/api/health"

# Vérifier frontend
curl http://localhost:3000
```

## 🐛 Résolution de Problèmes

### Erreurs Communes

#### Backend ne démarre pas
```powershell
# Vérifier l'environnement
.\scripts\env\activate_project_env.ps1

# Vérifier les dépendances
pip install -e .

# Vérifier JAVA_HOME
echo $env:JAVA_HOME
```

#### Frontend ne se lance pas
```powershell
cd services/web_api/interface-web-argumentative
npm install
npm start
```

#### Tests Playwright échouent
```powershell
# Installer les navigateurs Playwright
playwright install

# Vérifier que les serveurs tournent
Test-NetConnection localhost -Port 5003
Test-NetConnection localhost -Port 3000
```

### Messages d'Erreur Typiques

| Erreur | Cause | Solution |
|--------|-------|----------|
| `Connection refused` | Backend arrêté | Relancer `start_web_application.ps1` |
| `Module not found` | Environnement non activé | `activate_project_env.ps1` |
| `JVM not started` | JAVA_HOME incorrect | Vérifier `.env` |
| `npm ERR!` | Dépendances manquantes | `npm install` dans le dossier frontend |

## 📚 Documentation Supplémentaire

- **[Guide Installation](../GUIDE_INSTALLATION_ETUDIANTS.md)** : Configuration initiale
- **[Tests Fonctionnels](testing/functional_tests.md)** : Documentation des tests
- **[API Documentation](../argumentation_analysis/services/web_api/README.md)** : Référence API détaillée

## 🤝 Contribution

### Workflow de Développement
1. Créer une branche : `git checkout -b feature/nouvelle-fonctionnalite`
2. Développer et tester localement
3. Exécuter les tests : `.\scripts\run_all_and_test.ps1`
4. Commit et push : `git commit -am "Ajout nouvelle fonctionnalité"`
5. Créer une Pull Request

### Standards de Code
- **Backend** : PEP 8, type hints, documentation docstring
- **Frontend** : ESLint, Prettier, PropTypes
- **Tests** : Coverage > 80%, tests pour chaque composant

---

*Dernière mise à jour : 2025-06-06*  
*Version Application : 1.0.0*