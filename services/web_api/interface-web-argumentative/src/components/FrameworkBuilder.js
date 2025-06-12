import React, { useEffect, useState } from 'react';
import { analyzeDungFramework as buildFramework } from '../services/api';
import './FrameworkBuilder.css';

/**
 * Composant pour la construction de frameworks de Dung
 */
const FrameworkBuilder = () => {
  // État des arguments
  const [args, setArgs] = useState([]);
  const [currentArgument, setCurrentArgument] = useState({
    id: '',
    content: ''
  });

  // État des attaques
  const [attacks, setAttacks] = useState([]);
  const [currentAttack, setCurrentAttack] = useState({
    source: '',
    target: ''
  });

  // État des options
  const [options, setOptions] = useState({
    semantics: 'preferred',
    compute_extensions: true,
    include_visualization: true
  });

  // État de l'interface
  const [selectedArguments, setSelectedArguments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // État des résultats
  const [framework, setFramework] = useState(null);
  const [selectedExtension, setSelectedExtension] = useState(0);

  // Sémantiques disponibles
  const availableSemantics = [
    { id: 'grounded', name: 'Grounded', description: 'Extension unique et minimale' },
    { id: 'complete', name: 'Complete', description: 'Extensions complètes' },
    { id: 'preferred', name: 'Preferred', description: 'Extensions préférées maximales' },
    { id: 'stable', name: 'Stable', description: 'Extensions stables' }
  ];

  // Génération d'ID unique
  const generateId = () => {
    return `arg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };

  // Ajout d'un argument
  const addArgument = () => {
    if (!currentArgument.content.trim()) {
      alert('Veuillez saisir le contenu de l\'argument');
      return;
    }

    const newArgument = {
      id: currentArgument.id || generateId(),
      content: currentArgument.content.trim()
    };

    setArgs(prev => [...prev, newArgument]);
    setCurrentArgument({ id: '', content: '' });
  };

  // Suppression d'un argument
  const removeArgument = (id) => {
    setArgs(prev => prev.filter(arg => arg.id !== id));
    setAttacks(prev => prev.filter(attack => 
      attack.source !== id && attack.target !== id
    ));
    setSelectedArguments(prev => prev.filter(argId => argId !== id));
  };

  // Ajout d'une attaque
  const addAttack = () => {
    if (!currentAttack.source || !currentAttack.target) {
      alert('Veuillez sélectionner un argument source et cible');
      return;
    }

    if (currentAttack.source === currentAttack.target) {
      alert('Un argument ne peut pas s\'attaquer lui-même');
      return;
    }

    const newAttack = [currentAttack.source, currentAttack.target];
    if (!attacks.some(attack => 
      attack[0] === newAttack[0] && attack[1] === newAttack[1]
    )) {
      setAttacks(prev => [...prev, newAttack]);
    }
    setCurrentAttack({ source: '', target: '' });
  };

  // Suppression d'une attaque
  const removeAttack = (source, target) => {
    setAttacks(prev => prev.filter(attack => 
      !(attack[0] === source && attack[1] === target)
    ));
  };

  // Construction du framework
  const handleBuildFramework = async () => {
    if (args.length === 0) {
      alert('Veuillez ajouter au moins un argument');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await buildFramework(args, attacks);
      setFramework(response);
      setSelectedExtension(0);
    } catch (err) {
      setError(err.message);
      console.error('Erreur lors de la construction:', err);
    } finally {
      setLoading(false);
    }
  };

  // Rendu du formulaire d'argument
  const renderArgumentForm = () => (
    <div className="framework-section">
      <h3>📝 Ajouter un argument</h3>
      
      <div className="form-group">
        <label htmlFor="arg-id">ID (optionnel):</label>
        <input
          id="arg-id"
          type="text"
          value={currentArgument.id}
          onChange={(e) => setCurrentArgument(prev => ({ ...prev, id: e.target.value }))}
          placeholder="Laissez vide pour génération automatique"
          className="form-input"
        />
      </div>

      <div className="form-group">
        <label htmlFor="arg-content">Contenu de l'argument:</label>
        <textarea
          id="arg-content"
          value={currentArgument.content}
          onChange={(e) => setCurrentArgument(prev => ({ ...prev, content: e.target.value }))}
          placeholder="Décrivez votre argument..."
          rows={3}
          className="form-textarea"
        />
      </div>

      <button 
        onClick={addArgument}
        className="add-button"
        disabled={!currentArgument.content.trim()}
      >
        ➕ Ajouter l'argument
      </button>
    </div>
  );

  // Rendu de la liste des arguments
  const renderArgumentsList = () => (
    <div className="framework-section">
      <h3>📋 Arguments ({args.length})</h3>
      
      {args.length === 0 ? (
        <p className="empty-message">Aucun argument ajouté</p>
      ) : (
        <div className="arguments-grid">
          {args.map(arg => (
            <div key={arg.id} className="argument-card">
              <div className="argument-header">
                <strong>ID:</strong> {arg.id}
                <button 
                  onClick={() => removeArgument(arg.id)}
                  className="remove-button"
                  title="Supprimer l'argument"
                >
                  ❌
                </button>
              </div>
              <div className="argument-content">{arg.content}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  // Rendu des outils de relation
  const renderAttackTools = () => (
    <div className="framework-section">
      <h3>⚔️ Ajouter une attaque</h3>
      
      <div className="attack-form">
        <div className="form-group">
          <label htmlFor="attack-source">Argument source:</label>
          <select
            id="attack-source"
            value={currentAttack.source}
            onChange={(e) => setCurrentAttack(prev => ({ ...prev, source: e.target.value }))}
            className="form-select"
          >
            <option value="">Sélectionnez un argument</option>
            {args.map(arg => (
              <option key={arg.id} value={arg.id}>
                {arg.id} - {arg.content.substring(0, 30)}...
              </option>
            ))}
          </select>
        </div>

        <div className="attack-arrow">⚔️</div>

        <div className="form-group">
          <label htmlFor="attack-target">Argument cible:</label>
          <select
            id="attack-target"
            value={currentAttack.target}
            onChange={(e) => setCurrentAttack(prev => ({ ...prev, target: e.target.value }))}
            className="form-select"
          >
            <option value="">Sélectionnez un argument</option>
            {args.map(arg => (
              <option key={arg.id} value={arg.id}>
                {arg.id} - {arg.content.substring(0, 30)}...
              </option>
            ))}
          </select>
        </div>

        <button 
          onClick={addAttack}
          className="add-button"
          disabled={!currentAttack.source || !currentAttack.target || args.length < 2}
        >
          ➕ Ajouter l'attaque
        </button>
      </div>

      {attacks.length > 0 && (
        <div className="attacks-list">
          <h4>Attaques définies ({attacks.length})</h4>
          {attacks.map((attack, index) => (
            <div key={index} className="attack-item">
              <span className="attack-description">
                {attack[0]} ⚔️ {attack[1]}
              </span>
              <button 
                onClick={() => removeAttack(attack[0], attack[1])}
                className="remove-button"
                title="Supprimer l'attaque"
              >
                ❌
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  // Rendu des options
  const renderOptions = () => (
    <div className="framework-section">
      <h3>⚙️ Options de construction</h3>
      
      <div className="options-grid">
        <div className="form-group">
          <label htmlFor="semantics">Sémantique:</label>
          <select
            id="semantics"
            value={options.semantics}
            onChange={(e) => setOptions(prev => ({ ...prev, semantics: e.target.value }))}
            className="form-select"
          >
            {availableSemantics.map(sem => (
              <option key={sem.id} value={sem.id} title={sem.description}>
                {sem.name}
              </option>
            ))}
          </select>
          <small className="form-help">
            {availableSemantics.find(s => s.id === options.semantics)?.description}
          </small>
        </div>

        <div className="form-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={options.compute_extensions}
              onChange={(e) => setOptions(prev => ({ ...prev, compute_extensions: e.target.checked }))}
            />
            Calculer les extensions
          </label>
        </div>

        <div className="form-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={options.include_visualization}
              onChange={(e) => setOptions(prev => ({ ...prev, include_visualization: e.target.checked }))}
            />
            Inclure la visualisation
          </label>
        </div>
      </div>

      <button 
        onClick={handleBuildFramework}
        className="build-button"
        disabled={loading || args.length === 0}
      >
        {loading ? '🔄 Construction...' : '🏗️ Construire le framework'}
      </button>
    </div>
  );

  // Rendu des résultats
  const renderResults = () => {
    if (!framework) return null;

    return (
      <div className="framework-section results-section">
        <h3>📊 Résultats du framework</h3>
        
        {framework.extensions && framework.extensions.length > 0 ? (
          <div className="extensions-container">
            <h4>Extensions trouvées ({framework.extensions.length})</h4>
            
            <div className="extensions-tabs">
              {framework.extensions.map((ext, index) => (
                <button
                  key={index}
                  className={`extension-tab ${selectedExtension === index ? 'active' : ''}`}
                  onClick={() => setSelectedExtension(index)}
                >
                  Extension {index + 1}
                </button>
              ))}
            </div>

            <div className="extension-content">
              <div className="extension-arguments">
                <strong>Arguments acceptés:</strong>
                <div className="argument-tags">
                  {framework.extensions[selectedExtension]?.map(argId => (
                    <span key={argId} className="argument-tag accepted">
                      {argId}
                    </span>
                  ))}
                </div>
              </div>

              <div className="extension-arguments">
                <strong>Arguments rejetés:</strong>
                <div className="argument-tags">
                  {args.filter(arg => !framework.extensions[selectedExtension]?.includes(arg.id))
                    .map(arg => (
                      <span key={arg.id} className="argument-tag rejected">
                        {arg.id}
                      </span>
                    ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <p className="no-extensions">Aucune extension trouvée</p>
        )}

        {framework.statistics && (
          <div className="framework-stats">
            <h4>📈 Statistiques</h4>
            <div className="stats-grid">
              <div className="stat-item">
                <span className="stat-label">Arguments:</span>
                <span className="stat-value">{framework.statistics.arguments_count || args.length}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Attaques:</span>
                <span className="stat-value">{framework.statistics.attacks_count || attacks.length}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Extensions:</span>
                <span className="stat-value">{framework.extensions?.length || 0}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="framework-builder">
      <div className="framework-header">
        <h2>🏗️ Constructeur de Framework de Dung</h2>
        <p>Créez des frameworks d'argumentation et calculez leurs extensions selon différentes sémantiques.</p>
      </div>

      {error && (
        <div className="error-message">
          <strong>❌ Erreur:</strong> {error}
        </div>
      )}

      <div className="framework-content">
        <div className="framework-column">
          {renderArgumentForm()}
          {renderArgumentsList()}
        </div>
        
        <div className="framework-column">
          {renderAttackTools()}
          {renderOptions()}
        </div>
      </div>

      {renderResults()}
    </div>
  );
};

export default FrameworkBuilder; 