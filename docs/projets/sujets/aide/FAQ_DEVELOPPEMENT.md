# FAQ - Développement des Projets Epita 2025 Intelligence Symbolique

Ce document regroupe les questions fréquemment posées et leurs réponses pour vous aider à résoudre les problèmes courants que vous pourriez rencontrer lors du développement de vos projets.

## Table des matières

1. [Questions générales](#questions-générales)
2. [API Web](#api-web)
3. [Moteur d'analyse argumentative](#moteur-danalyse-argumentative)
4. [Interface Web](#interface-web)
5. [Serveur MCP](#serveur-mcp)
6. [TweetyProject](#tweetyproject)
7. [Déploiement](#déploiement)

## Questions générales

### Q: Comment obtenir de l'aide en cas de problème ?

**R:** Plusieurs options s'offrent à vous :
- Consultez cette FAQ et la documentation disponible
- Posez vos questions lors des réunions hebdomadaires
- Contactez l'équipe encadrante par email
- Utilisez le canal de communication dédié au projet

### Q: Où trouver la documentation du projet ?

**R:** La documentation est disponible dans plusieurs endroits :
- Le dossier `docs/projets/sujets/aide/` contient des guides spécifiques
- Le fichier `services/README.md` documente l'API web
- Les fichiers README dans chaque dossier du projet
- La documentation en ligne de TweetyProject

### Q: Comment organiser notre travail en équipe ?

**R:** Nous recommandons :
- Utiliser Git pour la gestion de version
- Diviser le travail en tâches claires et assignées
- Faire des réunions d'équipe régulières
- Documenter vos décisions et votre progression
- Utiliser des outils comme Trello ou GitHub Projects pour suivre les tâches

## API Web

### Q: Comment démarrer l'API web ?

**R:** Pour démarrer l'API web :

```bash
cd services/web_api
pip install -r requirements.txt
python app.py
```

L'API sera disponible sur http://localhost:5000.

### Q: Comment tester les endpoints de l'API ?

**R:** Plusieurs options :
- Utilisez l'endpoint `/api/endpoints` pour voir la documentation
- Utilisez Postman ou curl pour faire des requêtes manuelles
- Utilisez les tests automatisés dans `services/web_api/tests/`

### Q: Comment gérer les erreurs CORS avec l'API ?

**R:** L'API a déjà CORS activé avec Flask-CORS. Si vous rencontrez des problèmes :
1. Vérifiez que vous utilisez bien l'URL correcte (http://localhost:5000)
2. Assurez-vous que vos requêtes incluent les headers appropriés
3. Si nécessaire, modifiez la configuration CORS dans `app.py` :

```python
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

### Q: Comment étendre l'API avec de nouveaux endpoints ?

**R:** Pour ajouter un nouvel endpoint :
1. Créez un nouveau service dans `services/web_api/services/`
2. Définissez les modèles de requête/réponse dans `models/`
3. Ajoutez la route dans `app.py`
4. Documentez l'endpoint dans la fonction `list_endpoints()`

## Moteur d'analyse argumentative

### Q: Comment accéder au moteur d'analyse depuis mon code ?

**R:** Vous pouvez accéder au moteur de deux façons :
1. Via l'API web (recommandé pour l'interface web)
2. Directement via les imports Python (pour le serveur MCP) :

```python
from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer
```

### Q: Comment fonctionne la détection de sophismes ?

**R:** La détection de sophismes utilise plusieurs approches combinées :
1. Analyse par patterns linguistiques
2. Analyse structurelle des arguments
3. Analyse contextuelle
4. Évaluation de la sévérité

Ces analyses sont effectuées par différents composants comme `ComplexFallacyAnalyzer` et `ContextualFallacyAnalyzer`.

### Q: Comment sont calculées les extensions des frameworks de Dung ?

**R:** Les extensions sont calculées par TweetyProject selon différentes sémantiques :
- Grounded : extension unique, calculée par `SimpleGroundedReasoner`
- Preferred : extensions maximales, calculées par `SimplePreferredReasoner`
- Stable : extensions stables, calculées par `SimpleStableReasoner`

Le service `FrameworkService` encapsule ces calculs et les expose via l'API.

### Q: Comment gérer les performances pour les analyses complexes ?

**R:** Pour les analyses complexes :
- Utilisez le paramètre `options` pour limiter l'analyse aux aspects nécessaires
- Implémentez un système de cache pour les résultats fréquemment demandés
- Pour les frameworks volumineux, limitez les sémantiques calculées
- Utilisez des timeouts pour éviter les calculs trop longs

## Interface Web

### Q: Comment gérer les appels asynchrones à l'API ?

**R:** Utilisez `async/await` avec Axios ou fetch :

```javascript
// Avec Axios
const analyzeText = async (text) => {
  try {
    const response = await axios.post('http://localhost:5000/api/analyze', {
      text,
      options: { detect_fallacies: true }
    });
    return response.data;
  } catch (error) {
    console.error('Error analyzing text:', error);
    throw error;
  }
};

// Avec fetch
const analyzeText = async (text) => {
  try {
    const response = await fetch('http://localhost:5000/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        options: { detect_fallacies: true }
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error analyzing text:', error);
    throw error;
  }
};
```

### Q: Comment visualiser un framework de Dung avec D3.js ?

**R:** Voici un exemple simplifié :

```javascript
import * as d3 from 'd3';

const renderFramework = (framework, svgElement) => {
  const svg = d3.select(svgElement);
  const width = svg.attr('width');
  const height = svg.attr('height');
  
  // Créer les données pour D3
  const nodes = framework.arguments.map(arg => ({
    id: arg.id,
    label: arg.id,
    status: arg.status
  }));
  
  const links = framework.attack_relations.map(rel => ({
    source: rel.attacker,
    target: rel.attacked
  }));
  
  // Configurer la simulation de force
  const simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d => d.id).distance(100))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(width / 2, height / 2));
  
  // Créer les liens (flèches)
  const link = svg.append('g')
    .selectAll('line')
    .data(links)
    .enter().append('line')
    .attr('stroke', '#999')
    .attr('stroke-width', 2)
    .attr('marker-end', 'url(#arrowhead)');
  
  // Définir les marqueurs de flèche
  svg.append('defs').append('marker')
    .attr('id', 'arrowhead')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 15)
    .attr('refY', 0)
    .attr('orient', 'auto')
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .append('path')
    .attr('d', 'M0,-5L10,0L0,5')
    .attr('fill', '#999');
  
  // Créer les nœuds
  const node = svg.append('g')
    .selectAll('circle')
    .data(nodes)
    .enter().append('circle')
    .attr('r', 10)
    .attr('fill', d => {
      switch (d.status) {
        case 'accepted': return 'green';
        case 'rejected': return 'red';
        default: return 'orange';
      }
    });
  
  // Ajouter les labels
  const text = svg.append('g')
    .selectAll('text')
    .data(nodes)
    .enter().append('text')
    .text(d => d.label)
    .attr('font-size', 12)
    .attr('dx', 15)
    .attr('dy', 4);
  
  // Mise à jour des positions
  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);
    
    node
      .attr('cx', d => d.x)
      .attr('cy', d => d.y);
    
    text
      .attr('x', d => d.x)
      .attr('y', d => d.y);
  });
};
```

### Q: Comment mettre en évidence les sophismes dans le texte ?

**R:** Vous pouvez utiliser cette approche :

```jsx
import React from 'react';

const FallacyHighlighter = ({ text, fallacies }) => {
  if (!text || !fallacies || fallacies.length === 0) {
    return <div className="text-content">{text}</div>;
  }
  
  // Trier les sophismes par position de début
  const sortedFallacies = [...fallacies].sort((a, b) => 
    (a.location?.start || 0) - (b.location?.start || 0)
  );
  
  // Construire les segments de texte
  const segments = [];
  let lastIndex = 0;
  
  sortedFallacies.forEach(fallacy => {
    if (!fallacy.location) return;
    
    const { start, end } = fallacy.location;
    
    // Ajouter le texte avant le sophisme
    if (start > lastIndex) {
      segments.push({
        text: text.substring(lastIndex, start),
        isFallacy: false
      });
    }
    
    // Ajouter le sophisme
    segments.push({
      text: text.substring(start, end),
      isFallacy: true,
      fallacy
    });
    
    lastIndex = end;
  });
  
  // Ajouter le texte restant après le dernier sophisme
  if (lastIndex < text.length) {
    segments.push({
      text: text.substring(lastIndex),
      isFallacy: false
    });
  }
  
  return (
    <div className="text-content">
      {segments.map((segment, index) => (
        segment.isFallacy ? (
          <span 
            key={index}
            className="fallacy-highlight"
            style={{ 
              backgroundColor: `rgba(255, 0, 0, ${segment.fallacy.severity * 0.3})`,
              textDecoration: 'underline',
              cursor: 'pointer'
            }}
            title={`${segment.fallacy.name}: ${segment.fallacy.description}`}
          >
            {segment.text}
          </span>
        ) : (
          <span key={index}>{segment.text}</span>
        )
      ))}
    </div>
  );
};

export default FallacyHighlighter;
```

### Q: Comment implémenter un éditeur d'arguments avec analyse en temps réel ?

**R:** Utilisez un hook personnalisé avec debounce :

```jsx
import { useState, useEffect, useCallback } from 'react';
import { debounce } from 'lodash';
import { analyzeText } from '../services/api';

export const useRealtimeAnalysis = (initialText = '', debounceMs = 500) => {
  const [text, setText] = useState(initialText);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const performAnalysis = useCallback(async (textToAnalyze) => {
    if (!textToAnalyze.trim()) {
      setAnalysis(null);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await analyzeText(textToAnalyze);
      setAnalysis(result);
    } catch (err) {
      setError(err.message || 'Error analyzing text');
      console.error('Analysis error:', err);
    } finally {
      setLoading(false);
    }
  }, []);
  
  // Créer une version debounced de l'analyse
  const debouncedAnalysis = useCallback(
    debounce(performAnalysis, debounceMs),
    [performAnalysis, debounceMs]
  );
  
  // Mettre à jour le texte et déclencher l'analyse
  const updateText = useCallback((newText) => {
    setText(newText);
    debouncedAnalysis(newText);
  }, [debouncedAnalysis]);
  
  // Nettoyer le debounce à la destruction
  useEffect(() => {
    return () => {
      debouncedAnalysis.cancel();
    };
  }, [debouncedAnalysis]);
  
  return {
    text,
    updateText,
    analysis,
    loading,
    error,
    reanalyze: () => performAnalysis(text)
  };
};
```

## Serveur MCP

### Q: Comment initialiser JPype correctement ?

**R:** Voici un exemple d'initialisation robuste :

```python
import jpype
import jpype.imports
import os
from pathlib import Path

def initialize_jvm(jar_path, max_memory="2g"):
    """Initialise la JVM avec TweetyProject de manière robuste"""
    if jpype.isJVMStarted():
        return True
    
    try:
        # Vérifier que le fichier JAR existe
        jar_path = Path(jar_path)
        if not jar_path.exists():
            raise FileNotFoundError(f"JAR file not found: {jar_path}")
        
        # Démarrer la JVM avec les options appropriées
        jpype.startJVM(
            jpype.getDefaultJVMPath(),
            f"-Djava.class.path={jar_path}",
            f"-Xmx{max_memory}",
            "-Dfile.encoding=UTF-8",
            convertStrings=True
        )
        
        # Vérifier que la JVM est bien démarrée
        if not jpype.isJVMStarted():
            raise RuntimeError("JVM failed to start")
        
        return True
    except Exception as e:
        print(f"Error initializing JVM: {e}")
        return False
```

### Q: Comment structurer un outil MCP ?

**R:** Voici un modèle pour structurer un outil MCP :

```python
class MCPTool:
    """Classe de base pour les outils MCP"""
    
    def __init__(self, name, description, input_schema):
        self.name = name
        self.description = description
        self.input_schema = input_schema
    
    async def execute(self, params):
        """Méthode à implémenter dans les classes dérivées"""
        raise NotImplementedError("Subclasses must implement execute()")
    
    def validate_params(self, params):
        """Valide les paramètres selon le schéma"""
        # Implémentez la validation avec jsonschema
        pass

class FallacyDetectionTool(MCPTool):
    """Outil MCP pour la détection de sophismes"""
    
    def __init__(self):
        super().__init__(
            name="analyze_fallacy",
            description="Analyse un texte pour détecter les sophismes",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Texte à analyser"},
                    "language": {"type": "string", "enum": ["fr", "en"], "default": "fr"},
                    "confidence_threshold": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.5}
                },
                "required": ["text"]
            }
        )
        # Initialiser les composants nécessaires
        self.fallacy_analyzer = None
    
    async def execute(self, params):
        """Exécute l'analyse de sophismes"""
        # Valider les paramètres
        self.validate_params(params)
        
        # Extraire les paramètres
        text = params.get("text", "")
        language = params.get("language", "fr")
        threshold = params.get("confidence_threshold", 0.5)
        
        # Initialiser l'analyseur si nécessaire
        if not self.fallacy_analyzer:
            from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer
            self.fallacy_analyzer = ComplexFallacyAnalyzer()
        
        # Effectuer l'analyse
        try:
            result = self.fallacy_analyzer.analyze_fallacies(text)
            
            # Filtrer par seuil de confiance
            filtered_fallacies = [
                f for f in result.get("fallacies", [])
                if f.get("confidence", 0) >= threshold
            ]
            
            # Formater la réponse
            return {
                "fallacies": filtered_fallacies,
                "overall_quality": result.get("overall_quality", 0.5),
                "suggestions": result.get("suggestions", [])
            }
        except Exception as e:
            # Gérer les erreurs
            return {
                "error": str(e),
                "fallacies": [],
                "overall_quality": 0.0,
                "suggestions": ["Une erreur s'est produite lors de l'analyse."]
            }
