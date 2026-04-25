import React, { useState } from 'react';
import './AtmsContextView.css';

/**
 * Mock fixture for standalone development.
 */
export const MOCK_ATMS_DATA = {
  hypotheses: ['H1_efficient', 'H2_reliable', 'H3_cost', 'H4_biased'],
  contexts: {
    'H1,H2': {
      id: 'ctx_1',
      label: 'H1 + H2',
      hypotheses: ['H1_efficient', 'H2_reliable'],
      consistent: true,
      beliefs: {
        arg_efficient: { status: 'in', label: 'Le programme est efficace' },
        arg_reliable: { status: 'in', label: 'Les données sont fiables' },
        arg_cost: { status: 'out', label: 'Le coût est justifié' },
        arg_biased: { status: 'undecided', label: 'Biais détectés' },
      },
    },
    'H1,H3': {
      id: 'ctx_2',
      label: 'H1 + H3',
      hypotheses: ['H1_efficient', 'H3_cost'],
      consistent: true,
      beliefs: {
        arg_efficient: { status: 'in', label: 'Le programme est efficace' },
        arg_reliable: { status: 'undecided', label: 'Les données sont fiables' },
        arg_cost: { status: 'in', label: 'Le coût est justifié' },
        arg_biased: { status: 'out', label: 'Biais détectés' },
      },
    },
    'H2,H4': {
      id: 'ctx_3',
      label: 'H2 + H4',
      hypotheses: ['H2_reliable', 'H4_biased'],
      consistent: false,
      conflict: 'H2_reliable contradicts H4_biased',
      beliefs: {
        arg_efficient: { status: 'undecided', label: 'Le programme est efficace' },
        arg_reliable: { status: 'in', label: 'Les données sont fiables' },
        arg_cost: { status: 'out', label: 'Le coût est justifié' },
        arg_biased: { status: 'in', label: 'Biais détectés' },
      },
    },
    'H3,H4': {
      id: 'ctx_4',
      label: 'H3 + H4',
      hypotheses: ['H3_cost', 'H4_biased'],
      consistent: true,
      beliefs: {
        arg_efficient: { status: 'out', label: 'Le programme est efficace' },
        arg_reliable: { status: 'undecided', label: 'Les données sont fiables' },
        arg_cost: { status: 'in', label: 'Le coût est justifié' },
        arg_biased: { status: 'in', label: 'Biais détectés' },
      },
    },
  },
};

const STATUS_LABELS = {
  in: { label: 'IN', className: 'atms-status-in' },
  out: { label: 'OUT', className: 'atms-status-out' },
  undecided: { label: 'UNDECIDED', className: 'atms-status-undecided' },
};

/**
 * AtmsContextView — Context selector for ATMS hypothesis analysis.
 */
export default function AtmsContextView({ data = MOCK_ATMS_DATA }) {
  const [activeContext, setActiveContext] = useState(null);
  const contextKeys = Object.keys(data.contexts || {});

  const selectedCtx = activeContext ? data.contexts[activeContext] : null;

  return (
    <div className="atms-container" data-testid="atms-context-view">
      <div className="atms-header">
        <h3>ATMS Context Explorer</h3>
        <div className="atms-context-count">
          {contextKeys.length} contexts
        </div>
      </div>

      <div className="atms-selector">
        <select
          className="atms-dropdown"
          value={activeContext || ''}
          onChange={(e) => setActiveContext(e.target.value || null)}
          data-testid="atms-context-dropdown"
        >
          <option value="">Select a context...</option>
          {contextKeys.map((key) => {
            const ctx = data.contexts[key];
            return (
              <option key={key} value={key}>
                {ctx.label || key} {!ctx.consistent && '⚠'}
              </option>
            );
          })}
        </select>
      </div>

      {selectedCtx && (
        <div className="atms-context-detail" data-testid="atms-context-detail">
          <div className={`atms-consistency-badge ${selectedCtx.consistent ? 'atms-consistent' : 'atms-inconsistent'}`}>
            {selectedCtx.consistent ? 'Consistent' : 'Inconsistent'}
          </div>

          <div className="atms-hypotheses">
            <span className="atms-section-label">Hypotheses:</span>
            {selectedCtx.hypotheses.map((h) => (
              <span key={h} className="atms-hypothesis-chip">{h}</span>
            ))}
          </div>

          {selectedCtx.conflict && (
            <div className="atms-conflict" data-testid="atms-conflict">
              <span className="atms-conflict-icon">⚠</span>
              Conflict: {selectedCtx.conflict}
            </div>
          )}

          <div className="atms-beliefs-table">
            <div className="atms-beliefs-header">
              <span>Belief</span>
              <span>Status</span>
            </div>
            {Object.entries(selectedCtx.beliefs || {}).map(([id, belief]) => {
              const statusInfo = STATUS_LABELS[belief.status] || STATUS_LABELS.undecided;
              return (
                <div key={id} className="atms-belief-row" data-testid={`atms-belief-${id}`}>
                  <span className="atms-belief-label">{belief.label || id}</span>
                  <span className={`atms-status-badge ${statusInfo.className}`}>
                    {statusInfo.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!selectedCtx && (
        <div className="atms-empty" data-testid="atms-empty">
          Select a context to view belief status under different hypotheses.
        </div>
      )}
    </div>
  );
}
