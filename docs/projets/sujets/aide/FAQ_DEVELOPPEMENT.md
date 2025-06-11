# FAQ Développement - Projet Analyse d'Arguments

Cette FAQ vise à répondre aux questions courantes que vous pourriez rencontrer lors du développement et de la contribution au projet d'analyse d'arguments.

## Table des Matières
- [Documentation Générale et Guides](#documentation-générale-et-guides)
- [API Web](#api-web)
- [Moteur d'analyse argumentative](#moteur-danalyse-argumentative)
- [Interface Web](#interface-web)
- [Tests et Validation](#tests-et-validation)
- [Déploiement et Environnement](#déploiement-et-environnement)
- [Contribution et Bonnes Pratiques](#contribution-et-bonnes-pratiques)

---

## Documentation Générale et Guides

**Q: Où puis-je trouver la documentation principale du projet ?**
**R:** La documentation principale se trouve dans le dossier `docs/`. Le `README.md` à la racine contient également des informations importantes.

**Q: Quels sont les principaux guides et documents de référence ?**
**R:** Le projet dispose de plusieurs documents clés pour vous aider à démarrer et à approfondir :
-   **[`README.md`](README.md:0) (à la racine)** : Fournit une vue d'ensemble du projet, ses objectifs, et des instructions de démarrage rapide. C'est le premier fichier à consulter.
-   **[`GETTING_STARTED.md`](GETTING_STARTED.md:0)** : Guide de démarrage rapide, complémentaire au README principal.
-   **[`GUIDE_INSTALLATION_ETUDIANTS.md`](GUIDE_INSTALLATION_ETUDIANTS.md:0)** : Instructions détaillées pour l'installation de l'environnement de développement, spécifiquement pour les étudiants.
-   **Répertoire [`docs/guides/`](docs/guides/:0)** : Contient des guides thématiques plus approfondis :
    -   [`docs/guides/guide_developpeur.md`](docs/guides/guide_developpeur.md:0) : Informations essentielles pour les développeurs contribuant au projet (architecture, conventions, tests, etc.).
    -   [`docs/guides/guide_utilisation.md`](docs/guides/guide_utilisation.md:0) : Comment utiliser les fonctionnalités principales de l'application.
    -   [`docs/guides/integration_api_web.md`](docs/guides/integration_api_web.md:0) : Détails sur l'utilisation et l'extension de l'API Web.
    -   [`docs/guides/utilisation_agents_logiques.md`](docs/guides/utilisation_agents_logiques.md:0) : Explications sur l'utilisation des agents logiques et du moteur d'argumentation.
    -   D'autres guides spécifiques peuvent s'y trouver (par exemple, sur le déploiement, la contribution, etc.).
-   **[`docs/structure_projet.md`](docs/structure_projet.md:0)** : Décrit l'organisation des dossiers et des fichiers au sein du projet, vous aidant à naviguer dans le code source.
-   **[`docs/projets/sujets/aide/FAQ_DEVELOPPEMENT.md`](docs/projets/sujets/aide/FAQ_DEVELOPPEMENT.md:0) (ce fichier)** : Foire Aux Questions pour les problèmes courants de développement.
-   **[`services/README.md`](services/README.md:0)** : Documentation spécifique au(x) service(s) backend, notamment l'API Web.
-   Les `README.md` présents dans les sous-répertoires (par exemple, [`examples/README.md`](examples/README.md:0), [`scripts/README.md`](scripts/README.md:0), [`tests/README.md`](tests/README.md:0)) fournissent un contexte pour ces parties spécifiques du projet.

**Q: Comment comprendre rapidement l'architecture du projet ?**
**R:** Consultez `docs/architecture.md` (s'il existe) et `docs/structure_projet.md`. Le code est organisé en modules logiques (API, moteur d'analyse, interface).

---

## API Web

**Q: Comment démarrer l'API web ?**
**R:** Pour démarrer l'API web :
1.  Assurez-vous que votre environnement Python est correctement configuré. Vous pouvez utiliser le script [`setup_project_env.ps1`](setup_project_env.ps1:0) pour initialiser l'environnement du projet si nécessaire.
2.  Naviguez vers le répertoire de l'API et installez les dépendances :
    ```bash
    cd services/web_api
    pip install -r requirements.txt
    ```
3.  Démarrez l'API. La méthode recommandée (voir [`services/README.md#démarrage-rapide`](services/README.md:76)) est :
    ```bash
    python start_api.py
    ```
    Alternativement, vous pouvez utiliser :
    ```bash
    python app.py
    ```
L'API sera alors disponible sur http://localhost:5000. Des exemples de tests et d'utilisation de l'API se trouvent dans [`services/web_api/tests/`](services/web_api/tests/) et [`examples/logic_agents/api_integration_example.py`](examples/logic_agents/api_integration_example.py:0).

**Q: Comment tester les endpoints de l'API ?**
**R:** Plusieurs options :
- Utilisez l'endpoint `/api/endpoints` pour une documentation interactive des endpoints disponibles.
- Utilisez des outils comme Postman ou `curl` pour envoyer des requêtes manuelles. Des exemples de commandes `curl` sont disponibles dans le guide [`services/README.md#vérification-du-fonctionnement`](services/README.md:100).
- Exécutez les tests automatisés situés dans [`services/web_api/tests/`](services/web_api/tests/). Vous y trouverez des fichiers comme [`test_endpoints.py`](services/web_api/tests/test_endpoints.py:0) et [`test_services.py`](services/web_api/tests/test_services.py:0) qui couvrent différents aspects de l'API. Le guide [`services/README.md#tests-et-validation`](services/README.md:221) explique comment les exécuter.
- Consultez l'exemple d'intégration [`examples/logic_agents/api_integration_example.py`](examples/logic_agents/api_integration_example.py:0) pour voir comment interagir avec l'API depuis un script Python.

**Q: L'API retourne une erreur CORS, que faire ?**
**R:** Assurez-vous que l'origine de votre requête frontend (ex: `http://localhost:3000`) est autorisée dans la configuration CORS de l'API Flask (`app.py` ou configuration dédiée).

**Q: Comment étendre l'API avec de nouveaux endpoints ?**
**R:** Pour ajouter un nouvel endpoint, suivez ces étapes (détaillées dans [`services/README.md#développement-et-extension`](services/README.md:191)) :
1.  Créez votre logique métier dans un nouveau fichier de service, par exemple [`services/web_api/services/mon_nouveau_service.py`](services/web_api/services/mon_nouveau_service.py:0). Inspirez-vous de services existants comme [`services/web_api/services/analysis_service.py`](services/web_api/services/analysis_service.py:0).
2.  Définissez les modèles de données (requête et réponse) dans [`services/web_api/models/request_models.py`](services/web_api/models/request_models.py:0) et [`services/web_api/models/response_models.py`](services/web_api/models/response_models.py:0) en utilisant Pydantic.
3.  Ajoutez la nouvelle route Flask dans [`services/web_api/app.py`](services/web_api/app.py:0), en liant l'URL à votre service.
4.  Documentez le nouvel endpoint dans la fonction `list_endpoints()` (généralement dans `app.py` ou un module de documentation dédié) pour qu'il apparaisse sur `/api/endpoints`.
5.  N'oubliez pas d'ajouter des tests pour votre nouveau service et endpoint dans [`services/web_api/tests/`](services/web_api/tests/).
Pour plus de détails, consultez le guide [`docs/guides/integration_api_web.md`](docs/guides/integration_api_web.md:0).

---

## Moteur d'analyse argumentative

**Q: Comment accéder au moteur d'analyse depuis mon code ?**
**R:** Vous pouvez accéder au moteur de plusieurs manières :
1.  **Via l'API web** (recommandé pour l'interface web et les clients externes). Consultez la section [API Web](#api-web) de cette FAQ et le fichier [`services/README.md`](services/README.md:0).
2.  **Directement via les imports Python** (utile pour le développement du serveur MCP, des scripts, ou des tests). Voici un exemple d'import :
    ```python
    from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
    from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer
    # Et d'autres composants du moteur...
    ```
    Vous trouverez de nombreux exemples d'utilisation directe dans :
    - Les scripts du dossier [`examples/logic_agents/`](examples/logic_agents/) (par exemple, [`propositional_logic_example.py`](examples/logic_agents/propositional_logic_example.py:0), [`first_order_logic_example.py`](examples/logic_agents/first_order_logic_example.py:0)).
    - Les scripts de démonstration comme [`examples/scripts_demonstration/demo_tweety_interaction_simple.py`](examples/scripts_demonstration/demo_tweety_interaction_simple.py:0) et [`examples/scripts_demonstration/demonstration_epita.py`](examples/scripts_demonstration/demonstration_epita.py:0).
    - Les tests unitaires et d'intégration dans le dossier [`tests/`](tests/).
    Le guide [`docs/guides/utilisation_agents_logiques.md`](docs/guides/utilisation_agents_logiques.md:0) fournit également des informations utiles.

**Q: Comment fonctionne la détection de sophismes ?**
**R:** La détection de sophismes utilise une combinaison d'approches, notamment :
1.  Analyse par reconnaissance de patrons linguistiques.
2.  Analyse structurelle des arguments.
3.  Analyse contextuelle pour comprendre les nuances.
4.  Évaluation de la sévérité du sophisme détecté.

Ces analyses sont principalement effectuées par des composants tels que `ComplexFallacyAnalyzer` et `ContextualFallacyAnalyzer`. Pour voir comment ces analyseurs sont utilisés et testés, vous pouvez consulter :
- Les tests unitaires spécifiques, par exemple :
    - [`tests/agents/tools/analysis/enhanced/test_enhanced_complex_fallacy_analyzer.py`](tests/agents/tools/analysis/enhanced/test_enhanced_complex_fallacy_analyzer.py:0)
    - [`tests/agents/tools/analysis/enhanced/test_enhanced_contextual_fallacy_analyzer.py`](tests/agents/tools/analysis/enhanced/test_enhanced_contextual_fallacy_analyzer.py:0)
- Des exemples d'utilisation dans les scripts de démonstration ou les tests d'intégration qui font appel à la détection de sophismes.
Le guide [`docs/guides/guide_developpeur.md`](docs/guides/guide_developpeur.md:0) peut également contenir des sections pertinentes sur l'architecture de ces composants.

**Q: Comment sont calculées les extensions des frameworks de Dung ?**
**R:** Les extensions des frameworks d'argumentation de Dung sont calculées à l'aide de TweetyProject, qui implémente diverses sémantiques. Les principales utilisées sont :
- **Grounded Semantics** : Fournit une extension unique, généralement calculée avec `SimpleGroundedReasoner`.
- **Preferred Semantics** : Peut fournir plusieurs extensions maximales (au sens de l'inclusion), calculées avec `SimplePreferredReasoner`.
- **Stable Semantics** : Fournit des extensions qui attaquent tout argument en dehors d'elles-mêmes, calculées avec `SimpleStableReasoner`.

Le service `FrameworkService` (exposé via l'API Web, voir [`services/web_api/services/framework_service.py`](services/web_api/services/framework_service.py:0) si le fichier existe) encapsule ces calculs.
Pour des exemples concrets d'utilisation de ces reasoners avec TweetyProject en Python :
- Consultez les scripts dans [`examples/logic_agents/`](examples/logic_agents/), notamment ceux qui manipulent des `DungTheory` (par exemple, [`examples/logic_agents/combined_logic_example.py`](examples/logic_agents/combined_logic_example.py:0)).
- Le script [`examples/scripts_demonstration/demo_tweety_interaction_simple.py`](examples/scripts_demonstration/demo_tweety_interaction_simple.py:0) montre également des interactions basiques avec Tweety.
- Le guide [`docs/guides/utilisation_agents_logiques.md`](docs/guides/utilisation_agents_logiques.md:0) et les exemples de logique spécifiques (ex: [`docs/guides/exemples_logique_propositionnelle.md`](docs/guides/exemples_logique_propositionnelle.md:0)) peuvent illustrer la construction de théories et l'interrogation.

**Q: Comment gérer les performances pour les analyses complexes ?**
**R:** La gestion des performances pour les analyses complexes est cruciale. Voici quelques pistes :
-   **Limiter la portée de l'analyse** : Utilisez les paramètres `options` de l'API ou des agents pour ne demander que les analyses strictement nécessaires.
-   **Mise en cache** : Implémentez ou utilisez un système de cache pour les résultats d'analyses coûteuses et fréquemment demandées. Le [`docs/guides/guide_developpeur.md`](docs/guides/guide_developpeur.md:0) pourrait aborder les stratégies de cache du projet.
-   **Optimisation des frameworks d'argumentation** : Pour les frameworks volumineux, limitez le nombre de sémantiques calculées ou explorez des reasoners plus performants si disponibles dans TweetyProject pour des cas spécifiques.
-   **Timeouts** : Mettez en place des timeouts pour les opérations longues afin d'éviter de bloquer le système.
-   **Traitement asynchrone** : Pour les tâches très longues, envisagez un traitement asynchrone avec un système de notification ou de récupération des résultats différée.
Des exemples de code spécifiques illustrant ces techniques peuvent se trouver dans les services de l'API (par exemple, la gestion des timeouts lors d'appels à Tweety) ou dans des scripts d'orchestration complexes. Consultez également les tests de performance s'ils existent ([`scripts/execution/run_performance_tests.py`](scripts/execution/run_performance_tests.py:0)).

---

## Interface Web

**Q: Comment gérer les appels asynchrones à l'API ?**
**R:** Utilisez `async/await` avec `fetch` ou une librairie comme `axios`. Le projet fournit des exemples concrets dans le répertoire [`docs/projets/sujets/aide/interface-web/exemples-react/`](docs/projets/sujets/aide/interface-web/exemples-react/:0).

Plus spécifiquement, le hook personnalisé [`docs/projets/sujets/aide/interface-web/exemples-react/hooks/useArgumentationAPI.js`](docs/projets/sujets/aide/interface-web/exemples-react/hooks/useArgumentationAPI.js:0) montre une gestion robuste des appels à l'API du backend, incluant la gestion des états de chargement et des erreurs. Vous pouvez vous en inspirer pour vos propres composants.

**Exemple générique avec Axios (similaire à ce que vous pourriez trouver dans le hook) :**
```javascript
import axios from 'axios';

const callApi = async (endpoint, payload) => {
  // setLoading(true); // Gérer l'état de chargement
  try {
    const response = await axios.post(`/api/${endpoint}`, payload);
    // setData(response.data); // Stocker les données
    // setError(null);
    return response.data;
  } catch (error) {
    console.error(`Erreur lors de l'appel API à ${endpoint}:`, error);
    // setError(error); // Gérer l'erreur
    throw error; // Propager l'erreur pour une gestion ultérieure
  } finally {
    // setLoading(false);
  }
};

// Utilisation
// callApi('analyze', { text: "..." }).then(data => console.log(data));
```

**Exemple générique avec `fetch` :**
```javascript
const callApiFetch = async (endpoint, payload) => {
  try {
    const response = await fetch(`/api/${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: `HTTP error! status: ${response.status}` }));
      throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Erreur lors de l'appel API à ${endpoint}:`, error);
    throw error;
  }
};
```
Consultez le [`README.md`](docs/projets/sujets/aide/interface-web/exemples-react/README.md:0) dans le dossier des exemples React pour plus de contexte sur leur utilisation.

**Q: Comment visualiser un framework de Dung avec D3.js ?**
**R:** La visualisation de graphes d'argumentation peut être complexe. L'exemple de code ci-dessous donne une base avec D3.js. Pour une intégration plus poussée et des fonctionnalités avancées (comme la construction interactive de frameworks), vous pouvez examiner le composant [`FrameworkBuilder.jsx`](docs/projets/sujets/aide/interface-web/exemples-react/FrameworkBuilder.jsx:0) disponible dans les exemples React du projet. Ce composant pourrait utiliser D3.js ou une autre librairie de visualisation de graphes.

**Exemple de base avec D3.js (conceptuel) :**
```javascript
import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

const DungFrameworkVisualizer = ({ data }) => { // data = { nodes: [{id: 'a'}, ...], links: [{source: 'a', target: 'b'}, ...] }
  const ref = useRef();

  useEffect(() => {
    if (!data || !data.nodes || !data.links || !ref.current) return;

    const svgElement = ref.current;
    const { width, height } = svgElement.getBoundingClientRect();
    const svg = d3.select(svgElement);
    svg.selectAll("*").remove(); // Nettoyer le rendu précédent

    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.links).id(d => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const link = svg.append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(data.links)
      .join("line")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", d => Math.sqrt(d.value || 2));

    const node = svg.append("g")
      .attr("class", "nodes")
      .selectAll("g") // Groupe pour cercle + texte
      .data(data.nodes)
      .join("g")
      .call(drag(simulation));

    node.append("circle")
      .attr("r", 8)
      .attr("fill", "steelblue");

    node.append("text")
      .text(d => d.id)
      .attr("x", 12)
      .attr("y", 3);

    // Ajout de marqueurs pour les flèches (optionnel)
    svg.append("defs").selectAll("marker")
      .data(["arrow"]) // Différents types de flèches si besoin
      .join("marker")
        .attr("id", String)
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 18) // Ajuster en fonction du rayon du nœud et de la flèche
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
      .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", "#999");

    link.attr("marker-end", "url(#arrow)");


    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);
      node
        .attr("transform", d => `translate(${d.x},${d.y})`);
    });

    function drag(simulation) {
      // Fonctions dragstarted, dragged, dragended (voir exemple précédent ou D3 docs)
      // ... (code pour le drag & drop)
      function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }
      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }
      function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }
      return d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended);
    }

  }, [data]);

  return (
    <svg ref={ref} style={{ width: '100%', height: '400px', border: '1px solid #ccc' }}></svg>
  );
};

