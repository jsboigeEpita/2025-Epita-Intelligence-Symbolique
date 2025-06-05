# 🔧 Guide de Dépannage - Interface Web d'Analyse Argumentative

**Note Importante :** Ce guide de dépannage est un complément aux documentations principales du projet. Pour une compréhension approfondie de l'architecture, des composants et des procédures de développement, veuillez consulter :
*   Le portail des guides : [`docs/guides/README.md`](../../../../guides/README.md:1)
*   La documentation d'architecture globale : [`docs/architecture/architecture_globale.md`](../../../../architecture/architecture_globale.md:1)
*   La documentation des composants : [`docs/composants/`](../../../../composants/)

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

Avant de diagnostiquer les problèmes de démarrage, assurez-vous d'avoir suivi les étapes d'installation et de configuration décrites dans le [`Guide du Développeur`](../../../../guides/guide_developpeur.md:1) et le guide d'[`Intégration de l'API Web`](../../../../guides/integration_api_web.md:1).

### ❌ Erreur : "ModuleNotFoundError: No module named 'flask'"

**Cause :** Dépendances Python non installées

**Solutions :**
```bash
# Solution 1 : Installation simple
pip install -r requirements.txt

# Solution 2 : Mise à jour de pip
python -m pip install --upgrade pip
pip install -r requirements.txt

# Solution 3 : Environnement virtuel (recommandé)
# Assurez-vous que votre environnement est activé (voir activate_project_env.ps1)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### ❌ Erreur : "Address already in use" ou "Port 5000 is already in use"

**Cause :** Le port 5000 (ou le port configuré) est déjà utilisé par un autre processus.

**Solutions :**
```bash
# Solution 1 : Utiliser un autre port
# (Vérifiez le nom et l'emplacement du script de démarrage, ex: start_api.py ou dans services/web_api/)
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

**Cause :** Version incompatible de Pydantic. Le projet utilise une version spécifique.

**Solutions :**
```bash
# Solution 1 : Installer la version compatible (vérifiez requirements.txt pour la version exacte)
pip install pydantic==1.10.12 # Exemple de version, adaptez si besoin

# Solution 2 : Forcer la réinstallation
pip uninstall pydantic
pip install pydantic==1.10.12 # Exemple de version

# Solution 3 : Vérifier les conflits
pip check
```

### ❌ Erreur : "Permission denied" lors du démarrage

**Cause :** Permissions insuffisantes pour utiliser le port spécifié (souvent les ports < 1024).

**Solutions :**
```bash
# Windows : Exécuter en tant qu'administrateur
# Ou utiliser un port > 1024 (recommandé)
python start_api.py --port 8080

# Linux/Mac : Utiliser sudo (non recommandé pour le développement) ou un port > 1024 (recommandé)
python start_api.py --port 8080
```

## Erreurs de connexion

Ces erreurs surviennent lorsque l'interface utilisateur (ex: React) ne parvient pas à communiquer avec l'API backend. Consultez également le [`Guide du Développeur`](../../../../guides/guide_developpeur.md:1) et la documentation sur l'[`Intégration de l'API Web`](../../../../guides/integration_api_web.md:1).

### ❌ Erreur : "Connection refused" ou "Network Error"

**Diagnostic :**
```bash
# Vérifier que l'API est démarrée et écoute sur le bon port
curl http://localhost:5000/api/health 
# (Adaptez le port si vous en utilisez un autre)

# Vérifier les processus en cours
# Windows
netstat -an | findstr :5000

# Linux/Mac
netstat -an | grep :5000
```

**Solutions :**
1. **Redémarrer l'API**
   ```bash
   # Arrêter l'API (Ctrl+C dans le terminal où elle s'exécute)
   # Puis redémarrer (vérifiez le nom et l'emplacement du script)
   python start_api.py
   ```

