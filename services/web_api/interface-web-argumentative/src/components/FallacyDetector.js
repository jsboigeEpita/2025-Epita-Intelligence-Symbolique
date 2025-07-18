import React, { useRef, useState } from 'react';
import { detectFallacies } from '../services/api';
import { useAppContext } from '../context/AppContext';
import './FallacyDetector.css';

const FallacyDetector = () => {
  const {
    fallacyResult,
    setFallacyResult,
    textInputs,
    updateTextInput,
    isLoading,
    setIsLoading,
  } = useAppContext();

  const [error, setError] = useState(null);
  const [options, setOptions] = useState({
    severity_threshold: 0.3,
    include_explanations: true,
    fallacy_types: 'all'
  });
  
  const textareaRef = useRef(null);
  const text = textInputs.fallacy_detector;

  // Exemples de sophismes courants
  const fallacyExamples = [
    {
      type: "Ad Hominem",
      text: "Cette théorie sur le climat est fausse parce que son auteur a été condamné pour fraude fiscale.",
      description: "Attaque la personne au lieu de l'argument"
    },
    {
      type: "Appel à l'autorité",
      text: "Cette marque de voiture est la meilleure parce que mon mécanicien le dit.",
      description: "Fait appel à une autorité non qualifiée"
    },
    {
      type: "Pente glissante",
      text: "Si on autorise les gens à conduire à 85 km/h, bientôt ils voudront conduire à 200 km/h.",
      description: "Prédit des conséquences extrêmes sans justification"
    },
    {
      type: "Faux dilemme",
      text: "Soit vous êtes avec nous, soit vous êtes contre nous.",
      description: "Présente seulement deux options alors qu'il y en a d'autres"
    },
    {
      type: "Homme de paille",
      text: "Les écologistes veulent qu'on retourne à l'âge de pierre.",
      description: "Déforme la position de l'adversaire pour la critiquer plus facilement"
    },
    {
      type: "Raisonnement circulaire",
      text: "Dieu existe parce que la Bible le dit, et la Bible est vraie parce qu'elle est la parole de Dieu.",
      description: "La conclusion est utilisée comme prémisse"
    }
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;

    setIsLoading(true);
    setError(null);
    
    try {
      const detection = await detectFallacies(text, options);
      setFallacyResult(detection);
    } catch (err) {
      setError('Erreur lors de la détection : ' + err.message);
      setFallacyResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  const loadExample = (example) => {
    updateTextInput('fallacy_detector', example.text);
    setFallacyResult(null);
    setError(null);
  };

  const clearAll = () => {
    updateTextInput('fallacy_detector', '');
    setFallacyResult(null);
    setError(null);
  };

  const getSeverityLabel = (severity) => {
    if (severity >= 0.8) return 'Critique';
    if (severity >= 0.6) return 'Élevée';
    if (severity >= 0.4) return 'Modérée';
    return 'Faible';
  };

  const getSeverityColor = (severity) => {
    if (severity >= 0.8) return 'critical';
    if (severity >= 0.6) return 'high';
    if (severity >= 0.4) return 'medium';
    return 'low';
  };

  const getFallacyTypeIcon = (type) => {
    const icons = {
      'ad_hominem': '👤',
      'appeal_to_authority': '👑',
      'slippery_slope': '⛷️',
      'false_dilemma': '🔀',
      'straw_man': '🥪',
      'circular_reasoning': '🔄',
      'appeal_to_emotion': '😢',
      'bandwagon': '🚌',
      'hasty_generalization': '⚡',
      'red_herring': '🐟'
    };
    return icons[type] || '⚠️';
  };

  return (
    <div className="fallacy-detector">
      <div className="detector-header">
        <h2>⚠️ Détecteur de Sophismes</h2>
        <p>
          Identifiez automatiquement les sophismes et erreurs de raisonnement dans vos textes.
          Analyse spécialisée avec explications détaillées et niveaux de sévérité.
        </p>
      </div>

      {/* Exemples de sophismes */}
      <div className="fallacy-examples">
        <h3>📚 Exemples de sophismes courants</h3>
        <div className="examples-grid">
          {fallacyExamples.map((example, index) => (
            <div key={index} className="fallacy-example-card">
              <div className="example-header">
                <h4>{example.type}</h4>
                <button
                  className="btn btn-sm btn-primary"
                  onClick={() => loadExample(example)}
                  disabled={isLoading}
                >
                  Tester
                </button>
              </div>
              <p className="example-text">"{example.text}"</p>
              <p className="example-description">{example.description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Formulaire de détection */}
      <form onSubmit={handleSubmit} className="detector-form">
        <div className="form-group">
          <label htmlFor="fallacy-text" className="form-label">
            Texte à analyser
          </label>
          <textarea
            ref={textareaRef}
            id="fallacy-text"
            data-testid="fallacy-text-input"
            className="form-textarea"
            value={text}
            onChange={(e) => updateTextInput('fallacy_detector', e.target.value)}
            placeholder="Entrez le texte à analyser pour détecter les sophismes..."
            rows={6}
            required
          />
          <div className="textarea-stats">
            <span>Caractères: {text.length}</span>
            <span>Mots: {text.trim() ? text.trim().split(/\s+/).length : 0}</span>
          </div>
        </div>

        {/* Options de détection */}
        <div className="detection-options">
          <h4>Options de détection</h4>
          
          <div className="option-group">
            <label className="form-label">
              Seuil de sévérité: {(options.severity_threshold * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={options.severity_threshold}
              onChange={(e) => setOptions({
                ...options,
                severity_threshold: parseFloat(e.target.value)
              })}
              className="severity-slider"
            />
            <div className="severity-labels">
              <span>Toutes</span>
              <span>Modérées+</span>
              <span>Sévères</span>
            </div>
          </div>

          <div className="option-checkboxes">
            <label className="option-item">
              <input
                type="checkbox"
                checked={options.include_explanations}
                onChange={(e) => setOptions({
                  ...options,
                  include_explanations: e.target.checked
                })}
              />
              <span>Inclure les explications détaillées</span>
            </label>

            <div className="fallacy-types-selector">
              <label className="form-label">Types de sophismes à détecter:</label>
              <select
                value={options.fallacy_types}
                onChange={(e) => setOptions({
                  ...options,
                  fallacy_types: e.target.value
                })}
                className="form-select"
              >
                <option value="all">Tous les types</option>
                <option value="logical">Erreurs logiques</option>
                <option value="emotional">Appels émotionnels</option>
                <option value="authority">Appels à l'autorité</option>
                <option value="relevance">Hors-sujet</option>
              </select>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="form-actions">
          <button
            type="submit"
            data-testid="fallacy-submit-button"
            className="btn btn-primary btn-lg"
            disabled={isLoading || !text.trim() || text.length > 10000}
          >
            {isLoading ? (
              <>
                <span className="loading-spinner"></span>
                Détection en cours...
              </>
            ) : (
              <>
                🔍 Détecter les sophismes
              </>
            )}
          </button>
          <button
            type="button"
            data-testid="fallacy-reset-button"
            className="btn btn-secondary"
            onClick={clearAll}
            disabled={isLoading}
          >
            🗑️ Effacer
          </button>
        </div>
      </form>

      {/* Erreur */}
      {error && (
        <div className="error-message">
          <div className="error-icon">⚠️</div>
          <div className="error-content">
            <h4>Erreur de détection</h4>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Résultats */}
      {fallacyResult && (
        <div className="detection-results" data-testid="fallacy-results-container">
          <div className="results-header">
            <h3>🎯 Résultats de la détection</h3>
            <div className="results-stats">
              <span className="stat-item">
                <strong>{fallacyResult.fallacies?.length || 0}</strong> sophisme(s) détecté(s)
              </span>
              <span className="stat-item">
                <strong>{fallacyResult.confidence ? (fallacyResult.confidence * 100).toFixed(1) : 'N/A'}%</strong> confiance
              </span>
              <span className="stat-item">
                <strong>{fallacyResult.processing_time?.toFixed(3) || 'N/A'}s</strong> temps
              </span>
            </div>
          </div>

          {fallacyResult.fallacies && fallacyResult.fallacies.length > 0 ? (
            <div className="fallacies-detected">
              <div className="fallacies-summary">
                <h4>📊 Résumé des sophismes</h4>
                <div className="severity-distribution">
                  {['critical', 'high', 'medium', 'low'].map(level => {
                    const count = fallacyResult.fallacies.filter(f =>
                      getSeverityColor(f.severity) === level
                    ).length;
                    return count > 0 && (
                      <div key={level} className={`severity-count severity-${level}`}>
                        <span className="count">{count}</span>
                        <span className="label">{getSeverityLabel(level === 'critical' ? 0.9 : level === 'high' ? 0.7 : level === 'medium' ? 0.5 : 0.2)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="fallacies-list">
                {fallacyResult.fallacies.map((fallacy, index) => (
                  <div key={index} className={`fallacy-detection severity-${getSeverityColor(fallacy.severity)}`}>
                    <div className="fallacy-detection-header">
                      <div className="fallacy-info">
                        <span className="fallacy-icon">
                          {getFallacyTypeIcon(fallacy.type)}
                        </span>
                        <div className="fallacy-title">
                          <h5>{fallacy.name}</h5>
                          <span className="fallacy-type">{fallacy.type}</span>
                        </div>
                      </div>
                      <div className="severity-indicator">
                        <span className={`severity-badge severity-${getSeverityColor(fallacy.severity)}`}>
                          {getSeverityLabel(fallacy.severity)} ({(fallacy.severity * 100).toFixed(1)}%)
                        </span>
                      </div>
                    </div>

                    <div className="fallacy-content">
                      <p className="fallacy-description">{fallacy.description}</p>
                      
                      {fallacy.location && (
                        <div className="fallacy-location">
                          <strong>Position:</strong> Caractères {fallacy.location.start}-{fallacy.location.end}
                        </div>
                      )}

                      {fallacy.explanation && options.include_explanations && (
                        <div className="fallacy-explanation">
                          <h6>💡 Explication</h6>
                          <p>{fallacy.explanation}</p>
                        </div>
                      )}

                      {fallacy.suggestion && (
                        <div className="fallacy-suggestion">
                          <h6>🔧 Suggestion d'amélioration</h6>
                          <p>{fallacy.suggestion}</p>
                        </div>
                      )}

                      {fallacy.examples && fallacy.examples.length > 0 && (
                        <div className="fallacy-examples-detail">
                          <h6>📝 Exemples similaires</h6>
                          <ul>
                            {fallacy.examples.slice(0, 2).map((example, idx) => (
                              <li key={idx}>{example}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="no-fallacies">
              <div className="no-fallacies-icon">✅</div>
              <h4>Aucun sophisme détecté</h4>
              <p>
                Le texte analysé ne contient pas de sophismes évidents avec le seuil de sévérité actuel 
                ({(options.severity_threshold * 100).toFixed(0)}%).
              </p>
              <button
                className="btn btn-secondary"
                onClick={() => setOptions({
                  ...options,
                  severity_threshold: Math.max(0, options.severity_threshold - 0.2)
                })}
              >
                Réduire le seuil pour plus de sensibilité
              </button>
            </div>
          )}

          {/* Actions sur les résultats */}
          <div className="results-actions">
            <button 
              className="btn btn-secondary"
              onClick={() => {
                const report = {
                  text,
                  options,
                  results: fallacyResult,
                  timestamp: new Date().toISOString()
                };
                navigator.clipboard.writeText(JSON.stringify(report, null, 2));
              }}
            >
              📋 Copier le rapport
            </button>
            <button 
              className="btn btn-secondary"
              onClick={() => {
                const report = {
                  text,
                  options,
                  results: fallacyResult,
                  timestamp: new Date().toISOString()
                };
                const blob = new Blob([JSON.stringify(report, null, 2)], 
                  { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `rapport-sophismes-${Date.now()}.json`;
                a.click();
                URL.revokeObjectURL(url);
              }}
            >
              💾 Télécharger
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default FallacyDetector; 