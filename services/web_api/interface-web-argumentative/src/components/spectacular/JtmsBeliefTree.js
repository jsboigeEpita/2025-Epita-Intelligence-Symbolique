import React, { useState } from 'react';
import './JtmsBeliefTree.css';

const STATUS_ICONS = {
  valid: { icon: '✓', className: 'jtms-status-valid' },
  invalid: { icon: '✗', className: 'jtms-status-invalid' },
  unknown: { icon: '?', className: 'jtms-status-unknown' },
};

/**
 * Mock fixture for standalone development.
 */
export const MOCK_JTMS_DATA = {
  beliefs: {
    root_1: { name: 'root_1', label: 'Argument principal valide', valid: true, justifications: [], source: 'ExtractAgent' },
    root_2: { name: 'root_2', label: 'Données empiriques confirmées', valid: true, justifications: [], source: 'ExtractAgent' },
    derived_1: { name: 'derived_1', label: 'Conclusion intermédiaire', valid: true, justifications: ['root_1', 'root_2'], source: 'LogicAgent' },
    derived_2: { name: 'derived_2', label: 'Inférence logique A', valid: true, justifications: ['derived_1'], source: 'FOLAgent' },
    derived_3: { name: 'derived_3', label: 'Inférence logique B', valid: true, justifications: ['derived_1'], source: 'FOLAgent' },
    retracted_1: {
      name: 'retracted_1', label: 'Argument par autorité', valid: null,
      justifications: ['root_2'],
      retracted: true, retraction_reason: 'fallacy: appeal_to_authority',
      source: 'ExtractAgent',
    },
    retracted_2: {
      name: 'retracted_2', label: 'Conclusion basée sur argument retraité',
      valid: null, justifications: ['retracted_1'],
      retracted: true, retraction_reason: 'cascade: retracted_1 retracted',
      source: 'LogicAgent',
    },
    root_3: { name: 'root_3', label: 'Hypothèse non vérifiée', valid: null, justifications: [], source: 'InformalAgent' },
  },
};

function getBeliefStatus(valid) {
  if (valid === true) return 'valid';
  if (valid === false) return 'invalid';
  return 'unknown';
}

