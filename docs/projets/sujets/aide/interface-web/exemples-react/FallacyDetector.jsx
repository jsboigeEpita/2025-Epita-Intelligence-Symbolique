import React, { useState, useEffect } from 'react';
import { useArgumentationAPI } from './hooks/useArgumentationAPI';
import './FallacyDetector.css';

/**
 * Composant pour la détection de sophismes dans un texte
 * 
 * Ce composant utilise l'API d'argumentation pour détecter
 * les sophismes logiques et informels dans un texte donné.
 */
const FallacyDetector = ({ 
  initialText = '', 
  onFallaciesDetected = null,
  showAdvancedOptions = true 
}) => {
  // État local
  const [text, setText] = useState(initialText);
  const [options, setOptions] = useState({
    severity_threshold: 0.5,
    categories: [],
    max_fallacies: 10
  });
  const [showOptions, setShowOptions] = useState(false);

  // Hook API
  const { detectFallacies, loading, error } = useArgumentationAPI();
  
  // État des résultats
  const [results, setResults] = useState(null);
  const [selectedFallacy, setSelectedFallacy] = useState(null);

  // Catégories disponibles
  const availableCategories = [
    { id: 'formal', name: 'Sophismes formels', description: 'Erreurs de logique formelle' },
    { id: 'informal', name: 'Sophismes informels', description: 'Erreurs de raisonnement contextuel' },
    { id: 'emotional', name: 'Appels émotionnels', description: 'Manipulation émotionnelle' }
  ];

  // Effet pour notifier les résultats
  useEffect(() => {
    if (results && onFallaciesDetected) {
      onFallaciesDetected(results);
    }
  }, [results, onFallaciesDetected]);

  // Gestion de la soumission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!text.trim()) {
      alert('Veuillez saisir un texte à analyser');
      return;
    }

    try {
      const response = await detectFallacies(text, options);
      setResults(response);
      setSelectedFallacy(null);
    } catch (err) {
      console.error('Erreur lors de la détection:', err);
    }
  };

  // Gestion des options
  const handleOptionChange = (key, value) => {
    setOptions(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleCategoryToggle = (categoryId) => {
    setOptions(prev => ({
      ...prev,
      categories: prev.categories.includes(categoryId)
        ? prev.categories.filter(id => id !== categoryId)
        : [...prev.categories, categoryId]
    }));
  };

  // Rendu des options avancées
  const renderAdvancedOptions = () => {
    if (!showAdvancedOptions || !showOptions) return null;

    return (
      <div className="fallacy-options">
        <h4>Options de détection</h4>
        
        {/* Seuil de sévérité */}
        <div className="option-group">
          <label htmlFor="severity-threshold">
            Seuil de sévérité: {options.severity_threshold}
          </label>
          <input
            id="severity-threshold"
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={options.severity_threshold}
            onChange={(e) => handleOptionChange('severity_threshold', parseFloat(e.target.value))}
            className="severity-slider"
          />
          <div className="severity-labels">
            <span>Faible</span>
            <span>Élevée</span>
          </div>
        </div>

        {/* Catégories */}
        <div className="option-group">
          <label>Catégories à détecter:</label>
          <div className="category-checkboxes">
            {availableCategories.map(category => (
              <label key={category.id} className="category-checkbox">
                <input
                  type="checkbox"
                  checked={options.categories.includes(category.id)}
                  onChange={() => handleCategoryToggle(category.id)}
                />
                <span className="category-name">{category.name}</span>
                <span className="category-description">{category.description}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Nombre maximum */}
        <div className="option-group">
          <label htmlFor="max-fallacies">
            Nombre maximum de sophismes: {options.max_fallacies}
          </label>
          <input
            id="max-fallacies"
            type="range"
            min="1"
            max="20"
            value={options.max_fallacies}
            onChange={(e) => handleOptionChange('max_fallacies', parseInt(e.target.value))}
            className="max-slider"
          />
        </div>
      </div>
    );
  };

  // Rendu d'un sophisme
  const renderFallacy = (fallacy, index) => {
    const isSelected = selectedFallacy === index;
    const severityClass = fallacy.severity >= 0.7 ? 'high' : 
                         fallacy.severity >= 0.4 ? 'medium' : 'low';

    return (
      <div 
        key={index}
        className={`fallacy-item ${severityClass} ${isSelected ? 'selected' : ''}`}
        onClick={() => setSelectedFallacy(isSelected ? null : index)}
      >
        <div className="fallacy-header">
          <h4 className="fallacy-name">{fallacy.name}</h4>
          <div className="fallacy-metrics">
            <span className={`severity-badge ${severityClass}`}>
              Sévérité: {Math.round(fallacy.severity * 100)}%
            </span>
            <span className="confidence-badge">
              Confiance: {Math.round(fallacy.confidence * 100)}%
            </span>
          </div>
        </div>

        <p className="fallacy-description">{fallacy.description}</p>

        {isSelected && (
          <div className="fallacy-details">
            {fallacy.context && (
              <div className="fallacy-context">
                <strong>Contexte:</strong>
                <blockquote>"{fallacy.context}"</blockquote>
              </div>
            )}
            
            {fallacy.explanation && (
              <div className="fallacy-explanation">
                <strong>Explication:</strong>
                <p>{fallacy.explanation}</p>
              </div>
            )}

            {fallacy.location && (
              <div className="fallacy-location">
                <strong>Position:</strong> 
                Caractères {fallacy.location.start} à {fallacy.location.end}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  // Rendu des statistiques
  const renderStatistics = () => {
    if (!results) return null;

    return (
      <div className="fallacy-statistics">
        <h4>Statistiques de détection</h4>
        
        <div className="stats-grid">
          <div className="stat-item">
            <span className="stat-label">Total détecté:</span>
            <span className="stat-value">{results.fallacy_count}</span>
          </div>
          
          <div className="stat-item">
            <span className="stat-label">Temps de traitement:</span>
            <span className="stat-value">{Math.round(results.processing_time * 1000)}ms</span>
          </div>
        </div>

        {/* Distribution par sévérité */}
        {results.severity_distribution && (
          <div className="severity-distribution">
            <h5>Distribution par sévérité:</h5>
            <div className="distribution-bars">
              {Object.entries(results.severity_distribution).map(([level, count]) => (
                <div key={level} className="distribution-bar">
                  <span className="bar-label">{level}:</span>
                  <div className="bar-container">
                    <div 
                      className={`bar-fill ${level}`}
                      style={{ width: `${(count / results.fallacy_count) * 100}%` }}
                    />
                  </div>
                  <span className="bar-count">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Distribution par catégorie */}
        {results.category_distribution && (
          <div className="category-distribution">
            <h5>Distribution par catégorie:</h5>
            <div className="distribution-bars">
              {Object.entries(results.category_distribution).map(([category, count]) => (
                <div key={category} className="distribution-bar">
                  <span className="bar-label">{category}:</span>
                  <div className="bar-container">
                    <div 
                      className="bar-fill category"
                      style={{ width: `${(count / results.fallacy_count) * 100}%` }}
                    />
                  </div>
                  <span className="bar-count">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fallacy-detector">
      <div className="detector-header">
        <h3>Détecteur de Sophismes</h3>
        <p>Analysez votre texte pour identifier les erreurs de raisonnement</p>
      </div>

      <form onSubmit={handleSubmit} className="detector-form">
        {/* Zone de texte */}
        <div className="input-group">
          <label htmlFor="text-input">Texte à analyser:</label>
          <textarea
            id="text-input"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Saisissez le texte que vous souhaitez analyser pour détecter les sophismes..."
            rows={6}
            className="text-input"
            disabled={loading}
          />
          <div className="input-info">
            {text.length} caractères
          </div>
        </div>

        {/* Bouton d'options */}
        {showAdvancedOptions && (
          <button
            type="button"
            onClick={() => setShowOptions(!showOptions)}
            className="options-toggle"
          >
            {showOptions ? 'Masquer' : 'Afficher'} les options avancées
          </button>
        )}

        {/* Options avancées */}
        {renderAdvancedOptions()}

        {/* Bouton de soumission */}
        <button 
          type="submit" 
          disabled={loading || !text.trim()}
          className="submit-button"
        >
          {loading ? 'Analyse en cours...' : 'Détecter les sophismes'}
        </button>
      </form>

      {/* Affichage des erreurs */}
      {error && (
        <div className="error-message">
          <strong>Erreur:</strong> {error}
        </div>
      )}

      {/* Résultats */}
      {results && (
        <div className="detection-results">
          <div className="results-header">
            <h4>Résultats de la détection</h4>
            {results.fallacy_count === 0 ? (
              <p className="no-fallacies">Aucun sophisme détecté dans ce texte.</p>
            ) : (
              <p className="fallacies-found">
                {results.fallacy_count} sophisme{results.fallacy_count > 1 ? 's' : ''} détecté{results.fallacy_count > 1 ? 's' : ''}
              </p>
            )}
          </div>

          {/* Liste des sophismes */}
          {results.fallacies && results.fallacies.length > 0 && (
            <div className="fallacies-list">
              {results.fallacies.map((fallacy, index) => renderFallacy(fallacy, index))}
            </div>
          )}

          {/* Statistiques */}
          {renderStatistics()}
        </div>
      )}
    </div>
  );
};

export default FallacyDetector;