export default DungFrameworkVisualizer;
```
Consultez le [`README.md`](docs/projets/sujets/aide/interface-web/exemples-react/README.md:0) et les composants comme [`FrameworkBuilder.jsx`](docs/projets/sujets/aide/interface-web/exemples-react/FrameworkBuilder.jsx:0) pour des implémentations plus complètes et adaptées au projet.

**Q: Comment mettre en évidence les sophismes dans le texte ?**
**R:** Pour mettre en évidence les sophismes, vous pouvez créer un composant React qui prend le texte original et une liste d'objets représentant les sophismes (avec leurs positions `start` et `end`, type, message, etc.). Ce composant découpera le texte et enveloppera les segments de sophismes dans des balises `<span>` stylisées.

Le projet fournit un exemple concret avec le composant [`FallacyDetector.jsx`](docs/projets/sujets/aide/interface-web/exemples-react/FallacyDetector.jsx:0) et son CSS associé [`FallacyDetector.css`](docs/projets/sujets/aide/interface-web/exemples-react/FallacyDetector.css:0). Ces fichiers montrent une implémentation fonctionnelle que vous pouvez étudier et adapter.

**Concept général (similaire à ce que vous trouverez dans `FallacyDetector.jsx`) :**
```jsx
import React from 'react';
// import './FallacyDetector.css'; // Assurez-vous d'importer le CSS

