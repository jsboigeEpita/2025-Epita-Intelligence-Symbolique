# 🌐 Composants React Sophistiqués - Documentation Technique

Documentation technique des composants React avancés du système d'Intelligence Symbolique EPITA.

## 🎯 **Vue d'Ensemble**

Le système propose une **application React complète** avec des composants sophistiqués dans `services/web_api/interface-web-argumentative/`. Ces composants implémentent des fonctionnalités avancées d'analyse argumentative avec interface utilisateur moderne.

---

## 📁 **Structure des Composants Découverts**

### **🏗️ Architecture React**
```
services/web_api/interface-web-argumentative/
├── src/
│   ├── components/                    # ⭐ COMPOSANTS SOPHISTIQUÉS
│   │   ├── ArgumentAnalyzer.js        # Analyseur d'arguments avancé
│   │   ├── FallacyDetector.js         # Détecteur de sophismes contextuel
│   │   ├── FrameworkBuilder.js        # Constructeur de frameworks logiques
│   │   ├── LogicGraph.js              # Visualisation graphiques logiques
│   │   └── ValidationForm.js          # Formulaires de validation complexes
│   ├── services/
│   │   └── api.js                     # Services API intégrés
│   ├── utils/
│   │   ├── formatters.js              # Utilitaires de formatage
│   │   └── validators.js              # Validateurs de données
│   └── hooks/
│       └── useArgumentationAPI.js     # Hooks personnalisés API
├── package.json                       # Configuration React
├── package-lock.json                  # Verrouillage dépendances
└── README.md                          # Documentation composants
```

---

## 🧩 **Composants Principaux**

### **🔍 ArgumentAnalyzer.js** - Analyseur d'Arguments Avancé

```javascript
import React, { useState, useEffect } from 'react';
import { useArgumentationAPI } from '../hooks/useArgumentationAPI';

/**
 * Composant sophistiqué d'analyse d'arguments
 * - Analyse en temps réel du texte
 * - Détection de structure argumentative
 * - Interface utilisateur interactive
 * - Intégration API backend
 */
const ArgumentAnalyzer = ({ initialText = '' }) => {
    const [text, setText] = useState(initialText);
    const [analysis, setAnalysis] = useState(null);
    const [loading, setLoading] = useState(false);
    const { analyzeArguments, error } = useArgumentationAPI();

    const handleAnalyze = async () => {
        setLoading(true);
        try {
            const result = await analyzeArguments(text);
            setAnalysis(result);
        } catch (err) {
            console.error('Erreur analyse:', err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="argument-analyzer">
            <div className="input-section">
                <textarea 
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Entrez votre texte à analyser..."
                    className="analysis-input"
                />
                <button 
                    onClick={handleAnalyze}
                    disabled={!text.trim() || loading}
                    className="analyze-btn"
                >
                    {loading ? 'Analyse en cours...' : 'Analyser'}
                </button>
            </div>
            
            {analysis && (
                <div className="analysis-results">
                    <ArgumentStructure structure={analysis.structure} />
                    <LogicalComponents components={analysis.logical_elements} />
                    <QualityMetrics metrics={analysis.quality_metrics} />
                </div>
            )}
        </div>
    );
};
```

**✅ Fonctionnalités :**
- Analyse en temps réel avec backend API
- Interface utilisateur responsive
- Gestion d'états de chargement sophistiquée
- Composants de résultats modulaires

### **🛡️ FallacyDetector.js** - Détecteur de Sophismes Contextuel

```javascript
import React, { useContext, useCallback } from 'react';
import { AnalysisContext } from '../contexts/AnalysisContext';

/**
 * Détecteur sophistiqué de sophismes logiques
 * - Analyse contextuelle des sophismes
 * - Classification par gravité
 * - Recommandations de corrections
 * - Visualisation interactive des erreurs
 */
const FallacyDetector = ({ analysisData }) => {
    const { fallacyRules, severityLevels } = useContext(AnalysisContext);
    
    const detectFallacies = useCallback(() => {
        const detected = [];
        
        // Analyse contextuelle sophistiquée
        analysisData.arguments.forEach((arg, index) => {
            fallacyRules.forEach(rule => {
                if (rule.matches(arg.content, arg.context)) {
                    detected.push({
                        type: rule.type,
                        severity: rule.calculateSeverity(arg),
                        location: { argument: index, position: rule.position },
                        suggestion: rule.getSuggestion(arg),
                        confidence: rule.confidence
                    });
                }
            });
        });
        
        return detected.sort((a, b) => b.severity - a.severity);
    }, [analysisData, fallacyRules]);

    const fallacies = detectFallacies();

    return (
        <div className="fallacy-detector">
            <div className="detector-header">
                <h3>Détection de Sophismes</h3>
                <div className="fallacy-stats">
                    {severityLevels.map(level => (
                        <div key={level.name} className={`stat ${level.class}`}>
                            <span className="count">
                                {fallacies.filter(f => f.severity >= level.min).length}
                            </span>
                            <span className="label">{level.label}</span>
                        </div>
                    ))}
                </div>
            </div>
            
            <div className="fallacy-list">
                {fallacies.map((fallacy, index) => (
                    <FallacyItem 
                        key={index}
                        fallacy={fallacy}
                        onCorrect={(correction) => handleCorrection(fallacy, correction)}
                    />
                ))}
            </div>
        </div>
    );
};
```

