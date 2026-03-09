import React, { useEffect, useState } from 'react';
import './App.css';
import ArgumentAnalyzer from './components/ArgumentAnalyzer';
import ArgumentReconstructor from './components/ArgumentReconstructor';
import FallacyDetector from './components/FallacyDetector';
import FrameworkBuilder from './components/FrameworkBuilder';
import LogicGraph from './components/LogicGraph';
import ValidationForm from './components/ValidationForm';
import GovernanceDashboard from './components/governance/GovernanceDashboard';
import { checkAPIHealth } from './services/api';

function App() {
  const [activeTab, setActiveTab] = useState('analyzer');
  const [apiStatus, setApiStatus] = useState('checking');

  useEffect(() => {
    // Vérifier l'état de l'API au démarrage
    checkAPIHealth()
      .then(() => setApiStatus('connected'))
      .catch(() => setApiStatus('disconnected'));
  }, []);

  const tabs = [
    { id: 'analyzer', label: '🔍 Analyseur', component: ArgumentAnalyzer },
    { id: 'fallacies', label: '⚠️ Sophismes', component: FallacyDetector },
    { id: 'reconstructor', label: '🔄 Reconstructeur', component: ArgumentReconstructor },
    { id: 'logic-graph', label: '📊 Graphe Logique', component: LogicGraph },
    { id: 'validation', label: '✅ Validation', component: ValidationForm },
    { id: 'framework', label: '🏗️ Framework', component: FrameworkBuilder },
    { id: 'governance', label: '🏛️ Gouvernance', component: GovernanceDashboard }
  ];

  const renderActiveComponent = () => {
    const activeTabData = tabs.find(tab => tab.id === activeTab);
    if (activeTabData) {
      const Component = activeTabData.component;
      return <Component />;
    }
    return null;
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <h1>🎯 Interface d'Analyse Argumentative</h1>
          <p className="header-subtitle">
            Analysez vos arguments, détectez les sophismes et construisez des frameworks r
robustes
          </p>
          <div className={`api-status ${apiStatus}`}>
            <span className="status-indicator"></span>
            API: {apiStatus === 'connected' ? '✅ Connectée' :
                  apiStatus === 'disconnected' ? '❌ Déconnectée' : '🔄 Vérification...'} 
          </div>
        </div>
      </header>

      <nav className="tab-navigation">
        <div className="tab-container">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              disabled={apiStatus !== 'connected'}
              data-testid={
                tab.id === 'analyzer' ? 'analyzer-tab' :
                tab.id === 'fallacies' ? 'fallacy-detector-tab' :
                tab.id === 'reconstructor' ? 'reconstructor-tab' :
                tab.id === 'logic-graph' ? 'logic-graph-tab' :
                tab.id === 'validation' ? 'validation-tab' :
                tab.id === 'framework' ? 'framework-tab' : undefined
              }
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="main-content">
        {apiStatus !== 'connected' ? (
          <div className="api-error-state">
            <div className="error-icon">🚫</div>
            <h2>API Indisponible</h2>
            <p>
              L'API d'analyse argumentative n'est pas accessible.
              Veuillez vérifier qu'elle est démarrée sur le port 5000.
            </p>
            <div className="error-instructions">
              <h3>Pour démarrer l'API :</h3>
              <pre><code>cd services/web_api{'\n'}python start_api.py</code></pre>        
            </div>
          </div>
        ) : (
          <div className="component-container">
            {renderActiveComponent()}
          </div>
        )}
      </main>

      <footer className="App-footer">
        <div className="footer-content">
          <p>Interface Web d'Analyse Argumentative - Intelligence Symbolique 2025</p>     
          <div className="footer-links">
            <a href="/api/endpoints" target="_blank" rel="noopener noreferrer">
              📚 Documentation API
            </a>
            <span className="separator">•</span>
            <a href="/api/health" target="_blank" rel="noopener noreferrer">
              ❤️ Status API
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;