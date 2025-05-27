/**
 * Utilitaires de validation pour l'interface d'argumentation
 * 
 * Ce module contient des fonctions pour valider les données
 * avant envoi à l'API et pour vérifier la cohérence des inputs.
 */

/**
 * Valide un texte d'argument
 * @param {string} text - Texte à valider
 * @param {Object} options - Options de validation
 * @returns {Object} Résultat de validation avec erreurs éventuelles
 */
export const validateArgumentText = (text, options = {}) => {
  const {
    minLength = 10,
    maxLength = 5000,
    allowEmpty = false,
    requireSentences = true
  } = options;

  const errors = [];
  const warnings = [];

  // Vérification de base
  if (!text || typeof text !== 'string') {
    if (!allowEmpty) {
      errors.push('Le texte est requis');
    }
    return { isValid: allowEmpty, errors, warnings };
  }

  const trimmedText = text.trim();

  // Vérification de la longueur
  if (trimmedText.length < minLength) {
    errors.push(`Le texte doit contenir au moins ${minLength} caractères`);
  }

  if (trimmedText.length > maxLength) {
    errors.push(`Le texte ne peut pas dépasser ${maxLength} caractères`);
  }

  // Vérification de la structure
  if (requireSentences && trimmedText.length > 0) {
    const sentences = trimmedText.split(/[.!?]+/).filter(s => s.trim().length > 0);
    if (sentences.length === 0) {
      warnings.push('Le texte ne semble pas contenir de phrases complètes');
    }
  }

  // Vérification de caractères suspects
  const suspiciousPatterns = [
    { pattern: /(.)\1{10,}/, message: 'Répétition excessive de caractères détectée' },
    { pattern: /^\s*$/, message: 'Le texte ne contient que des espaces' },
    { pattern: /[^\w\s\p{P}\p{S}]/u, message: 'Caractères non standard détectés' }
  ];

  suspiciousPatterns.forEach(({ pattern, message }) => {
    if (pattern.test(trimmedText)) {
      warnings.push(message);
    }
  });

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    stats: {
      length: trimmedText.length,
      words: trimmedText.split(/\s+/).length,
      sentences: trimmedText.split(/[.!?]+/).filter(s => s.trim()).length
    }
  };
};

/**
 * Valide une liste de prémisses pour la validation d'arguments
 * @param {Array} premises - Liste des prémisses
 * @param {Object} options - Options de validation
 * @returns {Object} Résultat de validation
 */
export const validatePremises = (premises, options = {}) => {
  const {
    minPremises = 1,
    maxPremises = 10,
    minPremiseLength = 5,
    maxPremiseLength = 500
  } = options;

  const errors = [];
  const warnings = [];

  // Vérification de base
  if (!Array.isArray(premises)) {
    errors.push('Les prémisses doivent être fournies sous forme de liste');
    return { isValid: false, errors, warnings };
  }

  // Vérification du nombre de prémisses
  if (premises.length < minPremises) {
    errors.push(`Au moins ${minPremises} prémisse${minPremises > 1 ? 's' : ''} est requise`);
  }

  if (premises.length > maxPremises) {
    errors.push(`Maximum ${maxPremises} prémisses autorisées`);
  }

  // Validation de chaque prémisse
  premises.forEach((premise, index) => {
    const premiseValidation = validateArgumentText(premise, {
      minLength: minPremiseLength,
      maxLength: maxPremiseLength,
      allowEmpty: false
    });

    if (!premiseValidation.isValid) {
      errors.push(`Prémisse ${index + 1}: ${premiseValidation.errors.join(', ')}`);
    }

    premiseValidation.warnings.forEach(warning => {
      warnings.push(`Prémisse ${index + 1}: ${warning}`);
    });
  });

  // Vérification de la redondance
  const uniquePremises = new Set(premises.map(p => p.trim().toLowerCase()));
  if (uniquePremises.size < premises.length) {
    warnings.push('Certaines prémisses semblent redondantes');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    stats: {
      count: premises.length,
      totalLength: premises.join(' ').length,
      averageLength: premises.length > 0 ? Math.round(premises.join(' ').length / premises.length) : 0
    }
  };
};

/**
 * Valide une conclusion d'argument
 * @param {string} conclusion - Conclusion à valider
 * @param {Array} premises - Prémisses associées pour vérification de cohérence
 * @returns {Object} Résultat de validation
 */
