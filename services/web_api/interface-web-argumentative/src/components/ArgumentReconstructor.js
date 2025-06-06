import React, { useState } from 'react';
import * as api from '../services/api';

function ArgumentReconstructor() {
  const [argument, setArgument] = useState('');
  const [reconstruction, setReconstruction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleReconstruct = async () => {
    setLoading(true);
    setError(null);
    setReconstruction(null);
    try {
      const response = await api.analyzeText(argument);
      setReconstruction(response);
    } catch (err) {
      console.error("Erreur lors de la reconstruction de l'argument:", err);
      setError(err.response?.data?.error || 'Une erreur inattendue est survenue.');
    }
    setLoading(false);
  };

  const handleReset = () => {
    setArgument('');
    setReconstruction(null);
    setError(null);
    setLoading(false);
  };

  return (
    <div>
      <h2>Reconstructeur d'Arguments</h2>
      <textarea
        data-testid="reconstructor-text-input"
        value={argument}
        onChange={(e) => setArgument(e.target.value)}
        placeholder="Entrez l'argument à reconstruire..."
        rows="5"
        style={{ width: '100%', marginTop: '10px' }}
      />
      <button
        data-testid="reconstructor-submit-button"
        onClick={handleReconstruct}
        disabled={loading}
        style={{ marginTop: '10px' }}
      >
        {loading ? 'Reconstruction en cours...' : 'Reconstruire'}
      </button>
      <button
        data-testid="reconstructor-reset-button"
        onClick={handleReset}
        style={{ marginTop: '10px', marginLeft: '10px' }}
      >
        Réinitialiser
      </button>
      {loading && <div className="loading-spinner" data-testid="loading-spinner"></div>}
      {error && (
        <div data-testid="reconstructor-error-message" style={{ color: 'red', marginTop: '20px' }}>
          {error}
        </div>
      )}
      {reconstruction && (
        <div data-testid="reconstructor-results-container" style={{ marginTop: '20px' }}>
          <h3>Résultats de la Reconstruction :</h3>
          {reconstruction.argument_structure && (
            <div>
              <h4>Prémisses</h4>
              <ul>
                {reconstruction.argument_structure.premises.map((premise, index) => (
                  <li key={index}>Prémisse {index + 1}: {premise}</li>
                ))}
              </ul>
              <h4>Conclusion</h4>
              <p>{reconstruction.argument_structure.conclusion}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ArgumentReconstructor;