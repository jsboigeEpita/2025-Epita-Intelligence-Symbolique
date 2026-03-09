import React from 'react';

/**
 * ArgumentTree — Pure CSS/React argument graph visualization.
 * Displays arguments as nodes with attack/support edges.
 */

const TYPE_COLORS = {
  claim: '#0275d8',
  attack: '#d9534f',
  rebuttal: '#5cb85c',
  support: '#5bc0de',
};

const scoreToSize = (score) => Math.max(60, Math.min(120, score * 12));

export default function ArgumentTree({ rounds = [], attackGraph = [] }) {
  if (rounds.length === 0) {
    return <div className="argument-tree empty">Aucun argument.</div>;
  }

  const args = rounds.map(r => r.argument);

  return (
    <div className="argument-tree">
      <h4>Arbre d'arguments</h4>
      <div className="tree-canvas">
        {/* SVG edges */}
        <svg className="tree-edges" width="100%" height="100%">
          {attackGraph.map((edge, i) => {
            const fromIdx = args.findIndex(a => a.id === edge.from);
            const toIdx = args.findIndex(a => a.id === edge.to);
            if (fromIdx === -1 || toIdx === -1) return null;
            // Simple layout: nodes are vertically stacked
            const x1 = 200;
            const y1 = fromIdx * 110 + 40;
            const x2 = 200;
            const y2 = toIdx * 110 + 40;
            return (
              <line
                key={i}
                x1={x1 + 60} y1={y1}
                x2={x2 - 60} y2={y2}
                stroke="#d9534f"
                strokeWidth="2"
                strokeDasharray="6,3"
                markerEnd="url(#arrowhead)"
              />
            );
          })}
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
              <polygon points="0 0, 10 3.5, 0 7" fill="#d9534f" />
            </marker>
          </defs>
        </svg>

        {/* Argument nodes */}
        <div className="tree-nodes">
          {args.map((arg, i) => {
            const size = scoreToSize(arg.score || 5);
            return (
              <div
                key={arg.id}
                className="tree-node"
                style={{
                  borderColor: TYPE_COLORS[arg.type] || '#888',
                  borderWidth: '3px',
                }}
                title={`Score: ${arg.score}`}
              >
                <div className="node-header">
                  <span
                    className="node-type"
                    style={{ color: TYPE_COLORS[arg.type] || '#888' }}
                  >
                    {arg.type}
                  </span>
                  <span className="node-score" style={{
                    width: `${size / 3}px`,
                    height: `${size / 3}px`,
                    lineHeight: `${size / 3}px`,
                    backgroundColor: TYPE_COLORS[arg.type] || '#888',
                  }}>
                    {arg.score?.toFixed(1)}
                  </span>
                </div>
                <div className="node-text">{arg.text}</div>
                {arg.target && (
                  <div className="node-target">
                    Cible: {arg.target}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