const HighlightedTextWithFallacies = ({ text, fallacies }) => {
  // fallacies: [{ start: 0, end: 10, type: "Ad Hominem", message: "Attaque personnelle", severity: "high" }]
  if (!text) return null;
  if (!fallacies || fallacies.length === 0) {
    return <p>{text}</p>;
  }

  const sortedFallacies = [...fallacies].sort((a, b) => a.start - b.start);

  let lastIndex = 0;
  const elements = [];

  sortedFallacies.forEach((fallacy, index) => {
    // Texte avant le sophisme actuel
    if (fallacy.start > lastIndex) {
      elements.push(text.substring(lastIndex, fallacy.start));
    }
    // Le sophisme lui-même
    elements.push(
      <span
        key={`fallacy-${index}-${fallacy.start}`}
        className={`fallacy-highlight fallacy-type-${fallacy.type.toLowerCase().replace(/\s+/g, '-')} fallacy-severity-${fallacy.severity || 'medium'}`}
        title={`${fallacy.type}: ${fallacy.message || 'Sophisme détecté'}`}
      >
        {text.substring(fallacy.start, fallacy.end)}
      </span>
    );
    lastIndex = fallacy.end;
  });

  // Texte restant après le dernier sophisme
  if (lastIndex < text.length) {
    elements.push(text.substring(lastIndex));
  }

  return (
    <div className="highlighted-text-container">
      {elements.map((part, index) => (
        <React.Fragment key={`part-${index}`}>{part}</React.Fragment>
      ))}
    </div>
  );
};

