import { useState, useCallback } from 'react';

/**
 * Hook personnalisé pour interagir avec l'API d'analyse argumentative
 * 
 * Fonctionnalités :
 * - Gestion automatique du loading
 * - Gestion centralisée des erreurs
 * - Cache simple des résultats
 * - Retry automatique
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export const useArgumentationAPI = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [cache, setCache] = useState(new Map());

  // Fonction générique pour les appels API
  const apiCall = useCallback(async (endpoint, data = null, options = {}) => {
    const {
      method = data ? 'POST' : 'GET',
      useCache = false,
      retries = 1
    } = options;

    // Vérifier le cache
    const cacheKey = `${endpoint}-${JSON.stringify(data)}`;
    if (useCache && cache.has(cacheKey)) {
      return cache.get(cacheKey);
    }

    setLoading(true);
    setError(null);

    let lastError;
    
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const config = {
          method,
          headers: {
            'Content-Type': 'application/json',
          }
        };

        if (data) {
          config.body = JSON.stringify(data);
        }

        const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

        if (!response.ok) {
          throw new Error(`Erreur API: ${response.status} ${response.statusText}`);
        }

        const result = await response.json();

        // Mettre en cache si demandé
        if (useCache) {
          setCache(prev => new Map(prev).set(cacheKey, result));
        }

        return result;

      } catch (err) {
        lastError = err;
        
        // Attendre avant de réessayer (sauf au dernier essai)
        if (attempt < retries) {
          await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
        }
      }
    }

    // Si tous les essais ont échoué
    setError(lastError.message);
    throw lastError;

  }, [cache]);

  // Finaliser les appels
  const finishCall = useCallback(() => {
    setLoading(false);
  }, []);

  // Wrapper pour gérer le loading automatiquement
  const withLoading = useCallback(async (apiFunction) => {
    try {
      const result = await apiFunction();
      return result;
    } finally {
      finishCall();
    }
  }, [finishCall]);

  // Analyse complète de texte
  const analyzeText = useCallback(async (text, options = {}) => {
    return withLoading(() => apiCall('/api/analyze', { text, options }));
  }, [apiCall, withLoading]);

  // Validation d'argument
  const validateArgument = useCallback(async (premises, conclusion, argumentType = 'deductive') => {
    return withLoading(() => apiCall('/api/validate', {
      premises,
      conclusion,
      argument_type: argumentType
    }));
  }, [apiCall, withLoading]);

  // Détection de sophismes
  const detectFallacies = useCallback(async (text, options = {}) => {
    return withLoading(() => apiCall('/api/fallacies', { text, options }));
  }, [apiCall, withLoading]);

  // Construction de framework
  const buildFramework = useCallback(async (args, options = {}) => {
    return withLoading(() => apiCall('/api/framework', { arguments: args, options }));
  }, [apiCall, withLoading]);

  // Vérification de santé de l'API
  const checkHealth = useCallback(async () => {
    return withLoading(() => apiCall('/api/health', null, { useCache: true }));
  }, [apiCall, withLoading]);

  // Liste des endpoints
  const getEndpoints = useCallback(async () => {
    return withLoading(() => apiCall('/api/endpoints', null, { useCache: true }));
  }, [apiCall, withLoading]);

  // Utilitaires
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const clearCache = useCallback(() => {
    setCache(new Map());
  }, []);

  // Test de connectivité
  const testConnection = useCallback(async () => {
    try {
      await checkHealth();
      return true;
    } catch {
      return false;
    }
  }, [checkHealth]);

  return {
    // États
    loading,
    error,
    
    // Méthodes principales
    analyzeText,
    validateArgument,
    detectFallacies,
    buildFramework,
    checkHealth,
    getEndpoints,
    
    // Utilitaires
    clearError,
    clearCache,
    testConnection,
    
    // Méthode générique
    apiCall: (endpoint, data, options) => withLoading(() => apiCall(endpoint, data, options))
  };
};

/**
 * Hook pour la gestion d'état d'une analyse
 */
