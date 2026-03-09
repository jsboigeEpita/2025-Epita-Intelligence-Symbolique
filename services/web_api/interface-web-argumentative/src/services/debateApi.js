/**
 * API client for debate visualization.
 * Connects to the debate-related endpoints and provides mock data for demos.
 */

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || '';

const defaultHeaders = { 'Content-Type': 'application/json' };

const fetchJSON = async (url, options = {}) => {
  const response = await fetch(url, { headers: defaultHeaders, ...options });
  const json = await response.json();
  if (!response.ok) {
    throw new Error(json.detail || `Erreur ${response.status}`);
  }
  return json;
};

// Run a debate analysis via the custom workflow endpoint
export const runDebateAnalysis = (text, workflow = 'debate_tournament') =>
  fetchJSON(`${API_BASE_URL}/api/workflow/custom`, {
    method: 'POST',
    body: JSON.stringify({ text, workflow }),
  });

// Get Dung framework analysis
export const analyzeDungFramework = (args, attacks) =>
  fetchJSON(`${API_BASE_URL}/api/framework`, {
    method: 'POST',
    body: JSON.stringify({ arguments: args, attacks }),
  });

/**
 * Generate demo debate data for visualization when API is unavailable.
 */
export const getDemoDebate = () => ({
  topic: "Faut-il rendre le vote obligatoire en France ?",
  agents: [
    {
      id: 'agent-1',
      name: 'Socrate',
      personality: 'Dialecticien rigoureux',
      strategy: 'Questionnement socratique',
      totalScore: 7.8,
    },
    {
      id: 'agent-2',
      name: 'Aristote',
      personality: 'Pragmatique empirique',
      strategy: 'Argumentation par contre-exemple',
      totalScore: 7.2,
    },
  ],
  rounds: [
    {
      round: 1,
      agent: 'agent-1',
      argument: {
        id: 'arg-1',
        text: "Le vote obligatoire renforce la legitimite democratique car il garantit une representation exhaustive de la volonte populaire.",
        type: 'claim',
        score: 8.1,
        metrics: { clarity: 8, coherence: 9, relevance: 8, persuasion: 7, evidence: 8 },
      },
      timestamp: new Date(Date.now() - 300000).toISOString(),
    },
    {
      round: 2,
      agent: 'agent-2',
      argument: {
        id: 'arg-2',
        text: "Forcer le vote viole la liberte individuelle. Un vote contraint n'exprime pas une veritable conviction democratique.",
        type: 'attack',
        target: 'arg-1',
        score: 7.5,
        metrics: { clarity: 8, coherence: 7, relevance: 9, persuasion: 7, evidence: 6 },
      },
      timestamp: new Date(Date.now() - 240000).toISOString(),
    },
    {
      round: 3,
      agent: 'agent-1',
      argument: {
        id: 'arg-3',
        text: "La liberte inclut la responsabilite civique. Les pays avec vote obligatoire (Belgique, Australie) ont des taux de satisfaction democratique plus eleves.",
        type: 'rebuttal',
        target: 'arg-2',
        score: 8.4,
        metrics: { clarity: 9, coherence: 8, relevance: 8, persuasion: 8, evidence: 9 },
      },
      timestamp: new Date(Date.now() - 180000).toISOString(),
    },
    {
      round: 4,
      agent: 'agent-2',
      argument: {
        id: 'arg-4',
        text: "Correlation n'est pas causation. Ces pays different par bien d'autres facteurs institutionnels. Le vote blanc massif en Belgique montre les limites du systeme.",
        type: 'attack',
        target: 'arg-3',
        score: 7.9,
        metrics: { clarity: 7, coherence: 8, relevance: 8, persuasion: 8, evidence: 7 },
      },
      timestamp: new Date(Date.now() - 120000).toISOString(),
    },
  ],
  attackGraph: [
    { from: 'arg-2', to: 'arg-1' },
    { from: 'arg-3', to: 'arg-2' },
    { from: 'arg-4', to: 'arg-3' },
  ],
});
