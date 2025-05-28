import axios from 'axios';
import React, { useState } from 'react';

const TextAnalysis = () => {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleAnalyze = async () => {
    if (!text.trim()) {
      setError('Please enter some text to analyze');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await axios.post('http://localhost:5000/api/analyze', {
        text: text,
        options: {
          detect_fallacies: true,
          analyze_structure: true,
          evaluate_coherence: true
        }
      });

      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to analyze text');
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
      <h2>Text Analysis</h2>
      
      <div className="form-group">
        <label htmlFor="text-input">
          Enter text for argumentation analysis:
        </label>
        <textarea
          id="text-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter your argumentative text here..."
          disabled={loading}
        />
      </div>

      <div style={{ display: 'flex', gap: '1rem' }}>
        <button 
          className="btn" 
          onClick={handleAnalyze}
          disabled={loading || !text.trim()}
        >
          {loading ? (
            <div className="loading">
              <div className="spinner"></div>
              Analyzing...
            </div>
          ) : (
            'Analyze Text'
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
          <h3>Analysis Results</h3>
          <div className="result-content">
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default TextAnalysis; 