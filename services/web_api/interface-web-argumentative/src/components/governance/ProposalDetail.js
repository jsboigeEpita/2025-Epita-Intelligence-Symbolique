import React, { useState } from 'react';
import { startDeliberation } from '../../services/proposalApi';
import VotingPanel from './VotingPanel';
import ConsensusGauge from './ConsensusGauge';

const STATUS_LABELS = {
  pending: 'En attente',
  analyzing: 'Analyse en cours',
  debating: 'Débat',
  voting: 'Vote',
  decided: 'Décidé',
};

export default function ProposalDetail({ proposal, onUpdate }) {
  const [delibStatus, setDelibStatus] = useState(null);
  const [launching, setLaunching] = useState(false);

  if (!proposal) {
    return (
      <div className="proposal-detail empty">
        <p>Sélectionnez une proposition pour voir les détails.</p>
      </div>
    );
  }

  const { vote_counts = {} } = proposal;
  const total = (vote_counts.pour || 0) + (vote_counts.contre || 0) + (vote_counts.abstention || 0);

  const handleLaunchDelib = async (workflow) => {
    setLaunching(true);
    try {
      const result = await startDeliberation(proposal.id, workflow);
      setDelibStatus(result);
    } catch (e) {
      setDelibStatus({ status: 'failed', error: e.message });
    } finally {
      setLaunching(false);
    }
  };

  return (
    <div className="proposal-detail">
      <div className="detail-header">
        <h2>{proposal.title || 'Proposition'}</h2>
        <span className="detail-status">
          {STATUS_LABELS[proposal.status] || proposal.status}
        </span>
      </div>

      <div className="detail-meta">
        <span>Par <strong>{proposal.author}</strong></span>
        <span>{new Date(proposal.created_at).toLocaleString('fr-FR')}</span>
        {proposal.tags?.length > 0 && (
          <div className="detail-tags">
            {proposal.tags.map(t => <span key={t} className="tag">{t}</span>)}
          </div>
        )}
      </div>

      <div className="detail-text">{proposal.text}</div>

      {/* Vote Counts + Consensus */}
      <div className="detail-votes-section">
        <h3>Votes ({total})</h3>
        <div className="vote-bars">
          <div className="vote-bar">
            <span className="vote-label pour">Pour</span>
            <div className="vote-bar-fill" style={{
              width: total ? `${(vote_counts.pour / total) * 100}%` : '0%',
              backgroundColor: '#5cb85c'
            }} />
            <span className="vote-num">{vote_counts.pour || 0}</span>
          </div>
          <div className="vote-bar">
            <span className="vote-label contre">Contre</span>
            <div className="vote-bar-fill" style={{
              width: total ? `${(vote_counts.contre / total) * 100}%` : '0%',
              backgroundColor: '#d9534f'
            }} />
            <span className="vote-num">{vote_counts.contre || 0}</span>
          </div>
          <div className="vote-bar">
            <span className="vote-label abstention">Abstention</span>
            <div className="vote-bar-fill" style={{
              width: total ? `${(vote_counts.abstention / total) * 100}%` : '0%',
              backgroundColor: '#888'
            }} />
            <span className="vote-num">{vote_counts.abstention || 0}</span>
          </div>
        </div>
        <ConsensusGauge voteCounts={vote_counts} />
      </div>

      {/* Voting Panel */}
      <VotingPanel proposalId={proposal.id} onVoted={onUpdate} />

      {/* Analysis Results */}
      {proposal.analysis_results && (
        <div className="detail-analysis">
          <h3>Resultats d'analyse</h3>
          <pre className="analysis-json">
            {JSON.stringify(proposal.analysis_results, null, 2)}
          </pre>
        </div>
      )}

      {/* Deliberation Launch */}
      <div className="detail-deliberation">
        <h3>Deliberation</h3>
        {delibStatus && (
          <div className={`delib-status ${delibStatus.status}`}>
            Statut: {delibStatus.status}
            {delibStatus.error && <span className="delib-error"> — {delibStatus.error}</span>}
          </div>
        )}
        <div className="delib-actions">
          {['light', 'standard', 'democratech'].map(wf => (
            <button
              key={wf}
              onClick={() => handleLaunchDelib(wf)}
              disabled={launching}
              className="delib-btn"
            >
              {wf}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
