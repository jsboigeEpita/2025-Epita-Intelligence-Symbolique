import React, { useState, useCallback } from 'react';
import { useArgumentationAPI } from './hooks/useArgumentationAPI';
import './ValidationForm.css';

/**
 * Composant pour la validation d'arguments logiques
 * 
 * Fonctionnalités :
 * - Saisie de prémisses multiples
 * - Sélection du type d'argument
 * - Validation en temps réel
 * - Affichage détaillé des résultats
 */
const ValidationForm = () => {
  const [premises, setPremises] = useState(['']);
  const [conclusion, setConclusion] = useState('');
  const [argumentType, setArgumentType] = useState('deductive');
  const [result, setResult] = useState(null);
  
  const { validateArgument, loading, error } = useArgumentationAPI();

  // Ajouter une nouvelle prémisse
  const addPremise = useCallback(() => {
    setPremises(prev => [...prev, '']);
  }, []);

  // Supprimer une prémisse
  const removePremise = useCallback((index) => {
    setPremises(prev => prev.filter((_, i) => i !== index));
  }, []);

  // Modifier une prémisse
  const updatePremise = useCallback((index, value) => {
    setPremises(prev => prev.map((premise, i) => i === index ? value : premise));
  }, []);

  // Valider l'argument
  const handleValidate = useCallback(async () => {
    const validPremises = premises.filter(p => p.trim());
    
    if (validPremises.length === 0) {
      alert('Veuillez entrer au moins une prémisse');
      return;
    }
    
    if (!conclusion.trim()) {
      alert('Veuillez entrer une conclusion');
      return;
    }

    try {
      const validation = await validateArgument(validPremises, conclusion, argumentType);
      setResult(validation);
    } catch (err) {
      console.error('Erreur de validation:', err);
    }
  }, [premises, conclusion, argumentType, validateArgument]);

  // Réinitialiser le formulaire
  const handleReset = useCallback(() => {
    setPremises(['']);
    setConclusion('');
    setArgumentType('deductive');
    setResult(null);
  }, []);

  // Charger un exemple
  const loadExample = useCallback((exampleType) => {
    const examples = {
      valid_syllogism: {
        premises: [
          'Tous les hommes sont mortels',
          'Socrate est un homme'
        ],
        conclusion: 'Socrate est mortel',
        type: 'deductive'
      },
      invalid_syllogism: {
        premises: [
          'Tous les chats sont des animaux',
          'Tous les chiens sont des animaux'
        ],
        conclusion: 'Tous les chats sont des chiens',
        type: 'deductive'
      },
      inductive_reasoning: {
        premises: [
          'Le soleil s\'est levé tous les jours depuis des millénaires',
          'Les lois physiques sont constantes'
        ],
        conclusion: 'Le soleil se lèvera demain',
        type: 'inductive'
      },
      abductive_reasoning: {
        premises: [
          'La pelouse est mouillée',
          'Il pleut généralement la nuit'
        ],
        conclusion: 'Il a probablement plu cette nuit',
        type: 'abductive'
      }
    };

    const example = examples[exampleType];
    if (example) {
      setPremises(example.premises);
      setConclusion(example.conclusion);
      setArgumentType(example.type);
      setResult(null);
    }
  }, []);

  return (
    <div className="validation-form">
      <div className="form-header">
        <h2>✅ Validation d'Arguments</h2>
        <p>Vérifiez la validité logique de vos arguments en analysant la relation entre prémisses et conclusion.</p>
      </div>

      {/* Exemples prédéfinis */}
      <div className="examples-section">
        <h3>📚 Exemples</h3>
        <div className="examples-buttons">
          <button 
            onClick={() => loadExample('valid_syllogism')}
            className="example-btn valid"
            disabled={loading}
          >
            Syllogisme valide
          </button>
          <button 
            onClick={() => loadExample('invalid_syllogism')}
            className="example-btn invalid"
            disabled={loading}
          >
            Syllogisme invalide
          </button>
          <button 
            onClick={() => loadExample('inductive_reasoning')}
            className="example-btn inductive"
            disabled={loading}
          >
            Raisonnement inductif
          </button>
          <button 
            onClick={() => loadExample('abductive_reasoning')}
            className="example-btn abductive"
            disabled={loading}
          >
            Raisonnement abductif
          </button>
        </div>
      </div>

      {/* Formulaire de saisie */}
      <div className="form-content">
        {/* Prémisses */}
        <div className="premises-section">
          <h3>📝 Prémisses</h3>
          <p className="section-description">
            Entrez les prémisses de votre argument (les affirmations de base).
          </p>
          
          {premises.map((premise, index) => (
            <div key={index} className="premise-input-group">
              <label className="premise-label">
                Prémisse {index + 1}
              </label>
              <div className="premise-input-container">
                <textarea
                  value={premise}
                  onChange={(e) => updatePremise(index, e.target.value)}
                  placeholder={`Entrez la prémisse ${index + 1}...`}
                  className="premise-input"
                  rows={2}
                  disabled={loading}
                />
                {premises.length > 1 && (
                  <button
                    onClick={() => removePremise(index)}
                    className="remove-premise-btn"
                    disabled={loading}
                    title="Supprimer cette prémisse"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
          ))}
          
          <button
            onClick={addPremise}
            className="add-premise-btn"
            disabled={loading || premises.length >= 10}
          >
            ➕ Ajouter une prémisse
          </button>
        </div>

        {/* Conclusion */}
        <div className="conclusion-section">
          <h3>🎯 Conclusion</h3>
          <p className="section-description">
            Entrez la conclusion que vous tirez de vos prémisses.
          </p>
          
          <textarea
            value={conclusion}
            onChange={(e) => setConclusion(e.target.value)}
            placeholder="Entrez votre conclusion..."
            className="conclusion-input"
            rows={3}
            disabled={loading}
          />
        </div>

        {/* Type d'argument */}
        <div className="argument-type-section">
          <h3>🔍 Type d'argument</h3>
          <p className="section-description">
            Sélectionnez le type de raisonnement utilisé.
          </p>
          
          <div className="argument-type-options">
            <label className="argument-type-option">
              <input
                type="radio"
                value="deductive"
                checked={argumentType === 'deductive'}
                onChange={(e) => setArgumentType(e.target.value)}
                disabled={loading}
              />
              <div className="option-content">
                <strong>Déductif</strong>
                <span>La conclusion découle nécessairement des prémisses</span>
              </div>
            </label>
            
            <label className="argument-type-option">
              <input
                type="radio"
                value="inductive"
                checked={argumentType === 'inductive'}
                onChange={(e) => setArgumentType(e.target.value)}
                disabled={loading}
              />
              <div className="option-content">
                <strong>Inductif</strong>
                <span>La conclusion est probable basée sur les prémisses</span>
              </div>
            </label>
            
            <label className="argument-type-option">
              <input
                type="radio"
                value="abductive"
                checked={argumentType === 'abductive'}
                onChange={(e) => setArgumentType(e.target.value)}
                disabled={loading}
              />
              <div className="option-content">
                <strong>Abductif</strong>
                <span>La conclusion est la meilleure explication possible</span>
              </div>
            </label>
          </div>
        </div>

        {/* Boutons d'action */}
        <div className="form-actions">
          <button
            onClick={handleValidate}
            disabled={loading || !conclusion.trim() || premises.every(p => !p.trim())}
            className="validate-btn primary"
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Validation...
              </>
            ) : (
              '🚀 Valider l\'argument'
            )}
          </button>
          
          <button
            onClick={handleReset}
            disabled={loading}
            className="reset-btn secondary"
          >
            🔄 Réinitialiser
          </button>
        </div>
      </div>

      {/* Affichage des erreurs */}
      {error && (
        <div className="error-message">
          <h4>❌ Erreur</h4>
          <p>{error}</p>
        </div>
      )}

      {/* Résultats de validation */}
      {result && (
        <div className="validation-results">
          <h3>📊 Résultats de la validation</h3>
          
          {/* Vue d'ensemble */}
          <div className="results-overview">
            <div className="result-card">
              <div className={`result-status ${result.result.is_valid ? 'valid' : 'invalid'}`}>
                {result.result.is_valid ? '✅ Valide' : '❌ Invalide'}
              </div>
              <div className="result-type">
                Argument {result.argument_type}
              </div>
            </div>
            
            <div className="result-metrics">
              <div className="metric">
                <span className="metric-label">Validité</span>
                <span className="metric-value">
                  {(result.result.validity_score * 100).toFixed(1)}%
                </span>
              </div>
              <div className="metric">
                <span className="metric-label">Solidité</span>
                <span className="metric-value">
                  {(result.result.soundness_score * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>

          {/* Analyse des prémisses */}
          {result.result.premise_analysis && result.result.premise_analysis.length > 0 && (
            <div className="premise-analysis">
              <h4>📝 Analyse des prémisses</h4>
              {result.result.premise_analysis.map((analysis, index) => (
                <div key={index} className="premise-analysis-item">
                  <div className="premise-text">
                    <strong>Prémisse {index + 1}:</strong> {analysis.text}
                  </div>
                  <div className="premise-scores">
                    <span className="score">
                      Clarté: {(analysis.clarity_score * 100).toFixed(0)}%
                    </span>
                    <span className="score">
                      Spécificité: {(analysis.specificity_score * 100).toFixed(0)}%
                    </span>
                    <span className="score">
                      Crédibilité: {(analysis.credibility_score * 100).toFixed(0)}%
                    </span>
                    <span className="score overall">
                      Force: {(analysis.strength * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Problèmes identifiés */}
          {result.result.issues && result.result.issues.length > 0 && (
            <div className="issues-section">
              <h4>⚠️ Problèmes identifiés</h4>
              <ul className="issues-list">
                {result.result.issues.map((issue, index) => (
                  <li key={index} className="issue-item">
                    {issue}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggestions d'amélioration */}
          {result.result.suggestions && result.result.suggestions.length > 0 && (
            <div className="suggestions-section">
              <h4>💡 Suggestions d'amélioration</h4>
              <ul className="suggestions-list">
                {result.result.suggestions.map((suggestion, index) => (
                  <li key={index} className="suggestion-item">
                    {suggestion}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Métadonnées */}
          <div className="result-metadata">
            <span>Temps de traitement: {(result.processing_time * 1000).toFixed(0)}ms</span>
            <span>Type d'argument: {result.argument_type}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default ValidationForm;