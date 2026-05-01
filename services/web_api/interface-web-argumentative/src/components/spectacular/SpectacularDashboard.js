import React, { useState } from 'react';
import './SpectacularDashboard.css';
import { MOCK_SPECTACULAR_STATE, getFieldCounts } from '../../services/spectacularMockData';

const SECTION_ICONS = {
  'Extraction': '📝',
  'Formal Logic': '🔬',
  'Fallacies': '⚠️',
  'JTMS': '🔗',
  'ATMS': '🔀',
  'Dung': '🏗️',
  'ASPIC': '📐',
  'Counter-Arguments': '⚔️',
  'Debate': '🗣️',
  'Governance': '🏛️',
  'Quality': '📊',
  'Narrative': '📖',
  'Tweety Advanced': '🧮',
  'Workflow': '⚙️',
};

function CollapsibleSection({ title, icon, badge, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="spec-section">
      <div className="spec-section-header" onClick={() => setOpen(!open)} data-testid={`section-${title}`}>
        <div className="spec-section-title">
          <span className="spec-section-icon">{icon}</span>
          {title}
          <span className={`spec-section-badge ${badge.populated > 0 ? 'spec-badge-populated' : 'spec-badge-empty'}`}>
            {badge.populated}/{badge.total}
          </span>
        </div>
        <span className={`spec-section-chevron ${open ? 'open' : ''}`}>▶</span>
      </div>
      {open && <div className="spec-section-body">{children}</div>}
    </div>
  );
}

