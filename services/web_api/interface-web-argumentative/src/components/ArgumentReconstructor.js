import React, { useState } from 'react';
import * as api from '../services/api';
import { useAppContext } from '../context/AppContext';

function ArgumentReconstructor() {
  const {
    reconstructionResult,
    setReconstructionResult,
    textInputs,
    updateTextInput,
    isLoading,
    setIsLoading,
  } = useAppContext();

  const [error, setError] = useState(null);

  const argument = textInputs.reconstructor;

  const handleReconstruct = async () => {
    setIsLoading(true);
    setError(null);
    setReconstructionResult(null);
    try {
      const response = await api.analyzeText(argument);
      setReconstructionResult(response);
    } catch (err) {
      console.error("Erreur lors de la reconstruction de l'argument:", err);
      setError(err.response?.data?.error || 'Une erreur inattendue est survenue.');
    }
    setIsLoading(false);
  };

  const handleReset = () => {
    updateTextInput('reconstructor', '');
    setReconstructionResult(null);
    setError(null);
    setIsLoading(false);
  };

  return (
    <div>
      <h2>Reconstructeur d'Arguments</h2>
      <textarea
        data-testid="reconstructor-text-input"
        value={argument}
        onChange={(e) => updateTextInput('reconstructor', e.target.value)}
        placeholder="Entrez l'argument à reconstruire..."
        rows="5"
        style={{ width: '100%', marginTop: '10px' }}
      />
      <button
        data-testid="reconstructor-submit-button"
        onClick={handleReconstruct}
        disabled={isLoading}
        style={{ marginTop: '10px' }}
      >
        {isLoading ? 'Reconstruction en cours...' : 'Reconstruire'}
      </button>
      <button
        data-testid="reconstructor-reset-button"
        onClick={handleReset}
        style={{ marginTop: '10px', marginLeft: '10px' }}
      >
        Réinitialiser
      </button>
      {isLoading && <div className="loading-spinner" data-testid="loading-spinner"></div>}
      {error && (
        <div data-testid="reconstructor-error-message" style={{ color: 'red', marginTop: '20px' }}>
          {error}
        </div>
      )}
      {reconstructionResult && (
        <div data-testid="reconstructor-results-container" style={{ marginTop: '20px' }}>
          <h3>Résultats de la Reconstruction :</h3>
          {reconstructionResult.argument_structure && (
            <div>
              <h4>Prémisses</h4>
              <ul>
                {reconstructionResult.argument_structure.premises.map((premise, index) => (
                  <li key={index}>Prémisse {index + 1}: {premise}</li>
                ))}
              </ul>
              <h4>Conclusion</h4>
              <p>{reconstructionResult.argument_structure.conclusion}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ArgumentReconstructor;