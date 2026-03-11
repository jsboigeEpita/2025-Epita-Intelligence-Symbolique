import React, { useState } from 'react';
import AgentPanel from './AgentPanel';
import ArgumentTree from './ArgumentTree';
import ScoreBoard from './ScoreBoard';
import DebateTimeline from './DebateTimeline';
import StrategyIndicator from './StrategyIndicator';
import { getDemoDebate, runDebateAnalysis } from '../../services/debateApi';
import './DebateArena.css';

export default function DebateArena() {
  const [debate, setDebate] = useState(null);
  const [customText, setCustomText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [view, setView] = useState('timeline'); // timeline | tree | scores

  const handleLoadDemo = () => {
    setDebate(getDemoDebate());
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!customText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await runDebateAnalysis(customText);
      // If API returns structured data, use it; otherwise wrap
      if (result.results?.rounds) {
        setDebate(result.results);
      } else {
        setDebate({
          topic: customText.substring(0, 100),
          agents: [],
          rounds: [],
          attackGraph: [],
          rawResults: result,
        });
      }
    } catch (e) {
      setError(e.message);
      // Fall back to demo
      setDebate(getDemoDebate());
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="debate-arena">
      <div className="arena-header">
        <h2>Arene de Debat</h2>
        <div className="arena-actions">
          <button onClick={handleLoadDemo} className="demo-btn">
            Charger demo
          </button>
        </div>
      </div>

      {/* Custom analysis input */}
      <div className="arena-input">
        <textarea
          placeholder="Entrez un sujet de debat ou un texte argumentatif a analyser..."
          value={customText}
          onChange={e => setCustomText(e.target.value)}
        />
        <button onClick={handleAnalyze} disabled={loading || !customText.trim()}>
          {loading ? 'Analyse...' : 'Lancer le debat'}
        </button>
      </div>

      {error && <div className="arena-error">{error} (demo chargee)</div>}

      {debate && (
        <>
          <div className="arena-topic">
            <h3>{debate.topic}</h3>
          </div>

          <AgentPanel agents={debate.agents} />
          <StrategyIndicator agents={debate.agents} rounds={debate.rounds} />

          {/* View Switcher */}
          <div className="view-tabs">
            {[
              { id: 'timeline', label: 'Chronologie' },
              { id: 'tree', label: 'Arbre' },
              { id: 'scores', label: 'Scores' },
            ].map(tab => (
              <button
                key={tab.id}
                className={`view-tab ${view === tab.id ? 'active' : ''}`}
                onClick={() => setView(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="arena-view">
            {view === 'timeline' && (
              <DebateTimeline rounds={debate.rounds} agents={debate.agents} />
            )}
            {view === 'tree' && (
              <ArgumentTree rounds={debate.rounds} attackGraph={debate.attackGraph} />
            )}
            {view === 'scores' && (
              <ScoreBoard rounds={debate.rounds} agents={debate.agents} />
            )}
          </div>

          {/* Raw results if available */}
          {debate.rawResults && (
            <div className="arena-raw">
              <h4>Resultats bruts</h4>
              <pre>{JSON.stringify(debate.rawResults, null, 2)}</pre>
            </div>
          )}
        </>
      )}

      {!debate && (
        <div className="arena-empty">
          <p>Chargez la demo ou lancez une analyse pour visualiser un debat.</p>
        </div>
      )}
    </div>
  );
}
