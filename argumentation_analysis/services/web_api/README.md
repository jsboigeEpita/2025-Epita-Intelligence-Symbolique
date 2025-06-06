# API Web d'Analyse Argumentative

## Vue d'ensemble

Cette API Flask fournit des services web pour l'analyse de logique propositionnelle et d'argumentation. Elle expose des endpoints REST pour la conversion de texte en ensembles de croyances logiques et l'exécution de requêtes.

## 🚀 Démarrage Rapide

### Méthode Recommandée
```powershell
# Depuis la racine du projet
.\start_web_application.ps1 -BackendOnly
```

### Démarrage Manuel
```powershell
# Activer l'environnement
.\scripts\env\activate_project_env.ps1

# Lancer le serveur
python -m argumentation_analysis.services.web_api.app
```

L'API sera accessible sur http://localhost:5003

## 📡 Endpoints API

### Health Check
```http
GET /api/health
```
Vérification de l'état du serveur.

**Réponse :**
```json
{
  "status": "healthy",
  "timestamp": "2025-06-06T20:15:00Z",
  "version": "1.0.0"
}
```

### Conversion Texte → Ensemble de Croyances
```http
POST /api/logic/belief-set
Content-Type: application/json
```

**Corps de la requête :**
```json
{
  "text": "A -> B; B -> C",
  "logic_type": "propositional",
  "options": {
    "include_explanation": true
  }
}
```

**Réponse :**
```json
{
  "success": true,
  "conversion_timestamp": "2025-06-06T20:15:00Z",
  "belief_set": {
    "id": "bs_123456",
    "logic_type": "propositional",
    "content": "a=>b, b=>c",
    "source_text": "A -> B; B -> C",
    "creation_timestamp": "2025-06-06T20:15:00Z"
  },
  "processing_time": 0.145,
  "conversion_options": {
    "include_explanation": true
  }
}
```

### Exécution de Requête Logique
```http
POST /api/logic/query
Content-Type: application/json
```

**Corps de la requête :**
```json
{
  "belief_set_id": "bs_123456",
  "query": "a => c",
  "logic_type": "propositional",
  "options": {
    "include_explanation": true
  }
}
```

## 🏗️ Architecture

### Structure des Fichiers
```
argumentation_analysis/services/web_api/
├── app.py                 # Application Flask principale
├── start_api.py          # Script de démarrage
├── logic_service.py      # Service de logique (DEPRECATED)
├── models/
│   ├── request_models.py  # Modèles Pydantic pour requêtes
│   └── response_models.py # Modèles Pydantic pour réponses
├── services/
│   ├── logic_service.py   # Service principal de logique
│   ├── analysis_service.py
│   ├── fallacy_service.py
│   ├── framework_service.py
│   └── validation_service.py
└── tests/
    ├── test_basic.py
    ├── test_endpoints.py
    └── test_services.py
```

### Composants Principaux

#### `app.py`
Application Flask principale avec :
- Configuration CORS pour le frontend
- Routes API définies
- Gestion d'erreurs globale
- Support async/await

#### `services/logic_service.py`
Service principal pour :
- Conversion texte → ensemble de croyances
- Interface avec TweetyProject (Java)
- Gestion JPype et JVM
- Validation des entrées

#### `models/`
Modèles Pydantic pour :
- Validation automatique des requêtes
- Sérialisation des réponses
- Documentation automatique des types

## 🔧 Configuration

### Variables d'Environnement
```bash
# Java et JPype
JAVA_HOME=./libs/portable_jdk/jdk-17.0.11+9
USE_REAL_JPYPE=true
PYTHONPATH=./

# Flask
FLASK_ENV=development
FLASK_DEBUG=true
```

### Dépendances Principales
- **Flask** : Framework web
- **Pydantic** : Validation et sérialisation
- **JPype1** : Interface Java-Python
- **AsyncIO** : Support asynchrone

## 🧪 Tests

### Tests Unitaires
```powershell
# Tests complets
pytest argumentation_analysis/services/web_api/tests/ -v

# Test spécifique
pytest argumentation_analysis/services/web_api/tests/test_endpoints.py -v
```

### Tests d'Intégration
```powershell
# Tests fonctionnels avec Playwright
pytest tests/functional/test_logic_graph.py -v
```

### Tests Manuels
```powershell
# Health check
curl http://localhost:5003/api/health

# Test endpoint belief-set
$body = @{text="A -> B"; logic_type="propositional"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:5003/api/logic/belief-set" -Method POST -Body $body -ContentType "application/json"
```

## 📊 Monitoring

### Logs
- Niveau : INFO, DEBUG, ERROR
- Format : `[TIMESTAMP] [LEVEL] [MODULE] MESSAGE`
- Sortie : Console + fichiers (si configuré)

### Métriques
- Temps de traitement des requêtes
- Taux de succès/erreur
- Utilisation mémoire JVM

## 🐛 Résolution de Problèmes

### Erreurs Communes

#### JVM ne démarre pas
```
ERROR: JVM startup failed
```
**Solution :** Vérifier `JAVA_HOME` et `USE_REAL_JPYPE=true`

#### Import TweetyProject échoue
```
ERROR: TweetyProject classes not found
```
**Solution :** Vérifier le classpath Java et les JARs dans `libs/`

#### Erreur de sérialisation Pydantic
```
ERROR: validation error for LogicBeliefSetRequest
```
**Solution :** Vérifier le format JSON de la requête

### Debug Mode
```powershell
# Activer debug détaillé
$env:FLASK_DEBUG = "true"
python -m argumentation_analysis.services.web_api.app
```

## 🚀 Déploiement

### Développement
Le serveur utilise le serveur de développement Flask (non recommandé pour production).

### Production
Pour un déploiement en production, utiliser :
- **Gunicorn** : `gunicorn argumentation_analysis.services.web_api.app:app`
- **uWSGI** : Configuration dans `uwsgi.ini`
- **Docker** : Conteneurisation avec `Dockerfile`

## 🔄 Intégration Frontend

L'API est conçue pour fonctionner avec le frontend React situé dans :
```
services/web_api/interface-web-argumentative/
```

Configuration CORS activée pour :
- Origin: `http://localhost:3000`
- Methods: GET, POST, OPTIONS
- Headers: Content-Type, Authorization

## 📚 Documentation Supplémentaire

- **[Guide Application Web](../../../docs/WEB_APPLICATION_GUIDE.md)** : Guide complet
- **[Tests Fonctionnels](../../../tests/README_FUNCTIONAL_TESTS.md)** : Documentation tests
- **[Models Documentation](./models/README.md)** : Référence modèles Pydantic

---

*Dernière mise à jour : 2025-06-06*  
*Version API : 1.0.0*