```

### Q: Comment tester un serveur MCP ?

**R:** Vous pouvez tester votre serveur MCP de plusieurs façons :

1. **Tests unitaires** :

```python
import unittest
import json
import asyncio
from unittest.mock import patch, MagicMock
from your_mcp_server import MCPServer

class TestMCPServer(unittest.TestCase):
    def setUp(self):
        self.server = MCPServer("test_config.json")
        asyncio.run(self.server.initialize())
    
    async def test_tools_list(self):
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        response = await self.server.handle_request(request)
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 1)
        self.assertIn("result", response)
        self.assertIn("tools", response["result"])
        
        tools = response["result"]["tools"]
        tool_names = [tool["name"] for tool in tools]
        
        self.assertIn("analyze_fallacy", tool_names)
    
    async def test_fallacy_detection(self):
        with patch.object(self.server.tools["analyze_fallacy"], "execute") as mock_execute:
            mock_execute.return_value = {
                "fallacies": [{"type": "test_fallacy", "confidence": 0.8}],
                "overall_quality": 0.7
            }
            
            request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "analyze_fallacy",
                    "arguments": {"text": "Test text"}
                }
            }
            
            response = await self.server.handle_request(request)
            
            self.assertEqual(response["jsonrpc"], "2.0")
            self.assertEqual(response["id"], 2)
            self.assertIn("result", response)
            mock_execute.assert_called_once_with({"text": "Test text"})