function ExtractionSection({ state }) {
  const argCount = Object.keys(state.identified_arguments || {}).length;
  const extCount = (state.extracts || []).length;
  return (
    <>
      <div className="spec-field-grid">
        <div className="spec-field-item">
          <div className="spec-field-label">Source Text</div>
          <div className="spec-field-value">{state.raw_text}</div>
        </div>
        <div className="spec-field-item">
          <div className="spec-field-label">Text Length</div>
          <div className="spec-field-value">{state.raw_text_length} chars</div>
        </div>
        <div className="spec-field-item">
          <div className="spec-field-label">Arguments</div>
          <div className="spec-field-value">{argCount} identified</div>
        </div>
        <div className="spec-field-item">
          <div className="spec-field-label">Fact Extracts</div>
          <div className="spec-field-value">{extCount} extracted</div>
        </div>
      </div>
      {argCount > 0 && (
        <div style={{ marginTop: 10 }}>
          <div className="spec-field-label" style={{ marginBottom: 4 }}>Identified Arguments</div>
          <div className="spec-arg-list">
            {Object.entries(state.identified_arguments).map(([id, text]) => (
              <div key={id} className="spec-arg-item">
                <span className="spec-arg-id">{id}</span>
                <span className="spec-arg-text">{text}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {extCount > 0 && (
        <div style={{ marginTop: 10 }}>
          <div className="spec-field-label" style={{ marginBottom: 4 }}>Extracts</div>
          <div className="spec-arg-list">
            {(state.extracts || []).map((ext) => (
              <div key={ext.id} className="spec-arg-item">
                <span className="spec-arg-id" style={{ color: ext.type === 'fact' ? '#4ade80' : ext.type === 'statistic' ? '#38bdf8' : '#fbbf24' }}>
                  [{ext.type}]
                </span>
                <span className="spec-arg-text">{ext.text}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function FormalLogicSection({ state }) {
  return (
    <>
      <div className="spec-field-grid">
        {(state.belief_sets && Object.keys(state.belief_sets).length > 0) &&
          Object.entries(state.belief_sets).map(([id, bs]) => (
            <div key={id} className="spec-field-item">
              <div className="spec-field-label">{bs.logic_type} Belief Set</div>
              <div className="spec-field-value" style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.8rem' }}>
                {bs.content}
              </div>
            </div>
          ))}
      </div>
      {(state.fol_analysis_results || []).length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div className="spec-field-label" style={{ marginBottom: 4 }}>FOL Formulas ({state.fol_analysis_results.length})</div>
          <div className="spec-arg-list">
            {state.fol_analysis_results.map((r) => (
              <div key={r.id} className="spec-arg-item">
                <span className="spec-arg-id" style={{ color: r.status === 'verified' ? '#4ade80' : '#f87171' }}>
                  {r.status}
                </span>
                <span className="spec-arg-text" style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{r.formula}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {(state.nl_to_logic_translations || []).length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div className="spec-field-label" style={{ marginBottom: 4 }}>NL → Logic Translations ({state.nl_to_logic_translations.length})</div>
          <div className="spec-arg-list">
            {state.nl_to_logic_translations.map((t) => (
              <div key={t.id} className="spec-arg-item">
                <span className="spec-arg-id">{t.natural}</span>
                <span className="spec-arg-text" style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                  → {t.formal} <span style={{ color: 'var(--spec-text-dim)' }}>({(t.confidence * 100).toFixed(0)}%)</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      {(state.query_log || []).length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div className="spec-field-label" style={{ marginBottom: 4 }}>Query Log ({state.query_log.length})</div>
          <div className="spec-arg-list">
            {state.query_log.map((q) => (
              <div key={q.log_id} className="spec-arg-item">
                <span className="spec-arg-id" style={{ color: '#38bdf8' }}>{q.raw_result}</span>
                <span className="spec-arg-text">{q.interpreted_result}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {(state.formal_synthesis_reports || []).length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div className="spec-field-label" style={{ marginBottom: 4 }}>Formal Synthesis</div>
          {state.formal_synthesis_reports.map((r) => (
            <div key={r.id} className="spec-conclusion">
              <strong>{r.title}</strong> (coherence: {(r.coherence_score * 100).toFixed(0)}%)
              <br />{r.summary}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function FallaciesSection({ state }) {
  const fallacies = Object.entries(state.identified_fallacies || {});
  return (
    <>
      {fallacies.map(([id, f]) => (
        <div key={id} className="spec-fallacy-item">
          <div className="spec-fallacy-path">{f.taxonomy_path}</div>
          <div className="spec-fallacy-type">{f.type} → {f.target_argument_id}</div>
          <div className="spec-fallacy-justification">{f.justification}</div>
          <div className="spec-severity-bar">
            <div
              className="spec-severity-fill"
              style={{
                width: `${f.severity * 100}%`,
                background: f.severity > 0.6 ? 'var(--spec-danger)' : f.severity > 0.4 ? 'var(--spec-warning)' : 'var(--spec-success)',
              }}
            />
          </div>
        </div>
      ))}
      {(state.neural_fallacy_scores || []).length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div className="spec-field-label" style={{ marginBottom: 4 }}>Neural Detection (CamemBERT)</div>
          {state.neural_fallacy_scores.map((s, i) => (
            <div key={i} className="spec-arg-item">
              <span className="spec-arg-id" style={{ color: '#fbbf24' }}>{(s.score * 100).toFixed(0)}%</span>
              <span className="spec-arg-text">[{s.family}] {s.text_segment}</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function JtmsSection({ state }) {
  const beliefs = Object.entries(state.jtms_beliefs || {});
  const chains = state.jtms_retraction_chain || [];
  return (
    <>
      <div className="spec-belief-list">
        {beliefs.map(([id, b]) => (
          <div key={id} className="spec-belief-item">
            <span className={`spec-belief-status ${b.status === 'VALID' ? 'valid' : 'retracted'}`} />
            <span className={`spec-belief-name ${b.status === 'RETRACTED' ? 'retracted' : ''}`}>
              {b.name}
            </span>
            <span style={{ color: 'var(--spec-text-dim)', fontSize: '0.75rem', marginLeft: 'auto' }}>
              {b.justification}
            </span>
          </div>
        ))}
      </div>
      {chains.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div className="spec-field-label" style={{ marginBottom: 4 }}>Retraction Cascades</div>
          {chains.map((chain, i) => (
            <div key={i} className="spec-retraction-chain">
              <div className="spec-retraction-trigger">Trigger: {chain.trigger}</div>
              <div className="spec-retraction-cascade">
                {chain.retracted.map((r, j) => (
                  <div key={j} style={{ paddingLeft: (j + 1) * 12 }}>
                    ↳ {r}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function AtmsSection({ state }) {
  const contexts = state.atms_contexts || [];
  return (
    <>
      {contexts.map((ctx) => (
        <div key={ctx.id} className="spec-atms-context">
          <div className="spec-atms-hypothesis">{ctx.id}: {ctx.hypothesis}</div>
          <span className={`spec-atms-status ${ctx.status}`}>
            {ctx.status}
          </span>
          <div className="spec-field-grid" style={{ marginTop: 6 }}>
            <div className="spec-field-item">
              <div className="spec-field-label">Coherent ({ctx.beliefs_coherent.length})</div>
              <div className="spec-field-value" style={{ fontSize: '0.78rem', color: 'var(--spec-success)' }}>
                {ctx.beliefs_coherent.slice(0, 5).join(', ')}{ctx.beliefs_coherent.length > 5 ? '...' : ''}
              </div>
            </div>
            <div className="spec-field-item">
              <div className="spec-field-label">Incoherent ({ctx.beliefs_incoherent.length})</div>
              <div className="spec-field-value" style={{ fontSize: '0.78rem', color: 'var(--spec-danger)' }}>
                {ctx.beliefs_incoherent.length > 0 ? ctx.beliefs_incoherent.slice(0, 5).join(', ') : 'None'}
              </div>
            </div>
          </div>
        </div>
      ))}
    </>
  );
}

function DungSection({ state }) {
  const frameworks = Object.entries(state.dung_frameworks || {});
  return (
    <>
      {frameworks.map(([id, fw]) => (
        <div key={id}>
          <div className="spec-field-item" style={{ marginBottom: 8 }}>
            <div className="spec-field-label">Arguments ({fw.arguments.length}) & Attacks ({fw.attacks.length})</div>
          </div>
          {fw.extensions && (
            <div className="spec-dung-summary">
              {['grounded', 'preferred', 'stable'].map((extType) => {
                const ext = fw.extensions[extType];
                if (!ext) return null;
                const items = Array.isArray(ext[0]) ? ext : [ext];
                return (
                  <div key={extType} className="spec-dung-ext">
                    <div className="spec-dung-ext-label">{extType}</div>
                    {items.map((e, i) => (
                      <div key={i} className="spec-dung-ext-args">
                        {e.map((arg) => (
                          <span key={arg} className="spec-dung-arg-chip" style={{
                            background: extType === 'grounded' ? 'rgba(74,222,128,0.2)' :
                              extType === 'preferred' ? 'rgba(56,189,248,0.2)' : 'rgba(251,191,36,0.2)',
                            color: extType === 'grounded' ? '#4ade80' :
                              extType === 'preferred' ? '#38bdf8' : '#fbbf24',
                          }}>
                            {arg}
                          </span>
                        ))}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ))}
    </>
  );
}

function CounterArgumentsSection({ state }) {
  const cas = state.counter_arguments || [];
  return (
    <>
      {cas.map((ca) => (
        <div key={ca.id} className="spec-ca-item">
          <div className="spec-ca-header">
            <span style={{ color: 'var(--spec-accent)', fontSize: '0.85rem', fontWeight: 600 }}>
              {ca.id} vs {ca.original_argument}
            </span>
            <span className="spec-ca-strategy">{ca.strategy}</span>
          </div>
          <div className="spec-ca-content">{ca.counter_content}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--spec-text-dim)', marginTop: 2 }}>
            Score: {(ca.score * 100).toFixed(0)}%
          </div>
        </div>
      ))}
    </>
  );
}

function QualitySection({ state }) {
  const scores = state.argument_quality_scores || {};
  const virtueColors = (v) => v >= 0.8 ? '#4ade80' : v >= 0.6 ? '#fbbf24' : '#f87171';
  return (
    <>
      {Object.entries(scores).map(([argId, data]) => (
        <div key={argId} className="spec-quality-card">
          <div className="spec-quality-header">
            <span className="spec-quality-arg">{argId}</span>
            <span className="spec-quality-overall" style={{ color: virtueColors(data.overall) }}>
              {(data.overall * 100).toFixed(0)}%
            </span>
          </div>
          <div className="spec-quality-scores">
            {Object.entries(data.scores || {}).map(([virtue, val]) => (
              <span key={virtue} className="spec-quality-virtue">
                <span className="spec-quality-virtue-label">{virtue}:</span>
                <span className="spec-quality-virtue-value" style={{ color: virtueColors(val) }}>
                  {(val * 100).toFixed(0)}%
                </span>
              </span>
            ))}
          </div>
          {data.llm_assessment && (
            <div className="spec-quality-assessment">{data.llm_assessment}</div>
          )}
        </div>
      ))}
    </>
  );
}

function DebateSection({ state }) {
  const debates = state.debate_transcripts || [];
  return (
    <>
      {debates.map((d) => (
        <div key={d.id} className="spec-field-item">
          <div className="spec-field-label" style={{ marginBottom: 4 }}>
            {d.topic} — Outcome: <strong>{d.outcome}</strong>
          </div>
          <div className="spec-arg-list">
            {d.rounds.map((r) => (
              <div key={r.round} className="spec-arg-item">
                <span className="spec-arg-id">R{r.round}</span>
                <span className="spec-arg-text">
                  [{r.argument.type}] {r.argument.text}
                  <span style={{ color: 'var(--spec-text-dim)', fontSize: '0.75rem', marginLeft: 8 }}>
                    (score: {r.argument.score})
                  </span>
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}

function GovernanceSection({ state }) {
  const decisions = state.governance_decisions || [];
  return (
    <>
      {decisions.map((d) => (
        <div key={d.id} className="spec-field-item" style={{ marginBottom: 8 }}>
          <div className="spec-field-label">{d.proposal}</div>
          <div className="spec-field-value">
            <span style={{ color: d.result === 'adopted' ? '#4ade80' : '#f87171' }}>{d.result}</span>
            {' '}via {d.voting_method} — Pro: {d.votes.pro}, Con: {d.votes.con}, Abstain: {d.votes.abstain}
            <span style={{ color: 'var(--spec-text-dim)', marginLeft: 8 }}>
              Consensus: {(d.consensus_score * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      ))}
    </>
  );
}

function NarrativeSection({ state }) {
  return <div className="spec-narrative">{state.narrative}</div>;
}

function TweetyAdvancedSection({ state }) {
  const fields = [
    { key: 'ranking_results', label: 'Rankings' },
    { key: 'belief_revision_results', label: 'Belief Revisions' },
    { key: 'dialogue_results', label: 'Dialogues' },
    { key: 'probabilistic_results', label: 'Probabilistic' },
    { key: 'bipolar_results', label: 'Bipolar' },
  ];
  return (
    <div className="spec-field-grid">
      {fields.map(({ key, label }) => {
        const items = state[key] || [];
        return items.length > 0 ? (
          <div key={key} className="spec-field-item">
            <div className="spec-field-label">{label}</div>
            <div className="spec-field-value">
              {items.map((item, i) => (
                <div key={i} style={{ fontSize: '0.8rem', marginBottom: 2 }}>
                  {item.interpretation || item.result || JSON.stringify(item).slice(0, 80)}
                </div>
              ))}
            </div>
          </div>
        ) : null;
      })}
      {(state.aspic_results || []).length > 0 && (
        <div className="spec-field-item">
          <div className="spec-field-label">ASPIC Results</div>
          <div className="spec-field-value">
            {state.aspic_results.map((r) => (
              <div key={r.id} style={{ fontSize: '0.8rem', marginBottom: 2 }}>
                {r.conclusion} ({r.defeat_status})
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function WorkflowSection({ state }) {
  const wr = state.workflow_results || {};
  const conclusion = state.final_conclusion;
  return (
    <>
      {wr.phase_details && (
        <div style={{ marginBottom: 10 }}>
          <div className="spec-field-label" style={{ marginBottom: 4 }}>
            Phases ({wr.completed_phases}/{wr.total_phases})
          </div>
          <div className="spec-phase-list">
            {wr.phase_details.map((p) => (
              <span key={p.name} className="spec-phase-chip">
                {p.name} ({p.duration_s}s)
              </span>
            ))}
          </div>
        </div>
      )}
      {conclusion && (
        <div className="spec-conclusion">
          <div className="spec-field-label" style={{ marginBottom: 4 }}>Final Conclusion</div>
          {conclusion}
        </div>
      )}
    </>
  );
}

const SECTION_RENDERERS = {
  'Extraction': ExtractionSection,
  'Formal Logic': FormalLogicSection,
  'Fallacies': FallaciesSection,
  'JTMS': JtmsSection,
  'ATMS': AtmsSection,
  'Dung': DungSection,
  'Counter-Arguments': CounterArgumentsSection,
  'Quality': QualitySection,
  'Debate': DebateSection,
  'Governance': GovernanceSection,
  'Narrative': NarrativeSection,
  'Tweety Advanced': TweetyAdvancedSection,
  'Workflow': WorkflowSection,
};

const DEFAULTS_OPEN = ['Extraction', 'Narrative', 'Quality'];

export default function SpectacularDashboard() {
  const state = MOCK_SPECTACULAR_STATE;
  const counts = getFieldCounts(state);
  const coveragePct = ((counts.populated / counts.total) * 100).toFixed(0);

  return (
    <div className="spec-dashboard">
      <div className="spec-header">
        <div>
          <h2>Spectacular Analysis Dashboard</h2>
          <span className="spec-mock-badge">MOCK DATA — Track 1 pending</span>
        </div>
        <div className="spec-meta">
          <span>Document: {state.document_id}</span>
          <span>Workflow: {state.workflow}</span>
          <span>Duration: {state.duration_seconds}s</span>
          <span>Phases: {state.phases_completed}/{state.phases_total}</span>
        </div>
      </div>

      <div className="spec-coverage-bar">
        <div className="spec-coverage-label">
          <span>Field Coverage</span>
          <span>{counts.populated}/{counts.total} fields populated ({coveragePct}%)</span>
        </div>
        <div className="spec-coverage-track">
          <div className="spec-coverage-fill" style={{ width: `${coveragePct}%` }} />
        </div>
      </div>

      {Object.entries(SECTION_RENDERERS).map(([title, Renderer]) => {
        const badge = counts.by_section[title] || { populated: 0, total: 0 };
        return (
          <CollapsibleSection
            key={title}
            title={title}
            icon={SECTION_ICONS[title]}
            badge={badge}
            defaultOpen={DEFAULTS_OPEN.includes(title)}
          >
            <Renderer state={state} />
          </CollapsibleSection>
        );
      })}
    </div>
  );
}
