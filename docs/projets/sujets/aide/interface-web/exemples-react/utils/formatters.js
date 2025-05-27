/**
 * Utilitaires de formatage pour l'interface d'argumentation
 * 
 * Ce module contient des fonctions pour formater et présenter
 * les données de l'API d'argumentation de manière lisible.
 */

/**
 * Formate un score de confiance ou de sévérité en pourcentage
 * @param {number} score - Score entre 0 et 1
 * @param {number} decimals - Nombre de décimales (défaut: 0)
 * @returns {string} Score formaté avec le symbole %
 */
export const formatScore = (score, decimals = 0) => {
  if (typeof score !== 'number' || isNaN(score)) {
    return 'N/A';
  }
  
  const percentage = Math.round(score * 100 * Math.pow(10, decimals)) / Math.pow(10, decimals);
  return `${percentage}%`;
};

/**
 * Formate un temps de traitement en millisecondes
 * @param {number} timeInSeconds - Temps en secondes
 * @returns {string} Temps formaté avec l'unité appropriée
 */
export const formatProcessingTime = (timeInSeconds) => {
  if (typeof timeInSeconds !== 'number' || isNaN(timeInSeconds)) {
    return 'N/A';
  }
  
  const ms = timeInSeconds * 1000;
  
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  } else if (ms < 60000) {
    return `${(ms / 1000).toFixed(1)}s`;
  } else {
    const minutes = Math.floor(ms / 60000);
    const seconds = ((ms % 60000) / 1000).toFixed(1);
    return `${minutes}m ${seconds}s`;
  }
};

/**
 * Formate le niveau de sévérité d'un sophisme
 * @param {number} severity - Niveau de sévérité (0-1)
 * @returns {object} Objet avec le niveau et la couleur
 */
export const formatSeverityLevel = (severity) => {
  if (typeof severity !== 'number' || isNaN(severity)) {
    return { level: 'unknown', color: '#6c757d', label: 'Inconnu' };
  }
  
  if (severity >= 0.7) {
    return { level: 'high', color: '#dc3545', label: 'Élevée' };
  } else if (severity >= 0.4) {
    return { level: 'medium', color: '#ffc107', label: 'Modérée' };
  } else {
    return { level: 'low', color: '#28a745', label: 'Faible' };
  }
};

/**
 * Formate le statut d'un argument dans un framework
 * @param {string} status - Statut de l'argument
 * @returns {object} Objet avec le statut formaté et la couleur
 */
export const formatArgumentStatus = (status) => {
  const statusMap = {
    'accepted': { label: 'Accepté', color: '#28a745', icon: '✓' },
    'rejected': { label: 'Rejeté', color: '#dc3545', icon: '✗' },
    'undecided': { label: 'Indécis', color: '#ffc107', icon: '?' },
    'unknown': { label: 'Inconnu', color: '#6c757d', icon: '•' }
  };
  
  return statusMap[status] || statusMap['unknown'];
};

/**
 * Formate le type de sémantique d'un framework
 * @param {string} semantics - Type de sémantique
 * @returns {object} Objet avec le nom et la description
 */
export const formatSemantics = (semantics) => {
  const semanticsMap = {
    'grounded': {
      name: 'Grounded',
      description: 'Extension unique et minimale',
      color: '#007bff'
    },
    'complete': {
      name: 'Complete',
      description: 'Extensions complètes',
      color: '#28a745'
    },
    'preferred': {
      name: 'Preferred',
      description: 'Extensions préférées maximales',
      color: '#ffc107'
    },
    'stable': {
      name: 'Stable',
      description: 'Extensions stables',
      color: '#dc3545'
    },
    'semi-stable': {
      name: 'Semi-stable',
      description: 'Extensions semi-stables',
      color: '#6f42c1'
    }
  };
  
  return semanticsMap[semantics] || {
    name: semantics || 'Inconnu',
    description: 'Sémantique non reconnue',
    color: '#6c757d'
  };
};

/**
 * Formate une liste d'arguments pour l'affichage
 * @param {Array} arguments - Liste des arguments
 * @param {number} maxLength - Longueur maximale du texte (défaut: 100)
 * @returns {Array} Arguments formatés
 */
export const formatArgumentsList = (args, maxLength = 100) => {
  if (!Array.isArray(args)) {
    return [];
  }
  
  return args.map(arg => ({
    ...arg,
    shortContent: arg.content && arg.content.length > maxLength
      ? `${arg.content.substring(0, maxLength)}...`
      : arg.content,
    wordCount: arg.content ? arg.content.split(/\s+/).length : 0,
    charCount: arg.content ? arg.content.length : 0
  }));
};

/**
 * Formate les relations d'un framework pour l'affichage
 * @param {Array} relations - Liste des relations
 * @param {Array} arguments - Liste des arguments pour résolution des noms
 * @returns {Array} Relations formatées
 */
export const formatRelations = (relations, args = []) => {
  if (!Array.isArray(relations)) {
    return [];
  }
  
  const argMap = new Map(args.map(arg => [arg.id, arg]));
  
  return relations.map(relation => {
    const sourceArg = argMap.get(relation.attacker || relation.supporter);
    const targetArg = argMap.get(relation.target);
    
    return {
      ...relation,
      sourceName: sourceArg ? sourceArg.content.substring(0, 30) + '...' : relation.attacker || relation.supporter,
      targetName: targetArg ? targetArg.content.substring(0, 30) + '...' : relation.target,
      relationLabel: relation.type === 'attack' ? 'attaque' : 'supporte'
    };
  });
};

/**
 * Formate les statistiques de distribution
 * @param {Object} distribution - Objet de distribution
 * @param {number} total - Total pour calculer les pourcentages
 * @returns {Array} Distribution formatée avec pourcentages
 */