2. **Vérifier l'URL de l'API dans la configuration de l'interface utilisateur**
   ```javascript
   // Exemple : s'assurer que l'URL et le port correspondent à ceux de l'API
   const API_URL = 'http://localhost:5000'; // ou le port que vous utilisez
   ```
   Consultez la documentation de l'[`API Web`](../../../../composants/api_web.md:1) pour les détails des endpoints.

3. **Vérifier le firewall**
   Assurez-vous que votre pare-feu autorise les connexions sur le port utilisé par l'API.
   ```bash
   # Windows : Autoriser Python (ou le script de l'API) dans le firewall
   # Linux : Vérifier iptables ou ufw
   sudo iptables -L
   sudo ufw status
   ```
4. **Problèmes de communication inter-agents ?**
   Si l'erreur semble plus complexe et pourrait impliquer la communication entre agents (si l'API agit comme un agent ou interagit avec d'autres), consultez la section sur le [`MessageMiddleware` dans la documentation d'architecture](../../../../architecture/communication_agents.md:10).

### ❌ Erreur : "Timeout" ou requêtes très lentes

**Diagnostic :**
```bash
# Tester la latence vers un endpoint simple
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:5000/api/health

# Contenu de curl-format.txt (à créer dans le répertoire courant):
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
1. **Redémarrer l'API en mode debug pour plus de logs**
   ```bash
   python start_api.py --debug
   ```

2. **Vérifier les logs de l'API**
   Recherchez des erreurs ou des opérations longues.
   ```bash
   # Logs détaillés redirigés vers un fichier
   python start_api.py --debug 2>&1 | tee api.log
   ```

3. **Optimiser les imports dans le code de l'API**
   Des imports lourds au démarrage peuvent ralentir l'initialisation.
   ```python
   # Dans le fichier principal de l'API (ex: services/web_api/app.py)
   # Envisagez de différer les imports lourds si possible
   # try:
   #     from argumentation_analysis... # Module potentiellement lourd
   # except ImportError:
   #     pass # Gérer l'absence du module
   ```

## Problèmes CORS

Les problèmes CORS (Cross-Origin Resource Sharing) sont fréquents en développement web lorsque l'interface utilisateur et l'API sont sur des "origines" différentes (ports ou domaines).
Voir aussi le guide d'[`Intégration de l'API Web`](../../../../guides/integration_api_web.md:1) pour la configuration CORS.

### ❌ Erreur : "Access to fetch at '...' from origin '...' has been blocked by CORS policy"

**Diagnostic :**
```javascript
// Dans la console du navigateur (F12) de votre application React
fetch('http://localhost:5000/api/health') // Adaptez l'URL et le port
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('CORS Error:', error));
```

**Solutions :**

1. **Vérifier la configuration CORS dans l'API (Flask)**
   Assurez-vous que l'origine de votre application React (ex: `http://localhost:3000`) est autorisée.
   ```python
   # Dans le fichier principal de l'API (ex: services/web_api/app.py)
   from flask_cors import CORS
   
   app = Flask(__name__)
   # Exemple : autoriser les requêtes depuis localhost:3000 (React dev server)
   CORS(app, origins=["http://localhost:3000", "http://localhost:3001"]) 
   ```

2. **Redémarrer l'API après modification de la configuration CORS**
   ```bash
   # Arrêter l'API (Ctrl+C)
   python start_api.py
   ```

3. **Utiliser un proxy en développement (React)**
   C'est une solution courante pour éviter les problèmes CORS pendant le développement.
   ```json
   // Dans le fichier package.json de votre application React
   {
     "name": "mon-app-react",
     "version": "0.1.0",
     "proxy": "http://localhost:5000", // URL de votre API Flask
     // ... autres configurations
   }
   ```
   Après avoir ajouté cela, redémarrez votre serveur de développement React (`npm start`).

