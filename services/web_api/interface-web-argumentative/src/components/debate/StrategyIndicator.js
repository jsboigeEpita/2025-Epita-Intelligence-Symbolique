import React from 'react';

/**
 * StrategyIndicator — Shows each agent's current strategy and recent moves.
 */
export default function StrategyIndicator({ agents = [], rounds = [] }) {
  if (agents.length === 0) return null;

  return (
    <div className="strategy-indicator">
      <h4>Strategies en cours</h4>
      <div className="strategy-cards">
        {agents.map(agent => {
          const agentRounds = rounds.filter(r => r.agent === agent.id);
          const lastRound = agentRounds[agentRounds.length - 1];
          const lastType = lastRound?.argument?.type || '-';
          const attacks = agentRounds.filter(r => r.argument?.type === 'attack').length;
          const rebuttals = agentRounds.filter(r => r.argument?.type === 'rebuttal').length;

          return (
            <div key={agent.id} className="strategy-card">
              <div className="strategy-agent">{agent.name}</div>
              <div className="strategy-name">{agent.strategy}</div>
              <div className="strategy-stats">
                <span>Dernier: <strong>{lastType}</strong></span>
                <span>Attaques: {attacks}</span>
                <span>Rebuts: {rebuttals}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
