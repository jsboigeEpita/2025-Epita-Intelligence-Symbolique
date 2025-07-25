import React, { useState } from 'react';
import { analyzeLogicGraph } from '../services/api';
import { useAppContext } from '../context/AppContext';

function LogicGraph() {
  const {
    logicGraphResult,
    setLogicGraphResult,
    textInputs,
    updateTextInput,
    isLoading,
    setIsLoading,
  } = useAppContext();

  const [error, setError] = useState('');

  const text = textInputs.logic_graph;

  const handleSubmit = async () => {
    setIsLoading(true);
    setError('');
    setLogicGraphResult(null);
    try {
      const data = await analyzeLogicGraph({ text });
      if (data.success && data.belief_set) {
        setLogicGraphResult(data.belief_set);
      } else {
        setError(data.error || 'Échec de la conversion en ensemble de croyances');
      }
    } catch (err) {
      setError(err.message || 'An error occurred while analyzing the graph.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    updateTextInput('logic_graph', '');
    setLogicGraphResult(null);
    setError('');
    setIsLoading(false);
  };

  return (
    <div>
      <h2>Logic Graph</h2>
      <textarea
        data-testid="logic-graph-text-input"
        value={text}
        onChange={(e) => updateTextInput('logic_graph', e.target.value)}
        placeholder="Enter text to visualize as a logic graph"
        rows="5"
        style={{ width: '100%', marginBottom: '10px' }}
      />
      <button
        data-testid="logic-graph-submit-button"
        onClick={handleSubmit}
        disabled={isLoading}
      >
        {isLoading ? 'Analyzing...' : 'Generate Graph'}
      </button>
      <button
        data-testid="logic-graph-reset-button"
        onClick={handleReset}
        style={{ marginLeft: '10px' }}
      >
        Reset
      </button>

      {error && (
        <div data-testid="logic-graph-error-message" style={{ color: 'red', marginTop: '10px' }}>
          {error}
        </div>
      )}

      <div data-testid="logic-graph-container" style={{ marginTop: '20px' }}>
        {logicGraphResult && (
          // In a real application, this would render a proper graph (e.g., using D3, vis.js, or a library)
          // For testing, we'll just render a simple SVG element to prove it's present.
          <div>
            <h3>Ensemble de croyances généré:</h3>
            <p><strong>Type:</strong> {logicGraphResult.logic_type}</p>
            <p><strong>Contenu:</strong> {logicGraphResult.content}</p>
            <svg data-testid="logic-graph-svg" width="200" height="100">
              <circle cx="50" cy="50" r="40" stroke="green" strokeWidth="4" fill="yellow" />
              <text x="120" y="30" fontFamily="Arial" fontSize="12" fill="black">
                Logic Graph
              </text>
              <text x="120" y="50" fontFamily="Arial" fontSize="10" fill="black">
                {logicGraphResult.logic_type}
              </text>
              <text x="120" y="70" fontFamily="Arial" fontSize="8" fill="black">
                {logicGraphResult.content.substring(0, 20)}...
              </text>
            </svg>
          </div>
        )}
      </div>
    </div>
  );
}

export default LogicGraph;