4. **Configuration CORS avancée (si nécessaire)**
   Pour plus de contrôle sur les méthodes, les en-têtes, etc.
   ```python
   # Exemple de configuration plus détaillée
   CORS(app, 
        origins=["http://localhost:3000", "http://votre-domaine-deploiement.com"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        supports_credentials=True)
   ```

### ❌ Erreur : "Preflight request doesn't pass access control check"

Cela se produit souvent avec des requêtes "non simples" (ex: POST avec `Content-Type: application/json`, ou utilisant des en-têtes personnalisés). Le navigateur envoie une requête `OPTIONS` (preflight) pour vérifier les permissions CORS.

**Solution :**
Assurez-vous que votre serveur API gère correctement les requêtes `OPTIONS` et renvoie les en-têtes CORS appropriés. `Flask-CORS` gère cela automatiquement si bien configuré. Si vous n'utilisez pas `Flask-CORS` ou avez une configuration manuelle :
```python
# Exemple de gestion manuelle (Flask-CORS est préférable)
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        # Adaptez ces en-têtes à votre configuration CORS
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000") 
        response.headers.add('Access-Control-Allow-Headers', "Content-Type,Authorization")
        response.headers.add('Access-Control-Allow-Methods', "GET,POST,PUT,DELETE,OPTIONS")
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
```

## Erreurs de dépendances

Consultez le [`Guide du Développeur`](../../../../guides/guide_developpeur.md:1) et la documentation sur la [`Structure du Projet`](../../../../composants/structure_projet.md:1) pour comprendre comment les modules sont organisés.

### ❌ Erreur : "No module named 'argumentation_analysis'"

**Cause :** Le module principal du projet (`argumentation_analysis`) n'est pas dans le `PYTHONPATH`, ou le projet n'a pas été installé correctement en mode éditable.

**Solutions :**
```bash
# Solution 1 : Ajouter manuellement au PYTHONPATH (adaptez le chemin)
# Pour Linux/Mac (temporaire, pour la session actuelle du terminal)
export PYTHONPATH="${PYTHONPATH}:/chemin/vers/votre/projet/2025-Epita-Intelligence-Symbolique"
# Pour Windows (cmd, temporaire)
set PYTHONPATH=%PYTHONPATH%;C:\chemin\vers\votre\projet\2025-Epita-Intelligence-Symbolique
# Pour Windows (PowerShell, temporaire)
$env:PYTHONPATH = "$env:PYTHONPATH;C:\chemin\vers\votre\projet\2025-Epita-Intelligence-Symbolique"
# Pour une solution permanente, configurez les variables d'environnement de votre OS
# ou utilisez la solution 2.

# Solution 2 : Installation en mode développement (recommandé)
# Naviguez à la racine de votre projet 2025-Epita-Intelligence-Symbolique
cd /chemin/vers/votre/projet/2025-Epita-Intelligence-Symbolique
pip install -e . 
# Cela crée un lien symbolique vers votre code dans les packages Python.

# Solution 3 : Vérifier la structure du projet et les imports
# Le code dans l'API (ex: services/web_api/app.py) devrait pouvoir importer
# from argumentation_analysis.some_module import ...
# si la solution 1 ou 2 est correctement appliquée.
```

### ❌ Erreur : "ImportError: cannot import name 'ComplexFallacyAnalyzer'" (ou autre module d'analyse)

**Cause :** Certains modules d'analyse avancée pourraient ne pas être disponibles si des dépendances optionnelles sont manquantes ou si le système est configuré pour un mode dégradé.

**Solutions :**
1. **Fonctionnement normal en mode dégradé :** L'API est conçue pour fonctionner même si certains analyseurs avancés ne sont pas chargés, offrant alors des fonctionnalités de base.
2. **Vérifier les logs de l'API au démarrage :** L'API indique généralement quels modules sont chargés ou non.
   ```bash
   python start_api.py --debug
   ```