export const validateConclusion = (conclusion, premises = []) => {
  const errors = [];
  const warnings = [];

  // Validation de base du texte
  const textValidation = validateArgumentText(conclusion, {
    minLength: 5,
    maxLength: 1000,
    allowEmpty: false,
    requireSentences: true
  });

  if (!textValidation.isValid) {
    errors.push(...textValidation.errors);
  }
  warnings.push(...textValidation.warnings);

  // Vérification de la cohérence avec les prémisses
  if (premises.length > 0 && conclusion) {
    const conclusionWords = new Set(
      conclusion.toLowerCase().split(/\s+/).filter(word => word.length > 3)
    );
    
    const premiseWords = new Set(
      premises.join(' ').toLowerCase().split(/\s+/).filter(word => word.length > 3)
    );

    const commonWords = [...conclusionWords].filter(word => premiseWords.has(word));
    
    if (commonWords.length === 0) {
      warnings.push('La conclusion ne semble pas liée aux prémisses (aucun mot-clé commun)');
    }
  }

  // Vérification des indicateurs de conclusion
  const conclusionIndicators = [
    'donc', 'par conséquent', 'ainsi', 'c\'est pourquoi', 'en conséquence',
    'il s\'ensuit', 'on peut conclure', 'cela implique', 'de ce fait'
  ];

  const hasIndicator = conclusionIndicators.some(indicator => 
    conclusion.toLowerCase().includes(indicator)
  );

  if (!hasIndicator) {
    warnings.push('La conclusion pourrait bénéficier d\'un connecteur logique explicite');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    stats: textValidation.stats
  };
};

/**
 * Valide les options d'analyse
 * @param {Object} options - Options à valider
 * @returns {Object} Résultat de validation
 */
