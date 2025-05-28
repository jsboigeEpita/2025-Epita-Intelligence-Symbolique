import axios from 'axios';
import React, { useState } from 'react';

const LogicAnalysis = () => {
  const [text, setText] = useState('');
  const [logicType, setLogicType] = useState('propositional');
  const [beliefSetId, setBeliefSetId] = useState('');
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [beliefSetResult, setBeliefSetResult] = useState(null);
  const [queryResult, setQueryResult] = useState(null);
  const [error, setError] = useState(null);

  const handleCreateBeliefSet = async () => {
    if (!text.trim()) {
      setError('Please enter some text to convert to belief set');
      return;
    }

    setLoading(true);
    setError(null);
    setBeliefSetResult(null);

    try {
      const response = await axios.post('http://localhost:5000/api/logic/belief-set', {
        text: text,
        logic_type: logicType,
        options: {
          include_explanation: true,
          max_queries: 5,
          timeout: 10.0
        }
      });

      setBeliefSetResult(response.data);
      if (response.data.belief_set?.id) {
        setBeliefSetId(response.data.belief_set.id);
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create belief set');
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteQuery = async () => {
    if (!beliefSetId.trim()) {
      setError('Please create a belief set first');
      return;
    }
    if (!query.trim()) {
      setError('Please enter a query to execute');
      return;
    }

    setLoading(true);
    setError(null);
    setQueryResult(null);

    try {
      const response = await axios.post('http://localhost:5000/api/logic/query', {
        belief_set_id: beliefSetId,
        query: query,
        logic_type: logicType,
        options: {
          include_explanation: true,
          timeout: 10.0
        }
      });

      setQueryResult(response.data);
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to execute query');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setText('');
    setQuery('');
    setBeliefSetId('');
    setBeliefSetResult(null);
    setQueryResult(null);
    setError(null);
  };

  return (
    <div className="component-container">
      <h2>Logic Analysis</h2>
      
      <div className="form-group">
        <label htmlFor="logic-type">
          Logic Type:
        </label>
        <select
          id="logic-type"
          value={logicType}
          onChange={(e) => setLogicType(e.target.value)}
          disabled={loading}
        >
          <option value="propositional">Propositional Logic</option>
          <option value="first_order">First Order Logic</option>
          <option value="modal">Modal Logic</option>
        </select>
      </div>

      <div className="form-group">
        <label htmlFor="logic-text-input">
          Enter text to convert to belief set:
        </label>
        <textarea
          id="logic-text-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter logical statements here..."
          disabled={loading}
        />
      </div>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
        <button 
          className="btn" 
          onClick={handleCreateBeliefSet}
          disabled={loading || !text.trim()}
        >
          {loading ? (
            <div className="loading">
              <div className="spinner"></div>
              Creating...
            </div>
          ) : (
            'Create Belief Set'
          )}
        </button>
      </div>

      {beliefSetResult && (
        <div className="result-container info">
          <h3>Belief Set Created</h3>
          <div className="result-content">
            <p><strong>ID:</strong> {beliefSetResult.belief_set?.id}</p>
            <p><strong>Content:</strong> {beliefSetResult.belief_set?.content}</p>
            <details>
              <summary>Full Response</summary>
              <pre>{JSON.stringify(beliefSetResult, null, 2)}</pre>
            </details>
          </div>
        </div>
      )}

      {beliefSetId && (
        <>
          <div className="form-group">
            <label htmlFor="query-input">
              Enter query to execute:
            </label>
            <input
              type="text"
              id="query-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter logical query (e.g., 'p', 'q', 'p => q')"
              disabled={loading}
            />
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button 
              className="btn" 
              onClick={handleExecuteQuery}
              disabled={loading || !query.trim()}
            >
              {loading ? (
                <div className="loading">
                  <div className="spinner"></div>
                  Executing...
                </div>
              ) : (
                'Execute Query'
              )}
            </button>
            
            <button 
              className="btn btn-secondary" 
              onClick={handleClear}
              disabled={loading}
            >
              Clear All
            </button>
          </div>
        </>
      )}

      {error && (
        <div className="result-container error">
          <h3>Error</h3>
          <div className="result-content">
            <p>{error}</p>
          </div>
        </div>
      )}

      {queryResult && (
        <div className="result-container success">
          <h3>Query Results</h3>
          <div className="result-content">
            <p><strong>Query:</strong> {queryResult.result?.query}</p>
            <p><strong>Result:</strong> {queryResult.result?.result ? 'TRUE' : 'FALSE'}</p>
            <p><strong>Explanation:</strong> {queryResult.result?.explanation}</p>
            <details>
              <summary>Full Response</summary>
              <pre>{JSON.stringify(queryResult, null, 2)}</pre>
            </details>
          </div>
        </div>
      )}
    </div>
  );
};

export default LogicAnalysis; 