3. **Installer les dépendances manquantes :** Si des dépendances spécifiques sont nécessaires pour ces modules (ex: bibliothèques C++, modèles de ML lourds), assurez-vous qu'elles sont installées conformément au [`Guide du Développeur`](../../../../guides/guide_developpeur.md:1).
4. **Consulter la documentation des composants** comme [`Agents Spécialistes`](../../../../composants/agents_specialistes.md:1) ou [`Moteur de Raisonnement`](../../../../composants/reasoning_engine.md:1) pour comprendre les capacités attendues.

### ❌ Erreur : Conflits de versions de dépendances

**Diagnostic :**
```bash
# Vérifier les conflits de dépendances installées
pip check

# Lister toutes les versions des packages installés
pip list

# Vérifier la version d'une dépendance spécifique
pip show flask
```

**Solutions :**
```bash
# Solution la plus robuste : Créer un environnement virtuel propre
python -m venv fresh_env_name 
source fresh_env_name/bin/activate  # Linux/Mac
# ou
fresh_env_name\Scripts\activate     # Windows

# Réinstaller les dépendances à partir du fichier requirements.txt
pip install -r requirements.txt
# Si vous avez un fichier requirements-dev.txt pour les dépendances de développement :
# pip install -r requirements-dev.txt
```

## Problèmes React

### ❌ Erreur : "npm start" ne fonctionne pas ou l'application ne se lance pas

**Solutions :**
```bash
# Naviguez vers le répertoire de votre application React (ex: frontend/)

# Nettoyer le cache npm (peut résoudre des problèmes étranges)
npm cache clean --force

# Supprimer node_modules et le fichier package-lock.json, puis réinstaller
rm -rf node_modules package-lock.json # ou del /s /q node_modules package-lock.json sur Windows
npm install

# Vérifier la version de Node.js (doit être compatible avec le projet, ex: >= 16)
node --version
# Si nécessaire, mettez à jour Node.js ou utilisez un gestionnaire de versions comme nvm.

# Essayer de lancer à nouveau
npm start
```

### ❌ Erreur : "Module not found: Can't resolve './services/api'" (ou autre chemin de module)

**Cause :** Le chemin d'importation dans votre code React est incorrect ou le fichier/module n'existe pas à l'emplacement attendu.

**Solution :**
```bash
# Exemple : si l'erreur concerne './services/api' dans un composant React
# Vérifiez que le fichier src/services/api.js (ou .ts) existe.
# Sur Linux/Mac:
ls src/services/api.js 
# Sur Windows:
dir src\services\api.js

# Si le fichier n'existe pas, vous devrez peut-être le créer ou corriger le chemin d'import.
# Par exemple, si vous suivez le DEMARRAGE_RAPIDE.md, assurez-vous d'avoir créé ce fichier.
mkdir -p src/services # ou mkdir src\services sur Windows
# Puis copiez/collez le contenu nécessaire dans src/services/api.js
```
Vérifiez attentivement les chemins relatifs et absolus dans vos instructions `import`.

### ❌ Erreur : "Unexpected token" ou autre erreur de syntaxe dans le code React/JSX

**Solutions :**
1. **Vérifier la syntaxe JSX :** Assurez-vous que tous les tags sont correctement fermés, que les attributs sont valides, etc.
2. **Vérifier les imports/exports :** Des erreurs dans les déclarations `import` ou `export` peuvent causer des problèmes.
3. **Redémarrer le serveur de développement React :** Parfois, le serveur de développement peut avoir besoin d'être redémarré après des modifications importantes. Arrêtez-le (Ctrl+C) et relancez `npm start`.
4. **Utiliser un linter/formateur de code** (comme ESLint, Prettier) pour identifier les erreurs de syntaxe.

## Erreurs d'analyse

Ces erreurs proviennent de l'API lorsqu'elle traite une requête d'analyse. Consultez la documentation de l'[`API Web`](../../../../composants/api_web.md:1) pour les formats de requête et de réponse attendus.

### ❌ Erreur : "Données invalides" (souvent une réponse HTTP 400 Bad Request)

