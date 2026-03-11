import React from 'react';

/**
 * ScoreBoard — Real-time scoring table with multiple metrics.
 */
const METRIC_LABELS = {
  clarity: 'Clarte',
  coherence: 'Coherence',
  relevance: 'Pertinence',
  persuasion: 'Persuasion',
  evidence: 'Preuves',
};

export default function ScoreBoard({ rounds = [], agents = [] }) {
  if (rounds.length === 0) return null;

  // Compute average metrics per agent
  const agentStats = {};
  for (const agent of agents) {
    const agentRounds = rounds.filter(r => r.agent === agent.id);
    const metrics = {};
    const metricKeys = Object.keys(METRIC_LABELS);

    for (const key of metricKeys) {
      const values = agentRounds
        .map(r => r.argument?.metrics?.[key])
        .filter(v => v != null);
      metrics[key] = values.length
        ? (values.reduce((a, b) => a + b, 0) / values.length)
        : 0;
    }

    const avgScore = agentRounds.length
      ? agentRounds.reduce((s, r) => s + (r.argument?.score || 0), 0) / agentRounds.length
      : 0;

    agentStats[agent.id] = { ...agent, metrics, avgScore, roundCount: agentRounds.length };
  }

  return (
    <div className="score-board">
      <h4>Tableau de scores</h4>
      <table className="score-table">
        <thead>
          <tr>
            <th>Agent</th>
            <th>Tours</th>
            <th>Moy.</th>
            {Object.values(METRIC_LABELS).map(l => <th key={l}>{l}</th>)}
          </tr>
        </thead>
        <tbody>
          {agents.map(agent => {
            const stats = agentStats[agent.id];
            return (
              <tr key={agent.id}>
                <td className="agent-cell">{agent.name}</td>
                <td>{stats.roundCount}</td>
                <td className="score-cell">
                  <strong>{stats.avgScore.toFixed(1)}</strong>
                </td>
                {Object.keys(METRIC_LABELS).map(key => (
                  <td key={key}>
                    <span className="metric-bar">
                      <span
                        className="metric-fill"
                        style={{ width: `${(stats.metrics[key] / 10) * 100}%` }}
                      />
                      <span className="metric-value">{stats.metrics[key].toFixed(1)}</span>
                    </span>
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
