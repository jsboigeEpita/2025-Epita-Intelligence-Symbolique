# 🚀 Démarrage Rapide - Interface Web d'Analyse Argumentative

## ✅ Checklist Étape par Étape

### Phase 1 : Préparation de l'environnement (15 min)

#### ☐ 1. Vérification des prérequis
```bash
# Vérifier Python (version 3.8+)
python --version

# Vérifier Node.js (version 16+)
node --version

# Vérifier npm
npm --version
```

Pour une configuration plus automatisée de votre environnement de développement, notamment pour les dépendances Python et Java, vous pouvez utiliser le script [`setup_project_env.ps1`](../../../../../setup_project_env.ps1:0). Exécutez-le depuis la racine du projet :
```bash
# Depuis la racine du projet (par exemple, c:/dev/2025-Epita-Intelligence-Symbolique)
./setup_project_env.ps1
```
Ce script vous aidera à configurer Conda, le JDK portable et d'autres aspects essentiels. Ce script est crucial pour configurer correctement l'environnement, y compris les aspects liés à Java nécessaires au [Moteur de Raisonnement](../../../../../docs/composants/reasoning_engine.md:1) et au [Pont Tweety](../../../../../docs/composants/tweety_bridge.md:1). Pour plus de détails sur la gestion de la JVM et la configuration de l'environnement de développement, consultez le [Guide du Développeur](../../../../../docs/guides/guide_developpeur.md:1).

**Important :** Si le script `setup_project_env.ps1` a configuré un environnement Conda (par exemple, `epita-env`), assurez-vous de l'activer dans votre terminal avant de poursuivre avec les commandes `pip` et `python` :
```bash
conda activate epita-env
```
Adaptez `epita-env` si vous avez utilisé un nom différent lors de la configuration.

#### ☐ 2. Navigation vers le projet
```bash
# Aller dans le répertoire du projet
cd chemin/vers/votre/projet/2025-Epita-Intelligence-Symbolique

# Vérifier la structure (exemple pour l'API)
ls -la services/web_api/
```

#### ☐ 3. Installation des dépendances API
```bash
# Aller dans le répertoire de l'API
cd services/web_api

# Installer les dépendances Python
pip install -r requirements.txt
```
Pour une meilleure gestion des dépendances, il est recommandé d'utiliser un environnement virtuel Python. Le script [`setup_project_env.ps1`](../../../../../setup_project_env.ps1:0) peut vous aider à en configurer un avec Conda, comme mentionné ci-dessus. Si vous préférez un `venv` standard, référez-vous à la section "Problèmes courants".

```bash
# Vérifier l'installation (l'API devrait démarrer et s'arrêter rapidement)
python start_api.py --no-check
```

### Phase 2 : Démarrage de l'API (5 min)

#### ☐ 4. Lancement de l'API
```bash
# Méthode recommandée (depuis services/web_api/)
python start_api.py

# OU méthode alternative (depuis services/web_api/)
python app.py
```
Pour comprendre le fonctionnement interne de l'API, ses différentes routes et options de configuration, consultez la documentation de l'[API Web](../../../../../docs/composants/api_web.md:1) et le guide d'[Intégration de l'API Web](../../../../../docs/guides/integration_api_web.md:1).

#### ☐ 5. Test de l'API
```bash
# Test de santé (dans un nouveau terminal)
curl http://localhost:5000/api/health

# Test d'analyse simple
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Test argument"}'
```

Vous pouvez également tester l'API de manière plus complète en exécutant le script de test dédié depuis la racine du projet :
```bash
# Assurez-vous que l'API est démarrée et que votre environnement est activé
python libs/web_api/test_api.py
```
Ce script effectue une série de tests sur les différents points d'accès de l'API. Consultez le fichier [`libs/web_api/test_api.py`](../../../../../libs/web_api/test_api.py) pour plus de détails. Ce script de test est un bon exemple d'interaction avec les différents *endpoints* décrits dans la documentation de l'[API Web](../../../../../docs/composants/api_web.md:1).

**✅ Résultat attendu :** L'API répond avec un JSON contenant `"success": true` pour le test de santé, et une analyse pour le test d'analyse.

### Phase 3 : Configuration React (10 min)