**Diagnostic :**
```javascript
// Dans votre code React, avant d'envoyer la requête, logguez les données :
const requestData = {
  text: "Mon argument à analyser.",
  options: { // Assurez-vous que les options sont correctes
    detect_fallacies: true,
    analyze_structure: true,
    evaluate_coherence: true
    // ... autres options selon la doc de l'API
  }
};

console.log('Données envoyées à /api/analyze:', JSON.stringify(requestData, null, 2));

// Envoyez ensuite requestData à l'API.
```

**Solutions :**
1. **Vérifier que le champ `text` n'est pas vide ou manquant.**
2. **Vérifier que le corps de la requête est un JSON valide.**
3. **Vérifier que les champs et les types de données correspondent à ce qui est attendu par l'API** (voir la documentation de l'[`API Web`](../../../../composants/api_web.md:1)).
4. **Vérifier les `options` d'analyse :** Assurez-vous que les options envoyées sont valides et correctement formatées.

### ❌ Erreur : "Erreur interne du serveur" (souvent une réponse HTTP 500 Internal Server Error)

**Diagnostic :**
```bash
# La première chose à faire est de vérifier les logs de l'API en mode debug
python start_api.py --debug
# Recherchez la trace de l'erreur (stack trace) Python.

# Tester l'endpoint /api/analyze avec une requête simple en utilisant curl
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Ceci est un test simple."}'
```

**Solutions :**
1. **Redémarrer l'API.**
2. **Examiner attentivement les logs de l'API** pour identifier l'erreur Python exacte qui s'est produite côté serveur.
3. **Tester avec des données minimales :** Simplifiez au maximum le texte et les options envoyés pour voir si le problème persiste. Cela peut aider à isoler la cause.
4. **Vérifier les dépendances et la configuration des modules d'analyse** (voir section "Erreurs de dépendances").

## Problèmes de performance

### ❌ L'API est très lente à répondre aux requêtes d'analyse

**Diagnostic :**
```bash
# Mesurer le temps de réponse pour une requête d'analyse
# Sur Linux/Mac:
time curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Un texte d_exemple pour tester la performance."}'
# Sur Windows (PowerShell):
Measure-Command { Invoke-RestMethod -Uri http://localhost:5000/api/analyze -Method Post -ContentType "application/json" -Body '{"text": "Un texte d_exemple pour tester la performance."}' }
```

**Solutions :**
1. **Réduire la taille du texte analysé :** Des textes très longs peuvent prendre plus de temps.
2. **Désactiver certaines options d'analyse coûteuses :** Certaines analyses (ex: évaluation de cohérence profonde, détection de tous les types de sophismes) peuvent être plus gourmandes.
   ```javascript
   // Exemple dans le code React, en désactivant des options
   const analysisOptions = {
     detect_fallacies: true,
     analyze_structure: false,  // Désactiver temporairement pour tester
     evaluate_coherence: false  // Désactiver temporairement pour tester
   };
   ```
3. **Redémarrer l'API :** Parfois, cela peut aider si des ressources sont bloquées.
4. **Vérifier les logs de l'API en mode debug** pour voir si une étape spécifique de l'analyse prend beaucoup de temps.
5. **Consulter la documentation des composants** (ex: [`Moteur de Raisonnement`](../../../../composants/reasoning_engine.md:1)) pour comprendre les implications de performance de certaines fonctionnalités.

### ❌ Interface React lente ou peu réactive

**Solutions :**
1. **Optimiser les re-rendus des composants React :**
   Utilisez `React.memo` pour les composants fonctionnels, `shouldComponentUpdate` pour les composants de classe, et les hooks `useCallback` et `useMemo` pour mémoriser les fonctions et les valeurs.
   ```jsx
   // Exemple avec useCallback
   const handleAnalyze = useCallback(async () => {
     // Logique d'appel à l'API
   }, [textToAnalyze, analysisOptions]); // Dépendances correctes
   ```

