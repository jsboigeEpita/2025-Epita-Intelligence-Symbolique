# Guide d'intégration des projets Epita 2025 Intelligence Symbolique

Ce document est destiné aux étudiants travaillant sur les projets d'Intelligence Symbolique pour faciliter leur intégration et leur compréhension de l'architecture globale du système.

## Table des matières

1. [Vue d'ensemble du projet](#vue-densemble-du-projet)
2. [Architecture du système](#architecture-du-système)
3. [Guide pour le projet Interface Web](#guide-pour-le-projet-interface-web)
4. [Guide pour le projet Serveur MCP](#guide-pour-le-projet-serveur-mcp)
5. [Ressources communes](#ressources-communes)
6. [Processus de développement](#processus-de-développement)
7. [FAQ](#faq)

## Vue d'ensemble du projet

Le projet Epita 2025 Intelligence Symbolique est centré sur l'analyse argumentative, combinant des techniques d'intelligence artificielle symbolique et des approches modernes d'interaction utilisateur. Le système permet d'analyser des textes argumentatifs, de détecter des sophismes, de valider la structure logique des arguments et de construire des frameworks d'argumentation de Dung.

### Objectifs principaux

- Fournir des outils d'analyse argumentative accessibles et intuitifs
- Permettre la détection automatique de sophismes dans des textes
- Faciliter la visualisation et la manipulation de frameworks argumentatifs
- Intégrer ces outils avec des assistants IA modernes via le protocole MCP

## Architecture du système

Le système est composé de plusieurs couches :

1. **Moteur d'analyse argumentative** (`argumentation_analysis/`)
   - Agents spécialisés pour différentes tâches d'analyse
   - Outils de détection de sophismes et d'analyse structurelle
   - Orchestration des différents composants

2. **API Web** (`services/web_api/`)
   - Interface REST pour accéder aux fonctionnalités du moteur
   - Modèles de données standardisés
   - Services métier pour chaque type d'analyse

3. **Interface utilisateur** (à développer par le groupe Interface Web)
   - Application web React/Vue/Angular
   - Visualisations interactives
   - Expérience utilisateur intuitive

4. **Serveur MCP** (à développer par le groupe Serveur MCP)
   - Exposition des fonctionnalités via le protocole Model Context Protocol
   - Intégration avec des LLMs comme Claude et GPT
   - Gestion des sessions et du contexte

### Exemples d'intégration et Tests

Pour mieux comprendre comment ces composants interagissent, vous pouvez consulter les ressources suivantes :

*   **Scripts d'intégration d'API :** Un exemple concret d'appel à l'API pour utiliser les fonctionnalités du moteur d'analyse se trouve dans [`examples/logic_agents/api_integration_example.py`](examples/logic_agents/api_integration_example.py:0).
*   **Tests d'intégration :** Les tests d'intégration pour les agents logiques, qui illustrent leurs interactions avec le reste du système, sont disponibles dans [`tests/integration/test_logic_agents_integration.py`](tests/integration/test_logic_agents_integration.py:0). Pour l'intégration spécifique avec TweetyProject via JPype, référez-vous au répertoire [`tests/integration/jpype_tweety/`](tests/integration/jpype_tweety/).
*   **Scripts de démonstration :** Des scripts montrant l'utilisation combinée de plusieurs modules sont disponibles dans le répertoire [`examples/scripts_demonstration/`](examples/scripts_demonstration/).
*   **Notebooks illustratifs :** Un tutoriel sous forme de notebook, illustrant un flux d'intégration typique avec l'API et les agents logiques, est disponible ici : [`examples/notebooks/api_logic_tutorial.ipynb`](examples/notebooks/api_logic_tutorial.ipynb:0).
*   **Test de l'API Web :** Un script de test dédié pour l'API web, montrant comment interroger ses différents endpoints, se trouve dans [`libs/web_api/test_api.py`](libs/web_api/test_api.py:0).

## Guide pour le projet Interface Web

> **Étudiants :** erwin.rodrigues, robin.de-bastos

### Objectif du projet

Développer une interface web moderne et intuitive qui permet aux utilisateurs d'interagir avec le moteur d'analyse argumentative via l'API existante. L'interface doit permettre la saisie de textes, l'affichage des résultats d'analyse, la visualisation de frameworks de Dung et l'interaction avec ces visualisations.

### Démarrage rapide

1. **Configuration de l'environnement**

   ```bash
   # Démarrer l'API (nécessaire pour le développement)
   cd services/web_api
   pip install -r requirements.txt
   python app.py
   # L'API sera disponible sur http://localhost:5000
   
   # Créer un nouveau projet React
   npx create-react-app interface-argumentative
   cd interface-argumentative
   npm install axios d3 cytoscape react-bootstrap
   npm start
   # L'interface sera disponible sur http://localhost:3000
   ```

2. **Structure recommandée du projet**

   ```
   interface-argumentative/
   ├── src/
   │   ├── components/
   │   │   ├── argument/
   │   │   │   ├── ArgumentEditor.jsx
   │   │   │   ├── ArgumentViewer.jsx
   │   │   │   └── ValidationPanel.jsx
   │   │   ├── visualization/
   │   │   │   ├── ArgumentGraph.jsx
   │   │   │   ├── FallacyHighlighter.jsx
   │   │   │   └── FrameworkVisualizer.jsx
   │   │   └── ui/
   │   │       ├── ConfidenceMeter.jsx
   │   │       └── NavigationBar.jsx
   │   ├── hooks/
   │   │   ├── useArgumentAPI.js
   │   │   ├── useFallacyDetection.js
   │   │   └── useFrameworkBuilder.js
   │   ├── services/
   │   │   └── api.js
   │   ├── pages/
   │   │   ├── AnalysisPage.jsx
   │   │   ├── FrameworkPage.jsx
   │   │   └── HomePage.jsx
   │   └── App.js
   └── public/
   ```

3. **Intégration avec l'API**

   Créez un service API dans `src/services/api.js` :

   ```javascript
   import axios from 'axios';

   const API_BASE_URL = 'http://localhost:5000/api';

   export const analyzeText = async (text, options = {}) => {
     try {
       const response = await axios.post(`${API_BASE_URL}/analyze`, {
         text,
         options
       });
       return response.data;
     } catch (error) {
       console.error('Error analyzing text:', error);
       throw error;
     }
   };

   export const detectFallacies = async (text, options = {}) => {
     try {
       const response = await axios.post(`${API_BASE_URL}/fallacies`, {
         text,
         options
       });
       return response.data;
     } catch (error) {
       console.error('Error detecting fallacies:', error);
       throw error;
     }
   };

   export const buildFramework = async (arguments, options = {}) => {
     try {
       const response = await axios.post(`${API_BASE_URL}/framework`, {
         arguments,
         options
       });
       return response.data;
     } catch (error) {
       console.error('Error building framework:', error);
       throw error;
     }
   };
   ```

4. **Création d'un hook personnalisé**

   Créez un hook React dans `src/hooks/useArgumentAPI.js` :

   ```javascript
   import { useState, useCallback } from 'react';
   import { analyzeText } from '../services/api';

   export const useArgumentAPI = () => {
     const [loading, setLoading] = useState(false);
     const [error, setError] = useState(null);
     const [result, setResult] = useState(null);

     const analyze = useCallback(async (text, options = {}) => {
       setLoading(true);
       setError(null);
       try {
         const data = await analyzeText(text, options);
         setResult(data);
         return data;
       } catch (err) {
         setError(err.message || 'An error occurred during analysis');
         return null;
       } finally {
         setLoading(false);
       }
     }, []);

     return { analyze, loading, error, result };
   };
   ```

5. **Exemple de composant d'analyse**

   Créez un composant dans `src/components/argument/ArgumentEditor.jsx` :

   ```jsx
   import React, { useState } from 'react';
   import { useArgumentAPI } from '../../hooks/useArgumentAPI';
   import { Button, Form, Spinner, Alert } from 'react-bootstrap';
   import ValidationPanel from './ValidationPanel';

   const ArgumentEditor = () => {
     const [text, setText] = useState('');
     const { analyze, loading, error, result } = useArgumentAPI();

     const handleSubmit = async (e) => {
       e.preventDefault();
       if (text.trim()) {
         await analyze(text);
       }
     };

     return (
       <div className="argument-editor">
         <h2>Analyse d'argument</h2>
         <Form onSubmit={handleSubmit}>
           <Form.Group>
             <Form.Label>Entrez votre texte argumentatif :</Form.Label>
             <Form.Control
               as="textarea"
               rows={5}
               value={text}
               onChange={(e) => setText(e.target.value)}
               placeholder="Exemple : Tous les chats sont des animaux. Félix est un chat. Donc Félix est un animal."
             />
           </Form.Group>
           <Button 
             type="submit" 
             variant="primary" 
             disabled={loading || !text.trim()}
           >
             {loading ? (
               <>
                 <Spinner animation="border" size="sm" /> Analyse en cours...
               </>
             ) : (
               'Analyser'
             )}
           </Button>
         </Form>

         {error && <Alert variant="danger" className="mt-3">{error}</Alert>}

         {result && <ValidationPanel result={result} />}
       </div>
     );
   };

   export default ArgumentEditor;
   ```

### Ressources spécifiques

- **Exemples de code** : Consultez `docs/projets/sujets/aide/interface-web/exemples-react/` pour des composants prêts à l'emploi
- **Guide de démarrage rapide** : `docs/projets/sujets/aide/interface-web/DEMARRAGE_RAPIDE.md`
- **Documentation de l'API** : Accessible via `http://localhost:5000/api/endpoints` une fois l'API démarrée
*   **Exemples d'intégration API pour le frontend :** Bien que le guide se concentre sur React, les principes d'appel à l'API sont similaires pour d'autres frameworks. Pour un exemple Python d'appel à l'API, voir [`examples/logic_agents/api_integration_example.py`](examples/logic_agents/api_integration_example.py:0). Les tests d'intégration comme [`tests/integration/test_logic_agents_integration.py`](tests/integration/test_logic_agents_integration.py:0) peuvent aussi vous donner des idées sur les flux de données.

### Fonctionnalités à implémenter

1. **Éditeur d'arguments**
   - Zone de texte pour saisir des arguments
   - Options d'analyse configurables
   - Affichage des résultats d'analyse

2. **Visualisation de sophismes**
   - Mise en évidence des sophismes détectés dans le texte
   - Affichage des explications et des suggestions
   - Filtrage par type et sévérité

3. **Constructeur de frameworks**
   - Interface pour créer et éditer des arguments
   - Définition des relations d'attaque
   - Calcul et visualisation des extensions

4. **Visualisation interactive**
   - Graphe interactif des frameworks de Dung
   - Zoom, pan et sélection d'éléments
   - Différentes options de layout

## Guide pour le projet Serveur MCP

> **Étudiants :** enguerrand.turcat, titouan.verhille

### Objectif du projet

Développer un serveur MCP (Model Context Protocol) qui expose les fonctionnalités d'analyse argumentative aux LLMs comme Claude et GPT. Le serveur doit permettre aux modèles d'accéder aux outils d'analyse de sophismes, de validation d'arguments et de construction de frameworks de Dung via le protocole standardisé MCP.

### Démarrage rapide

1. **Configuration de l'environnement**

   ```bash
   # Créer un environnement virtuel
   python -m venv venv
   source venv/bin/activate  # ou venv\Scripts\activate sur Windows
   
   # Installer les dépendances
   pip install jpype1 flask pydantic websockets
   
   # Télécharger TweetyProject
   mkdir -p libs
   wget -O libs/tweety-full-1.28-with-dependencies.jar "https://tweetyproject.org/downloads/tweety-full-1.28-with-dependencies.jar"
   ```

2. **Structure recommandée du projet**

   ```
   mcp-server/
   ├── src/
   │   ├── tools/
   │   │   ├── fallacy_detection.py
   │   │   ├── framework_builder.py
   │   │   └── validation_tools.py
   │   ├── resources/
   │   │   ├── fallacy_taxonomy.py
   │   │   └── framework_examples.py
   │   ├── bridges/
   │   │   └── tweety_bridge.py
   │   ├── session/
   │   │   └── session_manager.py
   │   └── server.py
   ├── config.json
   ├── requirements.txt
   └── README.md
   ```

3. **Implémentation du bridge TweetyProject**

   Créez un bridge dans `src/bridges/tweety_bridge.py` :

   ```python
   import jpype
   import jpype.imports
   from jpype.types import *
   import threading
   from typing import Dict, List, Any, Optional

   class TweetyProjectBridge:
       """Bridge pour l'intégration TweetyProject via JPype"""
       
       def __init__(self, jar_path: str):
           self.jar_path = jar_path
           self.jvm_started = False
           self.class_cache = {}
           self.lock = threading.RLock()
           
       def initialize_jvm(self) -> bool:
           """Initialise la JVM avec TweetyProject"""
           if self.jvm_started:
               return True
               
           try:
               if not jpype.isJVMStarted():
                   jpype.startJVM(
                       jpype.getDefaultJVMPath(),
                       f"-Djava.class.path={self.jar_path}",
                       "-Xmx2g"
                   )
               
               # Import des classes principales
               self._load_core_classes()
               self.jvm_started = True
               return True
               
           except Exception as e:
               print(f"Erreur initialisation JVM: {e}")
               return False
       
       def _load_core_classes(self):
           """Charge les classes TweetyProject essentielles"""
           with self.lock:
               # Logique propositionnelle
               self.class_cache['PlParser'] = jpype.JClass(
                   "org.tweetyproject.logics.pl.parser.PlParser"
               )
               self.class_cache['PlBeliefSet'] = jpype.JClass(
                   "org.tweetyproject.logics.pl.syntax.PlBeliefSet"
               )
               
               # Argumentation
               self.class_cache['DungTheory'] = jpype.JClass(
                   "org.tweetyproject.arg.dung.syntax.DungTheory"
               )
               self.class_cache['Argument'] = jpype.JClass(
                   "org.tweetyproject.arg.dung.syntax.Argument"
               )
               self.class_cache['Attack'] = jpype.JClass(
                   "org.tweetyproject.arg.dung.syntax.Attack"
               )
   ```

4. **Implémentation d'un outil MCP**

   Créez un outil dans `src/tools/fallacy_detection.py` :

   ```python
   from typing import Dict, List, Any, Optional

   class FallacyDetectionTool:
       """Outil MCP pour la détection de sophismes"""
       
       def __init__(self):
           self.name = "analyze_fallacy"
           self.description = "Analyse un texte pour détecter les sophismes"
           self.input_schema = {
               "type": "object",
               "properties": {
                   "text": {"type": "string", "description": "Texte à analyser"},
                   "language": {"type": "string", "enum": ["fr", "en"], "default": "fr"},
                   "confidence_threshold": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.5}
               },
               "required": ["text"]
           }
       
       async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
           """Exécute l'analyse de sophismes"""
           text = params.get("text", "")
           language = params.get("language", "fr")
           threshold = params.get("confidence_threshold", 0.5)
           
           # Intégration avec le moteur d'analyse existant
           # TODO: Implémenter l'intégration réelle
           
           # Exemple de résultat
           return {
               "fallacies": [
                   {
                       "type": "hasty_generalization",
                       "name": "Généralisation hâtive",
                       "description": "Tirer une conclusion générale à partir d'un échantillon insuffisant",
                       "severity": 0.8,
                       "confidence": 0.9,
                       "location": {"start": 10, "end": 45},
                       "explanation": "L'argument généralise à partir d'un cas particulier"
                   }
               ],
               "overall_quality": 0.6,
               "suggestions": ["Considérer un échantillon plus large"]
           }
   ```

5. **Implémentation du serveur MCP**

   Créez le serveur dans `src/server.py` :

   ```python
   #!/usr/bin/env python3
   import asyncio
   import json
   import sys
   from typing import Dict, Any, List, Optional
   import logging

   # Configuration du logging
   logging.basicConfig(level=logging.INFO)
   logger = logging.getLogger("MCPServer")

   class MCPServer:
       """Serveur MCP pour l'analyse argumentative"""
       
       def __init__(self, config_path: str):
           self.config = self._load_config(config_path)
           self.tools = {}
           self.resources = {}
           self.running = False
           
       def _load_config(self, config_path: str) -> Dict[str, Any]:
           """Charge la configuration du serveur"""
           with open(config_path, 'r') as f:
               return json.load(f)
           
       async def initialize(self):
           """Initialise tous les composants du serveur"""
           logger.info("Initialisation du serveur MCP argumentatif...")
           
           # Initialisation des outils
           from tools.fallacy_detection import FallacyDetectionTool
           from tools.framework_builder import FrameworkBuilderTool
           
           fallacy_tool = FallacyDetectionTool()
           framework_tool = FrameworkBuilderTool()
           
           self.tools[fallacy_tool.name] = fallacy_tool
           self.tools[framework_tool.name] = framework_tool
           
           logger.info(f"Outils enregistrés: {list(self.tools.keys())}")
           
       async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
           """Gestionnaire principal des requêtes MCP"""
           try:
               method = request.get("method")
               params = request.get("params", {})
               request_id = request.get("id")
               
               # Gestion des différents types de requêtes
               if method == "initialize":
                   return self._create_response(request_id, {
                       "protocolVersion": "2024-05-01",
                       "capabilities": {
                           "tools": True,
                           "resources": True,
                           "prompts": False
                       },
                       "serverInfo": {
                           "name": "argumentative-analysis-server",
                           "version": "1.0.0"
                       }
                   })
               
               elif method == "tools/list":
                   return self._create_response(request_id, {
                       "tools": [
                           {
                               "name": tool.name,
                               "description": tool.description,
                               "inputSchema": tool.input_schema
                           }
                           for tool in self.tools.values()
                       ]
                   })
               
               elif method == "tools/call":
                   tool_name = params.get("name")
                   tool_args = params.get("arguments", {})
                   
                   if tool_name not in self.tools:
                       return self._create_error_response(
                           request_id, -32601, f"Outil inconnu: {tool_name}"
                       )
                   
                   # Exécution de l'outil
                   tool = self.tools[tool_name]
                   result = await tool.execute(tool_args)
                   
                   return self._create_response(request_id, result)
                   
               else:
                   return self._create_error_response(
                       request_id, -32601, f"Méthode inconnue: {method}"
                   )
                   
           except Exception as e:
               logger.error(f"Erreur lors du traitement de la requête: {e}")
               return self._create_error_response(
                   request.get("id"), -32603, f"Erreur interne: {str(e)}"
               )
       
       def _create_response(self, request_id: Any, result: Any) -> Dict[str, Any]:
           """Crée une réponse MCP standard"""
           return {
               "jsonrpc": "2.0",
               "id": request_id,
               "result": result
           }
       
       def _create_error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
           """Crée une réponse d'erreur MCP"""
           return {
               "jsonrpc": "2.0",
               "id": request_id,
               "error": {
                   "code": code,
                   "message": message
               }
           }
       
       async def run(self):
           """Lance le serveur MCP"""
           await self.initialize()
           self.running = True
           
           logger.info("Serveur MCP en écoute...")
           
           # Boucle principale de traitement des requêtes
           while self.running:
               try:
                   # Lecture depuis stdin (protocole stdio MCP)
                   line = await asyncio.get_event_loop().run_in_executor(
                       None, sys.stdin.readline
                   )
                   
                   if not line:
                       break
                   
                   # Parsing de la requête JSON-RPC
                   try:
                       request = json.loads(line.strip())
                   except json.JSONDecodeError as e:
                       logger.error(f"Requête JSON invalide: {e}")
                       continue
                   
                   # Traitement de la requête
                   response = await self.handle_request(request)
                   
                   # Envoi de la réponse
                   print(json.dumps(response), flush=True)
                   
               except KeyboardInterrupt:
                   logger.info("Arrêt du serveur demandé")
                   break
               except Exception as e:
                   logger.error(f"Erreur dans la boucle principale: {e}")

   # Point d'entrée principal
   async def main():
       """Point d'entrée principal du serveur"""
       import argparse
       
       parser = argparse.ArgumentParser(description="Serveur MCP pour l'analyse argumentative")
       parser.add_argument("--config", default="config.json", help="Fichier de configuration JSON")
       args = parser.parse_args()
       
       # Création et lancement du serveur
       server = MCPServer(args.config)
       
       try:
           await server.run()
       except KeyboardInterrupt:
           pass

   if __name__ == "__main__":
       asyncio.run(main())
   ```

### Ressources spécifiques

- **Documentation MCP** : [Model Context Protocol](https://github.com/anthropics/anthropic-cookbook/tree/main/model_context_protocol)
- **Exemples d'intégration** : `docs/projets/sujets/2.5.3_Developpement_Serveur_MCP_Analyse_Argumentative.md`
- **Documentation TweetyProject** : [TweetyProject](https://tweetyproject.org/doc/)
*   **Exemples d'utilisation des agents logiques :** Pour comprendre comment interagir avec le moteur d'analyse que votre serveur MCP exposera, consultez le guide [`docs/guides/utilisation_agents_logiques.md`](docs/guides/utilisation_agents_logiques.md:0).
*   **Tests d'intégration du moteur :** Les fichiers dans [`tests/integration/`](tests/integration/) (par exemple, [`tests/integration/test_logic_agents_integration.py`](tests/integration/test_logic_agents_integration.py:0)) montrent comment les composants du moteur sont testés ensemble.

### Fonctionnalités à implémenter

1. **Outils MCP**
   - Analyse de sophismes
   - Validation d'arguments
   - Construction de frameworks de Dung
   - Analyse de frameworks

2. **Ressources MCP**
   - Taxonomie de sophismes
   - Exemples de frameworks
   - Base d'arguments annotés

3. **Intégration avec les LLMs**
   - Configuration pour Claude Desktop
   - Intégration avec Roo
   - Support pour Semantic Kernel

4. **Gestion des sessions**
   - Persistance des analyses
   - Contexte conversationnel
   - Gestion d'état

## Ressources communes

### Documentation du moteur d'analyse

Le moteur d'analyse argumentative est organisé en plusieurs composants :

1. **Agents spécialisés**
   - `InformalAgent` : Analyse informelle des arguments
   - `PLAgent` : Analyse en logique propositionnelle
   - `PMAgent` : Gestion des modèles probabilistes

2. **Outils d'analyse**
   - `ComplexFallacyAnalyzer` : Détection avancée de sophismes
   - `ContextualFallacyAnalyzer` : Analyse contextuelle
   - `FallacySeverityEvaluator` : Évaluation de la sévérité des sophismes

3. **Orchestration**
   - `OperationalManager` : Coordination des opérations de bas niveau
   - `TacticalCoordinator` : Coordination des analyses tactiques

### API Web

L'API web expose les fonctionnalités suivantes :

1. **Endpoints**
   - `GET /api/health` : Vérification de l'état de l'API
   - `POST /api/analyze` : Analyse complète d'un texte
   - `POST /api/validate` : Validation logique d'un argument
   - `POST /api/fallacies` : Détection de sophismes
   - `POST /api/framework` : Construction de frameworks de Dung
   - `GET /api/endpoints` : Documentation des endpoints

2. **Modèles de données**
   - `AnalysisRequest` / `AnalysisResponse`
   - `ValidationRequest` / `ValidationResponse`
   - `FallacyRequest` / `FallacyResponse`
   - `FrameworkRequest` / `FrameworkResponse`

### Guides et Exemples Complémentaires

*   **Guide du développeur :** Pour une vue d'ensemble plus large des pratiques de développement et de l'architecture, consultez le [`docs/guides/guide_developpeur.md`](docs/guides/guide_developpeur.md:0).
*   **Utilisation des agents logiques :** Un guide détaillé sur l'utilisation directe des agents logiques est disponible : [`docs/guides/utilisation_agents_logiques.md`](docs/guides/utilisation_agents_logiques.md:0).
*   **Exemple d'intégration API :** Un script Python illustrant l'appel à l'API se trouve dans [`examples/logic_agents/api_integration_example.py`](examples/logic_agents/api_integration_example.py:0).
*   **Notebook tutoriel :** Pour un exemple interactif d'utilisation de l'API et des agents, voir [`examples/notebooks/api_logic_tutorial.ipynb`](examples/notebooks/api_logic_tutorial.ipynb:0).
*   **Script de test de l'API :** Pour voir comment tester les différents endpoints de l'API, référez-vous à [`libs/web_api/test_api.py`](libs/web_api/test_api.py:0).

## Processus de développement

### Workflow recommandé

1. **Planification**
   - Comprendre les exigences du projet
   - Identifier les composants à développer
   - Créer un plan de développement

2. **Développement**
   - Suivre une approche itérative
   - Commencer par les fonctionnalités de base
   - Ajouter progressivement des fonctionnalités avancées

3. **Tests**
   - Tester chaque composant individuellement
   - Effectuer des tests d'intégration
   - Valider les fonctionnalités avec des cas d'utilisation réels
    *   Consultez les tests d'intégration existants dans [`tests/integration/`](tests/integration/) pour des exemples, notamment [`tests/integration/test_logic_agents_integration.py`](tests/integration/test_logic_agents_integration.py:0) et le répertoire [`tests/integration/jpype_tweety/`](tests/integration/jpype_tweety/).

4. **Documentation**
   - Documenter le code
   - Créer des guides d'utilisation
   - Fournir des exemples

### Réunions et suivi

Des réunions régulières sont prévues pour suivre l'avancement des projets :

- **Réunions d'introduction** : Présentation détaillée des projets et de l'architecture
- **Suivis hebdomadaires** : Point sur l'avancement, discussion des problèmes rencontrés
- **Démonstrations** : Présentation des fonctionnalités développées

## FAQ

### Questions générales

**Q: Comment accéder au moteur d'analyse argumentative ?**  
R: Le moteur est accessible via l'API web ou directement via les imports Python depuis le package `argumentation_analysis`.

**Q: Comment tester les fonctionnalités sans développer l'interface complète ?**  
R: Vous pouvez utiliser des outils comme Postman ou curl pour tester l'API web directement.

### Questions spécifiques à l'interface web

**Q: Comment gérer les erreurs de l'API ?**  
R: L'API retourne des réponses d'erreur standardisées que vous pouvez capturer et afficher dans l'interface.

**Q: Comment visualiser les frameworks de Dung ?**  
R: Vous pouvez utiliser des bibliothèques comme D3.js ou Cytoscape.js pour créer des visualisations interactives.

### Questions spécifiques au serveur MCP

**Q: Comment tester le serveur MCP ?**  
R: Vous pouvez utiliser Claude Desktop ou Roo pour tester le serveur MCP une fois configuré.

**Q: Comment gérer les sessions MCP ?**  
R: Le protocole MCP prévoit des mécanismes de gestion de session que vous devrez implémenter dans votre serveur.

---

Pour toute question supplémentaire, n'hésitez pas à contacter l'équipe encadrante ou à consulter la documentation disponible.