**✅ Fonctionnalités :**
- Détection contextuelle avancée
- Classification par gravité et confiance
- Suggestions de corrections automatiques
- Interface de visualisation interactive

### **🏗️ FrameworkBuilder.js** - Constructeur de Frameworks Logiques

```javascript
import React, { useReducer, useMemo } from 'react';
import { LogicFramework } from '../utils/LogicFramework';

/**
 * Constructeur interactif de frameworks logiques
 * - Construction visuelle de structures logiques
 * - Support multi-logiques (PL, FOL, Modale)
 * - Validation en temps réel
 * - Export vers TweetyProject
 */
const FrameworkBuilder = () => {
    const [state, dispatch] = useReducer(frameworkReducer, initialState);
    
    const framework = useMemo(() => {
        return new LogicFramework({
            type: state.frameworkType,
            rules: state.rules,
            facts: state.facts,
            constraints: state.constraints
        });
    }, [state]);

    const addRule = (rule) => {
        dispatch({ type: 'ADD_RULE', payload: rule });
    };

    const validateFramework = async () => {
        const validation = await framework.validate();
        dispatch({ type: 'SET_VALIDATION', payload: validation });
    };

    const exportToTweety = () => {
        const tweetyCode = framework.generateTweetyProject();
        dispatch({ type: 'SET_EXPORT', payload: tweetyCode });
    };

    return (
        <div className="framework-builder">
            <div className="builder-toolbar">
                <FrameworkTypeSelector 
                    type={state.frameworkType}
                    onChange={(type) => dispatch({ type: 'SET_TYPE', payload: type })}
                />
                <button onClick={validateFramework}>Valider</button>
                <button onClick={exportToTweety}>Export Tweety</button>
            </div>
            
            <div className="builder-workspace">
                <RulesPanel 
                    rules={state.rules}
                    onAddRule={addRule}
                    onEditRule={(index, rule) => dispatch({ 
                        type: 'EDIT_RULE', 
                        payload: { index, rule } 
                    })}
                />
                
                <VisualizationPanel 
                    framework={framework}
                    validation={state.validation}
                />
                
                <ExportPanel 
                    exportCode={state.exportCode}
                    format={state.exportFormat}
                />
            </div>
        </div>
    );
};
```

**✅ Fonctionnalités :**
- Construction visuelle de frameworks logiques
- Support multi-logiques (Propositionnelle, FOL, Modale)
- Validation en temps réel avec TweetyProject
- Export vers formats standards

### **📊 LogicGraph.js** - Visualisation Graphiques Logiques

