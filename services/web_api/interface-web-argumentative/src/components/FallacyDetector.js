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
  // #2526 : `min_confidence` est envoyé au détecteur ; `include_explanations`
  // ne règle que l'affichage.
  const [options, setOptions] = useState({
    min_confidence: 0,
    include_explanations: true
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

  // La confiance du détecteur (#2526), sur les classes de couleur `severity-*`
  // du CSS : le détecteur ne calcule pas de sévérité.
  const getConfidenceLabel = (confidence) => {
    if (confidence >= 0.8) return 'élevée';
    if (confidence >= 0.5) return 'moyenne';
    return 'faible';
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.5) return 'medium';
    return 'low';
  };

  return (
    <div className="fallacy-detector">
      <div className="detector-header">
        <h2>⚠️ Détecteur de Sophismes</h2>
        <p>
          Identifiez automatiquement les sophismes et erreurs de raisonnement dans vos textes.
          Chaque détection porte la confiance du détecteur, sa famille dans la
          taxonomie des sophismes et une explication.
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
              Confiance minimale : {(options.min_confidence * 100).toFixed(0)}%
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={options.min_confidence}
              onChange={(e) => setOptions({
                ...options,
                min_confidence: parseFloat(e.target.value)
              })}
              className="severity-slider"
            />
            <div className="severity-labels">
              <span>Toutes</span>
              <span>Moyenne+</span>
              <span>Élevée</span>
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
                <strong>{fallacyResult.fallacy_count}</strong> sophisme(s) détecté(s)
              </span>
              <span className="stat-item">
                <strong>{fallacyResult.processing_time?.toFixed(1)}s</strong> temps
              </span>
            </div>
          </div>

          {fallacyResult.degraded && (
            <p className="detection-degraded">
              Détection partielle : {fallacyResult.degradation_reason}
            </p>
          )}

          {fallacyResult.fallacies && fallacyResult.fallacies.length > 0 ? (
            <div className="fallacies-detected">
              <div className="fallacies-summary">
                <h4>📊 Résumé des sophismes</h4>
                <div className="severity-distribution">
                  {['high', 'medium', 'low'].map(level => {
                    const count = fallacyResult.fallacies.filter(f =>
                      getConfidenceColor(f.confidence) === level
                    ).length;
                    return count > 0 && (
                      <div key={level} className={`severity-count severity-${level}`}>
                        <span className="count">{count}</span>
                        <span className="label">Confiance {getConfidenceLabel(level === 'high' ? 0.9 : level === 'medium' ? 0.6 : 0.2)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="fallacies-list">
                {fallacyResult.fallacies.map((fallacy, index) => (
                  <div key={index} className={`fallacy-detection severity-${getConfidenceColor(fallacy.confidence)}`}>
                    <div className="fallacy-detection-header">
                      <div className="fallacy-info">
                        <span className="fallacy-icon">⚠️</span>
                        <div className="fallacy-title">
                          <h5>{fallacy.name}</h5>
                          {fallacy.family && <span className="fallacy-type">{fallacy.family}</span>}
                        </div>
                      </div>
                      <div className="severity-indicator">
                        <span className={`severity-badge severity-${getConfidenceColor(fallacy.confidence)}`}>
                          Confiance {getConfidenceLabel(fallacy.confidence)} ({(fallacy.confidence * 100).toFixed(0)}%)
                        </span>
                      </div>
                    </div>

                    <div className="fallacy-content">
                      {fallacy.description && <p className="fallacy-description">{fallacy.description}</p>}

                      {fallacy.quote && (
                        <div className="fallacy-location">
                          <strong>Passage :</strong> « {fallacy.quote} »
                        </div>
                      )}

                      {fallacy.explanation && options.include_explanations && (
                        <div className="fallacy-explanation">
                          <h6>💡 Explication</h6>
                          <p>{fallacy.explanation}</p>
                        </div>
                      )}

                      {fallacy.example && (
                        <div className="fallacy-examples-detail">
                          <h6>📝 Exemple de la taxonomie</h6>
                          <p>{fallacy.example}</p>
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
              {fallacyResult.below_threshold > 0 ? (
                <>
                  <p>
                    {fallacyResult.below_threshold} détection(s) sous le seuil de confiance
                    ({(options.min_confidence * 100).toFixed(0)}%).
                  </p>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setOptions({
                      ...options,
                      min_confidence: Math.max(0, options.min_confidence - 0.2)
                    })}
                  >
                    Réduire le seuil pour plus de sensibilité
                  </button>
                </>
              ) : (
                <p>Le détecteur n'a trouvé aucun sophisme dans ce texte.</p>
              )}
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