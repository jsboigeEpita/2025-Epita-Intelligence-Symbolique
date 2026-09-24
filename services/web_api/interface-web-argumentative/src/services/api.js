// En mode de développement et de test E2E, l'URL du backend est fournie par une variable d'environnement.
// Cela permet au frontend (servi par le serveur de développement React) de communiquer avec le backend Python
// qui tourne sur un port différent. En production, cette variable peut être absente,
// et les requêtes utiliseront des chemins relatifs car le frontend est servi par le même serveur que l'API.
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || '';

// Configuration par défaut pour les requêtes
const defaultHeaders = {
  'Content-Type': 'application/json',
};

// Fonction utilitaire pour gérer les erreurs HTTP
const handleResponse = async (response) => {
  const json = await response.json();
  if (!response.ok) {
    // The API's error envelope (api/errors.py) carries its reason in `detail`;
    // a 422 carries a list there, hence the type check.
    const detail = typeof json.detail === 'string' ? json.detail : null;
    const errorMessage = json.message || json.error || detail || `Erreur API: ${response.status}`;
    throw new Error(errorMessage);
  }
  // Si la réponse est une enveloppe standard (contient un champ 'data'), on extrait les données.
  // Sinon, on retourne l'objet JSON complet.
  if (json.data !== undefined) {
    return json.data;
  }
  return json;
};

// Les appels au détecteur de sophismes (#2526) : le tier `llm` a mis 18 s sur
// une phrase et 53 s sur deux paragraphes ; 180 s laisse une marge de 3,4.
const FALLACY_TIMEOUT_MS = 180000;

// Fonction utilitaire pour les requêtes avec timeout
const fetchWithTimeout = (url, options, timeout = 30000) => {
  return Promise.race([
    fetch(url, options),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Timeout de la requête')), timeout)
    )
  ]);
};

// Analyse d'un texte argumentatif : structure (Tweety) et, sur demande, sophismes.
// La route renvoie { analysis_id, status, results } ; les vues lisent `results`.
// `fallacies` n'y figure que si la détection a été demandée (#2526).
export const analyzeText = async (text, options = {}) => {
  const detectFallacies = Boolean(options.detect_fallacies);
  const requestBody = {
    text,
    options: { detect_fallacies: detectFallacies }
  };

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/analyze`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(requestBody)
  }, detectFallacies ? FALLACY_TIMEOUT_MS : undefined);

  const json = await handleResponse(response);
  return {
    ...json.results,
    analysis_id: json.analysis_id,
    processing_time: json.results?.metadata?.duration
  };
};

// Validation d'un argument structuré
export const validateArgument = async (premises, conclusion, argumentType = 'deductive') => {
  const requestBody = {
    premises,
    conclusion,
    argument_type: argumentType
  };

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/validate`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(requestBody)
  });

  return handleResponse(response);
};

// Détection de sophismes : le détecteur de la phase sophismes du pipeline (#2526).
// Options acceptées : `tier` (taxonomy | hybrid | llm | full, `llm` par défaut) et
// `min_confidence` (0-1) ; l'API refuse toute autre clé.
export const detectFallacies = async (text, options = {}) => {
  const requestOptions = {};
  if (options.tier !== undefined) requestOptions.tier = options.tier;
  if (options.min_confidence !== undefined) requestOptions.min_confidence = options.min_confidence;

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/fallacies`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify({ text, options: requestOptions })
  }, FALLACY_TIMEOUT_MS);

  return handleResponse(response);
};

// Analyse de framework de Dung : POST /api/v1/framework/analyze (#2526).
// Ce backend renvoie { analysis: { extensions: { grounded, preferred, ... },
// graph_properties } } ; la vue lit les extensions d'une sémantique en liste de
// listes, et des statistiques. La sémantique grounded est une extension unique.
export const analyzeDungFramework = async (argumentList, attacks = [], semantics = 'preferred') => {
  const requestBody = {
    arguments: argumentList.map(arg => arg.id), // Extrait les IDs : ['a', 'b', ...]
    attacks: attacks, // Les attaques sont déjà au format [['source_id', 'target_id']]
    options: { semantics, compute_extensions: true }
  };

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/framework/analyze`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(requestBody)
  });

  const { analysis } = await handleResponse(response);
  const found = (analysis.extensions || {})[semantics] || [];
  const properties = analysis.graph_properties || {};
  return {
    ...analysis,
    semantics,
    extensions: semantics === 'grounded' ? [found] : found,
    statistics: {
      arguments_count: properties.num_arguments,
      attacks_count: properties.num_attacks
    }
  };
};

// Analyse et visualisation de graphe logique
export const analyzeLogicGraph = async (data) => {
  const { text, options } = data;
  const requestBody = {
    text,
    logic_type: 'propositional', // Ajout du type de logique manquant
    options: options || { layout: 'hierarchical' }
  };

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/logic/belief-set`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(requestBody)
  });

  return handleResponse(response);
};

// Vérification de l'état de l'API
export const checkAPIHealth = async () => {
  const response = await fetchWithTimeout(`${API_BASE_URL}/api/health`, {
    method: 'GET',
    headers: defaultHeaders
  }, 5000); // Timeout plus court pour le health check

  return handleResponse(response);
};

// Récupération de la liste des endpoints disponibles
export const getAPIEndpoints = async () => {
  const response = await fetchWithTimeout(`${API_BASE_URL}/api/endpoints`, {
    method: 'GET',
    headers: defaultHeaders
  });

  return handleResponse(response);
};

// Exemples d'utilisation pour les développeurs
export const getExampleAnalysis = () => {
  return analyzeText(
    "Tous les chats sont des animaux. Félix est un chat. Donc Félix est un animal.",
    { detect_fallacies: true }
  );
};

export const getExampleValidation = () => {
  return validateArgument(
    ["Tous les chats sont des animaux", "Félix est un chat"],
    "Félix est un animal",
    "deductive"
  );
};

export const getExampleFallacyDetection = () => {
  return detectFallacies(
    "Cette théorie sur le climat est fausse parce que son auteur a été condamné pour fraude fiscale."
  );
};

export const getExampleFramework = () => {
  return analyzeDungFramework([
    { id: 'A', text: 'Les voitures polluent' },
    { id: 'B', text: 'Les voitures électriques ne polluent pas' },
    { id: 'C', text: 'L\'électricité peut être produite proprement' }
  ], [
    { from: 'B', to: 'A', type: 'attack' },
    { from: 'C', to: 'B', type: 'attack' } // 'support' n'est pas un type d'attaque valide pour Dung. Corrigé.
  ]);
};

// Fonction de test de connectivité
export const testConnection = async () => {
  try {
    const health = await checkAPIHealth();
    return {
      success: true,
      message: 'Connexion réussie',
      data: health
    };
  } catch (error) {
    return {
      success: false,
      message: error.message,
      data: null
    };
  }
};

// Export par défaut pour faciliter l'import
// const apiService = {
//   analyzeText,
//   validateArgument,
//   detectFallacies,
//   analyzeDungFramework, // Remplacement de buildFramework
//   createBeliefSet,
//   executeLogicQuery,
//   generateLogicQueries,
//   interpretLogicResults,
//   analyzeLogicGraph,
//   checkAPIHealth,
//   getAPIEndpoints,
//   testConnection,
//   examples: {
//     getExampleAnalysis,
//     getExampleValidation,
//     getExampleFallacyDetection,
//     getExampleFramework // Cette fonction devra être adaptée pour utiliser analyzeDungFramework
//   }
// };