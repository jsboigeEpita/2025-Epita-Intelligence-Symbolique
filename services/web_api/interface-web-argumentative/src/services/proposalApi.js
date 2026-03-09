/**
 * API client for citizen proposals, voting, and deliberation.
 * Connects to the FastAPI endpoints defined in api/proposal_endpoints.py
 */

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || '';

const defaultHeaders = { 'Content-Type': 'application/json' };

const fetchJSON = async (url, options = {}) => {
  const response = await fetch(url, { headers: defaultHeaders, ...options });
  const json = await response.json();
  if (!response.ok) {
    const msg = json.detail || json.message || `Erreur ${response.status}`;
    const err = new Error(msg);
    err.status = response.status;
    throw err;
  }
  return json;
};

// ── Proposals ──

export const submitProposal = (text, author, { title, tags } = {}) =>
  fetchJSON(`${API_BASE_URL}/api/propose`, {
    method: 'POST',
    body: JSON.stringify({ text, author, title, tags }),
  });

export const listProposals = ({ status, limit = 50, offset = 0 } = {}) => {
  const params = new URLSearchParams();
  if (status) params.set('status', status);
  params.set('limit', String(limit));
  params.set('offset', String(offset));
  return fetchJSON(`${API_BASE_URL}/api/proposals?${params}`);
};

export const getProposal = (id) =>
  fetchJSON(`${API_BASE_URL}/api/proposals/${id}`);

// ── Voting ──

export const castVote = (proposalId, voterId, position) =>
  fetchJSON(`${API_BASE_URL}/api/proposals/${proposalId}/vote`, {
    method: 'POST',
    body: JSON.stringify({ voter_id: voterId, position }),
  });

// ── Deliberation ──

export const startDeliberation = (proposalId, workflow = 'democratech', options = {}) =>
  fetchJSON(`${API_BASE_URL}/api/deliberate`, {
    method: 'POST',
    body: JSON.stringify({ proposal_id: proposalId, workflow, options }),
  });

export const getDeliberationStatus = (delibId) =>
  fetchJSON(`${API_BASE_URL}/api/deliberate/${delibId}/status`);

// ── Capabilities ──

export const getCapabilities = () =>
  fetchJSON(`${API_BASE_URL}/api/capabilities`);

// ── Custom Workflow ──

export const runCustomWorkflow = (text, workflow = 'light') =>
  fetchJSON(`${API_BASE_URL}/api/workflow/custom`, {
    method: 'POST',
    body: JSON.stringify({ text, workflow }),
  });
