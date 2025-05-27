import React, { useState, useEffect, useCallback } from 'react';
import { useArgumentationAPI } from './hooks/useArgumentationAPI';
import './FrameworkBuilder.css';

/**
 * Composant pour la construction de frameworks de Dung
 * 
 * Ce composant permet de créer et visualiser des frameworks
 * d'argumentation avec calcul des extensions selon différentes sémantiques.
 */
const FrameworkBuilder = ({ 
  onFrameworkBuilt = null,
  showVisualization = true,
  allowSemantics = ['grounded', 'preferred', 'stable']
}) => {
  // État des arguments
  const [args, setArgs] = useState([]);
  const [currentArgument, setCurrentArgument] = useState({
    id: '',
    content: '',
    attacks: [],
    supports: []
  });

  // État des options
  const [options, setOptions] = useState({
    semantics: 'preferred',
    compute_extensions: true,
    include_visualization: showVisualization
  });

  // État de l'interface
  const [editingId, setEditingId] = useState(null);
  const [selectedArguments, setSelectedArguments] = useState([]);
  const [relationMode, setRelationMode] = useState('attack'); // 'attack' ou 'support'

  // Hook API
  const { buildFramework, loading, error } = useArgumentationAPI();
  
  // État des résultats
  const [framework, setFramework] = useState(null);
  const [selectedExtension, setSelectedExtension] = useState(0);

  // Sémantiques disponibles
  const availableSemantics = [
    { id: 'grounded', name: 'Grounded', description: 'Extension unique et minimale' },
    { id: 'complete', name: 'Complete', description: 'Extensions complètes' },
    { id: 'preferred', name: 'Preferred', description: 'Extensions préférées maximales' },
    { id: 'stable', name: 'Stable', description: 'Extensions stables' },
    { id: 'semi-stable', name: 'Semi-stable', description: 'Extensions semi-stables' }
  ].filter(sem => allowSemantics.includes(sem.id));

  // Effet pour notifier les résultats
  useEffect(() => {
    if (framework && onFrameworkBuilt) {
      onFrameworkBuilt(framework);
    }
  }, [framework, onFrameworkBuilt]);

  // Génération d'ID unique
  const generateId = useCallback(() => {
    return `arg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  // Ajout d'un argument
  const addArgument = () => {
    if (!currentArgument.content.trim()) {
      alert('Veuillez saisir le contenu de l\'argument');
      return;
    }

    const newArgument = {
      ...currentArgument,
      id: currentArgument.id || generateId()
    };

    setArgs(prev => [...prev, newArgument]);
    setCurrentArgument({
      id: '',
      content: '',
      attacks: [],
      supports: []
    });
  };

  // Modification d'un argument
  const updateArgument = (id, updates) => {
    setArgs(prev => prev.map(arg =>
      arg.id === id ? { ...arg, ...updates } : arg
    ));
  };

  // Suppression d'un argument
  const removeArgument = (id) => {
    setArgs(prev => {
      const filtered = prev.filter(arg => arg.id !== id);
      // Nettoyer les références dans les autres arguments
      return filtered.map(arg => ({
        ...arg,
        attacks: arg.attacks.filter(attackId => attackId !== id),
        supports: arg.supports.filter(supportId => supportId !== id)
      }));
    });
    setSelectedArguments(prev => prev.filter(argId => argId !== id));
  };

  // Gestion des relations
  const toggleArgumentSelection = (id) => {
    setSelectedArguments(prev => 
      prev.includes(id) 
        ? prev.filter(argId => argId !== id)
        : [...prev, id]
    );
  };

  const createRelation = () => {
    if (selectedArguments.length !== 2) {
      alert('Veuillez sélectionner exactement 2 arguments');
      return;
    }

    const [sourceId, targetId] = selectedArguments;
    const relationKey = relationMode === 'attack' ? 'attacks' : 'supports';

    updateArgument(sourceId, {
      [relationKey]: [...(args.find(arg => arg.id === sourceId)?.[relationKey] || []), targetId]
    });

    setSelectedArguments([]);
  };

  // Construction du framework
  const handleBuildFramework = async () => {
    if (args.length === 0) {
      alert('Veuillez ajouter au moins un argument');
      return;
    }

    try {
      const response = await buildFramework(args, options);
      setFramework(response);
      setSelectedExtension(0);
    } catch (err) {
      console.error('Erreur lors de la construction:', err);
    }
  };

  // Rendu du formulaire d'argument
  const renderArgumentForm = () => (
    <div className="argument-form">
      <h4>Ajouter un argument</h4>
      
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
        Ajouter l'argument
      </button>
    </div>
  );

  // Rendu de la liste des arguments
  const renderArgumentsList = () => (
    <div className="arguments-list">
      <h4>Arguments ({arguments.length})</h4>
      
      {arguments.length === 0 ? (
        <p className="empty-message">Aucun argument ajouté</p>
      ) : (
        <div className="arguments-grid">
          {arguments.map(arg => (
            <div 
              key={arg.id}
              className={`argument-card ${selectedArguments.includes(arg.id) ? 'selected' : ''}`}
              onClick={() => toggleArgumentSelection(arg.id)}
            >
              <div className="argument-header">
                <span className="argument-id">{arg.id}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeArgument(arg.id);
                  }}
                  className="remove-button"
                  title="Supprimer"
                >
                  ×
                </button>
              </div>
              
              <div className="argument-content">
                {editingId === arg.id ? (
                  <textarea
                    value={arg.content}
                    onChange={(e) => updateArgument(arg.id, { content: e.target.value })}
                    onBlur={() => setEditingId(null)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && e.ctrlKey) {
                        setEditingId(null);
                      }
                    }}
                    className="edit-textarea"
                    autoFocus
                  />
                ) : (
                  <p 
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingId(arg.id);
                    }}
                    className="content-text"
                  >
                    {arg.content}
                  </p>
                )}
              </div>

              <div className="argument-relations">
                {arg.attacks.length > 0 && (
                  <div className="relation-info attacks">
                    Attaque: {arg.attacks.join(', ')}
                  </div>
                )}
                {arg.supports.length > 0 && (
                  <div className="relation-info supports">
                    Supporte: {arg.supports.join(', ')}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  // Rendu des outils de relation
  const renderRelationTools = () => (
    <div className="relation-tools">
      <h4>Créer des relations</h4>
      
      <div className="relation-mode">
        <label>
          <input
            type="radio"
            value="attack"
            checked={relationMode === 'attack'}
            onChange={(e) => setRelationMode(e.target.value)}
          />
          Attaque
        </label>
        <label>
          <input
            type="radio"
            value="support"
            checked={relationMode === 'support'}
            onChange={(e) => setRelationMode(e.target.value)}
          />
          Support
        </label>
      </div>

      <div className="selection-info">
        {selectedArguments.length === 0 && (
          <p>Sélectionnez 2 arguments pour créer une relation</p>
        )}
        {selectedArguments.length === 1 && (
          <p>Sélectionnez un second argument</p>
        )}
        {selectedArguments.length === 2 && (
          <div>
            <p>
              <strong>{selectedArguments[0]}</strong> {relationMode === 'attack' ? 'attaque' : 'supporte'} <strong>{selectedArguments[1]}</strong>
            </p>
            <button onClick={createRelation} className="create-relation-button">
              Créer la relation
            </button>
          </div>
        )}
        {selectedArguments.length > 2 && (
          <p className="error">Trop d'arguments sélectionnés</p>
        )}
      </div>

      {selectedArguments.length > 0 && (
        <button 
          onClick={() => setSelectedArguments([])}
          className="clear-selection-button"
        >
          Effacer la sélection
        </button>
      )}
    </div>
  );

  // Rendu des options
  const renderOptions = () => (
    <div className="framework-options">
      <h4>Options du framework</h4>
      
      <div className="option-group">
        <label htmlFor="semantics">Sémantique:</label>
        <select
          id="semantics"
          value={options.semantics}
          onChange={(e) => setOptions(prev => ({ ...prev, semantics: e.target.value }))}
          className="form-select"
        >
          {availableSemantics.map(sem => (
            <option key={sem.id} value={sem.id}>
              {sem.name} - {sem.description}
            </option>
          ))}
        </select>
      </div>

      <div className="option-group">
        <label>
          <input
            type="checkbox"
            checked={options.compute_extensions}
            onChange={(e) => setOptions(prev => ({ ...prev, compute_extensions: e.target.checked }))}
          />
          Calculer les extensions
        </label>
      </div>

      {showVisualization && (
        <div className="option-group">
          <label>
            <input
              type="checkbox"
              checked={options.include_visualization}
              onChange={(e) => setOptions(prev => ({ ...prev, include_visualization: e.target.checked }))}
            />
            Inclure la visualisation
          </label>
        </div>
      )}
    </div>
  );

  // Rendu des extensions
  const renderExtensions = () => {
    if (!framework || !framework.extensions || framework.extensions.length === 0) {
      return null;
    }

    return (
      <div className="extensions-section">
        <h4>Extensions ({framework.semantics_used})</h4>
        
        <div className="extensions-tabs">
          {framework.extensions.map((ext, index) => (
            <button
              key={index}
              onClick={() => setSelectedExtension(index)}
              className={`extension-tab ${selectedExtension === index ? 'active' : ''}`}
            >
              Extension {index + 1}
              {ext.is_preferred && <span className="preferred-badge">Préférée</span>}
            </button>
          ))}
        </div>

        {framework.extensions[selectedExtension] && (
          <div className="extension-details">
            <div className="extension-info">
              <p><strong>Type:</strong> {framework.extensions[selectedExtension].type}</p>
              <p><strong>Arguments:</strong> {framework.extensions[selectedExtension].arguments.length}</p>
              <p><strong>Complète:</strong> {framework.extensions[selectedExtension].is_complete ? 'Oui' : 'Non'}</p>
              <p><strong>Préférée:</strong> {framework.extensions[selectedExtension].is_preferred ? 'Oui' : 'Non'}</p>
            </div>
            
            <div className="extension-arguments">
              <h5>Arguments dans l'extension:</h5>
              {framework.extensions[selectedExtension].arguments.length === 0 ? (
                <p className="empty-extension">Extension vide</p>
              ) : (
                <div className="extension-args-list">
                  {framework.extensions[selectedExtension].arguments.map(argId => {
                    const arg = framework.arguments.find(a => a.id === argId);
                    return (
                      <div key={argId} className="extension-arg">
                        <strong>{argId}</strong>
                        {arg && <span>: {arg.content}</span>}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  // Rendu des statistiques
  const renderStatistics = () => {
    if (!framework) return null;

    return (
      <div className="framework-statistics">
        <h4>Statistiques</h4>
        <div className="stats-grid">
          <div className="stat-item">
            <span className="stat-label">Arguments:</span>
            <span className="stat-value">{framework.argument_count}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Attaques:</span>
            <span className="stat-value">{framework.attack_count}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Supports:</span>
            <span className="stat-value">{framework.support_count}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Extensions:</span>
            <span className="stat-value">{framework.extension_count}</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">Temps:</span>
            <span className="stat-value">{Math.round(framework.processing_time * 1000)}ms</span>
          </div>
        </div>
      </div>
    );
  };

  // Rendu de la visualisation
  const renderVisualization = () => {
    if (!framework || !framework.visualization) return null;

    return (
      <div className="framework-visualization">
        <h4>Visualisation</h4>
        <div className="visualization-container">
          <svg width="600" height="400" className="framework-svg">
            {/* Rendu des arêtes */}
            {framework.visualization.edges.map((edge, index) => {
              const fromNode = framework.visualization.nodes.find(n => n.id === edge.from);
              const toNode = framework.visualization.nodes.find(n => n.id === edge.to);
              
              if (!fromNode || !toNode) return null;
              
              return (
                <g key={index}>
                  <line
                    x1={fromNode.x + 50}
                    y1={fromNode.y + 25}
                    x2={toNode.x + 50}
                    y2={toNode.y + 25}
                    stroke={edge.color}
                    strokeWidth="2"
                    markerEnd="url(#arrowhead)"
                  />
                </g>
              );
            })}
            
            {/* Rendu des nœuds */}
            {framework.visualization.nodes.map(node => (
              <g key={node.id}>
                <rect
                  x={node.x}
                  y={node.y}
                  width="100"
                  height="50"
                  fill={node.color}
                  stroke="#333"
                  strokeWidth="2"
                  rx="5"
                />
                <text
                  x={node.x + 50}
                  y={node.y + 25}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize="12"
                  fill="white"
                >
                  {node.label}
                </text>
              </g>
            ))}
            
            {/* Définition des flèches */}
            <defs>
              <marker
                id="arrowhead"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon
                  points="0 0, 10 3.5, 0 7"
                  fill="#333"
                />
              </marker>
            </defs>
          </svg>
        </div>
      </div>
    );
  };

  return (
    <div className="framework-builder">
      <div className="builder-header">
        <h3>Constructeur de Framework de Dung</h3>
        <p>Créez et analysez des frameworks d'argumentation</p>
      </div>

      <div className="builder-content">
        {/* Colonne gauche - Construction */}
        <div className="builder-left">
          {renderArgumentForm()}
          {renderRelationTools()}
          {renderOptions()}
          
          <button 
            onClick={handleBuildFramework}
            disabled={loading || arguments.length === 0}
            className="build-button"
          >
            {loading ? 'Construction...' : 'Construire le framework'}
          </button>
        </div>

        {/* Colonne droite - Arguments et résultats */}
        <div className="builder-right">
          {renderArgumentsList()}
          
          {error && (
            <div className="error-message">
              <strong>Erreur:</strong> {error}
            </div>
          )}

          {framework && (
            <div className="framework-results">
              {renderStatistics()}
              {renderExtensions()}
              {renderVisualization()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FrameworkBuilder;