```

2. **Tests manuels avec Claude Desktop** :

Configurez Claude Desktop pour utiliser votre serveur MCP :

```json
{
  "mcpServers": {
    "argumentative-analysis": {
      "command": "python",
      "args": ["path/to/your/server.py", "--config", "config.json"]
    }
  }
}
```

Puis demandez à Claude d'utiliser vos outils :
"Analyse cet argument pour détecter les sophismes : 'Tous les politiciens mentent, donc Pierre ment.'"

### Q: Comment gérer les sessions dans un serveur MCP ?

**R:** Voici un exemple de gestionnaire de sessions :

```python
import time
import uuid
from typing import Dict, Any, Optional

class Session:
    """Représente une session MCP"""
    
    def __init__(self, session_id: str, client_id: str):
        self.id = session_id
        self.client_id = client_id
        self.created_at = time.time()
        self.last_activity = time.time()
        self.context = {}
    
    def update_activity(self):
        """Met à jour le timestamp de dernière activité"""
        self.last_activity = time.time()
    
    def is_expired(self, timeout_seconds: int) -> bool:
        """Vérifie si la session a expiré"""
        return (time.time() - self.last_activity) > timeout_seconds

class SessionManager:
    """Gestionnaire de sessions MCP"""
    
    def __init__(self, session_timeout: int = 3600):
        self.sessions: Dict[str, Session] = {}
        self.session_timeout = session_timeout
    
    def create_session(self, client_id: str) -> str:
        """Crée une nouvelle session"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = Session(session_id, client_id)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Récupère une session par son ID"""
        session = self.sessions.get(session_id)
        if session:
            session.update_activity()
        return session
    
    def update_session_context(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Met à jour le contexte d'une session"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.context.update(updates)
        return True
    
    def cleanup_expired_sessions(self):
        """Nettoie les sessions expirées"""
        expired_ids = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired(self.session_timeout)
        ]
        
        for session_id in expired_ids:
            del self.sessions[session_id]
        
        return len(expired_ids)
