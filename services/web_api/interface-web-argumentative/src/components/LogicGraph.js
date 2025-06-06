import React, { useState } from 'react';
import { analyzeLogicGraph } from '../services/api';

function LogicGraph() {
  const [text, setText] = useState('');
  const [graphData, setGraphData] = useState(null);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async () => {
    setIsLoading(true);
    setError('');
    setGraphData(null);
    try {
      const data = await analyzeLogicGraph({ text });
      setGraphData(data.graph);
    } catch (err) {
      setError(err.message || 'An error occurred while analyzing the graph.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setText('');
    setGraphData(null);
    setError('');
    setIsLoading(false);
  };

  return (
    <div>
      <h2>Logic Graph</h2>
      <textarea
        data-testid="logic-graph-text-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
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
        {graphData && (
          // In a real application, this would render a proper graph (e.g., using D3, vis.js, or a library)
          // For testing, we'll just render a simple SVG element to prove it's present.
          <svg data-testid="logic-graph-svg" width="100" height="100">
            <circle cx="50" cy="50" r="40" stroke="green" strokeWidth="4" fill="yellow" />
          </svg>
        )}
      </div>
    </div>
  );
}

export default LogicGraph;