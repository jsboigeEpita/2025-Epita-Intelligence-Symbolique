import React, { useRef, useState } from 'react';
import { analyzeText } from '../services/api';
import './ArgumentAnalyzer.css';

const ArgumentAnalyzer = () => {
  const [text, setText] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [options, setOptions] = useState({
    detect_fallacies: true,
    analyze_structure: true,
    evaluate_coherence: true
  });
  
  const textareaRef = useRef(null);

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

    setLoading(true);
    setError(null);
    
    try {
      const result = await analyzeText(text, options);
      setAnalysis(result);
    } catch (err) {
      setError('Erreur lors de l\'analyse : ' + err.message);
      setAnalysis(null);
    } finally {
      setLoading(false);
    }
  };

  const loadExample = (example) => {
    setText(example.text);
    setAnalysis(null);
    setError(null);
  };

  const clearAll = () => {
    setText('');
    setAnalysis(null);
    setError(null);
  };

  const getQualityColor = (quality) => {
    if (quality >= 0.8) return 'excellent';
    if (quality >= 0.6) return 'good';
    if (quality >= 0.4) return 'average';
    return 'poor';
  };

  const getSeverityColor = (severity) => {
    if (severity >= 0.8) return 'critical';
    if (severity >= 0.6) return 'high';
    if (severity >= 0.4) return 'medium';
    return 'low';
  };

  return (
    <div className="argument-analyzer">
      <div className="analyzer-header">
        <h2>🔍 Analyseur d'Arguments</h2>
        <p>
          Entrez votre texte argumentatif pour une analyse complète incluant 
          la détection de sophismes, l'évaluation de la structure et la cohérence logique.
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
              disabled={loading}
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
            onChange={(e) => setText(e.target.value)}
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
            <label className="option-item">
              <input
                type="checkbox"
                checked={options.analyze_structure}
                onChange={(e) => setOptions({
                  ...options,
                  analyze_structure: e.target.checked
                })}
              />
              <span>Analyser la structure</span>
            </label>
            <label className="option-item">
              <input
                type="checkbox"
                checked={options.evaluate_coherence}
                onChange={(e) => setOptions({
                  ...options,
                  evaluate_coherence: e.target.checked
                })}
              />
              <span>Évaluer la cohérence</span>
            </label>
          </div>
        </div>

        {/* Boutons d'action */}
        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary btn-lg"
            disabled={loading || !text.trim()}
          >
            {loading ? (
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
            disabled={loading}
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
      {analysis && (
        <div className="analysis-results">
          <div className="results-header">
            <h3>📊 Résultats de l'analyse</h3>
            <div className="analysis-metadata">
              <span>⏱️ {analysis.metadata?.duration?.toFixed(3)}s</span>
              <span>📅 {new Date().toLocaleString()}</span>
            </div>
          </div>

          {/* Métriques principales */}
          <div className="metrics-grid">
            <div className={`metric-card quality-${getQualityColor(analysis.results?.overall_quality)}`}>
              <div className="metric-icon">🎯</div>
              <div className="metric-content">
                <h4>Qualité globale</h4>
                <div className="metric-value">
                  {(analysis.results?.overall_quality * 100).toFixed(1)}%
                </div>
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-icon">⚠️</div>
              <div className="metric-content">
                <h4>Sophismes détectés</h4>
                <div className="metric-value">
                  {analysis.results?.fallacy_count || 0}
                </div>
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-icon">🏗️</div>
              <div className="metric-content">
                <h4>Structure</h4>
                <div className="metric-value">
                  {analysis.results?.argument_structure?.argument_type || 'N/A'}
                </div>
              </div>
            </div>

            <div className="metric-card">
              <div className="metric-icon">🔗</div>
              <div className="metric-content">
                <h4>Cohérence</h4>
                <div className="metric-value">
                  {analysis.results?.argument_structure ?
                    (analysis.results.argument_structure.coherence * 100).toFixed(1) + '%' :
                    'N/A'
                  }
                </div>
              </div>
            </div>
          </div>

          {/* Sophismes détectés */}
          {analysis.results?.fallacies && analysis.results.fallacies.length > 0 && (
            <div className="fallacies-section">
              <h4>⚠️ Sophismes détectés</h4>
              <div className="fallacies-list">
                {analysis.results.fallacies.map((fallacy, index) => (
                  <div key={index} className={`fallacy-item severity-${getSeverityColor(fallacy.severity)}`}>
                    <div className="fallacy-header">
                      <h5>{fallacy.name}</h5>
                      <span className="severity-badge">
                        Sévérité: {(fallacy.severity * 100).toFixed(1)}%
                      </span>
                    </div>
                    <p className="fallacy-description">{fallacy.description}</p>
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
          {analysis.results?.argument_structure && (
            <div className="structure-section">
              <h4>🏗️ Structure argumentative</h4>
              
              <div className="structure-overview">
                <div className="structure-metric">
                  <strong>Type:</strong> {analysis.results.argument_structure.argument_type}
                </div>
                <div className="structure-metric">
                  <strong>Force:</strong> {(analysis.results.argument_structure.strength * 100).toFixed(1)}%
                </div>
                <div className="structure-metric">
                  <strong>Cohérence:</strong> {(analysis.results.argument_structure.coherence * 100).toFixed(1)}%
                </div>
              </div>
              
              {analysis.results.argument_structure.premises && analysis.results.argument_structure.premises.length > 0 && (
                <div className="premises-section">
                  <h5>📝 Prémisses identifiées</h5>
                  <ol className="premises-list">
                    {analysis.results.argument_structure.premises.map((premise, index) => (
                      <li key={index} className="premise-item">
                        {premise}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
              
              {analysis.results.argument_structure.conclusion && (
                <div className="conclusion-section">
                  <h5>🎯 Conclusion</h5>
                  <div className="conclusion-text">
                    {analysis.results.argument_structure.conclusion}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Recommandations */}
          {analysis.results?.suggestions && analysis.results.suggestions.length > 0 && (
            <div className="suggestions-section">
              <h4>💡 Recommandations</h4>
              <ul className="suggestions-list">
                {analysis.results.suggestions.map((suggestion, index) => (
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
                const resultsText = JSON.stringify(analysis, null, 2);
                navigator.clipboard.writeText(resultsText);
              }}
            >
              📋 Copier les résultats
            </button>
            <button 
              className="btn btn-secondary"
              onClick={() => {
                const blob = new Blob([JSON.stringify(analysis, null, 2)], 
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