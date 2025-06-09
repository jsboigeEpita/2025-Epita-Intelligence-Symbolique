# Démos Playwright - Interface d'Analyse Argumentative

## 🎯 Résumé de la Démonstration

Les démos Playwright ont été intégrées avec succès et sont maintenant opérationnelles. L'architecture inclut :

- **Backend Flask** avec API REST pour l'analyse argumentative
- **Frontend React** avec interface utilisateur moderne
- **Tests Playwright** automatisés pour validation fonctionnelle
- **Orchestrateur unifié** pour gérer le cycle de vie complet

## 🚀 Lancement des Démos

### Option 1: Démo Complète Automatisée (Recommandée)

```bash
# Lancement automatique avec backend mock + frontend + tests Playwright
python demo_playwright_complet.py
```

Cette commande :
1. Lance automatiquement un backend mock sur le port 5003
2. Démarre le frontend React sur le port 3000
3. Exécute les tests Playwright en mode visible
4. Génère des captures d'écran dans `logs/`
5. Nettoie automatiquement les processus

### Option 2: Orchestrateur Intégré (Quand le backend fonctionne)

```bash
# Test complet avec backend réel (nécessite résolution des dépendances)
python scripts/run_webapp_integration.py --visible --frontend

# Test backend seulement
python scripts/run_webapp_integration.py --backend

# Test rapide avec sous-ensemble
python scripts/run_webapp_integration.py --quick --visible
```

### Option 3: Tests Playwright Directs

```bash
# Tests spécifiques avec environnement activé
powershell -File scripts/env/activate_project_env.ps1 -CommandToRun "python -m pytest tests/functional/test_webapp_homepage.py -v --headed"
```

## 🎭 Interface Démontrée

L'interface React comprend 6 onglets principaux :

1. **🔍 Analyseur** - Analyse d'arguments textuels
2. **⚠️ Sophismes** - Détection de fallacies logiques  
3. **🔄 Reconstructeur** - Reconstruction d'arguments incomplets
4. **📊 Graphe Logique** - Visualisation de structures logiques
5. **✅ Validation** - Validation formelle d'arguments
6. **🏗️ Framework** - Construction de frameworks argumentatifs

## 📸 Captures d'Écran Générées

Les démos génèrent automatiquement :
- `logs/demo_interface.png` - Page d'accueil complète
- `logs/demo_homepage.png` - État initial de l'interface
- `logs/demo_analyzer.png` - Onglet analyseur
- `logs/demo_fallacies.png` - Détecteur de sophismes
- `logs/demo_interaction.png` - Tests d'interaction utilisateur

## 🔧 Configuration

### Ports Utilisés
- **Backend**: 5003 (principal), avec failover sur 5004-5006
- **Frontend**: 3000 (React dev server)

### Variables d'Environnement
```bash
BROWSER=none                    # Empêche ouverture automatique navigateur
GENERATE_SOURCEMAP=false       # Optimise build React
HEADLESS=false                  # Mode visible pour démos
```

## 🛠️ Architecture Technique

### Backend Mock (Pour Démos)
Le fichier `backend_mock_demo.py` fournit un serveur Flask minimaliste avec :
- Endpoints API compatibles (`/api/health`, `/api/analyze`, etc.)
- Réponses mockées réalistes
- CORS activé pour développement
- Logging détaillé

### Frontend React
Interface moderne avec :
- Composants modulaires par fonctionnalité
- Gestion d'état avec hooks React
- Communication API via Axios
- Design responsive et accessible

### Tests Playwright
Suite complète incluant :
- Tests de navigation et chargement
- Validation des composants UI
- Tests d'interaction utilisateur
- Capture automatique d'artifacts (screenshots, traces)

## 🐛 Résolution de Problèmes

### Problème: Backend ne démarre pas
**Cause**: Conflit de dépendances (semantic-kernel vs pydantic)
**Solution**: Utiliser le backend mock avec `python backend_mock_demo.py`

### Problème: Tests Playwright échouent
**Cause**: Environnement Python non configuré
**Solution**: 
```bash
pip install psutil playwright pytest-playwright aiohttp pyyaml
python -m playwright install
```

### Problème: Frontend ne se charge pas
**Cause**: Dépendances npm manquantes
**Solution**:
```bash
cd services/web_api/interface-web-argumentative
npm install
```

## 📊 Résultats de la Démonstration

✅ **Backend Mock**: Opérationnel sur port 5003
✅ **Frontend React**: Démarrage réussi sur port 3000  
✅ **Interface Utilisateur**: Chargement et affichage corrects
✅ **Navigation**: Tests d'onglets fonctionnels
✅ **Captures d'Écran**: Génération automatique réussie
⚠️ **Interaction API**: Limitée par le mock (comportement attendu)

## 🔮 Prochaines Étapes

1. **Résoudre les dépendances du backend réel** pour utilisation complète
2. **Étendre les tests Playwright** avec scénarios utilisateur complexes  
3. **Intégrer l'orchestrateur** dans la CI/CD
4. **Optimiser les performances** frontend/backend

## 📝 Notes Importantes

- Les démos utilisent un backend mock pour éviter les problèmes de dépendances
- L'interface montre "API: Déconnectée" avec le mock (comportement normal)
- Les captures d'écran sont automatiquement générées dans `logs/`
- L'orchestrateur unifie la gestion des processus backend/frontend/tests

---

**Date**: 08/06/2025
**Version**: 1.0.0
**Auteur**: Projet Intelligence Symbolique EPITA