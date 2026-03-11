import React from 'react';

/**
 * Consensus gauge: computes a simple consensus percentage.
 *
 * Formula: if there are votes, consensus = max(pour, contre) / total * 100
 * A high value indicates strong agreement one way.
 * Equal split = 50% (low consensus).
 */
export default function ConsensusGauge({ voteCounts = {} }) {
  const pour = voteCounts.pour || 0;
  const contre = voteCounts.contre || 0;
  const abstention = voteCounts.abstention || 0;
  const total = pour + contre + abstention;

  if (total === 0) {
    return (
      <div className="consensus-gauge">
        <div className="gauge-label">Consensus</div>
        <div className="gauge-bar">
          <div className="gauge-fill" style={{ width: '0%' }} />
        </div>
        <div className="gauge-value">— (aucun vote)</div>
      </div>
    );
  }

  const dominant = Math.max(pour, contre);
  const consensus = Math.round((dominant / total) * 100);
  const direction = pour >= contre ? 'Pour' : 'Contre';

  let color;
  if (consensus >= 75) color = '#5cb85c';
  else if (consensus >= 50) color = '#f0ad4e';
  else color = '#d9534f';

  return (
    <div className="consensus-gauge">
      <div className="gauge-label">Consensus</div>
      <div className="gauge-bar">
        <div
          className="gauge-fill"
          style={{ width: `${consensus}%`, backgroundColor: color }}
        />
      </div>
      <div className="gauge-value">
        {consensus}% — Tendance: {direction}
      </div>
    </div>
  );
}
