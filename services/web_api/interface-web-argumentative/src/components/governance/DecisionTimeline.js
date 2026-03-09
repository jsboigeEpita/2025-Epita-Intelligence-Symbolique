import React from 'react';

/**
 * DecisionTimeline — Shows chronological events for a proposal.
 *
 * Generates timeline entries from proposal metadata:
 * creation, status changes, vote summary.
 */
export default function DecisionTimeline({ proposal }) {
  if (!proposal) return null;

  const events = [];

  // Created
  events.push({
    time: proposal.created_at,
    label: 'Proposition soumise',
    detail: `Par ${proposal.author}`,
    icon: 'create',
  });

  // Status
  if (proposal.status !== 'pending') {
    events.push({
      time: proposal.updated_at || proposal.created_at,
      label: `Statut: ${proposal.status}`,
      detail: '',
      icon: 'status',
    });
  }

  // Votes
  const total = (proposal.vote_counts?.pour || 0) +
                (proposal.vote_counts?.contre || 0) +
                (proposal.vote_counts?.abstention || 0);
  if (total > 0) {
    events.push({
      time: proposal.updated_at || proposal.created_at,
      label: `${total} vote${total > 1 ? 's' : ''} enregistre${total > 1 ? 's' : ''}`,
      detail: `Pour: ${proposal.vote_counts.pour}, Contre: ${proposal.vote_counts.contre}, Abstention: ${proposal.vote_counts.abstention}`,
      icon: 'vote',
    });
  }

  // Analysis results
  if (proposal.analysis_results) {
    events.push({
      time: proposal.updated_at || proposal.created_at,
      label: 'Analyse terminee',
      detail: 'Resultats disponibles',
      icon: 'analysis',
    });
  }

  // Decision
  if (proposal.status === 'decided') {
    events.push({
      time: proposal.updated_at || proposal.created_at,
      label: 'Decision prise',
      detail: proposal.vote_counts?.pour > proposal.vote_counts?.contre ? 'Approuvee' : 'Rejetee',
      icon: 'decision',
    });
  }

  const ICON_MAP = {
    create: '\u{1F4DD}',
    status: '\u{1F504}',
    vote: '\u{1F5F3}',
    analysis: '\u{1F50D}',
    decision: '\u{2705}',
  };

  return (
    <div className="decision-timeline">
      <h4>Chronologie</h4>
      <div className="timeline-track">
        {events.map((ev, i) => (
          <div key={i} className="timeline-event">
            <div className="timeline-icon">{ICON_MAP[ev.icon] || '\u{25CF}'}</div>
            <div className="timeline-content">
              <div className="timeline-label">{ev.label}</div>
              {ev.detail && <div className="timeline-detail">{ev.detail}</div>}
              <div className="timeline-time">
                {new Date(ev.time).toLocaleString('fr-FR')}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
