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
# Depuis la racine du projet (d:/Dev/2025-Epita-Intelligence-Symbolique)
./setup_project_env.ps1
```
Ce script vous aidera à configurer Conda, le JDK portable et d'autres aspects essentiels.

#### ☐ 2. Navigation vers le projet
```bash
# Aller dans le répertoire du projet
cd d:/Dev/2025-Epita-Intelligence-Symbolique

# Vérifier la structure
ls -la services/web_api/
```

#### ☐ 3. Installation des dépendances API
```bash
# Aller dans le répertoire de l'API
cd services/web_api

# Installer les dépendances Python
pip install -r requirements.txt

# Vérifier l'installation
python start_api.py --no-check
```

### Phase 2 : Démarrage de l'API (5 min)

#### ☐ 4. Lancement de l'API
```bash
# Méthode recommandée
python start_api.py

# OU méthode alternative
python app.py
```

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
# Assurez-vous que l'API est démarrée
python libs/web_api/test_api.py
```
Ce script effectue une série de tests sur les différents points d'accès de l'API. Consultez le fichier [`libs/web_api/test_api.py`](../../../../../libs/web_api/test_api.py) pour plus de détails.

**✅ Résultat attendu :** L'API répond avec un JSON contenant `"success": true`

### Phase 3 : Configuration React (10 min)

#### ☐ 6. Création du projet React
```bash
# Dans un nouveau terminal, retour à la racine
cd d:/Dev/2025-Epita-Intelligence-Symbolique

# Créer le projet React
npx create-react-app interface-web-argumentative
cd interface-web-argumentative

# Installer les dépendances supplémentaires
npm install axios
```

#### ☐ 7. Configuration CORS (si nécessaire)
Si vous rencontrez des erreurs CORS, ajoutez dans `services/web_api/app.py` :
```python
# Déjà configuré dans l'API, mais vérifiez que CORS est activé
CORS(app, origins=["http://localhost:3000"])
```

### Phase 4 : Premier composant (15 min)

#### ☐ 8. Création du service API
Créez `src/services/api.js` :
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
      options: {
        detect_fallacies: true,
        analyze_structure: true,
        evaluate_coherence: true
      }
    })
  });
  
  if (!response.ok) {
    throw new Error(`Erreur API: ${response.status}`);
  }
  
  return response.json();
};

export const checkAPIHealth = async () => {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  return response.json();
};
```

#### ☐ 9. Composant de test simple
Remplacez le contenu de `src/App.js` :
```jsx
import React, { useState, useEffect } from 'react';
import { analyzeText, checkAPIHealth } from './services/api';
import './App.css';