export const useAnalysisState = () => {
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);

  const addToHistory = useCallback((analysisResult) => {
    setHistory(prev => [
      {
        id: Date.now(),
        text: text,
        result: analysisResult,
        timestamp: new Date().toISOString()
      },
      ...prev.slice(0, 9) // Garder seulement les 10 derniers
    ]);
  }, [text]);

  const clearHistory = useCallback(() => {
    setHistory([]);
  }, []);

  const loadFromHistory = useCallback((historyItem) => {
    setText(historyItem.text);
    setResult(historyItem.result);
  }, []);

  return {
    text,
    setText,
    result,
    setResult,
    history,
    addToHistory,
    clearHistory,
    loadFromHistory
  };
};

/**
 * Hook pour la gestion des options d'analyse
 */
export const useAnalysisOptions = (defaultOptions = {}) => {
  const [options, setOptions] = useState({
    detect_fallacies: true,
    analyze_structure: true,
    evaluate_coherence: true,
    severity_threshold: 0.5,
    include_context: true,
    ...defaultOptions
  });

  const updateOption = useCallback((key, value) => {
    setOptions(prev => ({
      ...prev,
      [key]: value
    }));
  }, []);

  const resetOptions = useCallback(() => {
    setOptions({
      detect_fallacies: true,
      analyze_structure: true,
      evaluate_coherence: true,
      severity_threshold: 0.5,
      include_context: true,
      ...defaultOptions
    });
  }, [defaultOptions]);

  const getPreset = useCallback((presetName) => {
    const presets = {
      quick: {
        detect_fallacies: true,
        analyze_structure: false,
        evaluate_coherence: false,
        severity_threshold: 0.7,
        include_context: false
      },
      complete: {
        detect_fallacies: true,
        analyze_structure: true,
        evaluate_coherence: true,
        severity_threshold: 0.3,
        include_context: true
      },
      fallacies_only: {
        detect_fallacies: true,
        analyze_structure: false,
        evaluate_coherence: false,
        severity_threshold: 0.5,
        include_context: true
      },
      structure_only: {
        detect_fallacies: false,
        analyze_structure: true,
        evaluate_coherence: true,
        severity_threshold: 0.5,
        include_context: false
      }
    };

    return presets[presetName] || options;
  }, [options]);

  const applyPreset = useCallback((presetName) => {
    const preset = getPreset(presetName);
    setOptions(preset);
  }, [getPreset]);

  return {
    options,
    updateOption,
    resetOptions,
    getPreset,
    applyPreset
  };
};

/**
 * Hook pour la gestion des erreurs avec retry
 */
export const useErrorHandler = () => {
  const [errors, setErrors] = useState([]);

  const addError = useCallback((error, context = '') => {
    const errorObj = {
      id: Date.now(),
      message: error.message || error,
      context,
      timestamp: new Date().toISOString(),
      type: getErrorType(error)
    };

    setErrors(prev => [errorObj, ...prev.slice(0, 4)]); // Garder 5 erreurs max
  }, []);

  const clearErrors = useCallback(() => {
    setErrors([]);
  }, []);

  const removeError = useCallback((errorId) => {
    setErrors(prev => prev.filter(err => err.id !== errorId));
  }, []);

  const getErrorType = (error) => {
    const message = error.message || error;
    
    if (message.includes('400')) return 'validation';
    if (message.includes('500')) return 'server';
    if (message.includes('Connection') || message.includes('Network')) return 'network';
    if (message.includes('CORS')) return 'cors';
    
    return 'unknown';
  };

  const getErrorSuggestion = useCallback((errorType) => {
    const suggestions = {
      validation: 'Vérifiez le format de vos données d\'entrée',
      server: 'Problème côté serveur. Réessayez dans quelques instants',
      network: 'Vérifiez que l\'API est démarrée et accessible',
      cors: 'Problème de CORS. Vérifiez la configuration de l\'API',
      unknown: 'Erreur inconnue. Consultez la console pour plus de détails'
    };

    return suggestions[errorType] || suggestions.unknown;
  }, []);

  return {
    errors,
    addError,
    clearErrors,
    removeError,
    getErrorSuggestion
  };
};

export default useArgumentationAPI;