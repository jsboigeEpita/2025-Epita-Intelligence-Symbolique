import React, { useRef, useState } from 'react';
import { analyzeText } from '../services/api';
import { useAppContext } from '../context/AppContext';
import './ArgumentAnalyzer.css';

const ArgumentAnalyzer = () => {
  const {
    analysisResult,
    setAnalysisResult,
    textInputs,
    updateTextInput,
    isLoading,
    setIsLoading,
  } = useAppContext();

  const [error, setError] = useState(null);
  // #2526 : la route calcule la structure à chaque appel, et les sophismes sur
  // demande. Qualité globale, type d'argument, force et cohérence ne sont
  // calculés par rien : la vue ne les affiche plus.
  const [options, setOptions] = useState({
    detect_fallacies: true
  });
  
  const textareaRef = useRef(null);
  const text = textInputs.analyzer;

  // Exemples d'arguments prédéfinis
  const examples = [
    {
      title: "Argument déductif valide",
      text: "Tous les chats sont des animaux. Félix est un chat. Donc Félix est un animal."
    },
    {
      title: "Argument avec sophisme (Ad Hominem)",
      text: "Cette théorie sur le climat est fausse parce que son auteur a été condamné pour fraude fiscale."
    },
    {
      title: "Argument inductif",
      text: "J'ai observé 100 corbeaux et ils étaient tous noirs. Donc tous les corbeaux sont probablement noirs."
    },
    {
      title: "Raisonnement circulaire",
      text: "Dieu existe parce que la Bible le dit, et la Bible est vraie parce qu'elle est la parole de Dieu."
    }
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;

    setIsLoading(true);
    setError(null);
    
    try {
      const result = await analyzeText(text, options);
      setAnalysisResult(result);
    } catch (err) {
      setError('Erreur lors de l\'analyse : ' + err.message);
      setAnalysisResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  const loadExample = (example) => {
    updateTextInput('analyzer', example.text);
    setAnalysisResult(null);
    setError(null);
  };

  const clearAll = () => {
    updateTextInput('analyzer', '');
    setAnalysisResult(null);
    setError(null);
  };

  // La confiance du détecteur, sur les classes de couleur `severity-*` du CSS.
  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.5) return 'medium';
    return 'low';
  };

  return (
    <div className="argument-analyzer">
      <div className="analyzer-header">
        <h2>🔍 Analyseur d'Arguments</h2>
        <p>
          Entrez votre texte argumentatif : l'analyse en extrait la structure
          (prémisses et conclusion) et, si l'option est cochée, en détecte les sophismes.
        </p>
      </div>

      {/* Exemples prédéfinis */}
      <div className="examples-section">
        <h3>📝 Exemples prédéfinis</h3>
        <div className="examples-grid">
          {examples.map((example, index) => (
            <button
              key={index}
              className="example-button"
              onClick={() => loadExample(example)}
              disabled={isLoading}
            >
              <strong>{example.title}</strong>
              <span>{example.text.substring(0, 80)}...</span>
            </button>
          ))}
        </div>
      </div>

      {/* Formulaire d'analyse */}
      <form onSubmit={handleSubmit} className="analyzer-form">
        <div className="form-group">
          <label htmlFor="argument-text" className="form-label">
            Texte à analyser
          </label>
          <textarea
            ref={textareaRef}
            id="argument-text"
            className="form-textarea"
            value={text}
            onChange={(e) => updateTextInput('analyzer', e.target.value)}
            placeholder="Entrez votre argument ici..."
            rows={6}
            required
          />
          <div className="textarea-stats">
            <span>Caractères: {text.length}</span>
            <span>Mots: {text.trim() ? text.trim().split(/\s+/).length : 0}</span>
          </div>
        </div>

        {/* Options d'analyse */}
        <div className="options-section">
          <h4>Options d'analyse</h4>
          <div className="options-grid">
            <label className="option-item">
              <input
                type="checkbox"
                checked={options.detect_fallacies}
                onChange={(e) => setOptions({
                  ...options,
                  detect_fallacies: e.target.checked
                })}
              />
              <span>Détecter les sophismes</span>
            </label>
          </div>
        </div>

        {/* Boutons d'action */}
        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            disabled={isLoading || !text.trim()}
          >
            {isLoading ? (
              <>
                <span className="loading-spinner"></span>
                Analyse en cours...
              </>
            ) : (
              <>
                🔍 Analyser l'argument
              </>
            )}
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={clearAll}
            disabled={isLoading}
          >
            🗑️ Effacer tout
          </button>
        </div>
      </form>

      {/* Erreur */}
      {error && (
        <div className="error-message">
          <div className="error-icon">⚠️</div>
          <div className="error-content">
            <h4>Erreur d'analyse</h4>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Résultats d'analyse */}
      {analysisResult && (
        <div className="analysis-results" data-testid="analyzer-results">
          <div className="results-header">
            <h3>📊 Résultats de l'analyse</h3>
            <div className="analysis-metadata">
              <span>⏱️ {analysisResult.processing_time?.toFixed(3)}s</span>
              <span>📅 {new Date().toLocaleString()}</span>
            </div>
          </div>

          {/* Métriques principales */}
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-icon">⚠️</div>
              <div className="metric-content">
                <h4>Sophismes détectés</h4>
                <div className="metric-value">
                  {analysisResult.fallacies ? analysisResult.fallacy_count : 'non recherchés'}
                </div>
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-icon">🏗️</div>
              <div className="metric-content">
                <h4>Prémisses</h4>
                <div className="metric-value">
                  {analysisResult.argument_structure?.premises?.length ?? 'N/A'}
                </div>
              </div>
            </div>
          </div>

          {/* Sophismes détectés */}
          {analysisResult.fallacies && analysisResult.fallacies.length > 0 && (
            <div className="fallacies-section">
              <h4>⚠️ Sophismes détectés</h4>
              <div className="fallacies-list">
                {analysisResult.fallacies.map((fallacy, index) => (
                  <div key={index} className={`fallacy-item severity-${getConfidenceColor(fallacy.confidence)}`}>
                    <div className="fallacy-header">
                      <h5>{fallacy.name}</h5>
                      <span className="severity-badge">
                        Confiance : {(fallacy.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    {fallacy.family && <p className="fallacy-family">{fallacy.family}</p>}
                    {fallacy.description && <p className="fallacy-description">{fallacy.description}</p>}
                    {fallacy.explanation && (
                      <div className="fallacy-explanation">
                        <strong>Explication:</strong> {fallacy.explanation}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Structure argumentative */}
          {analysisResult.argument_structure && (
            <div className="structure-section">
              <h4>🏗️ Structure argumentative</h4>

              {analysisResult.argument_structure.premises && analysisResult.argument_structure.premises.length > 0 && (
                <div className="premises-section">
                  <h5>📝 Prémisses identifiées</h5>
                  <ol className="premises-list">
                    {analysisResult.argument_structure.premises.map((premise, index) => (
                      <li key={index} className="premise-item">
                        {premise}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
              
              {analysisResult.argument_structure.conclusion && (
                <div className="conclusion-section">
                  <h5>🎯 Conclusion</h5>
                  <div className="conclusion-text">
                    {analysisResult.argument_structure.conclusion}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Recommandations */}
          {analysisResult.suggestions && analysisResult.suggestions.length > 0 && (
            <div className="suggestions-section">
              <h4>💡 Recommandations</h4>
              <ul className="suggestions-list">
                {analysisResult.suggestions.map((suggestion, index) => (
                  <li key={index} className="suggestion-item">
                    {suggestion}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Actions sur les résultats */}
          <div className="results-actions">
            <button 
              className="btn btn-secondary"
              onClick={() => {
                const resultsText = JSON.stringify(analysisResult, null, 2);
                navigator.clipboard.writeText(resultsText);
              }}
            >
              📋 Copier les résultats
            </button>
            <button 
              className="btn btn-secondary"
              onClick={() => {
                const blob = new Blob([JSON.stringify(analysisResult, null, 2)],
                  { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `analyse-argument-${Date.now()}.json`;
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

export default ArgumentAnalyzer; 