export default HighlightedTextWithFallacies;
```
**CSS (extrait conceptuel, voir [`FallacyDetector.css`](docs/projets/sujets/aide/interface-web/exemples-react/FallacyDetector.css:0) pour l'implémentation réelle) :**
```css
/* .fallacy-highlight {
  padding: 0.1em 0.2em;
  margin: 0 0.1em;
  border-radius: 3px;
  cursor: help;
}

.fallacy-type-ad-hominem {
  background-color: rgba(255, 0, 0, 0.2);
  border-bottom: 2px solid rgba(255, 0, 0, 0.5);
}

.fallacy-severity-high {
  font-weight: bold;
} */
```
Référez-vous aux fichiers [`FallacyDetector.jsx`](docs/projets/sujets/aide/interface-web/exemples-react/FallacyDetector.jsx:0) et [`FallacyDetector.css`](docs/projets/sujets/aide/interface-web/exemples-react/FallacyDetector.css:0) pour l'implémentation détaillée et les styles utilisés dans le projet.

**Q: Comment implémenter un éditeur d'arguments avec analyse en temps réel ?**
**R:** Pour implémenter un éditeur d'arguments avec analyse en temps réel, vous combinerez un champ de texte (par exemple, `textarea`), un état React pour stocker le texte, et un `useEffect` pour déclencher l'analyse. Il est crucial d'utiliser une technique de *debounce* pour éviter de surcharger l'API à chaque frappe.

Le projet fournit des exemples pertinents dans [`docs/projets/sujets/aide/interface-web/exemples-react/`](docs/projets/sujets/aide/interface-web/exemples-react/:0) :
-   Le composant [`ArgumentAnalyzer.jsx`](docs/projets/sujets/aide/interface-web/exemples-react/ArgumentAnalyzer.jsx:0) est susceptible de contenir une telle logique.
-   Le hook [`useArgumentationAPI.js`](docs/projets/sujets/aide/interface-web/exemples-react/hooks/useArgumentationAPI.js:0) gère les appels à l'API et pourrait être utilisé par `ArgumentAnalyzer.jsx`.

**Concept général (inspiré par les composants existants) :**
```jsx
import React, { useState, useEffect, useCallback } from 'react';
// Importer le hook API et la fonction de debounce
// import { useYourApiHook } from './hooks/useArgumentationAPI'; // Adaptez le chemin
// import { debounce } from 'lodash'; // ou une implémentation maison

