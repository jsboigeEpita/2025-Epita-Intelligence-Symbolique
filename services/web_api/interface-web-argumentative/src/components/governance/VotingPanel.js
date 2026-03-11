import React, { useState } from 'react';
import { castVote } from '../../services/proposalApi';

const POSITIONS = [
  { id: 'pour', label: 'Voter Pour', color: '#5cb85c' },
  { id: 'contre', label: 'Voter Contre', color: '#d9534f' },
  { id: 'abstention', label: "S'abstenir", color: '#888' },
];

export default function VotingPanel({ proposalId, onVoted }) {
  const [voterId, setVoterId] = useState('');
  const [voting, setVoting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleVote = async (position) => {
    if (!voterId.trim()) {
      setError('Veuillez entrer votre identifiant.');
      return;
    }
    setVoting(true);
    setError(null);
    setResult(null);
    try {
      const res = await castVote(proposalId, voterId.trim(), position);
      setResult(res);
      onVoted?.();
    } catch (e) {
      if (e.status === 409) {
        setError('Vous avez deja vote sur cette proposition.');
      } else {
        setError(e.message);
      }
    } finally {
      setVoting(false);
    }
  };

  return (
    <div className="voting-panel">
      <h3>Voter</h3>
      <div className="voter-input">
        <input
          type="text"
          placeholder="Votre identifiant"
          value={voterId}
          onChange={e => setVoterId(e.target.value)}
          disabled={voting}
        />
      </div>
      <div className="vote-buttons">
        {POSITIONS.map(p => (
          <button
            key={p.id}
            onClick={() => handleVote(p.id)}
            disabled={voting || !voterId.trim()}
            className="vote-btn"
            style={{ borderColor: p.color }}
          >
            {p.label}
          </button>
        ))}
      </div>
      {result && (
        <div className="vote-result success">
          Vote enregistre: <strong>{result.position}</strong>
        </div>
      )}
      {error && <div className="vote-result error">{error}</div>}
    </div>
  );
}