```

## TweetyProject

### Q: Comment créer un framework de Dung avec TweetyProject ?

**R:** Voici un exemple :

```python
def create_dung_framework(arguments, attacks):
    """Crée un framework de Dung avec TweetyProject"""
    # Importer les classes nécessaires
    DungTheory = jpype.JClass("org.tweetyproject.arg.dung.syntax.DungTheory")
    Argument = jpype.JClass("org.tweetyproject.arg.dung.syntax.Argument")
    Attack = jpype.JClass("org.tweetyproject.arg.dung.syntax.Attack")
    
    # Créer le framework
    theory = DungTheory()
    
    # Créer les arguments
    arg_objects = {}
    for arg_name in arguments:
        arg_obj = Argument(arg_name)
        theory.add(arg_obj)
        arg_objects[arg_name] = arg_obj
    
    # Ajouter les attaques
    for attacker, attacked in attacks:
        if attacker in arg_objects and attacked in arg_objects:
            attack = Attack(arg_objects[attacker], arg_objects[attacked])
            theory.add(attack)
    
    return theory
```

### Q: Comment calculer les extensions d'un framework ?

**R:** Voici comment calculer différentes extensions :

```python
def calculate_extensions(framework, semantics=["grounded"]):
    """Calcule les extensions d'un framework selon différentes sémantiques"""
    extensions = {}
    
    if "grounded" in semantics:
        # Extension grounded
        GroundedReasoner = jpype.JClass("org.tweetyproject.arg.dung.reasoner.SimpleGroundedReasoner")
        reasoner = GroundedReasoner()
        extension = reasoner.getModel(framework)
        extensions["grounded"] = [str(arg) for arg in extension]
    
    if "preferred" in semantics:
        # Extensions préférées
        PreferredReasoner = jpype.JClass("org.tweetyproject.arg.dung.reasoner.SimplePreferredReasoner")
        reasoner = PreferredReasoner()
        extension_set = reasoner.getModels(framework)
        extensions["preferred"] = [
            [str(arg) for arg in ext]
            for ext in extension_set
        ]
    
    if "stable" in semantics:
        # Extensions stables
        StableReasoner = jpype.JClass("org.tweetyproject.arg.dung.reasoner.SimpleStableReasoner")
        reasoner = StableReasoner()
        extension_set = reasoner.getModels(framework)
        extensions["stable"] = [
            [str(arg) for arg in ext]
            for ext in extension_set
        ]
    
    return extensions
