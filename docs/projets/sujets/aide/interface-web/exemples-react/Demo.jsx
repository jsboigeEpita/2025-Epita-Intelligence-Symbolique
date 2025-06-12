import React, { useState } from 'react';
import ArgumentAnalyzer from './ArgumentAnalyzer';
import ValidationForm from './ValidationForm';
import FallacyDetector from './FallacyDetector';
import FrameworkBuilder from './FrameworkBuilder';
import './Demo.css';

/**
 * Composant de démonstration complète de l'API d'argumentation
 * 
 * Ce composant présente tous les outils disponibles dans une interface
 * unifiée permettant de tester toutes les fonctionnalités de l'API.
 */
const Demo = () => {
  const [activeTab, setActiveTab] = useState('analyzer');
  const [results, setResults] = useState({});

  // Onglets disponibles
  const tabs = [
    {
      id: 'analyzer',
      name: 'Analyseur d\'Arguments',
      description: 'Analyse complète de textes argumentatifs',
      icon: '🔍'
    },
    {
      id: 'validator',
      name: 'Validateur Logique',
      description: 'Validation de la structure logique',
      icon: '✓'
    },
    {
      id: 'fallacy',
      name: 'Détecteur de Sophismes',
      description: 'Identification des erreurs de raisonnement',
      icon: '⚠️'
    },
    {
      id: 'framework',
      name: 'Framework de Dung',
      description: 'Construction de frameworks d\'argumentation',
      icon: '🏗️'
    }
  ];

  // Exemples de textes pour chaque outil
  const examples = {
    analyzer: [
      {
        title: "Argument sur l'environnement",
        text: "Les émissions de CO2 augmentent chaque année. Le réchauffement climatique s'accélère. Les glaciers fondent à un rythme alarmant. Par conséquent, nous devons agir rapidement pour réduire notre empreinte carbone."
      },
      {
        title: "Argument économique",
        text: "L'investissement dans l'éducation génère des retours économiques importants. Les pays avec un système éducatif performant ont une croissance plus forte. Donc, augmenter le budget de l'éducation est rentable à long terme."
      }
    ],
    validator: [
      {
        title: "Syllogisme classique",
        premises: [
          "Tous les hommes sont mortels",
          "Socrate est un homme"
        ],
        conclusion: "Donc Socrate est mortel"
      },
      {
        title: "Argument inductif",
        premises: [
          "Le soleil s'est levé chaque jour depuis des millénaires",
          "Les lois physiques sont constantes"
        ],
        conclusion: "Le soleil se lèvera demain"
      }
    ],
    fallacy: [
      {
        title: "Attaque personnelle",
        text: "Vous ne pouvez pas avoir raison sur le changement climatique parce que vous n'êtes pas scientifique. De plus, votre opinion ne compte pas car vous êtes trop jeune pour comprendre ces enjeux complexes."
      },
      {
        title: "Faux dilemme",
        text: "Soit nous construisons cette autoroute, soit notre économie s'effondre. Il n'y a que ces deux options possibles pour l'avenir de notre région."
      }
    ],
    framework: [
      {
        title: "Débat simple",
        arguments: [
          {
            id: "A",
            content: "Il faut interdire les voitures en centre-ville",
            attacks: ["B"],
            supports: []
          },
          {
            id: "B", 
            content: "Les voitures sont nécessaires pour l'économie locale",
            attacks: ["A"],
            supports: []
          },
          {
            id: "C",
            content: "Les transports en commun sont une alternative viable",
            attacks: [],
            supports: ["A"]
          }
        ]
      }
    ]
  };

  // Gestionnaire de changement d'onglet
  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
  };

  // Gestionnaire de résultats
  const handleResults = (toolName, data) => {
    setResults(prev => ({
      ...prev,
      [toolName]: data
    }));
  };

  // Chargement d'un exemple
  const loadExample = (example) => {
    // Cette fonction pourrait être étendue pour pré-remplir les formulaires
    console.log('Chargement de l\'exemple:', example);
  };

  // Rendu de la navigation
  const renderNavigation = () => (
    <nav className="demo-nav">
      <div className="nav-header">
        <h1>🎯 Démo API d'Argumentation</h1>
        <p>Interface complète pour tester tous les outils d'analyse argumentative</p>
      </div>
      
      <div className="nav-tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
          >
            <span className="tab-icon">{tab.icon}</span>
            <div className="tab-content">
              <span className="tab-name">{tab.name}</span>
              <span className="tab-description">{tab.description}</span>
            </div>
          </button>
        ))}
      </div>
    </nav>
  );

  // Rendu des exemples
  const renderExamples = () => {
    const currentExamples = examples[activeTab];
    if (!currentExamples || currentExamples.length === 0) return null;

    return (
      <div className="examples-section">
        <h3>📚 Exemples</h3>
        <div className="examples-grid">
          {currentExamples.map((example, index) => (
            <div key={index} className="example-card">
              <h4>{example.title}</h4>
              {example.text && (
                <p className="example-text">{example.text}</p>
              )}
              {example.premises && (
                <div className="example-premises">
                  <strong>Prémisses:</strong>
                  <ul>
                    {example.premises.map((premise, i) => (
                      <li key={i}>{premise}</li>
                    ))}
                  </ul>
                  <strong>Conclusion:</strong> {example.conclusion}
                </div>
              )}
              {example.arguments && (
                <div className="example-framework">
                  <strong>Arguments:</strong>
                  <ul>
                    {example.arguments.map(arg => (
                      <li key={arg.id}>
                        <strong>{arg.id}:</strong> {arg.content}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <button 
                onClick={() => loadExample(example)}
                className="load-example-btn"
              >
                Charger cet exemple
              </button>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Rendu du contenu principal
  const renderMainContent = () => {
    switch (activeTab) {
      case 'analyzer':
        return (
          <ArgumentAnalyzer
            onAnalysisComplete={(data) => handleResults('analyzer', data)}
            showAdvancedOptions={true}
          />
        );
      
      case 'validator':
        return (
          <ValidationForm
            onValidationComplete={(data) => handleResults('validator', data)}
            showArgumentType={true}
          />
        );
      
      case 'fallacy':
        return (
          <FallacyDetector
            onFallaciesDetected={(data) => handleResults('fallacy', data)}
            showAdvancedOptions={true}
          />
        );
      
      case 'framework':
        return (
          <FrameworkBuilder
            onFrameworkBuilt={(data) => handleResults('framework', data)}
            showVisualization={true}
            allowSemantics={['grounded', 'preferred', 'stable', 'complete']}
          />
        );
      
      default:
        return <div>Outil non trouvé</div>;
    }
  };

  // Rendu du résumé des résultats
  const renderResultsSummary = () => {
    const hasResults = Object.keys(results).length > 0;
    if (!hasResults) return null;

    return (
      <div className="results-summary">
        <h3>📊 Résumé des Résultats</h3>
        <div className="summary-grid">
          {Object.entries(results).map(([tool, data]) => (
            <div key={tool} className="summary-card">
              <h4>{tabs.find(t => t.id === tool)?.name || tool}</h4>
              <div className="summary-content">
                {tool === 'analyzer' && data && (
                  <div>
                    <p>Qualité: {Math.round((data.overall_quality || 0) * 100)}%</p>
                    <p>Sophismes: {data.fallacy_count || 0}</p>
                    <p>Cohérence: {Math.round((data.coherence_score || 0) * 100)}%</p>
                  </div>
                )}
                {tool === 'validator' && data && (
                  <div>
                    <p>Validité: {Math.round((data.result?.validity_score || 0) * 100)}%</p>
                    <p>Solidité: {Math.round((data.result?.soundness_score || 0) * 100)}%</p>
                    <p>Problèmes: {data.result?.issues?.length || 0}</p>
                  </div>
                )}
                {tool === 'fallacy' && data && (
                  <div>
                    <p>Sophismes détectés: {data.fallacy_count || 0}</p>
                    <p>Temps: {Math.round((data.processing_time || 0) * 1000)}ms</p>
                  </div>
                )}
                {tool === 'framework' && data && (
                  <div>
                    <p>Arguments: {data.argument_count || 0}</p>
                    <p>Attaques: {data.attack_count || 0}</p>
                    <p>Extensions: {data.extension_count || 0}</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // Rendu des informations d'aide
  const renderHelpInfo = () => (
    <div className="help-info">
      <h3>ℹ️ Informations</h3>
      <div className="help-content">
        <div className="help-section">
          <h4>À propos de cette démo</h4>
          <p>
            Cette interface de démonstration présente tous les outils disponibles 
            dans l'API d'argumentation. Chaque onglet correspond à un service 
            différent avec ses propres fonctionnalités.
          </p>
        </div>
        
        <div className="help-section">
          <h4>Comment utiliser</h4>
          <ol>
            <li>Sélectionnez un outil dans la navigation</li>
            <li>Utilisez les exemples fournis ou saisissez vos propres données</li>
            <li>Configurez les options selon vos besoins</li>
            <li>Lancez l'analyse et consultez les résultats</li>
          </ol>
        </div>

        <div className="help-section">
          <h4>Configuration API</h4>
          <p>
            Assurez-vous que l'API est démarrée sur <code>http://localhost:5000</code>.
            Vous pouvez modifier l'URL dans le hook <code>useArgumentationAPI</code>.
          </p>
        </div>

        <div className="help-section">
          <h4>Ressources</h4>
          <ul>
            <li><a href="#guide">Guide d'utilisation complet</a></li>
            <li><a href="#troubleshooting">Guide de dépannage</a></li>
            <li><a href="#api-docs">Documentation API</a></li>
          </ul>
        </div>
      </div>
    </div>
  );

  return (
    <div className="demo-container">
      {renderNavigation()}
      
      <div className="demo-content">
        <div className="main-panel">
          {renderMainContent()}
        </div>
        
        <div className="side-panel">
          {renderExamples()}
          {renderResultsSummary()}
          {renderHelpInfo()}
        </div>
      </div>
    </div>
  );
};

export default Demo;