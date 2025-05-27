import React, { useState, useCallback } from 'react';
import './ArgumentAnalyzer.css';

/**
 * Composant principal d'analyse d'arguments
 * 
 * Fonctionnalités :
 * - Analyse complète de texte
 * - Affichage des sophismes détectés
 * - Visualisation de la structure argumentative
 * - Gestion des erreurs et du loading
 */
const ArgumentAnalyzer = () => {
  const [text, setText] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [options, setOptions] = useState({
    detect_fallacies: true,
    analyze_structure: true,
    evaluate_coherence: true,
    severity_threshold: 0.5,
    include_context: true
  });

  // Fonction d'analyse avec gestion d'erreurs
  const analyzeText = useCallback(async () => {
    if (!text.trim()) {
      setError('Veuillez entrer un texte à analyser');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:5000/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: text.trim(),
          options
        })
      });

      if (!response.ok) {
        throw new Error(`Erreur API: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();
      
      if (result.success) {
        setAnalysis(result);
      } else {
        throw new Error('L\'analyse a échoué');
      }
    } catch (err) {
      console.error('Erreur lors de l\'analyse:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [text, options]);

  // Gestion des changements d'options
  const handleOptionChange = (option, value) => {
    setOptions(prev => ({
      ...prev,
      [option]: value
    }));
  };

  // Réinitialisation
  const handleReset = () => {
    setText('');
    setAnalysis(null);
    setError(null);
  };

  // Exemples prédéfinis
  const loadExample = (exampleText) => {
    setText(exampleText);
    setAnalysis(null);
    setError(null);
  };

  const examples = [
    {
      name: "Argument valide",
      text: "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."
    },
    {
      name: "Généralisation hâtive",
      text: "J'ai rencontré trois personnes de cette ville et elles étaient toutes impolies. Donc tous les habitants de cette ville sont impolis."
    },
    {
      name: "Ad Hominem",
      text: "Vous ne pouvez pas critiquer ce projet car vous n'êtes pas expert en la matière et vous avez échoué dans vos propres projets."
    },
    {
      name: "Faux dilemme",
      text: "Soit nous augmentons les impôts, soit nous laissons s'effondrer tous les services publics. Il n'y a pas d'autre choix."
    }
  ];

  return (
    <div className="argument-analyzer">
      <div className="analyzer-header">
        <h2>🔍 Analyseur d'Arguments</h2>
        <p>Analysez vos textes argumentatifs pour détecter les sophismes et évaluer la structure logique.</p>
      </div>

      {/* Section des exemples */}
      <div className="examples-section">
        <h3>📚 Exemples prédéfinis</h3>
        <div className="examples-grid">
          {examples.map((example, index) => (
            <button
              key={index}
              className="example-button"
              onClick={() => loadExample(example.text)}
              disabled={loading}
            >
              {example.name}
            </button>
          ))}
        </div>
      </div>

      {/* Section de saisie */}
      <div className="input-section">
        <h3>✏️ Votre texte</h3>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Entrez votre argument ici... 

Exemple : 'Tous les politiciens sont corrompus. Jean est politicien. Donc Jean est corrompu.'"
          rows={6}
          className="text-input"
          disabled={loading}
        />
        
        <div className="character-count">
          {text.length} caractères
        </div>
      </div>

      {/* Options d'analyse */}
      <div className="options-section">
        <h3>⚙️ Options d'analyse</h3>
        <div className="options-grid">
          <label className="option-item">
            <input
              type="checkbox"
              checked={options.detect_fallacies}
              onChange={(e) => handleOptionChange('detect_fallacies', e.target.checked)}
              disabled={loading}
            />
            <span>Détecter les sophismes</span>
          </label>
          
          <label className="option-item">
            <input
              type="checkbox"
              checked={options.analyze_structure}
              onChange={(e) => handleOptionChange('analyze_structure', e.target.checked)}
              disabled={loading}
            />
            <span>Analyser la structure</span>
          </label>
          
          <label className="option-item">
            <input
              type="checkbox"
              checked={options.evaluate_coherence}
              onChange={(e) => handleOptionChange('evaluate_coherence', e.target.checked)}
              disabled={loading}
            />
            <span>Évaluer la cohérence</span>
          </label>
          
          <label className="option-item">
            <input
              type="checkbox"
              checked={options.include_context}
              onChange={(e) => handleOptionChange('include_context', e.target.checked)}
              disabled={loading}
            />
            <span>Inclure le contexte</span>
          </label>
        </div>
        
        <div className="threshold-section">
          <label>
            Seuil de sévérité: {options.severity_threshold}
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={options.severity_threshold}
              onChange={(e) => handleOptionChange('severity_threshold', parseFloat(e.target.value))}
              disabled={loading}
              className="threshold-slider"
            />
          </label>
        </div>
      </div>

      {/* Boutons d'action */}
      <div className="action-buttons">
        <button
          onClick={analyzeText}
          disabled={loading || !text.trim()}
          className="analyze-button primary"
        >
          {loading ? (
            <>
              <span className="spinner"></span>
              Analyse en cours...
            </>
          ) : (
            '🚀 Analyser'
          )}
        </button>
        
        <button
          onClick={handleReset}
          disabled={loading}
          className="reset-button secondary"
        >
          🔄 Réinitialiser
        </button>
      </div>

      {/* Affichage des erreurs */}
      {error && (
        <div className="error-message">
          <h4>❌ Erreur</h4>
          <p>{error}</p>
          <details>
            <summary>Conseils de dépannage</summary>
            <ul>
              <li>Vérifiez que l'API est démarrée sur le port 5000</li>
              <li>Testez la connexion : <code>curl http://localhost:5000/api/health</code></li>
              <li>Vérifiez la console du navigateur pour plus de détails</li>
            </ul>
          </details>
        </div>
      )}

      {/* Résultats de l'analyse */}
      {analysis && (
        <div className="results-section">
          <h3>📊 Résultats de l'analyse</h3>
          
          {/* Métriques globales */}
          <div className="metrics-overview">
            <div className="metric-card">
              <div className="metric-value">
                {(analysis.overall_quality * 100).toFixed(1)}%
              </div>
              <div className="metric-label">Qualité globale</div>
            </div>
            
            <div className="metric-card">
              <div className="metric-value">
                {(analysis.coherence_score * 100).toFixed(1)}%
              </div>
              <div className="metric-label">Cohérence</div>
            </div>
            
            <div className="metric-card">
              <div className="metric-value">
                {analysis.fallacy_count}
              </div>
              <div className="metric-label">Sophismes détectés</div>
            </div>
            
            <div className="metric-card">
              <div className="metric-value">
                {(analysis.processing_time * 1000).toFixed(0)}ms
              </div>
              <div className="metric-label">Temps de traitement</div>
            </div>
          </div>

          {/* Sophismes détectés */}
          {analysis.fallacies && analysis.fallacies.length > 0 && (
            <div className="fallacies-section">
              <h4>🚫 Sophismes détectés</h4>
              {analysis.fallacies.map((fallacy, index) => (
                <div key={index} className="fallacy-card">
                  <div className="fallacy-header">
                    <h5>{fallacy.name}</h5>
                    <div className="severity-badge" data-severity={getSeverityLevel(fallacy.severity)}>
                      {(fallacy.severity * 100).toFixed(0)}%
                    </div>
                  </div>
                  
                  <p className="fallacy-description">{fallacy.description}</p>
                  
                  {fallacy.context && (
                    <div className="fallacy-context">
                      <strong>Contexte :</strong> "{fallacy.context}"
                    </div>
                  )}
                  
                  {fallacy.explanation && (
                    <div className="fallacy-explanation">
                      <strong>Explication :</strong> {fallacy.explanation}
                    </div>
                  )}
                  
                  <div className="fallacy-meta">
                    <span>Confiance: {(fallacy.confidence * 100).toFixed(0)}%</span>
                    <span>Type: {fallacy.type}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Structure argumentative */}
          {analysis.argument_structure && (
            <div className="structure-section">
              <h4>🏗️ Structure argumentative</h4>
              
              <div className="structure-overview">
                <div className="structure-metric">
                  <strong>Type :</strong> {analysis.argument_structure.argument_type}
                </div>
                <div className="structure-metric">
                  <strong>Force :</strong> {(analysis.argument_structure.strength * 100).toFixed(1)}%
                </div>
                <div className="structure-metric">
                  <strong>Cohérence :</strong> {(analysis.argument_structure.coherence * 100).toFixed(1)}%
                </div>
              </div>
              
              {analysis.argument_structure.premises && analysis.argument_structure.premises.length > 0 && (
                <div className="premises-section">
                  <h5>📝 Prémisses identifiées</h5>
                  <ol className="premises-list">
                    {analysis.argument_structure.premises.map((premise, index) => (
                      <li key={index} className="premise-item">
                        {premise}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
              
              {analysis.argument_structure.conclusion && (
                <div className="conclusion-section">
                  <h5>🎯 Conclusion</h5>
                  <div className="conclusion-text">
                    {analysis.argument_structure.conclusion}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Pas de sophismes détectés */}
          {analysis.fallacy_count === 0 && (
            <div className="no-fallacies">
              <h4>✅ Aucun sophisme détecté</h4>
              <p>Votre argument semble logiquement cohérent selon les critères d'analyse.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Fonction utilitaire pour déterminer le niveau de sévérité
const getSeverityLevel = (severity) => {
  if (severity < 0.3) return 'low';
  if (severity < 0.7) return 'medium';
  return 'high';
};

export default ArgumentAnalyzer;