```

### Q: Comment gérer les erreurs de TweetyProject ?

**R:** Utilisez cette approche pour gérer les erreurs :

```python
def safe_tweety_operation(operation_func, *args, **kwargs):
    """Exécute une opération TweetyProject de manière sécurisée"""
    try:
        return {
            "success": True,
            "result": operation_func(*args, **kwargs)
        }
    except jpype.JException as e:
        java_exception = str(e.javaClass()).split('.')[-1]
        message = str(e.message())
        return {
            "success": False,
            "error_type": "java_exception",
            "java_class": java_exception,
            "message": message
        }
    except Exception as e:
        return {
            "success": False,
            "error_type": "python_exception",
            "message": str(e)
        }
```

## Déploiement

### Q: Comment déployer l'API web en production ?

**R:** Vous pouvez utiliser Gunicorn avec Nginx :

1. Installez Gunicorn :
```bash
pip install gunicorn
```

2. Créez un fichier `wsgi.py` :
```python
from services.web_api.app import app

if __name__ == "__main__":
    app.run()
```

3. Démarrez avec Gunicorn :
```bash
gunicorn --bind 0.0.0.0:8000 wsgi:app
```

4. Configurez Nginx comme proxy inverse :
```nginx
server {
    listen 80;
    server_name your_domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Q: Comment déployer l'interface web ?

**R:** Pour une application React :

1. Créez une version de production :
```bash
npm run build
```

2. Servez les fichiers statiques avec Nginx :
```nginx
server {
    listen 80;
    server_name your_frontend_domain.com;
    root /path/to/build;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### Q: Comment déployer le serveur MCP ?

**R:** Pour déployer le serveur MCP :

1. Créez un service systemd :
```ini
[Unit]
Description=MCP Argumentative Analysis Server
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/mcp_server
ExecStart=/usr/bin/python3 server.py --config config.json
Restart=on-failure
Environment=PYTHONPATH=/path/to/project

[Install]
WantedBy=multi-user.target
```

2. Activez et démarrez le service :
```bash
sudo systemctl enable mcp-server
sudo systemctl start mcp-server
```

3. Configurez les clients MCP pour utiliser le serveur déployé.

---

Si vous avez d'autres questions qui ne sont pas couvertes dans cette FAQ, n'hésitez pas à les poser lors des réunions hebdomadaires ou à contacter l'équipe encadrante.