function App() {
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [apiStatus, setApiStatus] = useState('checking');

  useEffect(() => {
    // Vérifier l'état de l'API au démarrage
    checkAPIHealth()
      .then(() => setApiStatus('connected'))
      .catch(() => setApiStatus('disconnected'));
  }, []);

  const handleAnalyze = async () => {
    if (!text.trim()) return;
    
    setLoading(true);
    try {
      const analysis = await analyzeText(text);
      setResult(analysis);
    } catch (error) {
      console.error('Erreur:', error);
      alert('Erreur lors de l\'analyse. Vérifiez que l\'API est démarrée.');
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
                apiStatus === 'disconnected' ? '❌ Déconnectée' : '🔄 Vérification...'}
        </div>
      </header>

      <main style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
        <div>
          <h2>Analyseur d'Arguments</h2>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Entrez votre argument ici..."
            rows={6}
            style={{ width: '100%', padding: '10px', fontSize: '16px' }}
          />
          <br />
          <button 
            onClick={handleAnalyze}
            disabled={loading || !text.trim() || apiStatus !== 'connected'}
            style={{ 
              padding: '10px 20px', 
              fontSize: '16px', 
              marginTop: '10px',
              backgroundColor: loading ? '#ccc' : '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? 'Analyse en cours...' : 'Analyser'}
          </button>
        </div>

        {result && (
          <div style={{ marginTop: '30px', padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '5px' }}>
            <h3>Résultats</h3>
            <p><strong>Qualité globale:</strong> {(result.overall_quality * 100).toFixed(1)}%</p>
            <p><strong>Sophismes détectés:</strong> {result.fallacy_count}</p>
            <p><strong>Temps de traitement:</strong> {result.processing_time?.toFixed(3)}s</p>
            
            {result.fallacies && result.fallacies.length > 0 && (
              <div>
                <h4>Sophismes détectés:</h4>
                {result.fallacies.map((fallacy, index) => (
                  <div key={index} style={{ 
                    margin: '10px 0', 
                    padding: '10px', 
                    backgroundColor: 'white', 
                    borderRadius: '3px',
                    border: '1px solid #dee2e6'
                  }}>
                    <strong>{fallacy.name}</strong>
                    <p>{fallacy.description}</p>
                    <small>Sévérité: {(fallacy.severity * 100).toFixed(1)}%</small>
                  </div>
                ))}
              </div>
            )}
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
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed !important;
}
```

### Phase 5 : Test et validation (5 min)

#### ☐ 11. Démarrage de React
```bash
# Dans le répertoire de votre projet React
npm start
```

#### ☐ 12. Test complet
1. **Vérifiez que l'API est connectée** (indicateur vert)
2. **Testez avec un argument simple** :
   ```
   Tous les chats sont des animaux. Félix est un chat. Donc Félix est un animal.
   ```
3. **Testez avec un sophisme** :
   ```
   Vous ne pouvez pas critiquer ce projet car vous n'êtes pas expert en la matière.
   ```

**✅ Résultat attendu :** L'interface affiche les résultats d'analyse avec les sophismes détectés.

Pour des tests plus automatisés et approfondis de l'API elle-même, vous pouvez réutiliser le script [`libs/web_api/test_api.py`](../../../../../libs/web_api/test_api.py) mentionné précédemment. Cela peut être utile pour vérifier que l'API fonctionne correctement avant de tester l'intégration complète avec l'interface React.

## 🎯 Objectifs de validation

À la fin de cette checklist, vous devriez avoir :

- ✅ Une API fonctionnelle sur `http://localhost:5000`
- ✅ Une interface React sur `http://localhost:3000`
- ✅ Communication réussie entre React et l'API
- ✅ Affichage des résultats d'analyse
- ✅ Détection de sophismes basique

## 🚨 Problèmes courants et solutions

### Problème : "Module not found" lors de l'import de l'API
**Solution :**
```bash
# Vérifiez que vous êtes dans le bon répertoire
cd services/web_api
python -c "import sys; print(sys.path)"
```

### Problème : Erreur CORS
**Solution :**
1. Vérifiez que CORS est activé dans l'API
2. Redémarrez l'API après modification
3. Utilisez `http://localhost:3000` (pas `127.0.0.1`)

### Problème : "Connection refused"
**Solution :**
1. Vérifiez que l'API est démarrée : `curl http://localhost:5000/api/health`
2. Vérifiez le port utilisé
3. Redémarrez l'API si nécessaire

### Problème : Dépendances Python manquantes
**Solution :**
```bash
# Réinstaller les dépendances
pip install --upgrade pip
pip install -r requirements.txt

# Ou utiliser un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

## 📚 Prochaines étapes

Une fois cette checklist terminée, consultez :

1. **[GUIDE_UTILISATION_API.md](./GUIDE_UTILISATION_API.md)** - Documentation complète de l'API
2. **[exemples-react/](./exemples-react/)** - Composants React avancés
3. **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Solutions aux problèmes courants

## 🎉 Félicitations !

Vous avez maintenant une base fonctionnelle pour votre projet d'interface web d'analyse argumentative. Vous pouvez commencer à développer des fonctionnalités plus avancées !

---

**Temps estimé total : 50 minutes**

*En cas de problème, consultez le guide de troubleshooting ou contactez l'équipe du projet.*