export const formatDistribution = (distribution, total) => {
  if (!distribution || typeof distribution !== 'object' || !total) {
    return [];
  }
  
  return Object.entries(distribution).map(([key, value]) => ({
    category: key,
    count: value,
    percentage: total > 0 ? Math.round((value / total) * 100) : 0,
    label: key.charAt(0).toUpperCase() + key.slice(1)
  }));
};

/**
 * Formate un texte pour l'affichage avec mise en évidence
 * @param {string} text - Texte à formater
 * @param {Object} location - Position de mise en évidence
 * @returns {Object} Texte formaté avec parties avant, mise en évidence et après
 */
export const formatTextWithHighlight = (text, location) => {
  if (!text || !location || typeof location.start !== 'number' || typeof location.end !== 'number') {
    return {
      before: text || '',
      highlight: '',
      after: ''
    };
  }
  
  const start = Math.max(0, location.start);
  const end = Math.min(text.length, location.end);
  
  return {
    before: text.substring(0, start),
    highlight: text.substring(start, end),
    after: text.substring(end)
  };
};

/**
 * Formate les erreurs de validation pour l'affichage
 * @param {Array} errors - Liste des erreurs
 * @returns {Array} Erreurs formatées avec icônes et couleurs
 */
export const formatValidationErrors = (errors) => {
  if (!Array.isArray(errors)) {
    return [];
  }
  
  return errors.map((error, index) => ({
    id: index,
    message: error,
    type: 'error',
    icon: '⚠️',
    color: '#dc3545'
  }));
};

/**
 * Formate les suggestions d'amélioration
 * @param {Array} suggestions - Liste des suggestions
 * @returns {Array} Suggestions formatées avec icônes
 */
export const formatSuggestions = (suggestions) => {
  if (!Array.isArray(suggestions)) {
    return [];
  }
  
  return suggestions.map((suggestion, index) => ({
    id: index,
    message: suggestion,
    type: 'suggestion',
    icon: '💡',
    color: '#007bff'
  }));
};

/**
 * Formate un nombre avec séparateurs de milliers
 * @param {number} number - Nombre à formater
 * @returns {string} Nombre formaté
 */
export const formatNumber = (number) => {
  if (typeof number !== 'number' || isNaN(number)) {
    return '0';
  }
  
  return number.toLocaleString('fr-FR');
};

/**
 * Formate une date/heure pour l'affichage
 * @param {Date|string|number} date - Date à formater
 * @returns {string} Date formatée
 */
export const formatDateTime = (date) => {
  try {
    const dateObj = new Date(date);
    if (isNaN(dateObj.getTime())) {
      return 'Date invalide';
    }
    
    return dateObj.toLocaleString('fr-FR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch (error) {
    return 'Date invalide';
  }
};

/**
 * Formate la taille d'un texte de manière lisible
 * @param {string} text - Texte à analyser
 * @returns {Object} Statistiques formatées du texte
 */
export const formatTextStats = (text) => {
  if (typeof text !== 'string') {
    return {
      characters: 0,
      words: 0,
      sentences: 0,
      paragraphs: 0
    };
  }
  
  const characters = text.length;
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  const sentences = text.trim() ? text.split(/[.!?]+/).filter(s => s.trim()).length : 0;
  const paragraphs = text.trim() ? text.split(/\n\s*\n/).filter(p => p.trim()).length : 0;
  
  return {
    characters: formatNumber(characters),
    words: formatNumber(words),
    sentences: formatNumber(sentences),
    paragraphs: formatNumber(paragraphs)
  };
};

/**
 * Crée un résumé formaté des résultats d'analyse
 * @param {Object} results - Résultats de l'analyse
 * @returns {Object} Résumé formaté
 */
export const formatAnalysisSummary = (results) => {
  if (!results || typeof results !== 'object') {
    return {
      status: 'Aucun résultat',
      quality: 'N/A',
      issues: 0,
      recommendations: []
    };
  }
  
  const quality = results.overall_quality || 0;
  const fallacyCount = results.fallacy_count || 0;
  
  let status = 'Excellent';
  let statusColor = '#28a745';
  
  if (quality < 0.3 || fallacyCount > 5) {
    status = 'Problématique';
    statusColor = '#dc3545';
  } else if (quality < 0.6 || fallacyCount > 2) {
    status = 'À améliorer';
    statusColor = '#ffc107';
  } else if (quality < 0.8 || fallacyCount > 0) {
    status = 'Correct';
    statusColor = '#007bff';
  }
  
  const recommendations = [];
  
  if (fallacyCount > 0) {
    recommendations.push(`Corriger ${fallacyCount} sophisme${fallacyCount > 1 ? 's' : ''} détecté${fallacyCount > 1 ? 's' : ''}`);
  }
  
  if (quality < 0.6) {
    recommendations.push('Renforcer la structure argumentative');
  }
  
  if (results.coherence_score && results.coherence_score < 0.5) {
    recommendations.push('Améliorer la cohérence logique');
  }
  
  return {
    status,
    statusColor,
    quality: formatScore(quality),
    issues: fallacyCount,
    recommendations
  };
};

// Export par défaut d'un objet contenant toutes les fonctions
export default {
  formatScore,
  formatProcessingTime,
  formatSeverityLevel,
  formatArgumentStatus,
  formatSemantics,
  formatArgumentsList,
  formatRelations,
  formatDistribution,
  formatTextWithHighlight,
  formatValidationErrors,
  formatSuggestions,
  formatNumber,
  formatDateTime,
  formatTextStats,
  formatAnalysisSummary
};