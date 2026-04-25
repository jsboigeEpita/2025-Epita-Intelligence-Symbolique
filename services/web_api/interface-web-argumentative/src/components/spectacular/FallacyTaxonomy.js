import React, { useState } from 'react';
import './FallacyTaxonomy.css';

/**
 * Mock taxonomy tree — 8 families, each with subcategories and leaf fallacies.
 * Represents the hierarchical drill-down structure (depth 2-3).
 */
export const MOCK_TAXONOMY = {
  name: 'Fallacy Taxonomy',
  children: [
    {
      name: 'Ad Hominem',
      children: [
        { name: 'Abusive', detected: true, path: 'Ad Hominem > Abusive', severity: 'high' },
        { name: 'Circumstantial', detected: false, path: 'Ad Hominem > Circumstantial' },
        { name: 'Tu Quoque', detected: true, path: 'Ad Hominem > Tu Quoque', severity: 'medium' },
      ],
    },
    {
      name: 'Appeal to Authority',
      children: [
        { name: 'False Authority', detected: true, path: 'Appeal to Authority > False Authority', severity: 'high' },
        { name: 'Anonymous Authority', detected: false, path: 'Appeal to Authority > Anonymous Authority' },
      ],
    },
    {
      name: 'Straw Man',
      children: [
        { name: 'Misrepresentation', detected: false, path: 'Straw Man > Misrepresentation' },
        { name: 'Exaggeration', detected: true, path: 'Straw Man > Exaggeration', severity: 'medium' },
      ],
    },
    {
      name: 'False Dilemma',
      children: [
        { name: 'Black-or-White', detected: false, path: 'False Dilemma > Black-or-White' },
        { name: 'Excluded Middle', detected: false, path: 'False Dilemma > Excluded Middle' },
      ],
    },
    {
      name: 'Slippery Slope',
      children: [
        { name: 'Causal Chain', detected: true, path: 'Slippery Slope > Causal Chain', severity: 'low' },
        { name: 'Fear Mongering', detected: false, path: 'Slippery Slope > Fear Mongering' },
      ],
    },
    {
      name: 'Circular Reasoning',
      children: [
        { name: 'Begging the Question', detected: false, path: 'Circular Reasoning > Begging the Question' },
        { name: 'Tautology', detected: false, path: 'Circular Reasoning > Tautology' },
      ],
    },
    {
      name: 'Hasty Generalization',
      children: [
        { name: 'Small Sample', detected: true, path: 'Hasty Generalization > Small Sample', severity: 'medium' },
        { name: 'Unrepresentative Sample', detected: false, path: 'Hasty Generalization > Unrepresentative Sample' },
      ],
    },
    {
      name: 'Red Herring',
      children: [
        { name: 'Distraction', detected: false, path: 'Red Herring > Distraction' },
        { name: 'Topic Shift', detected: false, path: 'Red Herring > Topic Shift' },
      ],
    },
  ],
};

const SEVERITY_COLORS = {
  high: '#f87171',
  medium: '#fbbf24',
  low: '#4ade80',
};

function countDetected(node) {
  if (!node.children) return node.detected ? 1 : 0;
  return node.children.reduce((sum, child) => sum + countDetected(child), 0);
}

function countLeaves(node) {
  if (!node.children) return 1;
  return node.children.reduce((sum, child) => sum + countLeaves(child), 0);
}

function TaxonomyNode({ node, depth = 0 }) {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;
  const isLeaf = !hasChildren;
  const detected = node.detected;
  const detectedCount = hasChildren ? countDetected(node) : 0;
  const totalLeaves = hasChildren ? countLeaves(node) : 0;

  return (
    <div className="taxonomy-node-wrapper">
      <div
        className={`taxonomy-node ${isLeaf ? 'taxonomy-leaf' : 'taxonomy-branch'} ${detected ? 'taxonomy-detected' : ''}`}
        style={{ paddingLeft: depth * 20 + 8 }}
        data-testid={`taxonomy-${node.name.replace(/\s+/g, '-').toLowerCase()}`}
        onClick={() => hasChildren && setExpanded(!expanded)}
      >
        {hasChildren && (
          <span className="taxonomy-expand-icon">{expanded ? '▼' : '▶'}</span>
        )}
        {isLeaf && <span className="taxonomy-leaf-spacer" />}

        <span className="taxonomy-node-name">
          {node.name}
        </span>

        {hasChildren && detectedCount > 0 && (
          <span className="taxonomy-count-badge">{detectedCount}/{totalLeaves} detected</span>
        )}

        {isLeaf && detected && (
          <span className="taxonomy-detected-badge" style={{ borderColor: SEVERITY_COLORS[node.severity] || '#38bdf8' }}>
            detected
          </span>
        )}

        {isLeaf && node.severity && (
          <span className="taxonomy-severity" style={{ color: SEVERITY_COLORS[node.severity] }}>
            {node.severity}
          </span>
        )}
      </div>

      {hasChildren && expanded && (
        <div className="taxonomy-children">
          {node.children.map((child) => (
            <TaxonomyNode key={child.name} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * FallacyTaxonomy — Interactive drill-down explorer for fallacy classification taxonomy.
 */
export default function FallacyTaxonomy({ taxonomy = MOCK_TAXONOMY, detectedFallacies = [] }) {
  const [filter, setFilter] = useState('all'); // 'all' | 'detected'

  const detectedSet = new Set(detectedFallacies);

  const filteredChildren = filter === 'detected'
    ? (taxonomy.children || []).filter((family) => countDetected(family) > 0)
    : taxonomy.children || [];

  const totalDetected = countDetected(taxonomy);
  const totalLeaves = countLeaves(taxonomy);

  return (
    <div className="taxonomy-container" data-testid="fallacy-taxonomy">
      <div className="taxonomy-header">
        <h3>Fallacy Taxonomy Explorer</h3>
        <div className="taxonomy-stats">
          <span className="taxonomy-stat">{totalDetected} detected</span>
          <span className="taxonomy-stat-divider">/</span>
          <span className="taxonomy-stat">{totalLeaves} types</span>
        </div>
      </div>

      <div className="taxonomy-filters">
        <button
          className={`taxonomy-filter-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
          data-testid="filter-all"
        >
          All
        </button>
        <button
          className={`taxonomy-filter-btn ${filter === 'detected' ? 'active' : ''}`}
          onClick={() => setFilter('detected')}
          data-testid="filter-detected"
        >
          Detected only ({totalDetected})
        </button>
      </div>

      <div className="taxonomy-tree">
        {filteredChildren.map((family) => (
          <TaxonomyNode key={family.name} node={family} depth={0} />
        ))}
        {filteredChildren.length === 0 && (
          <div className="taxonomy-empty">No fallacies detected.</div>
        )}
      </div>
    </div>
  );
}
