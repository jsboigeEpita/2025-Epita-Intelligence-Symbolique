# 🔧 Guide de Dépannage - Interface Web d'Analyse Argumentative

## 📋 Table des matières

1. [Problèmes de démarrage de l'API](#problèmes-de-démarrage-de-lapi)
2. [Erreurs de connexion](#erreurs-de-connexion)
3. [Problèmes CORS](#problèmes-cors)
4. [Erreurs de dépendances](#erreurs-de-dépendances)
5. [Problèmes React](#problèmes-react)
6. [Erreurs d'analyse](#erreurs-danalyse)
7. [Problèmes de performance](#problèmes-de-performance)
8. [Outils de diagnostic](#outils-de-diagnostic)

## Problèmes de démarrage de l'API

### ❌ Erreur : "ModuleNotFoundError: No module named 'flask'"

**Cause :** Dépendances Python non installées

**Solutions :**
```bash
# Solution 1 : Installation simple
pip install -r requirements.txt

# Solution 2 : Mise à jour de pip
python -m pip install --upgrade pip
pip install -r requirements.txt

# Solution 3 : Environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### ❌ Erreur : "Address already in use" ou "Port 5000 is already in use"

**Cause :** Le port 5000 est déjà utilisé

**Solutions :**
```bash
# Solution 1 : Utiliser un autre port
python start_api.py --port 8080

# Solution 2 : Trouver et arrêter le processus
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:5000 | xargs kill -9

# Solution 3 : Redémarrer le système (dernière option)
```

### ❌ Erreur : "ImportError: cannot import name 'UrlConstraints' from 'pydantic'"

**Cause :** Version incompatible de Pydantic

**Solutions :**
```bash
# Solution 1 : Installer la version compatible
pip install pydantic==1.10.12

# Solution 2 : Forcer la réinstallation
pip uninstall pydantic
pip install pydantic==1.10.12

# Solution 3 : Vérifier les conflits
pip check
```

### ❌ Erreur : "Permission denied" lors du démarrage

**Cause :** Permissions insuffisantes

**Solutions :**
```bash
# Windows : Exécuter en tant qu'administrateur
# Ou utiliser un port > 1024
python start_api.py --port 8080

# Linux/Mac : Utiliser sudo (non recommandé) ou port > 1024
python start_api.py --port 8080
```

## Erreurs de connexion

### ❌ Erreur : "Connection refused" ou "Network Error"

**Diagnostic :**
```bash
# Vérifier que l'API est démarrée
curl http://localhost:5000/api/health

# Vérifier les processus en cours
# Windows
netstat -an | findstr :5000

# Linux/Mac
netstat -an | grep :5000
```

**Solutions :**
1. **Redémarrer l'API**
   ```bash
   # Arrêter l'API (Ctrl+C)
   # Puis redémarrer
   python start_api.py
   ```

2. **Vérifier l'URL**
   ```javascript
   // Utiliser localhost, pas 127.0.0.1
   const API_URL = 'http://localhost:5000';
   ```

3. **Vérifier le firewall**
   ```bash
   # Windows : Autoriser Python dans le firewall
   # Linux : Vérifier iptables
   sudo iptables -L
   ```

### ❌ Erreur : "Timeout" ou requêtes très lentes

**Diagnostic :**
```bash
# Tester la latence
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:5000/api/health

# Contenu de curl-format.txt :
#     time_namelookup:  %{time_namelookup}\n
#        time_connect:  %{time_connect}\n
#     time_appconnect:  %{time_appconnect}\n
#    time_pretransfer:  %{time_pretransfer}\n
#       time_redirect:  %{time_redirect}\n
#  time_starttransfer:  %{time_starttransfer}\n
#                     ----------\n
#          time_total:  %{time_total}\n
```

**Solutions :**
1. **Redémarrer l'API en mode debug**
   ```bash
   python start_api.py --debug
   ```

2. **Vérifier les logs**
   ```bash
   # Logs détaillés
   python start_api.py --debug 2>&1 | tee api.log
   ```

3. **Optimiser les imports**
   ```python
   # Dans app.py, commenter temporairement les imports lourds
   # try:
   #     from argumentation_analysis...
   # except ImportError:
   #     pass
   ```

## Problèmes CORS

### ❌ Erreur : "Access to fetch at '...' from origin '...' has been blocked by CORS policy"

**Diagnostic :**
```javascript
// Dans la console du navigateur
fetch('http://localhost:5000/api/health')
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('CORS Error:', error));
```

**Solutions :**

1. **Vérifier la configuration CORS dans l'API**
   ```python
   # Dans services/web_api/app.py
   from flask_cors import CORS
   
   app = Flask(__name__)
   CORS(app, origins=["http://localhost:3000", "http://localhost:3001"])
   ```

2. **Redémarrer l'API après modification**
   ```bash
   # Arrêter l'API (Ctrl+C)
   python start_api.py
   ```

3. **Utiliser un proxy en développement (React)**
   ```json
   // Dans package.json
   {
     "name": "mon-app",
     "version": "0.1.0",
     "proxy": "http://localhost:5000",
     // ...
   }
   ```

4. **Configuration avancée CORS**
   ```python
   # Pour plus de flexibilité
   CORS(app, 
        origins=["http://localhost:3000"],
        methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"])
   ```

### ❌ Erreur : "Preflight request doesn't pass access control check"

**Solution :**
```python
# Ajouter le support des requêtes OPTIONS
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response
```

## Erreurs de dépendances

### ❌ Erreur : "No module named 'argumentation_analysis'"

**Cause :** Le module principal n'est pas dans le PYTHONPATH

**Solutions :**
```bash
# Solution 1 : Ajouter au PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/2025-Epita-Intelligence-Symbolique"

# Solution 2 : Installation en mode développement
cd /path/to/2025-Epita-Intelligence-Symbolique
pip install -e .

# Solution 3 : Vérifier le chemin dans le code
# Le code dans app.py devrait déjà gérer cela
```

### ❌ Erreur : "ImportError: cannot import name 'ComplexFallacyAnalyzer'"

**Cause :** Modules d'analyse non disponibles (mode dégradé)

**Solutions :**
1. **Mode normal** - L'API fonctionne en mode dégradé
2. **Vérifier les logs** pour voir quels modules sont disponibles
3. **Installer les dépendances manquantes** si nécessaire

### ❌ Erreur : Conflits de versions

**Diagnostic :**
```bash
# Vérifier les conflits
pip check

# Lister les versions installées
pip list

# Vérifier une dépendance spécifique
pip show flask
```

**Solutions :**
```bash
# Créer un environnement propre
python -m venv fresh_env
source fresh_env/bin/activate  # Linux/Mac
# ou
fresh_env\Scripts\activate     # Windows

pip install -r requirements.txt
```

## Problèmes React

### ❌ Erreur : "npm start" ne fonctionne pas

**Solutions :**
```bash
# Nettoyer le cache npm
npm cache clean --force

# Supprimer node_modules et réinstaller
rm -rf node_modules package-lock.json
npm install

# Vérifier la version de Node.js
node --version  # Doit être >= 16
```

### ❌ Erreur : "Module not found: Can't resolve './services/api'"

**Solution :**
```bash
# Vérifier que le fichier existe
ls src/services/api.js

# Créer le fichier s'il n'existe pas
mkdir -p src/services
# Puis copier le contenu depuis DEMARRAGE_RAPIDE.md
```

### ❌ Erreur : "Unexpected token" dans le code React

**Solutions :**
1. **Vérifier la syntaxe JSX**
2. **Vérifier les imports/exports**
3. **Redémarrer le serveur de développement**

## Erreurs d'analyse

### ❌ Erreur : "Données invalides" (400)

**Diagnostic :**
```javascript
// Vérifier le format de la requête
const testData = {
  text: "Mon argument",
  options: {
    detect_fallacies: true,
    analyze_structure: true,
    evaluate_coherence: true
  }
};

console.log('Données envoyées:', JSON.stringify(testData, null, 2));
```

**Solutions :**
1. **Vérifier que le texte n'est pas vide**
2. **Vérifier le format JSON**
3. **Vérifier les types de données**

### ❌ Erreur : "Erreur interne du serveur" (500)

**Diagnostic :**
```bash
# Vérifier les logs de l'API
python start_api.py --debug

# Tester avec un texte simple
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Test simple"}'
```

**Solutions :**
1. **Redémarrer l'API**
2. **Vérifier les logs pour l'erreur exacte**
3. **Tester avec des données minimales**

## Problèmes de performance

### ❌ L'API est très lente

**Diagnostic :**
```bash
# Mesurer le temps de réponse
time curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Test"}'
```

**Solutions :**
1. **Réduire la taille du texte analysé**
2. **Désactiver certaines options d'analyse**
   ```javascript
   const options = {
     detect_fallacies: true,
     analyze_structure: false,  // Désactiver temporairement
     evaluate_coherence: false
   };
   ```
3. **Redémarrer l'API**

### ❌ Interface React lente

**Solutions :**
1. **Optimiser les re-rendus**
   ```jsx
   // Utiliser useCallback et useMemo
   const handleAnalyze = useCallback(async () => {
     // ...
   }, [text]);
   ```

2. **Ajouter un debounce**
   ```javascript
   import { debounce } from 'lodash';
   
   const debouncedAnalyze = debounce(analyzeText, 500);
   ```

## Outils de diagnostic

### 🔍 Script de diagnostic automatique

Créez `diagnostic.py` dans `services/web_api/` :

```python
#!/usr/bin/env python3
import requests
import sys
import json
from pathlib import Path

def check_api_health():
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=5)
        if response.status_code == 200:
            print("✅ API Health Check: OK")
            return True
        else:
            print(f"❌ API Health Check: Status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ API Health Check: Connection refused")
        return False
    except requests.exceptions.Timeout:
        print("❌ API Health Check: Timeout")
        return False

def test_analyze_endpoint():
    try:
        data = {
            "text": "Test argument",
            "options": {"detect_fallacies": True}
        }
        response = requests.post(
            'http://localhost:5000/api/analyze',
            json=data,
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            print("✅ Analyze Endpoint: OK")
            print(f"   Processing time: {result.get('processing_time', 'N/A')}s")
            return True
        else:
            print(f"❌ Analyze Endpoint: Status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Analyze Endpoint: {str(e)}")
        return False

def check_dependencies():
    required = ['flask', 'flask_cors', 'pydantic']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"✅ {package}: Installed")
        except ImportError:
            print(f"❌ {package}: Missing")
            missing.append(package)
    
    return len(missing) == 0

def main():
    print("🔍 Diagnostic de l'API d'Analyse Argumentative")
    print("=" * 50)
    
    # Vérifier les dépendances
    print("\n📦 Vérification des dépendances:")
    deps_ok = check_dependencies()
    
    # Vérifier l'API
    print("\n🌐 Vérification de l'API:")
    health_ok = check_api_health()
    
    if health_ok:
        analyze_ok = test_analyze_endpoint()
    else:
        analyze_ok = False
    
    # Résumé
    print("\n📊 Résumé:")
    print(f"   Dépendances: {'✅' if deps_ok else '❌'}")
    print(f"   API Health: {'✅' if health_ok else '❌'}")
    print(f"   Endpoint Analyze: {'✅' if analyze_ok else '❌'}")
    
    if all([deps_ok, health_ok, analyze_ok]):
        print("\n🎉 Tout fonctionne correctement!")
        return 0
    else:
        print("\n⚠️  Des problèmes ont été détectés. Consultez le guide de troubleshooting.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### 🔍 Utilisation du diagnostic

```bash
# Lancer le diagnostic
cd services/web_api
python diagnostic.py

# Diagnostic avec logs détaillés
python diagnostic.py 2>&1 | tee diagnostic.log
```

### 🔍 Tests manuels rapides

```bash
# Test 1 : API Health
curl http://localhost:5000/api/health

# Test 2 : Analyse simple
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Test"}'

# Test 3 : Validation
curl -X POST http://localhost:5000/api/validate \
  -H "Content-Type: application/json" \
  -d '{"premises": ["A"], "conclusion": "B"}'

# Test 4 : Endpoints
curl http://localhost:5000/api/endpoints
```

## 📞 Support et aide

### Avant de demander de l'aide

1. ✅ Exécutez le script de diagnostic
2. ✅ Vérifiez les logs de l'API
3. ✅ Testez avec des données simples
4. ✅ Redémarrez l'API et React

### Informations à fournir

Quand vous demandez de l'aide, incluez :

1. **Version de Python** : `python --version`
2. **Version de Node.js** : `node --version`
3. **Système d'exploitation**
4. **Message d'erreur exact**
5. **Logs de l'API** (mode debug)
6. **Résultat du diagnostic**

### Logs utiles

```bash
# Logs API avec timestamp
python start_api.py --debug 2>&1 | while IFS= read -r line; do echo "$(date '+%Y-%m-%d %H:%M:%S') $line"; done

# Logs React
npm start 2>&1 | tee react.log

# Logs réseau (navigateur)
# F12 > Network > Préserver les logs
```

---

**💡 Conseil :** La plupart des problèmes se résolvent en redémarrant l'API et en vérifiant les URLs utilisées.

*Ce guide est maintenu par l'équipe du projet. N'hésitez pas à contribuer avec vos propres solutions !*