function BeliefNode({ belief, beliefs, childrenMap, depth = 0, hoveredId, setHoveredId }) {
  const [collapsed, setCollapsed] = useState(false);
  const status = getBeliefStatus(belief.valid);
  const statusInfo = STATUS_ICONS[status];
  const isRetracted = belief.retracted || belief.valid === null;
  const isHovered = hoveredId === belief.name;

  const childNames = (childrenMap && childrenMap[belief.name]) || [];
  const children = childNames.map((n) => beliefs[n]).filter(Boolean);

  const isRoot = !belief.justifications || belief.justifications.length === 0;

  return (
    <div className="jtms-node-wrapper">
      <div
        className={`jtms-node ${statusInfo.className} ${isRetracted ? 'jtms-retracted' : ''} ${isHovered ? 'jtms-hovered' : ''}`}
        style={{ paddingLeft: depth * 24 + 12 }}
        onMouseEnter={() => setHoveredId(belief.name)}
        onMouseLeave={() => setHoveredId(null)}
        data-testid={`belief-node-${belief.name}`}
      >
        {children.length > 0 && (
          <button
            className="jtms-collapse-btn"
            onClick={() => setCollapsed(!collapsed)}
            data-testid={`collapse-btn-${belief.name}`}
          >
            {collapsed ? '▶' : '▼'}
          </button>
        )}
        {children.length === 0 && <span className="jtms-leaf-spacer" />}

        <span className={`jtms-status-icon ${statusInfo.className}`}>
          {statusInfo.icon}
        </span>

        <span className={`jtms-belief-label ${isRetracted ? 'jtms-strikethrough' : ''}`}>
          {belief.label || belief.name}
        </span>

        {isRoot && <span className="jtms-badge jtms-badge-root">root</span>}
        {isRetracted && belief.retraction_reason && (
          <span className="jtms-badge jtms-badge-retracted">retracted</span>
        )}
        {belief.source && <span className="jtms-badge jtms-badge-source">{belief.source}</span>}
      </div>

      {isHovered && (
        <div className="jtms-tooltip" style={{ marginLeft: depth * 24 + 40 }}>
          <div className="jtms-tooltip-title">{belief.label || belief.name}</div>
          <div className="jtms-tooltip-detail">Status: {status}</div>
          {belief.justifications && belief.justifications.length > 0 && (
            <div className="jtms-tooltip-detail">
              Justifications: {belief.justifications.join(', ')}
            </div>
          )}
          {isRetracted && belief.retraction_reason && (
            <div className="jtms-tooltip-detail jtms-tooltip-retraction">
              Reason: {belief.retraction_reason}
            </div>
          )}
          {children.length > 0 && (
            <div className="jtms-tooltip-detail">
              Derives: {children.map((c) => c.name).join(', ')}
            </div>
          )}
        </div>
      )}

      {!collapsed && children.length > 0 && (
        <div className="jtms-children">
          {children.map((child) => (
            <BeliefNode
              key={child.name}
              belief={child}
              beliefs={beliefs}
              childrenMap={childrenMap}
              depth={depth + 1}
              hoveredId={hoveredId}
              setHoveredId={setHoveredId}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Build a tree structure where each belief appears exactly once.
 * A belief is a child of its first justification; if no justifications, it's a root.
 */
function buildTree(beliefs) {
  const claimed = new Set();
  const childrenMap = {};

  // First pass: assign each belief to its first justification's children list
  Object.values(beliefs).forEach((b) => {
    if (b.justifications && b.justifications.length > 0) {
      const parent = b.justifications[0];
      if (!childrenMap[parent]) childrenMap[parent] = [];
      childrenMap[parent].push(b.name);
      claimed.add(b.name);
    }
  });

  const roots = Object.values(beliefs)
    .filter((b) => !claimed.has(b.name))
    .map((b) => b.name);

  return { roots, childrenMap };
}

/**
 * JtmsBeliefTree — Collapsible tree explorer for JTMS beliefs with retraction cascades.
 */
export default function JtmsBeliefTree({ data = MOCK_JTMS_DATA }) {
  const [hoveredId, setHoveredId] = useState(null);
  const beliefs = data.beliefs || {};
  const { roots, childrenMap } = buildTree(beliefs);

  const counts = { valid: 0, invalid: 0, unknown: 0, retracted: 0 };
  Object.values(beliefs).forEach((b) => {
    counts[getBeliefStatus(b.valid)]++;
    if (b.retracted) counts.retracted++;
  });

  return (
    <div className="jtms-tree-container" data-testid="jtms-belief-tree">
      <div className="jtms-tree-header">
        <h3>JTMS Belief Explorer</h3>
        <div className="jtms-summary">
          <span className="jtms-summary-item jtms-status-valid">{counts.valid} valid</span>
          <span className="jtms-summary-item jtms-status-invalid">{counts.invalid} invalid</span>
          <span className="jtms-summary-item jtms-status-unknown">{counts.unknown} unknown</span>
          {counts.retracted > 0 && (
            <span className="jtms-summary-item jtms-status-retracted">{counts.retracted} retracted</span>
          )}
        </div>
      </div>

      <div className="jtms-tree-body">
        {roots.length === 0 && (
          <div className="jtms-empty">No beliefs to display.</div>
        )}
        {roots.map((name) => (
          <BeliefNode
            key={name}
            belief={beliefs[name]}
            beliefs={beliefs}
            childrenMap={childrenMap}
            hoveredId={hoveredId}
            setHoveredId={setHoveredId}
          />
        ))}
      </div>
    </div>
  );
}