2. **Utiliser le "debouncing" ou "throttling" pour les événements fréquents :**
   Si l'analyse est déclenchée par la saisie de l'utilisateur (ex: `onChange` sur un `textarea`), utilisez `debounce` pour ne pas appeler l'API à chaque frappe.
   ```javascript
   import { debounce } from 'lodash'; // ou une implémentation maison
   
   // Exécute analyzeTextFunction au plus une fois toutes les 500ms
   const debouncedAnalyze = debounce(analyzeTextFunction, 500); 
   
   // Appeler debouncedAnalyze dans le gestionnaire d'événements
   ```
3. **Virtualisation de listes :** Si vous affichez de longues listes de résultats, utilisez des bibliothèques comme `react-window` ou `react-virtualized`.
4. **Profiler l'application React :** Utilisez les outils de développement React (onglet "Profiler") pour identifier les goulots d'étranglement.

## Outils de diagnostic

Avant d'utiliser les outils de diagnostic spécifiques, assurez-vous que votre environnement de projet est correctement configuré et activé. Exécutez le script [`activate_project_env.ps1`](../../../../../activate_project_env.ps1) (ou son équivalent pour votre OS) pour initialiser ou vérifier votre environnement Conda/Python, les dépendances, et d'autres configurations cruciales, comme décrit dans le [`Guide du Développeur`](../../../../guides/guide_developpeur.md:1).

### 🔍 Script de diagnostic automatique de l'API

