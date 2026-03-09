import React, { useState, useCallback } from 'react';
import ProposalList from './ProposalList';
import ProposalDetail from './ProposalDetail';
import ConflictMap from './ConflictMap';
import DecisionTimeline from './DecisionTimeline';
import { submitProposal, getProposal } from '../../services/proposalApi';
import './GovernanceDashboard.css';

export default function GovernanceDashboard() {
  const [selected, setSelected] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ text: '', author: '', title: '', tags: '' });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSelect = useCallback((proposal) => {
    setSelected(proposal);
  }, []);

  const handleUpdate = useCallback(async () => {
    if (selected) {
      try {
        const updated = await getProposal(selected.id);
        setSelected(updated);
      } catch (_) { /* ignore */ }
    }
    setRefreshKey(k => k + 1);
  }, [selected]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      const tags = formData.tags ? formData.tags.split(',').map(t => t.trim()).filter(Boolean) : [];
      const p = await submitProposal(formData.text, formData.author, {
        title: formData.title || undefined,
        tags: tags.length ? tags : undefined,
      });
      setSelected(p);
      setShowForm(false);
      setFormData({ text: '', author: '', title: '', tags: '' });
      setRefreshKey(k => k + 1);
    } catch (e) {
      setSubmitError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="governance-dashboard">
      <div className="dashboard-toolbar">
        <h2>Dashboard de Gouvernance</h2>
        <button
          className="new-proposal-btn"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? 'Annuler' : '+ Nouvelle proposition'}
        </button>
      </div>

      {showForm && (
        <form className="proposal-form" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Titre (optionnel)"
            value={formData.title}
            onChange={e => setFormData(d => ({ ...d, title: e.target.value }))}
          />
          <textarea
            placeholder="Texte de la proposition (min. 10 caracteres)"
            value={formData.text}
            onChange={e => setFormData(d => ({ ...d, text: e.target.value }))}
            required
            minLength={10}
          />
          <div className="form-row">
            <input
              type="text"
              placeholder="Auteur"
              value={formData.author}
              onChange={e => setFormData(d => ({ ...d, author: e.target.value }))}
              required
            />
            <input
              type="text"
              placeholder="Tags (virgules)"
              value={formData.tags}
              onChange={e => setFormData(d => ({ ...d, tags: e.target.value }))}
            />
          </div>
          <button type="submit" disabled={submitting}>
            {submitting ? 'Soumission...' : 'Soumettre'}
          </button>
          {submitError && <div className="form-error">{submitError}</div>}
        </form>
      )}

      <div className="dashboard-grid">
        <div className="dashboard-sidebar">
          <ProposalList
            key={refreshKey}
            onSelect={handleSelect}
            selectedId={selected?.id}
          />
        </div>

        <div className="dashboard-main">
          <ProposalDetail proposal={selected} onUpdate={handleUpdate} />

          {selected && (
            <div className="dashboard-extras">
              <ConflictMap voteCounts={selected.vote_counts} />
              <DecisionTimeline proposal={selected} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