export const validateAnalysisOptions = (options) => {
  const errors = [];
  const warnings = [];

  if (!options || typeof options !== 'object') {
    return { isValid: true, errors, warnings }; // Options optionnelles
  }

  // Validation du seuil de sévérité
  if (options.severity_threshold !== undefined) {
    if (typeof options.severity_threshold !== 'number' || 
        options.severity_threshold < 0 || 
        options.severity_threshold > 1) {
      errors.push('Le seuil de sévérité doit être un nombre entre 0 et 1');
    }
  }

  // Validation des catégories
  if (options.categories !== undefined) {
    if (!Array.isArray(options.categories)) {
      errors.push('Les catégories doivent être fournies sous forme de liste');
    } else {
      const validCategories = ['formal', 'informal', 'emotional'];
      const invalidCategories = options.categories.filter(cat => !validCategories.includes(cat));
      if (invalidCategories.length > 0) {
        warnings.push(`Catégories non reconnues: ${invalidCategories.join(', ')}`);
      }
    }
  }

  // Validation du nombre maximum de sophismes
  if (options.max_fallacies !== undefined) {
    if (!Number.isInteger(options.max_fallacies) || options.max_fallacies < 1 || options.max_fallacies > 50) {
      errors.push('Le nombre maximum de sophismes doit être un entier entre 1 et 50');
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
};

/**
 * Valide un argument pour un framework de Dung
 * @param {Object} argument - Argument à valider
 * @returns {Object} Résultat de validation
 */
export const validateFrameworkArgument = (argument) => {
  const errors = [];
  const warnings = [];

  // Vérification de la structure
  if (!argument || typeof argument !== 'object') {
    errors.push('L\'argument doit être un objet');
    return { isValid: false, errors, warnings };
  }

  // Validation de l'ID
  if (!argument.id || typeof argument.id !== 'string') {
    errors.push('L\'argument doit avoir un ID valide');
  } else if (!/^[a-zA-Z0-9_-]+$/.test(argument.id)) {
    errors.push('L\'ID ne peut contenir que des lettres, chiffres, tirets et underscores');
  }

  // Validation du contenu
  const contentValidation = validateArgumentText(argument.content, {
    minLength: 5,
    maxLength: 1000,
    allowEmpty: false
  });

  if (!contentValidation.isValid) {
    errors.push(...contentValidation.errors.map(err => `Contenu: ${err}`));
  }
  warnings.push(...contentValidation.warnings.map(warn => `Contenu: ${warn}`));

  // Validation des relations
  if (argument.attacks && !Array.isArray(argument.attacks)) {
    errors.push('Les attaques doivent être une liste d\'IDs');
  }

  if (argument.supports && !Array.isArray(argument.supports)) {
    errors.push('Les supports doivent être une liste d\'IDs');
  }

  // Vérification des auto-références
  if (argument.attacks && argument.attacks.includes(argument.id)) {
    errors.push('Un argument ne peut pas s\'attaquer lui-même');
  }

  if (argument.supports && argument.supports.includes(argument.id)) {
    errors.push('Un argument ne peut pas se supporter lui-même');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
};

/**
 * Valide une liste d'arguments pour un framework
 * @param {Array} arguments - Liste des arguments
 * @returns {Object} Résultat de validation
 */
export const validateFrameworkArguments = (args) => {
  const errors = [];
  const warnings = [];

  if (!Array.isArray(args)) {
    errors.push('Les arguments doivent être fournis sous forme de liste');
    return { isValid: false, errors, warnings };
  }

  if (args.length === 0) {
    errors.push('Au moins un argument est requis');
    return { isValid: false, errors, warnings };
  }

  if (args.length > 20) {
    warnings.push('Un grand nombre d\'arguments peut affecter les performances');
  }

  // Validation de chaque argument
  const ids = new Set();
  args.forEach((arg, index) => {
    const argValidation = validateFrameworkArgument(arg);
    
    if (!argValidation.isValid) {
      errors.push(`Argument ${index + 1}: ${argValidation.errors.join(', ')}`);
    }
    
    argValidation.warnings.forEach(warning => {
      warnings.push(`Argument ${index + 1}: ${warning}`);
    });

    // Vérification des IDs uniques
    if (arg.id) {
      if (ids.has(arg.id)) {
        errors.push(`ID dupliqué: ${arg.id}`);
      } else {
        ids.add(arg.id);
      }
    }
  });

  // Validation des références croisées
  args.forEach(arg => {
    if (arg.attacks) {
      arg.attacks.forEach(targetId => {
        if (!ids.has(targetId)) {
          errors.push(`Référence d'attaque invalide: ${arg.id} -> ${targetId}`);
        }
      });
    }

    if (arg.supports) {
      arg.supports.forEach(targetId => {
        if (!ids.has(targetId)) {
          errors.push(`Référence de support invalide: ${arg.id} -> ${targetId}`);
        }
      });
    }
  });

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    stats: {
      count: args.length,
      totalAttacks: args.reduce((sum, arg) => sum + (arg.attacks ? arg.attacks.length : 0), 0),
      totalSupports: args.reduce((sum, arg) => sum + (arg.supports ? arg.supports.length : 0), 0)
    }
  };
};

/**
 * Valide les options d'un framework
 * @param {Object} options - Options à valider
 * @returns {Object} Résultat de validation
 */
export const validateFrameworkOptions = (options) => {
  const errors = [];
  const warnings = [];

  if (!options || typeof options !== 'object') {
    return { isValid: true, errors, warnings }; // Options optionnelles
  }

  // Validation de la sémantique
  if (options.semantics) {
    const validSemantics = ['grounded', 'complete', 'preferred', 'stable', 'semi-stable'];
    if (!validSemantics.includes(options.semantics)) {
      errors.push(`Sémantique non supportée: ${options.semantics}`);
    }
  }

  // Validation des booléens
  if (options.compute_extensions !== undefined && typeof options.compute_extensions !== 'boolean') {
    errors.push('compute_extensions doit être un booléen');
  }

  if (options.include_visualization !== undefined && typeof options.include_visualization !== 'boolean') {
    errors.push('include_visualization doit être un booléen');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
};

/**
 * Valide une URL d'API
 * @param {string} url - URL à valider
 * @returns {Object} Résultat de validation
 */
export const validateApiUrl = (url) => {
  const errors = [];
  const warnings = [];

  if (!url || typeof url !== 'string') {
    errors.push('L\'URL est requise');
    return { isValid: false, errors, warnings };
  }

  try {
    const urlObj = new URL(url);
    
    // Vérification du protocole
    if (!['http:', 'https:'].includes(urlObj.protocol)) {
      errors.push('L\'URL doit utiliser le protocole HTTP ou HTTPS');
    }

    // Avertissement pour HTTP en production
    if (urlObj.protocol === 'http:' && !['localhost', '127.0.0.1'].includes(urlObj.hostname)) {
      warnings.push('L\'utilisation de HTTP n\'est pas recommandée en production');
    }

    // Vérification du port
    if (urlObj.port && (parseInt(urlObj.port) < 1 || parseInt(urlObj.port) > 65535)) {
      errors.push('Le port doit être entre 1 et 65535');
    }

  } catch (error) {
    errors.push('Format d\'URL invalide');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
};

/**
 * Fonction utilitaire pour valider plusieurs champs en une fois
 * @param {Object} validations - Objet contenant les validations à effectuer
 * @returns {Object} Résultat global de validation
 */
export const validateMultiple = (validations) => {
  const allErrors = [];
  const allWarnings = [];
  let isValid = true;

  Object.entries(validations).forEach(([field, validation]) => {
    if (validation && typeof validation === 'object') {
      if (!validation.isValid) {
        isValid = false;
      }
      
      if (validation.errors) {
        validation.errors.forEach(error => {
          allErrors.push(`${field}: ${error}`);
        });
      }
      
      if (validation.warnings) {
        validation.warnings.forEach(warning => {
          allWarnings.push(`${field}: ${warning}`);
        });
      }
    }
  });

  return {
    isValid,
    errors: allErrors,
    warnings: allWarnings
  };
};

// Export par défaut d'un objet contenant toutes les fonctions
export default {
  validateArgumentText,
  validatePremises,
  validateConclusion,
  validateAnalysisOptions,
  validateFrameworkArgument,
  validateFrameworkArguments,
  validateFrameworkOptions,
  validateApiUrl,
  validateMultiple
};