Un script de diagnostic `diagnostic.py` peut être créé dans le répertoire `services/web_api/` (ou un autre emplacement pertinent pour les scripts de test de l'API) pour vérifier rapidement l'état de l'API et ses dépendances de base.

```python
#!/usr/bin/env python3
# Chemin suggéré : services/web_api/diagnostic.py
import requests
import sys
import json
# import importlib # Pour vérifier les modules

API_BASE_URL = "http://localhost:5000/api" # Adaptez si votre port est différent

def check_api_health():
    print(f"Checking API health at {API_BASE_URL}/health...")
    try:
        response = requests.get(f'{API_BASE_URL}/health', timeout=5)
        if response.status_code == 200:
            print("✅ API Health Check: OK")
            return True
        else:
            print(f"❌ API Health Check: Status {response.status_code}, Response: {response.text[:100]}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ API Health Check: Connection refused. L'API est-elle démarrée sur {API_BASE_URL}?")
        return False
    except requests.exceptions.Timeout:
        print("❌ API Health Check: Timeout")
        return False

def test_analyze_endpoint():
    print(f"Testing analyze endpoint at {API_BASE_URL}/analyze...")
    try:
        data = {
            "text": "Ceci est un argument de test.",
            "options": {"detect_fallacies": True, "analyze_structure": False}
        }
        response = requests.post(
            f'{API_BASE_URL}/analyze',
            json=data,
            timeout=15 # Augmenté pour les analyses potentiellement plus longues
        )
        if response.status_code == 200:
            result = response.json()
            print("✅ Analyze Endpoint: OK")
            print(f"   Processing time: {result.get('processing_time', 'N/A')}s")
            # print(f"   Result keys: {list(result.keys())}") # Pour voir ce que l'API retourne
            return True
        else:
            print(f"❌ Analyze Endpoint: Status {response.status_code}")
            print(f"   Response: {response.text[:200]}") # Afficher une partie de la réponse d'erreur
            return False
    except requests.exceptions.Timeout:
        print(f"❌ Analyze Endpoint: Timeout. L'analyse prend trop de temps ou l'API est bloquée.")
        return False
    except Exception as e:
        print(f"❌ Analyze Endpoint: Erreur inattendue - {str(e)}")
        return False

def check_python_dependencies():
    # Cette fonction est simplifiée. Pour une vérification robuste,
    # il est préférable de s'appuyer sur `pip check` et l'activation de l'env.
    print("Checking basic Python dependencies...")
    required_modules = ['flask', 'flask_cors', 'pydantic', 'requests']
    missing = []
    for module_name in required_modules:
        try:
            __import__(module_name) # Tente d'importer le module
            print(f"✅ Module '{module_name}': Trouvé")
        except ImportError:
            print(f"❌ Module '{module_name}': Manquant. Veuillez l'installer (ex: pip install {module_name})")
            missing.append(module_name)
    return not missing # True si aucune dépendance manquante

def main():
    print("🔍 Diagnostic de l'API d'Analyse Argumentative")
    print("=" * 50)
    
    deps_ok = check_python_dependencies()
    
    print("\n🌐 Vérification de l'API (assurez-vous qu'elle est lancée séparément):")
    health_ok = check_api_health()
    
    analyze_ok = False
    if health_ok:
        analyze_ok = test_analyze_endpoint()
    
    print("\n📊 Résumé du Diagnostic:")
    print(f"   Dépendances Python de base: {'✅ OK' if deps_ok else '❌ Problèmes détectés'}")
    print(f"   Santé de l'API (Health Check): {'✅ OK' if health_ok else '❌ Problème ou API non démarrée'}")
    print(f"   Endpoint d'Analyse (/analyze): {'✅ OK' if analyze_ok else '❌ Problème'}")
    
    if deps_ok and health_ok and analyze_ok:
        print("\n🎉 Le diagnostic de base semble bon ! Si des problèmes persistent, consultez les logs détaillés.")
        return 0
    else:
        print("\n⚠️ Des problèmes ont été détectés. Veuillez vérifier les messages ci-dessus et consulter le guide de troubleshooting complet.")
        return 1

if __name__ == "__main__":
    # Note: Ce script vérifie une API externe. Il ne démarre pas l'API lui-même.
    # Assurez-vous que l'API Flask est en cours d'exécution avant de lancer ce script.
    sys.exit(main())
```

### 🔍 Utilisation du script de diagnostic

1.  Sauvegardez le code Python ci-dessus dans un fichier nommé `diagnostic.py` (par exemple, dans `services/web_api/diagnostic.py` ou `scripts/diagnostic_api.py`).
2.  Assurez-vous que votre API Flask est démarrée dans un terminal séparé.
3.  Exécutez le script de diagnostic depuis un autre terminal (avec l'environnement Python activé) :

```bash
# Naviguez vers le répertoire où vous avez sauvegardé diagnostic.py
# Par exemple :
# cd services/web_api 
python diagnostic.py

# Pour rediriger la sortie vers un fichier log :
python diagnostic.py 2>&1 | tee diagnostic_api.log
```

### 🧪 Script de test complet de l'API

Pour un ensemble de tests plus exhaustifs couvrant plusieurs endpoints de l'API (health check, analyse, validation, etc.) avec des charges utiles prédéfinies, utilisez le script [`libs/web_api/test_api.py`](../../../../../libs/web_api/test_api.py) (le chemin peut varier, vérifiez sa localisation actuelle dans le projet). Ce script est généralement plus détaillé que le diagnostic rapide.
Consultez le [`Guide du Développeur`](../../../../guides/guide_developpeur.md:1) pour des instructions sur l'exécution des suites de tests complètes.

```bash
# Exemple de commande pour lancer les tests de l'API (adaptez le chemin si nécessaire)
python ../../../../../libs/web_api/test_api.py 
```
Ce script vous donnera un bon aperçu du fonctionnement général de l'API.

### 🔍 Tests manuels rapides avec `curl`

Ces commandes `curl` vous permettent de tester rapidement les endpoints de base de l'API depuis votre terminal.

```bash
# Test 1 : Vérifier la santé de l'API
curl http://localhost:5000/api/health
# Attendu : {"status": "healthy", "version": "..."} ou similaire

# Test 2 : Analyse simple
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Ceci est un argument de test."}'
# Attendu : Un JSON avec les résultats de l'analyse

# Test 3 : Endpoint de validation (si applicable à votre API)
curl -X POST http://localhost:5000/api/validate \
  -H "Content-Type: application/json" \
  -d '{"premises": ["Tous les hommes sont mortels.", "Socrate est un homme."], "conclusion": "Socrate est mortel."}'
# Attendu : Un JSON avec le résultat de la validation

# Test 4 : Lister les endpoints disponibles (si votre API a un tel endpoint)
curl http://localhost:5000/api/endpoints
# Attendu : Une liste des endpoints et de leurs descriptions
```

## 📞 Support et aide

### Avant de demander de l'aide

1. ✅ **Consultez ce guide et les autres documentations** (notamment le [`Portail des Guides`](../../../../guides/README.md:1) et le [`Guide du Développeur`](../../../../guides/guide_developpeur.md:1)).
2. ✅ Exécutez le script de diagnostic de l'API (si disponible et applicable).
3. ✅ Vérifiez attentivement les logs de l'API (en mode debug) et de votre application React.
4. ✅ Essayez de reproduire le problème avec des données ou des étapes minimales.
5. ✅ Redémarrez l'API et votre application React.
6. ✅ Assurez-vous que votre environnement de développement est correctement configuré et activé.

### Informations à fournir lors d'une demande d'aide

Pour obtenir une aide efficace, veuillez fournir autant d'informations pertinentes que possible :

1.  **Description du problème :** Qu'essayez-vous de faire ? Quel est le comportement attendu ? Quel est le comportement observé ?
2.  **Étapes pour reproduire :** Décrivez précisément comment reproduire le problème.
3.  **Version de Python :** Résultat de `python --version`
4.  **Version de Node.js et npm :** Résultats de `node --version` et `npm --version`
5.  **Système d'exploitation et version** (ex: Windows 10, Ubuntu 22.04, macOS Sonoma)
6.  **Navigateur et version** (si le problème concerne l'interface web)
7.  **Message d'erreur exact :** Copiez-collez l'intégralité du message d'erreur.
8.  **Logs pertinents :**
    *   Logs de la console du navigateur (onglet Console et Network des outils de développement F12).
    *   Logs complets de l'API Flask (lancée en mode debug).
9.  **Résultat du script de diagnostic** (si exécuté).
10. **Extraits de code pertinents** (si vous pensez que le problème est lié à votre code).

### Logs utiles et comment les obtenir

```bash
# Logs de l'API Flask avec timestamp et mode debug (recommandé)
# (Vérifiez le nom et l'emplacement du script de démarrage de l'API)
python start_api.py --debug 2>&1 | while IFS= read -r line; do echo "$(date '+%Y-%m-%d %H:%M:%S.%3N') $line"; done | tee api_debug.log

# Logs du serveur de développement React (npm start)
# La sortie est généralement dans le terminal où vous avez lancé `npm start`.
# Vous pouvez la rediriger vers un fichier si nécessaire :
npm start 2>&1 | tee react_dev_server.log

# Logs réseau du navigateur
# Ouvrez les outils de développement (F12), allez à l'onglet "Network".
# Cochez "Preserve log" (ou "Conserver les journaux").
# Reproduisez le problème. Vous pourrez alors inspecter les requêtes et réponses,
# ou exporter le journal en format HAR.
```

---

**💡 Conseil général :** La majorité des problèmes de développement initiaux sont souvent liés à des erreurs de configuration de l'environnement, des dépendances manquantes/incompatibles, des erreurs de frappe dans les URLs ou les noms de fichiers, ou des problèmes CORS. Une vérification systématique de ces points résout de nombreux cas.

*Ce guide est maintenu par l'équipe du projet. N'hésitez pas à contribuer avec vos propres solutions et découvertes ! Pensez à créer une Pull Request pour suggérer des améliorations.*