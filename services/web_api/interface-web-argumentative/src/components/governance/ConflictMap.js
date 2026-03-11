import React from 'react';

/**
 * ConflictMap — Visualizes conflicts between positions (pour vs contre).
 *
 * Displays vote distribution as a horizontal stacked bar with conflict
 * intensity indicator. A high conflict ratio (close to 50/50) shows red.
 */
export default function ConflictMap({ voteCounts = {} }) {
  const pour = voteCounts.pour || 0;
  const contre = voteCounts.contre || 0;
  const total = pour + contre;

  if (total === 0) {
    return (
      <div className="conflict-map">
        <h4>Carte des conflits</h4>
        <p className="empty-msg">Pas de votes pour/contre a comparer.</p>
      </div>
    );
  }

  const pourPct = Math.round((pour / total) * 100);
  const contrePct = 100 - pourPct;

  // Conflict intensity: 0 = unanimous, 1 = 50/50
  const conflictRatio = 1 - Math.abs(pour - contre) / total;
  let conflictLevel, conflictColor;
  if (conflictRatio < 0.3) {
    conflictLevel = 'Faible';
    conflictColor = '#5cb85c';
  } else if (conflictRatio < 0.6) {
    conflictLevel = 'Modere';
    conflictColor = '#f0ad4e';
  } else {
    conflictLevel = 'Eleve';
    conflictColor = '#d9534f';
  }

  return (
    <div className="conflict-map">
      <h4>Carte des conflits</h4>
      <div className="conflict-bar">
        <div
          className="conflict-pour"
          style={{ width: `${pourPct}%`, backgroundColor: '#5cb85c' }}
        >
          {pourPct > 15 && `Pour ${pourPct}%`}
        </div>
        <div
          className="conflict-contre"
          style={{ width: `${contrePct}%`, backgroundColor: '#d9534f' }}
        >
          {contrePct > 15 && `Contre ${contrePct}%`}
        </div>
      </div>
      <div className="conflict-indicator">
        <span
          className="conflict-dot"
          style={{ backgroundColor: conflictColor }}
        />
        Intensite du conflit: <strong>{conflictLevel}</strong> ({Math.round(conflictRatio * 100)}%)
      </div>
    </div>
  );
}
