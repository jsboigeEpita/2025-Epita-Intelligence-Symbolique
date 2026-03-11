import React from 'react';

/**
 * DebateTimeline — Chronological list of debate interventions.
 */
const TYPE_ICONS = {
  claim: '\u{1F4AC}',
  attack: '\u{2694}',
  rebuttal: '\u{1F6E1}',
  support: '\u{1F91D}',
};

const TYPE_COLORS = {
  claim: '#0275d8',
  attack: '#d9534f',
  rebuttal: '#5cb85c',
  support: '#5bc0de',
};

export default function DebateTimeline({ rounds = [], agents = [] }) {
  if (rounds.length === 0) return null;

  const agentMap = {};
  agents.forEach(a => { agentMap[a.id] = a; });

  return (
    <div className="debate-timeline">
      <h4>Chronologie du debat</h4>
      <div className="debate-track">
        {rounds.map((round, i) => {
          const agent = agentMap[round.agent] || { name: round.agent };
          const arg = round.argument;
          return (
            <div key={i} className="debate-entry">
              <div className="entry-round">Tour {round.round}</div>
              <div
                className="entry-marker"
                style={{ backgroundColor: TYPE_COLORS[arg.type] || '#888' }}
              >
                {TYPE_ICONS[arg.type] || '\u{25CF}'}
              </div>
              <div className="entry-body">
                <div className="entry-header">
                  <span className="entry-agent">{agent.name}</span>
                  <span
                    className="entry-type"
                    style={{ color: TYPE_COLORS[arg.type] || '#888' }}
                  >
                    {arg.type}
                  </span>
                  <span className="entry-score">{arg.score?.toFixed(1)}/10</span>
                </div>
                <div className="entry-text">{arg.text}</div>
                <div className="entry-time">
                  {new Date(round.timestamp).toLocaleTimeString('fr-FR')}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
