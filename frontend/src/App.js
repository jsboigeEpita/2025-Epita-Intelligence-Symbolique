import React, { useState } from 'react';
import './App.css';
import FallacyDetection from './components/FallacyDetection';
import LogicAnalysis from './components/LogicAnalysis';
import TextAnalysis from './components/TextAnalysis';

function App() {
  const [activeTab, setActiveTab] = useState('text-analysis');
  const [apiStatus, setApiStatus] = useState(null);

  // Check API health
  React.useEffect(() => {
    fetch('http://localhost:5000/api/health')
      .then(response => response.json())
      .then(data => {
        setApiStatus(data.status === 'healthy' ? 'connected' : 'error');
      })
      .catch(() => {
        setApiStatus('disconnected');
      });
  }, []);

  const getStatusColor = () => {
    switch (apiStatus) {
      case 'connected': return '#4CAF50';
      case 'error': return '#FF9800';
      case 'disconnected': return '#F44336';
      default: return '#9E9E9E';
    }
  };

  const getStatusText = () => {
    switch (apiStatus) {
      case 'connected': return 'API Connected';
      case 'error': return 'API Error';
      case 'disconnected': return 'API Disconnected';
      default: return 'Checking...';
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Argumentation Analysis</h1>
        <div className="api-status" style={{ color: getStatusColor() }}>
          ● {getStatusText()}
        </div>
      </header>

      <nav className="nav-tabs">
        <button 
          className={activeTab === 'text-analysis' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('text-analysis')}
        >
          Text Analysis
        </button>
        <button 
          className={activeTab === 'fallacy-detection' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('fallacy-detection')}
        >
          Fallacy Detection
        </button>
        <button 
          className={activeTab === 'logic-analysis' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('logic-analysis')}
        >
          Logic Analysis
        </button>
      </nav>

      <main className="main-content">
        {activeTab === 'text-analysis' && <TextAnalysis />}
        {activeTab === 'fallacy-detection' && <FallacyDetection />}
        {activeTab === 'logic-analysis' && <LogicAnalysis />}
      </main>
    </div>
  );
}

export default App;