// Fonction de débounce (exemple simple, utilisez lodash.debounce en production)
const debounce = (func, delay) => {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(this, args), delay);
  };
};


const RealtimeArgumentEditor = () => {
  const [text, setText] = useState('');
  // const { data: analysis, error, isLoading, callApi } = useYourApiHook(); // Utilisation du hook
  const [analysis, setAnalysis] = useState(null); // Simulé si pas de hook
  const [isLoading, setIsLoading] = useState(false); // Simulé si pas de hook

  // Simuler callApi si pas de hook
  const callApi = async (endpoint, payload) => {
    setIsLoading(true);
    console.log("Appel API (simulé) pour:", payload);
    return new Promise(resolve => setTimeout(() => {
      setIsLoading(false);
      resolve({
        clarity: Math.random() > 0.5 ? 'Bonne' : 'À améliorer',
        fallacies: Math.random() > 0.3 ? [{ type: 'Ad Hominem', position: [0,5], message: "Exemple"}] : [],
        // ... autres résultats d'analyse
      });
    }, 1500));
  };


  // eslint-disable-next-line react-hooks/exhaustive-deps
  const debouncedAnalyzeText = useCallback(
    debounce(async (inputText) => {
      if (!inputText.trim()) {
        setAnalysis(null);
        return;
      }
      // setIsLoading(true); // Géré par le hook
      try {
        const result = await callApi('analyzeFullArgument', { text: inputText }); // Adaptez l'endpoint
        setAnalysis(result);
      } catch (apiError) {
        console.error("Erreur d'analyse:", apiError);
        setAnalysis({ error: "Impossible d'analyser le texte.", details: apiError.message });
      }
      // setIsLoading(false); // Géré par le hook
    }, 750), // Délai de débounce (e.g., 750ms)
    [callApi] // Dépendance au callApi du hook
  );

  useEffect(() => {
    debouncedAnalyzeText(text);
  }, [text, debouncedAnalyzeText]);

  const handleTextChange = (e) => {
    setText(e.target.value);
  };

  return (
    <div className="argument-editor-container">
      <textarea
        value={text}
        onChange={handleTextChange}
        placeholder="Écrivez votre argument ici pour une analyse en temps réel..."
        rows={10}
        className="argument-textarea" // Pour le style
      />
      {isLoading && <p className="loading-message">Analyse en cours...</p>}
      {/* {error && <p className="error-message">Erreur: {error.message}</p>} */}
      {analysis && !isLoading && (
        <div className="analysis-results">
          <h4>Résultats de l'analyse :</h4>
          {analysis.error && <p style={{color: 'red'}}>{analysis.error}</p>}
          {!analysis.error && (
            <>
              <p>Clarté : {analysis.clarity || 'N/A'}</p>
              <p>Sophismes détectés : {analysis.fallacies?.length || 0}</p>
              {analysis.fallacies?.map((f, i) => (
                <div key={i} className="fallacy-item">
                  - {f.type} (positions: {f.position?.join('-') || 'N/A'}): {f.message}
                </div>
              ))}
              {/* Afficher d'autres résultats d'analyse ici */}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default RealtimeArgumentEditor;
```
Pour une implémentation complète et stylisée, référez-vous à [`ArgumentAnalyzer.jsx`](docs/projets/sujets/aide/interface-web/exemples-react/ArgumentAnalyzer.jsx:0), [`ArgumentAnalyzer.css`](docs/projets/sujets/aide/interface-web/exemples-react/ArgumentAnalyzer.css:0), et au hook [`useArgumentationAPI.js`](docs/projets/sujets/aide/interface-web/exemples-react/hooks/useArgumentationAPI.js:0).

---

## Tests et Validation

**Q: Comment lancer les tests unitaires ?**
**R:** Pour lancer les tests unitaires, utilisez la commande suivante à la racine du projet :
```bash
pytest tests/unit
```
Assurez-vous que votre environnement est correctement configuré (voir [`setup_project_env.ps1`](setup_project_env.ps1:0) ou [`setup_project_env.sh`](setup_project_env.sh:0)) et que les dépendances de test sont installées (souvent incluses dans `requirements.txt` ou un fichier `requirements-dev.txt`).
La configuration de `pytest` peut être trouvée dans [`pytest.ini`](pytest.ini:0).
Pour des options d'exécution alternatives ou des scripts de test spécifiques, consultez le répertoire [`scripts/testing/`](scripts/testing/). Le guide [`docs/guides/guide_developpeur.md`](docs/guides/guide_developpeur.md:0) (section Tests) peut également fournir plus de détails.

**Q: Comment lancer les tests d'intégration ?**
**R:** Pour lancer les tests d'intégration, utilisez :
```bash
pytest tests/integration
```
Ces tests peuvent avoir des dépendances externes (par exemple, une API Web en cours d'exécution pour tester les clients API) ou nécessiter une configuration d'environnement plus spécifique. Consultez le [`README.md`](tests/integration/README.md:0) dans le dossier `tests/integration` et le [`docs/guides/guide_developpeur.md`](docs/guides/guide_developpeur.md:0) pour les prérequis.
Le fichier [`pytest.ini`](pytest.ini:0) s'applique également ici.

**Q: Où trouver des exemples de tests ?**
**R:** Vous trouverez de nombreux exemples de tests dans les répertoires suivants :
-   [`tests/unit/`](tests/unit/) : Pour les tests unitaires ciblant des fonctions ou classes isolées. Par exemple :
    -   Tests des analyseurs de sophismes : [`tests/agents/tools/analysis/enhanced/test_enhanced_complex_fallacy_analyzer.py`](tests/agents/tools/analysis/enhanced/test_enhanced_complex_fallacy_analyzer.py:0)
    -   Tests des utilitaires centraux : [`tests/project_core/`](tests/project_core/)
-   [`tests/integration/`](tests/integration/) : Pour les tests vérifiant l'interaction entre plusieurs composants. Par exemple :
    -   Tests des endpoints de l'API (si l'API est structurée ainsi) : `services/web_api/tests/test_endpoints.py` (chemin hypothétique basé sur [`services/README.md`](services/README.md:0)) ou des tests d'intégration client API dans [`tests/integration/`](tests/integration/).
    -   Tests d'intégration des outils d'agents : [`tests/integration/test_agents_tools_integration.py`](tests/integration/test_agents_tools_integration.py:0)
Parcourez ces dossiers pour trouver des tests pertinents pour la fonctionnalité que vous souhaitez tester.

**Q: Comment ajouter un nouveau test ?**
**R:** Pour ajouter un nouveau test :
1.  **Identifiez la portée** : Déterminez s'il s'agit d'un test unitaire (isolant un composant) ou d'un test d'intégration (vérifiant l'interaction entre composants).
2.  **Localisation** :
    *   Pour les tests unitaires, placez votre fichier dans un sous-répertoire de [`tests/unit/`](tests/unit/) qui reflète la structure du code source (par exemple, un test pour `argumentation_analysis/logic/my_module.py` irait dans `tests/unit/argumentation_analysis/logic/test_my_module.py`).
    *   Pour les tests d'intégration, placez-le dans [`tests/integration/`](tests/integration/).
3.  **Nommage** : Nommez votre fichier `test_*.py` (par exemple, `test_nouvelle_fonctionnalite.py`) et vos fonctions de test `test_*` (par exemple, `def test_comportement_attendu():`).
4.  **Écriture** :
    *   Importez les modules nécessaires et `pytest`.
    *   Utilisez des fixtures `pytest` (définies dans des fichiers `conftest.py` ou localement, voir par exemple [`tests/fixtures/agent_fixtures.py`](tests/fixtures/agent_fixtures.py:0)) pour préparer l'environnement de test (données, objets mockés, etc.).
    *   Écrivez des assertions claires (`assert condition`) pour vérifier les résultats.
5.  **Exécution** : Lancez `pytest` pour vérifier que votre nouveau test passe et n'introduit pas de régressions.
Consultez le guide [`docs/guides/guide_developpeur.md`](docs/guides/guide_developpeur.md:0) (section sur l'écriture des tests) pour des conventions et des exemples plus détaillés.

---

## Déploiement et Environnement

**Q: Comment configurer l'environnement de développement ?**
**R:** La configuration de l'environnement de développement est une étape cruciale. Suivez ces indications :
-   **Scripts d'initialisation** : Utilisez les scripts fournis à la racine du projet :
    -   [`setup_project_env.ps1`](setup_project_env.ps1:0) pour Windows (PowerShell).
    -   [`setup_project_env.sh`](setup_project_env.sh:0) pour Linux/macOS (Bash).
    Ces scripts créent généralement un environnement virtuel Python, installent les dépendances et peuvent effectuer d'autres configurations initiales.
-   **Dépendances Python** :
    -   La liste principale des dépendances Python se trouve dans [`requirements.txt`](requirements.txt:0) (pour `pip`).
    -   Si vous utilisez Conda, le fichier [`environment.yml`](environment.yml:0) définit l'environnement.
-   **Java Development Kit (JDK)** : Une version compatible du JDK est requise pour JPype et l'utilisation de TweetyProject. Assurez-vous que `JAVA_HOME` est correctement configuré.
-   **Guides d'installation** : Pour des instructions plus détaillées, consultez :
    -   [`GUIDE_INSTALLATION_ETUDIANTS.md`](GUIDE_INSTALLATION_ETUDIANTS.md:0)
    -   [`GETTING_STARTED.md`](GETTING_STARTED.md:0)
    -   La section "Configuration de l'environnement" dans [`docs/guides/guide_developpeur.md`](docs/guides/guide_developpeur.md:0).

**Q: Quelles sont les dépendances clés du projet ?**
**R:** Les dépendances clés du projet incluent :
-   **Backend :**
    -   **Python** : Langage principal.
    -   **Java (via JPype)** : Pour l'intégration avec les bibliothèques Java.
    -   **TweetyProject** : Bibliothèque Java pour la logique et l'argumentation. Les `.jar` nécessaires sont souvent inclus dans le projet (voir [`libs/`](libs/:0) ou une configuration Maven/Gradle si applicable).
    -   **Flask** : Framework web pour l'API (voir [`services/web_api/requirements.txt`](services/web_api/requirements.txt:0) si spécifique, sinon [`requirements.txt`](requirements.txt:0) global).
    -   **Pydantic** : Pour la validation des données de l'API.
    Les dépendances Python sont listées dans [`requirements.txt`](requirements.txt:0) et/ou [`environment.yml`](environment.yml:0).
-   **Frontend (Interface Web) :**
    -   **React** : Bibliothèque JavaScript pour la construction de l'interface utilisateur.
    -   **D3.js** : Pour les visualisations de données (graphiques, etc.).
    -   **Axios/fetch** : Pour les appels à l'API backend.
    Les dépendances frontend seraient listées dans un fichier `package.json` au sein du répertoire du frontend (par exemple, `interface-web/package.json`).
-   **Outils de développement et de test :**
    -   **pytest** : Framework de test.
    -   **Git** : Système de contrôle de version.
Consultez les fichiers de dépendances mentionnés pour les versions exactes.

**Q: Comment déployer l'application en production ?**
**R:** Le déploiement d'une application de ce type (backend Python/Flask, frontend React) en production est un processus multi-étapes. Voici les composants typiques :

-   **Backend (API Flask) :**
    1.  **Serveur WSGI** : Utiliser un serveur WSGI robuste comme Gunicorn ou uWSGI pour exécuter l'application Flask (plutôt que le serveur de développement Flask).
    2.  **Reverse Proxy** : Placer l'application WSGI derrière un reverse proxy comme Nginx ou Apache. Nginx peut gérer les requêtes HTTP/HTTPS, la terminaison SSL, servir les fichiers statiques, le load balancing, et la mise en cache.
    3.  **Gestionnaire de processus** : Utiliser un gestionnaire de processus comme `systemd` (Linux), `supervisor`, ou des conteneurs (Docker) pour gérer le cycle de vie de l'application (démarrage, arrêt, redémarrage automatique en cas d'échec).
    4.  **Configuration** : Externaliser la configuration (clés secrètes, URL de base de données, modes de débogage) via des variables d'environnement ou des fichiers de configuration spécifiques à l'environnement.

-   **Frontend (Application React) :**
    1.  **Build de production** : Générer les fichiers statiques optimisés de l'application React (par exemple, avec `npm run build` ou `yarn build`).
    2.  **Hébergement des fichiers statiques** : Servir ces fichiers statiques via le reverse proxy (Nginx) ou un service de CDN (Content Delivery Network) pour de meilleures performances.

-   **Base de données et autres services :** Configurer et sécuriser les bases de données, les services de cache (Redis), etc., requis par l'application.

-   **Logging et Monitoring :** Mettre en place des solutions de logging centralisé et de monitoring pour surveiller la santé et les performances de l'application.

Pour des instructions spécifiques au projet, consultez le guide [`docs/guides/guide_deploiement.md`](docs/guides/guide_deploiement.md:0) s'il existe. Des exemples de configuration pour Nginx ou des fichiers `Dockerfile` peuvent également être présents dans le projet (par exemple, dans un dossier `deployment/` ou à la racine).
Le script [`scripts/env/setup_prod_env.sh`](scripts/env/setup_prod_env.sh:0) (s'il existe) pourrait contenir des étapes d'automatisation pour un environnement de production.

---

## Contribution et Bonnes Pratiques

**Q: Comment contribuer au projet ?**
**R:** Nous encourageons les contributions ! Voici le processus typique :
1.  **Fork & Clone** : Forkez le dépôt principal sur GitHub, puis clonez votre fork localement.
2.  **Branche** : Créez une nouvelle branche descriptive pour votre fonctionnalité ou correction de bug (par exemple, `feature/nouvelle-analyse` ou `fix/bug-affichage-sophisme`).
    ```bash
    git checkout -b feature/ma-nouvelle-feature
    ```
3.  **Développement** : Faites vos modifications, en respectant les conventions de codage (voir question suivante).
4.  **Tests** : Ajoutez des tests pour vos modifications et assurez-vous que tous les tests passent.
5.  **Commit** : Committez vos changements avec des messages clairs et concis (voir la question sur les commits).
6.  **Push** : Poussez votre branche sur votre fork :
    ```bash
    git push origin feature/ma-nouvelle-feature
    ```
7.  **Pull Request (PR)** : Ouvrez une Pull Request depuis votre branche vers la branche principale (souvent `main` ou `develop`) du dépôt original. Décrivez bien vos changements dans la PR.
8.  **Revue** : Votre PR sera revue par les mainteneurs. Adressez les commentaires et suggestions.
9.  **Merge** : Une fois approuvée, votre PR sera fusionnée.

Pour des directives plus détaillées, consultez le fichier `CONTRIBUTING.md` (s'il existe à la racine du projet) ou la section "Contribuer au projet" dans le [`docs/guides/guide_developpeur.md`](docs/guides/guide_developpeur.md:0).

**Q: Quelles sont les conventions de codage ?**
**R:** Le respect des conventions de codage est essentiel pour la maintenabilité :
-   **Python :**
    -   Suivre **PEP 8** pour le style du code.
    -   Utiliser un linter comme Flake8 et un formateur comme Black. Les configurations peuvent être présentes dans des fichiers comme `.flake8`, `pyproject.toml`.
    -   Rédiger des **docstrings** complètes (par exemple, style Google ou NumPy) pour tous les modules, classes, fonctions et méthodes publiques.
-   **JavaScript/React :**
    -   Suivre un guide de style reconnu (par exemple, Airbnb JavaScript Style Guide).
    -   Utiliser **Prettier** pour le formatage automatique du code (configuration dans `.prettierrc` ou `package.json`).
    -   Utiliser **ESLint** pour le linting (configuration dans `.eslintrc.js` ou similaire).
-   **Général :**
    -   Écrire des commentaires clairs et concis pour expliquer les parties complexes ou non évidentes du code.
    -   Nommer les variables, fonctions et classes de manière descriptive.
    -   Viser un code modulaire et facile à tester.

Consultez la section "Conventions de codage" dans le [`docs/guides/guide_developpeur.md`](docs/guides/guide_developpeur.md:0) pour les règles spécifiques au projet et des exemples.

**Q: Comment gérer les branches et les commits ?**
**R:** Une bonne gestion des branches et des commits facilite la collaboration et la maintenance de l'historique :
-   **Branches :**
    -   Utilisez des noms de branches clairs, descriptifs et préfixés par leur type (par exemple, `feature/`, `fix/`, `docs/`, `refactor/`). Exemples : `feature/analyse-contextuelle-avancee`, `fix/erreur-calcul-extension-stable`.
    -   Basez vos nouvelles branches sur la branche de développement principale la plus à jour (souvent `develop` ou `main`).
    -   Supprimez les branches fusionnées localement et sur le remote (si vous avez les droits) pour garder le dépôt propre.
-   **Commits :**
    -   Faites des **commits atomiques** : chaque commit doit représenter une modification logique et cohérente.
    -   Écrivez des **messages de commit clairs et informatifs**. Une pratique courante est d'utiliser le format [Conventional Commits](https://www.conventionalcommits.org/). Par exemple :
        -   `feat: Ajoute le support pour la sémantique préférée`
        -   `fix: Corrige une erreur de division par zéro dans le calcul du score`
        -   `docs: Met à jour la documentation de l'API pour le endpoint /analyze`
        -   `refactor: Simplifie la logique de gestion des états dans le composant ArgumentEditor`
        -   `test: Ajoute des tests unitaires pour le FallacyService`
    -   Le message doit avoir un sujet concis (max 50-72 caractères) et optionnellement un corps plus détaillé.

Ces pratiques sont souvent détaillées dans `CONTRIBUTING.md` ou le [`docs/guides/guide_developpeur.md`](docs/guides/guide_developpeur.md:0).

**Q: Où signaler les bugs ou proposer des fonctionnalités ?**
**R:** Pour signaler des bugs ou proposer de nouvelles fonctionnalités, veuillez utiliser l'onglet **"Issues"** du dépôt GitHub du projet.

Lorsque vous créez une issue :
-   **Pour les bugs :**
    -   Vérifiez si un bug similaire n'a pas déjà été signalé.
    -   Fournissez une description claire et concise du bug.
    -   Listez les étapes exactes pour reproduire le bug.
    -   Décrivez le comportement observé et le comportement attendu.
    -   Incluez des informations sur votre environnement (OS, version du navigateur, version du projet, etc.) si pertinent.
    -   Ajoutez des captures d'écran ou des logs d'erreur si possible.
-   **Pour les propositions de fonctionnalités :**
    -   Décrivez clairement la fonctionnalité que vous souhaitez voir ajoutée.
    -   Expliquez le cas d'usage ou le problème que cette fonctionnalité résoudrait.
    -   Si possible, suggérez une implémentation ou une approche.

Des modèles d'issues (bug report, feature request) peuvent être configurés sur le dépôt pour vous guider.