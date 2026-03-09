import React, { useState, useEffect, useCallback } from 'react';
import { listProposals } from '../../services/proposalApi';

const STATUS_LABELS = {
  pending: 'En attente',
  analyzing: 'Analyse en cours',
  debating: 'Débat',
  voting: 'Vote',
  decided: 'Décidé',
};

const STATUS_COLORS = {
  pending: '#888',
  analyzing: '#f0ad4e',
  debating: '#5bc0de',
  voting: '#0275d8',
  decided: '#5cb85c',
};

export default function ProposalList({ onSelect, selectedId }) {
  const [proposals, setProposals] = useState([]);
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listProposals({ status: statusFilter || undefined });
      setProposals(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { refresh(); }, [refresh]);

  // Auto-refresh every 10s
  useEffect(() => {
    const id = setInterval(refresh, 10000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <div className="proposal-list">
      <div className="proposal-list-header">
        <h3>Propositions</h3>
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="status-filter"
        >
          <option value="">Tous</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <button onClick={refresh} className="refresh-btn" title="Rafraichir">
          &#x21bb;
        </button>
      </div>

      {loading && proposals.length === 0 && <p className="loading-msg">Chargement...</p>}
      {error && <p className="error-msg">{error}</p>}

      {proposals.length === 0 && !loading && (
        <p className="empty-msg">Aucune proposition.</p>
      )}

      <ul className="proposal-items">
        {proposals.map(p => {
          const total = (p.vote_counts?.pour || 0) + (p.vote_counts?.contre || 0) + (p.vote_counts?.abstention || 0);
          return (
            <li
              key={p.id}
              className={`proposal-item ${selectedId === p.id ? 'selected' : ''}`}
              onClick={() => onSelect?.(p)}
            >
              <div className="proposal-item-header">
                <span
                  className="status-badge"
                  style={{ backgroundColor: STATUS_COLORS[p.status] || '#888' }}
                >
                  {STATUS_LABELS[p.status] || p.status}
                </span>
                <span className="vote-count">{total} vote{total !== 1 ? 's' : ''}</span>
              </div>
              <div className="proposal-item-title">
                {p.title || p.text.substring(0, 80)}
              </div>
              <div className="proposal-item-meta">
                par {p.author} &middot; {new Date(p.created_at).toLocaleDateString('fr-FR')}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