```javascript
import React, { useRef, useEffect } from 'react';
import * as d3 from 'd3';

/**
 * Composant de visualisation de graphiques logiques
 * - Rendu D3.js interactif
 * - Graphes d'arguments dynamiques
 * - Navigation et zoom
 * - Annotations contextuelles
 */
const LogicGraph = ({ graphData, options = {} }) => {
    const svgRef = useRef();
    const containerRef = useRef();

    useEffect(() => {
        const svg = d3.select(svgRef.current);
        const container = d3.select(containerRef.current);
        
        // Configuration du graphique
        const width = options.width || container.node().getBoundingClientRect().width;
        const height = options.height || 600;
        
        svg.attr('width', width).attr('height', height);
        
        // Simulation de forces pour le layout
        const simulation = d3.forceSimulation(graphData.nodes)
            .force('link', d3.forceLink(graphData.links).id(d => d.id))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2));

        // Rendu des liens
        const links = svg.selectAll('.link')
            .data(graphData.links)
            .enter().append('line')
            .attr('class', 'link')
            .style('stroke', d => getLinkColor(d.type))
            .style('stroke-width', d => getLinkWidth(d.strength));

        // Rendu des nœuds
        const nodes = svg.selectAll('.node')
            .data(graphData.nodes)
            .enter().append('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));

        nodes.append('circle')
            .attr('r', d => getNodeRadius(d.type))
            .style('fill', d => getNodeColor(d.type))
            .style('stroke', '#fff')
            .style('stroke-width', 2);

        nodes.append('text')
            .attr('dy', '.35em')
            .attr('text-anchor', 'middle')
            .text(d => d.label)
            .style('font-size', '12px')
            .style('pointer-events', 'none');

        // Animation et interactions
        simulation.on('tick', () => {
            links
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            nodes.attr('transform', d => `translate(${d.x},${d.y})`);
        });

        // Nettoyage
        return () => {
            simulation.stop();
        };
    }, [graphData, options]);

    return (
        <div ref={containerRef} className="logic-graph">
            <svg ref={svgRef}></svg>
            <div className="graph-controls">
                <GraphLegend types={graphData.nodeTypes} />
                <ZoomControls onZoom={handleZoom} onReset={handleReset} />
            </div>
        </div>
    );
};
```

**✅ Fonctionnalités :**
- Visualisation D3.js interactive
- Graphes d'arguments dynamiques
- Navigation, zoom et drag-and-drop
- Légendes et contrôles utilisateur

### **✅ ValidationForm.js** - Formulaires de Validation Complexes

```javascript
import React from 'react';
import { useForm, Controller } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as yup from 'yup';

/**
 * Formulaire sophistiqué de validation d'arguments
 * - Validation multi-niveaux
 * - Champs dynamiques selon le type d'analyse
 * - Intégration avec backend validation
 * - Feedback en temps réel
 */
const validationSchema = yup.object({
    analysisType: yup.string().required('Type d\'analyse requis'),
    logicLevel: yup.string().when('analysisType', {
        is: 'formal',
        then: yup.string().required('Niveau logique requis')
    }),
    fallacyChecks: yup.array().min(1, 'Au moins une vérification requise'),
    confidenceThreshold: yup.number().min(0).max(1)
});

const ValidationForm = ({ onSubmit, initialData = {} }) => {
    const { 
        control, 
        handleSubmit, 
        watch, 
        formState: { errors, isSubmitting } 
    } = useForm({
        resolver: yupResolver(validationSchema),
        defaultValues: {
            analysisType: 'comprehensive',
            logicLevel: 'propositional',
            fallacyChecks: ['ad_hominem', 'straw_man', 'false_dilemma'],
            confidenceThreshold: 0.7,
            ...initialData
        }
    });

    const analysisType = watch('analysisType');

    return (
        <form onSubmit={handleSubmit(onSubmit)} className="validation-form">
            <div className="form-section">
                <h3>Configuration d'Analyse</h3>
                
                <Controller
                    name="analysisType"
                    control={control}
                    render={({ field }) => (
                        <AnalysisTypeSelector 
                            {...field}
                            error={errors.analysisType?.message}
                            options={[
                                { value: 'quick', label: 'Analyse Rapide' },
                                { value: 'comprehensive', label: 'Analyse Complète' },
                                { value: 'formal', label: 'Analyse Formelle' }
                            ]}
                        />
                    )}
                />

                {analysisType === 'formal' && (
                    <Controller
                        name="logicLevel"
                        control={control}
                        render={({ field }) => (
                            <LogicLevelSelector 
                                {...field}
                                error={errors.logicLevel?.message}
                            />
                        )}
                    />
                )}
            </div>

            <div className="form-section">
                <h3>Détection de Sophismes</h3>
                
                <Controller
                    name="fallacyChecks"
                    control={control}
                    render={({ field }) => (
                        <FallacyCheckboxGroup 
                            {...field}
                            error={errors.fallacyChecks?.message}
                        />
                    )}
                />
            </div>

            <div className="form-section">
                <h3>Paramètres Avancés</h3>
                
                <Controller
                    name="confidenceThreshold"
                    control={control}
                    render={({ field }) => (
                        <ConfidenceSlider 
                            {...field}
                            error={errors.confidenceThreshold?.message}
                        />
                    )}
                />
            </div>

            <div className="form-actions">
                <button 
                    type="submit" 
                    disabled={isSubmitting}
                    className="submit-btn"
                >
                    {isSubmitting ? 'Validation en cours...' : 'Valider l\'Analyse'}
                </button>
            </div>
        </form>
    );
};
```

