import axios from 'axios';
import React, { useState } from 'react';

const FallacyDetection = () => {
  const [text, setText] = useState('');
  const [severityThreshold, setSeverityThreshold] = useState(0.5);
  const [includeContext, setIncludeContext] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleDetect = async () => {
    if (!text.trim()) {
      setError('Please enter some text to analyze');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post('http://localhost:5000/api/fallacies', {
        text: text,
        options: {
          severity_threshold: severityThreshold,
          include_context: includeContext
        }
      });

      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to detect fallacies');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setText('');
    setResult(null);
    setError(null);
  };

  return (
    <div className="component-container">
      <h2>Fallacy Detection</h2>
      
      <div className="form-group">
        <label htmlFor="fallacy-text-input">
          Enter text to analyze for fallacies:
        </label>
        <textarea
          id="fallacy-text-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter text to check for logical fallacies..."
          disabled={loading}
        />
      </div>

      <div className="grid">
        <div className="form-group">
          <label htmlFor="severity-threshold">
            Severity Threshold: {severityThreshold}
          </label>
          <input
            type="range"
            id="severity-threshold"
            min="0"
            max="1"
            step="0.1"
            value={severityThreshold}
            onChange={(e) => setSeverityThreshold(parseFloat(e.target.value))}
            disabled={loading}
          />
        </div>

        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={includeContext}
              onChange={(e) => setIncludeContext(e.target.checked)}
              disabled={loading}
              style={{ marginRight: '0.5rem' }}
            />
            Include Context
          </label>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '1rem' }}>
        <button 
          className="btn" 
          onClick={handleDetect}
          disabled={loading || !text.trim()}
        >
          {loading ? (
            <div className="loading">
              <div className="spinner"></div>
              Detecting...
            </div>
          ) : (
            'Detect Fallacies'
          )}
        </button>
        
        <button 
          className="btn btn-secondary" 
          onClick={handleClear}
          disabled={loading}
        >
          Clear
        </button>
      </div>

      {error && (
        <div className="result-container error">
          <h3>Error</h3>
          <div className="result-content">
            <p>{error}</p>
          </div>
        </div>
      )}

      {result && (
        <div className="result-container success">
          <h3>Fallacy Detection Results</h3>
          <div className="result-content">
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default FallacyDetection; 