#### ☐ 6. Création du projet React
```bash
# Dans un nouveau terminal, retour à la racine du projet
cd chemin/vers/votre/projet/2025-Epita-Intelligence-Symbolique

# Créer le projet React (remplacez interface-web-argumentative si déjà existant ou pour un autre nom)
npx create-react-app interface-web-argumentative
cd interface-web-argumentative

# Installer les dépendances supplémentaires
npm install axios
```
Axios est utilisé ici pour simplifier les appels HTTP vers l'API. Pour plus de détails sur la manière dont l'interface communique avec le backend, référez-vous au guide d'[Intégration de l'API Web](../../../../../docs/guides/integration_api_web.md:1).

#### ☐ 7. Configuration CORS (si nécessaire)
Si vous rencontrez des erreurs CORS, vérifiez la configuration dans `services/web_api/app.py`. Normalement, l'API est déjà configurée pour accepter les requêtes depuis `http://localhost:3000`.
```python
# Extrait de services/web_api/app.py (vérifiez que CORS est bien configuré)
# from flask_cors import CORS
# CORS(app, origins=["http://localhost:3000"]) # ou une configuration plus permissive pour le développement
```
La gestion CORS est un aspect important de la sécurité et de la communication entre domaines. Plus d'informations sont disponibles dans le guide d'[Intégration de l'API Web](../../../../../docs/guides/integration_api_web.md:1).

### Phase 4 : Premier composant (15 min)

#### ☐ 8. Création du service API
Créez `src/services/api.js` dans votre projet React :
Ce service encapsule la logique d'appel à l'API. Les *endpoints* `/api/analyze` et `/api/health` sont documentés en détail dans la documentation de l'[API Web](../../../../../docs/composants/api_web.md:1). Les options passées à `/api/analyze` (comme `detect_fallacies`) sont également décrites dans cette documentation.
```javascript
const API_BASE_URL = 'http://localhost:5000';

export const analyzeText = async (text) => {
  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      options: { // Consultez la doc de l'API Web pour toutes les options disponibles
        detect_fallacies: true,
        analyze_structure: true,
        evaluate_coherence: true
      }
    })
  });
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ message: 'Erreur API inconnue' }));
    throw new Error(`Erreur API: ${response.status} - ${errorData.message || 'Pas de message spécifique'}`);
  }
  
  return response.json();
};

export const checkAPIHealth = async () => {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) {
    throw new Error(`Erreur API Health: ${response.status}`);
  }
  return response.json();
};
```

#### ☐ 9. Composant de test simple
Remplacez le contenu de `src/App.js` :
Cet exemple montre comment appeler le service `api.js` et afficher les résultats. La structure des données retournées par l'API (par exemple, `result.overall_quality`, `result.fallacies`) est définie dans la documentation de l'[API Web](../../../../../docs/composants/api_web.md:1).
```jsx
import React, { useState, useEffect } from 'react';
import { analyzeText, checkAPIHealth } from './services/api';
import './App.css';

function App() {
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState('checking');
  const [error, setError] = useState(null);

  useEffect(() => {
    checkAPIHealth()
      .then(data => {
        if (data.success) {
          setApiStatus('connected');
        } else {
          setApiStatus('disconnected');
          setError('L\'API a répondu mais n\'est pas saine.');
        }
      })
      .catch(err => {
        setApiStatus('disconnected');
        setError(`Impossible de joindre l'API: ${err.message}`);
        console.error(err);
      });
  }, []);

  const handleAnalyze = async () => {
    if (!text.trim()) return;
    
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const analysis = await analyzeText(text);
      setResult(analysis);
    } catch (err) {
      console.error('Erreur:', err);
      setError(`Erreur lors de l'analyse: ${err.message}. Vérifiez que l'API est démarrée et accessible.`);
      alert(`Erreur lors de l'analyse: ${err.message}. Vérifiez que l'API est démarrée et accessible.`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Interface Web d'Analyse Argumentative</h1>
        <div className={`api-status ${apiStatus}`}>
          API: {apiStatus === 'connected' ? '✅ Connectée' : 
                apiStatus === 'disconnected' ? `❌ Déconnectée` : '🔄 Vérification...'}
        </div>
        {error && <p style={{color: 'red'}}>{error}</p>}
      </header>

      <main style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
        <div>
          <h2>Analyseur d'Arguments</h2>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Entrez votre argument ici..."
            rows={6}
            style={{ width: '100%', padding: '10px', fontSize: '16px', boxSizing: 'border-box' }}
          />
          <br />
          <button 
            onClick={handleAnalyze}
            disabled={loading || !text.trim() || apiStatus !== 'connected'}
            style={{ 
              padding: '10px 20px', 
              fontSize: '16px', 
              marginTop: '10px',
              backgroundColor: (loading || apiStatus !== 'connected') ? '#ccc' : '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: (loading || apiStatus !== 'connected') ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? 'Analyse en cours...' : 'Analyser'}
          </button>
        </div>

        {result && (
          <div style={{ marginTop: '30px', padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '5px', textAlign: 'left' }}>
            <h3>Résultats</h3>
            {/* Adaptez l'affichage en fonction de la structure exacte des résultats de VOTRE API */}
            <p><strong>Qualité globale (exemple):</strong> {result.overall_quality !== undefined ? (result.overall_quality * 100).toFixed(1) + '%' : 'N/A'}</p>
            <p><strong>Nombre de sophismes (exemple):</strong> {result.fallacy_count !== undefined ? result.fallacy_count : 'N/A'}</p>
            <p><strong>Temps de traitement (exemple):</strong> {result.processing_time?.toFixed(3)}s</p>
            
            {result.fallacies && result.fallacies.length > 0 && (
              <div>
                <h4>Sophismes détectés (exemple):</h4>
                {result.fallacies.map((fallacy, index) => (
                  <div key={index} style={{ 
                    margin: '10px 0', 
                    padding: '10px', 
                    backgroundColor: 'white', 
                    borderRadius: '3px',
                    border: '1px solid #dee2e6'
                  }}>
                    <strong>{fallacy.name || 'Sophisme Inconnu'}</strong>
                    <p>{fallacy.description || 'Pas de description.'}</p>
                    {fallacy.severity !== undefined && <small>Sévérité: {(fallacy.severity * 100).toFixed(1)}%</small>}
                  </div>
                ))}
              </div>
            )}
            <details>
              <summary>Données brutes JSON</summary>
              <pre style={{whiteSpace: 'pre-wrap', wordBreak: 'break-all', backgroundColor: '#eee', padding: '10px'}}>
                {JSON.stringify(result, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
```

#### ☐ 10. Styles CSS de base
Ajoutez dans `src/App.css` :
```css
.App {
  text-align: center;
}

.App-header {
  background-color: #282c34;
  padding: 20px;
  color: white;
}

.api-status {
  margin-top: 10px;
  padding: 5px 10px;
  border-radius: 3px;
  font-size: 14px;
  display: inline-block; /* Pour que le padding soit correct */
}

.api-status.connected {
  background-color: #d4edda;
  color: #155724;
}

.api-status.disconnected {
  background-color: #f8d7da;
  color: #721c24;
}

.api-status.checking {
  background-color: #fff3cd;
  color: #856404;
}

textarea {
  font-family: inherit;
  resize: vertical;
  box-sizing: border-box; /* S'assurer que padding et border sont inclus dans la largeur/hauteur */
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed !important;
}
```

### Phase 5 : Test et validation (5 min)

#### ☐ 11. Démarrage de React
```bash
# Dans le répertoire de votre projet React (ex: interface-web-argumentative)
npm start
```

#### ☐ 12. Test complet
1.  **Vérifiez que l'API est connectée** (indicateur vert dans l'interface).
2.  **Testez avec un argument simple** :
    ```
    Tous les chats sont des animaux. Félix est un chat. Donc Félix est un animal.
    ```
3.  **Testez avec un sophisme** (si votre API le gère) :
    ```
    Vous ne pouvez pas critiquer ce projet car vous n'êtes pas expert en la matière.
    ```

**✅ Résultat attendu :** L'interface affiche les résultats d'analyse. Si des sophismes sont détectés par l'API, ils devraient apparaître.

Pour des tests plus automatisés et approfondis de l'API elle-même, vous pouvez réutiliser le script [`libs/web_api/test_api.py`](../../../../../libs/web_api/test_api.py) mentionné précédemment. Ce script est un outil précieux pour valider le bon fonctionnement de votre backend. Assurez-vous de comprendre son utilisation en consultant la documentation de l'[API Web](../../../../../docs/composants/api_web.md:1) et le [Guide du Développeur](../../../../../docs/guides/guide_developpeur.md:1) pour les bonnes pratiques de test.

## 🎯 Objectifs de validation

À la fin de cette checklist, vous devriez avoir :

- ✅ Une API fonctionnelle sur `http://localhost:5000`
- ✅ Une interface React sur `http://localhost:3000`
- ✅ Communication réussie entre React et l'API
- ✅ Affichage des résultats d'analyse (la structure exacte dépendra de votre API)
- ✅ Détection de sophismes basique (si implémentée et configurée dans l'API)

## 🚨 Problèmes courants et solutions

### Problème : "Module not found" lors de l'import dans l'API Python
**Solution :**
Assurez-vous que votre terminal est bien dans le répertoire `services/web_api` et que votre environnement Python (Conda ou venv) est activé.
```bash
# Vérifiez le répertoire courant
pwd  # ou 'cd' sur Windows

# Vérifiez le PYTHONPATH si nécessaire (généralement géré par l'environnement virtuel)
python -c "import sys; print(sys.path)"
```

### Problème : Erreur CORS
**Solution :**
1.  Vérifiez que CORS est correctement configuré et activé dans `services/web_api/app.py` pour autoriser `http://localhost:3000`.
2.  Redémarrez l'API Python après toute modification.
3.  Assurez-vous d'accéder à votre application React via `http://localhost:3000` et non `http://127.0.0.1:3000` (ou vice-versa, soyez cohérent).

### Problème : "Connection refused" ou l'API ne répond pas
**Solution :**
1.  Vérifiez que l'API Python est bien démarrée et écoute sur `http://localhost:5000`. Testez avec `curl http://localhost:5000/api/health`.
2.  Vérifiez qu aucun autre processus n'utilise le port 5000.
3.  Consultez les logs de l'API Python pour d'éventuelles erreurs au démarrage.
4.  Redémarrez l'API si nécessaire.

### Problème : Dépendances Python manquantes ou conflits
**Solution :**
Assurez-vous que votre environnement virtuel (Conda ou venv) est activé.
```bash
# (Après activation de l'environnement)
# Réinstaller les dépendances depuis services/web_api/
pip install --upgrade pip
pip install -r requirements.txt

# Pour un environnement venv standard (si non géré par setup_project_env.ps1)
# python -m venv venv # Crée l'environnement dans le dossier courant
# source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows (cmd)
# .\venv\Scripts\Activate.ps1 # Windows (PowerShell)
# pip install -r requirements.txt
```
Consultez le [Guide du Développeur](../../../../../docs/guides/guide_developpeur.md:1) pour plus de détails sur la gestion des environnements.

## 📚 Prochaines étapes

Une fois cette checklist terminée, consultez :

1.  **Documentation de l'[API Web (Composant)](../../../../../docs/composants/api_web.md:1)** - Description détaillée du composant API, de ses routes et de ses options.
2.  **[Guide d'Intégration de l'API Web](../../../../../docs/guides/integration_api_web.md:1)** - Comment utiliser et intégrer l'API plus en profondeur.
3.  **[Exemples React avancés](./exemples-react/)** (`./exemples-react/`) - Pour des composants et des fonctionnalités React plus élaborés.
4.  **[Guide de Troubleshooting général](./TROUBLESHOOTING.md)** (`./TROUBLESHOOTING.md`) - Solutions aux problèmes courants non spécifiques à ce démarrage rapide.
5.  **[Portail des Guides](../../../../../docs/guides/README.md:1)** - Accès à tous les guides officiels du projet.
6.  **[Architecture Globale](../../../../../docs/architecture/architecture_globale.md:1)** - Pour comprendre le contexte plus large du système dans lequel s'intègre votre interface.

## 🎉 Félicitations !

Vous avez maintenant une base fonctionnelle pour votre projet d'interface web d'analyse argumentative. Vous pouvez commencer à développer des fonctionnalités plus avancées en vous appuyant sur la documentation complète du projet !

---

**Temps estimé total : 50-60 minutes** (peut varier selon l'expérience)

*En cas de problème, consultez les guides mentionnés ou contactez l'équipe du projet.*