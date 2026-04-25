import React, { useRef, useState, useCallback } from 'react';
import useDungGraphRenderer from './useDungGraphRenderer';
import './DungGraph.css';

/**
 * Mock fixture for standalone development.
 */
export const MOCK_DUNG_DATA = {
  arguments: [
    { id: 'a1', label: 'a1', text: 'Le programme est efficace' },
    { id: 'a2', label: 'a2', text: 'Contre-argument méthodologique' },
    { id: 'a3', label: 'a3', text: 'Les données sont fiables' },
    { id: 'a4', label: 'a4', text: 'Le coût est justifié' },
    { id: 'a5', label: 'a5', text: 'Attaque sur les biais' },
    { id: 'a6', label: 'a6', text: 'Confirmation par études indépendantes' },
    { id: 'a7', label: 'a7', text: 'Critique du modèle économique' },
    { id: 'a8', label: 'a8', text: 'Contre la transposabilité' },
  ],
  attacks: [
    { from: 'a5', to: 'a1' },
    { from: 'a2', to: 'a3' },
    { from: 'a7', to: 'a4' },
    { from: 'a8', to: 'a6' },
  ],
  extensions: {
    grounded: ['a1', 'a3', 'a4', 'a6'],
    preferred: [['a1', 'a3', 'a4', 'a6'], ['a2', 'a4', 'a5', 'a6']],
    stable: [['a1', 'a3', 'a4', 'a6']],
  },
};

const EXT_COLORS = {
  grounded: { fill: 'rgba(74, 222, 128, 0.3)', stroke: '#4ade80' },
  preferred: { fill: 'rgba(56, 189, 248, 0.3)', stroke: '#38bdf8' },
  stable: { fill: 'rgba(251, 191, 36, 0.3)', stroke: '#fbbf24' },
};

/**
 * DungGraph — Interactive D3.js force-directed graph for Dung argumentation frameworks.
 */
export default function DungGraph({ data = MOCK_DUNG_DATA }) {
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [activeExtension, setActiveExtension] = useState('grounded');
  const [tooltip, setTooltip] = useState({ show: false, x: 0, y: 0, content: '' });

  const getExtMembership = useCallback((nodeId) => {
    const ext = data.extensions[activeExtension];
    if (!ext) return 'none';
    const flat = Array.isArray(ext[0]) ? ext.flat() : ext;
    return flat.includes(nodeId) ? activeExtension : 'none';
  }, [data.extensions, activeExtension]);

  const argTextMap = {};
  (data.arguments || []).forEach((a) => { argTextMap[a.id] = a.text || a.label || a.id; });

  useDungGraphRenderer(svgRef, containerRef, data, activeExtension, getExtMembership, argTextMap, setTooltip);

  const getNodeExtensions = (nodeId) => {
    const result = [];
    if (data.extensions) {
      for (const [type, ext] of Object.entries(data.extensions)) {
        const flat = Array.isArray(ext[0]) ? ext.flat() : ext;
        if (flat.includes(nodeId)) result.push(type);
      }
    }
    return result;
  };

  return (
    <div className="dung-graph-container" data-testid="dung-graph">
      <div className="dung-graph-header">
        <h3>Dung Argumentation Framework</h3>
        <div className="dung-graph-legend">
          {Object.entries(EXT_COLORS).map(([type, colors]) => (
            <div key={type} className="dung-legend-item">
              <span className="dung-legend-dot" style={{ background: colors.stroke }} />
              <span>{type}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="dung-ext-selector">
        {['grounded', 'preferred', 'stable'].map((type) => (
          <button
            key={type}
            className={`dung-ext-btn ${activeExtension === type ? 'active' : ''}`}
            onClick={() => setActiveExtension(type)}
            data-testid={`ext-btn-${type}`}
          >
            {type}
          </button>
        ))}
      </div>

      <div className="dung-svg-container" ref={containerRef}>
        <svg ref={svgRef} />
        {tooltip.show && (
          <div className="dung-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
            {tooltip.content}
          </div>
        )}
      </div>

      {selectedNode && (
        <div className="dung-detail-panel" data-testid="dung-detail">
          <div className="dung-detail-arg">{selectedNode.id}: {argTextMap[selectedNode.id]}</div>
          <div className="dung-detail-ext">
            Extensions:{' '}
            {getNodeExtensions(selectedNode.id).map((ext) => (
              <span key={ext} style={{
                background: EXT_COLORS[ext] ? EXT_COLORS[ext].fill : '#64748b',
                color: EXT_COLORS[ext] ? EXT_COLORS[ext].stroke : '#e2e8f0',
              }}>
                {ext}
              </span>
            ))}
            {getNodeExtensions(selectedNode.id).length === 0 && (
              <span style={{ color: '#64748b' }}>none</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
