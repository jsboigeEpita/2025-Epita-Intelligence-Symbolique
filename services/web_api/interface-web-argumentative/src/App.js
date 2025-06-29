import React, { /* useEffect, useState */ } from 'react';
import './App.css';
// import ArgumentAnalyzer from './components/ArgumentAnalyzer';
// import ArgumentReconstructor from './components/ArgumentReconstructor';
// import FallacyDetector from './components/FallacyDetector';
// import FrameworkBuilder from './components/FrameworkBuilder';
// import LogicGraph from './components/LogicGraph';
// import ValidationForm from './components/ValidationForm';
// import { checkAPIHealth } from './services/api';

function App() {
  console.log('[DEBUG] Le composant App est sur le point de rendre (version simplifiée).');
  // const [activeTab, setActiveTab] = useState('analyzer');
  // const [apiStatus, setApiStatus] = useState('checking');
  // const [apiError, setApiError] = useState(null);

  // useEffect(() => {
  //   console.log('[Debug] useEffect a démarré. Appel de checkAPIHealth...');
  //   // Vérifier l'état de l'API au démarrage
  //   checkAPIHealth()
  //     .then((data) => {
  //       console.log('[Debug] checkAPIHealth a réussi. Données:', data);
  //       console.log('[Debug] Appel de setApiStatus("connected")');
  //       setApiStatus('connected');
  //     })
  //     .catch((error) => {
  //       console.error('[Debug] checkAPIHealth a échoué:', error);
  //       setApiStatus('disconnected');
  //       setApiError(error.message);
  //     });
  // }, []);

  // const tabs = [
  //   { id: 'analyzer', label: '🔍 Analyseur', component: ArgumentAnalyzer },
  //   // { id: 'fallacies', label: '⚠️ Sophismes', component: FallacyDetector },
  //   // { id: 'reconstructor', label: '🔄 Reconstructeur', component: ArgumentReconstructor },
  //   // { id: 'logic-graph', label: '📊 Graphe Logique', component: LogicGraph },
  //   // { id: 'validation', label: '✅ Validation', component: ValidationForm },
  //   // { id: 'framework', label: '🏗️ Framework', component: FrameworkBuilder }
  // ];

  // const renderActiveComponent = () => {
  //   const activeTabData = tabs.find(tab => tab.id === activeTab);
  //   if (activeTabData) {
  //     const Component = activeTabData.component;
  //     return <Component />;
  //   }
  //   return null;
  // };

  return (
    <div className="App">
      <h1>Test de Rendu React Minimal</h1>
      <p>Si ce message s'affiche, le problème vient des composants ou des services qui ont été commentés.</p>
    </div>
  );
}

export default App;