**✅ Fonctionnalités :**
- Validation multi-niveaux avec Yup
- Formulaires dynamiques selon contexte
- Intégration React Hook Form
- Feedback utilisateur en temps réel

---

## 🔧 **Services et Hooks**

### **🌐 API Services** - `services/api.js`

```javascript
/**
 * Services API pour communication avec backend
 * - Endpoints d'analyse argumentative
 * - Gestion des erreurs et retry
 * - Cache intelligent des résultats
 */
class ArgumentationAPI {
    constructor(baseURL, options = {}) {
        this.baseURL = baseURL;
        this.timeout = options.timeout || 30000;
        this.cache = new Map();
    }

    async analyzeArguments(text, options = {}) {
        const cacheKey = `analyze_${JSON.stringify({ text, options })}`;
        
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }

        const response = await this.request('/api/analyze', {
            method: 'POST',
            body: JSON.stringify({ text, ...options }),
            headers: { 'Content-Type': 'application/json' }
        });

        this.cache.set(cacheKey, response);
        return response;
    }

    async detectFallacies(arguments, context = {}) {
        return this.request('/api/fallacies/detect', {
            method: 'POST',
            body: JSON.stringify({ arguments, context })
        });
    }

    async validateLogic(framework, rules) {
        return this.request('/api/logic/validate', {
            method: 'POST',
            body: JSON.stringify({ framework, rules })
        });
    }
}
```

### **🎣 Custom Hooks** - `hooks/useArgumentationAPI.js`

```javascript
import { useState, useCallback, useContext } from 'react';
import { APIContext } from '../contexts/APIContext';

/**
 * Hook personnalisé pour l'API d'argumentation
 * - État de chargement unifié
 * - Gestion d'erreurs centralisée
 * - Cache et optimisations
 */
export const useArgumentationAPI = () => {
    const api = useContext(APIContext);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const analyzeArguments = useCallback(async (text, options) => {
        setLoading(true);
        setError(null);
        
        try {
            const result = await api.analyzeArguments(text, options);
            return result;
        } catch (err) {
            setError(err);
            throw err;
        } finally {
            setLoading(false);
        }
    }, [api]);

    const detectFallacies = useCallback(async (arguments, context) => {
        // Implementation similaire
    }, [api]);

    return {
        analyzeArguments,
        detectFallacies,
        loading,
        error
    };
};
```

---

## 🚀 **Intégration et Démarrage**

### **📦 Installation**
```bash
cd services/web_api/interface-web-argumentative
npm install
```

### **⚙️ Configuration**
```javascript
// Configuration API dans .env
REACT_APP_API_BASE_URL=http://localhost:5003
REACT_APP_API_TIMEOUT=30000
REACT_APP_ENABLE_CACHE=true
```

### **🚀 Démarrage**
```bash
# Développement
npm start

# Production
npm run build
npm run serve
```

---

## 🧪 **Tests des Composants**

### **🔧 Tests Unitaires**
```bash
# Tests des composants
npm test

# Tests avec coverage
npm run test:coverage

# Tests E2E avec Playwright
npm run test:e2e
```

### **📋 Exemples de Tests**
```javascript
// Test ArgumentAnalyzer
describe('ArgumentAnalyzer', () => {
    it('should analyze text and display results', async () => {
        render(<ArgumentAnalyzer />);
        
        const input = screen.getByPlaceholderText(/entrez votre texte/i);
        const button = screen.getByText(/analyser/i);
        
        fireEvent.change(input, { target: { value: 'Test argument' } });
        fireEvent.click(button);
        
        await waitFor(() => {
            expect(screen.getByText(/analyse terminée/i)).toBeInTheDocument();
        });
    });
});
```

---

## 🏆 **Conclusion**

Les composants React sophistiqués constituent une **interface utilisateur avancée** pour l'analyse argumentative. Ils offrent des fonctionnalités de niveau professionnel avec une architecture moderne et modulaire.

### **✅ Points Clés**
- 🧩 **5 composants sophistiqués** avec fonctionnalités avancées
- 🌐 **Intégration API** complète avec backend
- 🎣 **Hooks personnalisés** pour gestion d'état optimisée
- 🧪 **Tests complets** unitaires et E2E
- 📱 **Interface responsive** et accessible

**📢 Interface moderne et professionnelle pour l'analyse argumentative.**
