import React from 'react';

/**
 * AgentPanel — Displays agent profiles with personality, strategy, and score.
 */
export default function AgentPanel({ agents = [] }) {
  if (agents.length === 0) return null;

  return (
    <div className="agent-panel">
      <h4>Agents</h4>
      <div className="agent-cards">
        {agents.map(agent => (
          <div key={agent.id} className="agent-card">
            <div className="agent-avatar">
              {agent.name.charAt(0).toUpperCase()}
            </div>
            <div className="agent-info">
              <div className="agent-name">{agent.name}</div>
              <div className="agent-personality">{agent.personality}</div>
              <div className="agent-strategy">
                Strategie: <strong>{agent.strategy}</strong>
              </div>
            </div>
            <div className="agent-score">
              <div className="score-value">{agent.totalScore?.toFixed(1)}</div>
              <div className="score-label">Score</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
