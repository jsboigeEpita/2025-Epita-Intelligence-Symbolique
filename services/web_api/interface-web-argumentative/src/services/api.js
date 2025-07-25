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
    const errorMessage = json.message || json.error || `Erreur API: ${response.status}`;
    throw new Error(errorMessage);
  }
  // Si la réponse est une enveloppe standard (contient un champ 'data'), on extrait les données.
  // Sinon, on retourne l'objet JSON complet.
  if (json.data !== undefined) {
    return json.data;
  }
  return json;
};

// Fonction utilitaire pour les requêtes avec timeout
const fetchWithTimeout = (url, options, timeout = 30000) => {
  return Promise.race([
    fetch(url, options),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Timeout de la requête')), timeout)
    )
  ]);
};

// Analyse complète d'un texte argumentatif
export const analyzeText = async (text, options = {}) => {
  const defaultOptions = {
    detect_fallacies: true,
    analyze_structure: true,
    evaluate_coherence: true
  };

  const requestBody = {
    text,
    options: { ...defaultOptions, ...options }
  };

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/analyze`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(requestBody)
  });

  return handleResponse(response);
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

// Détection spécialisée de sophismes
export const detectFallacies = async (text, options = {}) => {
  const defaultOptions = {
    severity_threshold: 0.3,
    include_explanations: true,
    fallacy_types: 'all'
  };

  const requestBody = {
    text,
    options: { ...defaultOptions, ...options }
  };

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/fallacies`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(requestBody)
  });

  return handleResponse(response);
};

// Analyse de framework de Dung via le nouveau backend centralisé
export const analyzeDungFramework = async (argumentList, attacks = []) => {
  // Les données sont directement Pydantic-compatibles depuis le frontend
  const requestBody = {
    arguments: argumentList.map(arg => arg.id), // Extrait les IDs : ['a', 'b', ...]
    attacks: attacks // Les attaques sont déjà au format [['source_id', 'target_id']]
  };

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/v1/framework/analyze`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(requestBody)
  });

  return handleResponse(response);
};

// Requêtes logiques avancées
export const createBeliefSet = async (beliefs) => {
  const requestBody = { beliefs };

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/logic/belief-set`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(requestBody)
  });

  return handleResponse(response);
};

export const executeLogicQuery = async (beliefSet, query) => {
  const requestBody = {
    belief_set: beliefSet,
    query
  };

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/logic/query`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(requestBody)
  });

  return handleResponse(response);
};

export const generateLogicQueries = async (beliefSet, count = 5) => {
  const requestBody = {
    belief_set: beliefSet,
    count
  };

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/logic/generate-queries`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(requestBody)
  });

  return handleResponse(response);
};

export const interpretLogicResults = async (results, context = '') => {
  const requestBody = {
    results,
    context
  };

  const response = await fetchWithTimeout(`${API_BASE_URL}/api/logic/interpret`, {
    method: 'POST',
    headers: defaultHeaders,
    body: JSON.stringify(requestBody)
  });

  return handleResponse(response);
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
    {
      detect_fallacies: true,
      analyze_structure: true,
      evaluate_coherence: true
    }
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