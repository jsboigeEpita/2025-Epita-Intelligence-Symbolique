import React, { useState } from 'react';
import { validateArgument } from '../services/api';
import './ValidationForm.css';

/**
 * Composant pour la validation d'arguments logiques
 */
const ValidationForm = () => {
  // État du formulaire
  const [premises, setPremises] = useState(['']);
  const [conclusion, setConclusion] = useState('');
  const [argumentType, setArgumentType] = useState('deductive');
  
  // État de l'interface
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Types d'arguments disponibles
  const argumentTypes = [
    { 
      id: 'deductive', 
      name: 'Déductif', 
      description: 'La conclusion suit nécessairement des prémisses'
    },
    { 
      id: 'inductive', 
      name: 'Inductif', 
      description: 'La conclusion est probable basée sur les prémisses'
    },
    { 
      id: 'abductive', 
      name: 'Abductif', 
      description: 'La meilleure explication possible des prémisses'
    }
  ];

  // Ajout d'une prémisse
  const addPremise = () => {
    setPremises(prev => [...prev, '']);
  };

  // Modification d'une prémisse
  const updatePremise = (index, value) => {
    setPremises(prev => prev.map((premise, i) => 
      i === index ? value : premise
    ));
  };

  // Suppression d'une prémisse
  const removePremise = (index) => {
    if (premises.length > 1) {
      setPremises(prev => prev.filter((_, i) => i !== index));
    }
  };

  // Validation de l'argument
  const handleValidation = async () => {
    // Vérification des champs
    const validPremises = premises.filter(p => p.trim());
    if (validPremises.length === 0) {
      alert('Veuillez saisir au moins une prémisse');
      return;
    }
    if (!conclusion.trim()) {
      alert('Veuillez saisir une conclusion');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await validateArgument(validPremises, conclusion.trim(), argumentType);
      setResult(response);
    } catch (err) {
      setError(err.message);
      console.error('Erreur lors de la validation:', err);
    } finally {
      setLoading(false);
    }
  };

  // Exemple prédéfini
  const loadExample = () => {
    setPremises([
      'Tous les chats sont des animaux',
      'Félix est un chat'
    ]);
    setConclusion('Félix est un animal');
    setArgumentType('deductive');
    setResult(null);
    setError(null);
  };

  // Réinitialisation
  const resetForm = () => {
    setPremises(['']);
    setConclusion('');
    setArgumentType('deductive');
    setResult(null);
    setError(null);
  };

  // Rendu du formulaire de validation
  const renderValidationForm = () => (
    <div className="validation-section">
      <h3>📋 Structure de l'argument</h3>
      
      {/* Type d'argument */}
      <div className="form-group">
        <label htmlFor="argument-type">Type d'argument:</label>
        <select
          id="argument-type"
          value={argumentType}
          onChange={(e) => setArgumentType(e.target.value)}
          className="form-select"
        >
          {argumentTypes.map(type => (
            <option key={type.id} value={type.id} title={type.description}>
              {type.name}
            </option>
          ))}
        </select>
        <small className="form-help">
          {argumentTypes.find(t => t.id === argumentType)?.description}
        </small>
      </div>

      {/* Prémisses */}
      <div className="premises-section">
        <div className="premises-header">
          <h4>🔹 Prémisses</h4>
          <button onClick={addPremise} className="add-premise-button">
            ➕ Ajouter une prémisse
          </button>
        </div>
        
        <div className="premises-list">
          {premises.map((premise, index) => (
            <div key={index} className="premise-item">
              <div className="premise-label">Prémisse {index + 1}:</div>
              <div className="premise-input-group">
                <textarea
                  value={premise}
                  onChange={(e) => updatePremise(index, e.target.value)}
                  placeholder={`Saisissez la prémisse ${index + 1}...`}
                  className="premise-textarea"
                  rows={2}
                />
                {premises.length > 1 && (
                  <button 
                    onClick={() => removePremise(index)}
                    className="remove-premise-button"
                    title="Supprimer cette prémisse"
                  >
                    ❌
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Conclusion */}
      <div className="form-group">
        <label htmlFor="conclusion">🎯 Conclusion:</label>
        <textarea
          id="conclusion"
          value={conclusion}
          onChange={(e) => setConclusion(e.target.value)}
          placeholder="Saisissez la conclusion de votre argument..."
          className="form-textarea"
          rows={3}
        />
      </div>

      {/* Boutons d'action */}
      <div className="action-buttons">
        <button 
          onClick={handleValidation}
          className="validate-button"
          disabled={loading || premises.every(p => !p.trim()) || !conclusion.trim()}
        >
          {loading ? '🔄 Validation...' : '✅ Valider l\'argument'}
        </button>
        
        <button onClick={loadExample} className="example-button">
          📝 Charger un exemple
        </button>
        
        <button onClick={resetForm} className="reset-button">
          🔄 Réinitialiser
        </button>
      </div>
    </div>
  );

  // Rendu des résultats
  const renderResults = () => {
    if (!result) return null;

    return (
      <div className="validation-section results-section">
        <h3>📊 Résultats de la validation</h3>
        
        {/* Statut global */}
        <div className={`validation-status ${result.is_valid ? 'valid' : 'invalid'}`}>
          <div className="status-icon">
            {result.is_valid ? '✅' : '❌'}
          </div>
          <div className="status-content">
            <h4>
              {result.is_valid ? 'Argument valide' : 'Argument invalide'}
            </h4>
            <p className="status-description">
              {result.validation_message || 'Aucune description disponible'}
            </p>
          </div>
          {result.confidence && (
            <div className="confidence-score">
              <span className="confidence-label">Confiance:</span>
              <span className="confidence-value">
                {Math.round(result.confidence * 100)}%
              </span>
            </div>
          )}
        </div>

        {/* Détails de validation */}
        {result.details && (
          <div className="validation-details">
            <h4>🔍 Détails de l'analyse</h4>
            
            {result.details.structure_analysis && (
              <div className="detail-item">
                <strong>Structure logique:</strong>
                <p>{result.details.structure_analysis}</p>
              </div>
            )}
            
            {result.details.logical_validity && (
              <div className="detail-item">
                <strong>Validité logique:</strong>
                <p>{result.details.logical_validity}</p>
              </div>
            )}
            
            {result.details.soundness_check && (
              <div className="detail-item">
                <strong>Vérification de solidité:</strong>
                <p>{result.details.soundness_check}</p>
              </div>
            )}
          </div>
        )}

        {/* Problèmes identifiés */}
        {result.issues && result.issues.length > 0 && (
          <div className="validation-issues">
            <h4>⚠️ Problèmes identifiés</h4>
            <div className="issues-list">
              {result.issues.map((issue, index) => (
                <div key={index} className={`issue-item ${issue.severity || 'warning'}`}>
                  <div className="issue-header">
                    <span className="issue-type">{issue.type || 'Problème'}</span>
                    <span className="issue-severity">{issue.severity || 'Avertissement'}</span>
                  </div>
                  <div className="issue-message">{issue.message}</div>
                  {issue.suggestion && (
                    <div className="issue-suggestion">
                      <strong>Suggestion:</strong> {issue.suggestion}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Suggestions d'amélioration */}
        {result.suggestions && result.suggestions.length > 0 && (
          <div className="validation-suggestions">
            <h4>💡 Suggestions d'amélioration</h4>
            <ul className="suggestions-list">
              {result.suggestions.map((suggestion, index) => (
                <li key={index} className="suggestion-item">
                  {suggestion}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Score de qualité */}
        {result.quality_score && (
          <div className="quality-score">
            <h4>📈 Score de qualité</h4>
            <div className="score-bar">
              <div 
                className="score-fill"
                style={{ width: `${result.quality_score * 100}%` }}
              ></div>
            </div>
            <div className="score-text">
              {Math.round(result.quality_score * 100)}/100
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="validation-form">
      <div className="validation-header">
        <h2>✅ Validation d'Arguments Logiques</h2>
        <p>Vérifiez la validité logique de vos arguments en spécifiant les prémisses et la conclusion.</p>
      </div>

      {error && (
        <div className="error-message">
          <strong>❌ Erreur:</strong> {error}
        </div>
      )}

      <div className="validation-content">
        {renderValidationForm()}
        {renderResults()}
      </div>
    </div>
  );
};

export default ValidationForm; 