# Rapport sur les données de test préparées

## Introduction

Ce rapport présente l'ensemble des données de test préparées pour le projet d'analyse d'argumentation. Ces données ont été conçues pour couvrir tous les scénarios de test définis dans la spécification, en s'assurant qu'elles sont réalistes, représentatives et facilement accessibles pour les tests automatisés.

## Structure des données de test

Les données de test sont organisées selon la structure suivante:

```
tests/test_data/
├── README.md                           # Documentation générale
├── conftest.py                         # Fixtures pytest pour accéder aux données
├── extract_definitions/                # Fichiers de définitions d'extraits
│   ├── valid/                          # Définitions valides
│   ├── partial/                        # Définitions partiellement valides
│   └── invalid/                        # Définitions invalides
├── source_texts/                       # Textes sources pour les tests
│   ├── with_markers/                   # Textes avec marqueurs valides
│   ├── partial_markers/                # Textes avec marqueurs partiellement présents
│   └── no_markers/                     # Textes sans marqueurs
├── service_configs/                    # Configurations pour les services
│   ├── llm/                            # Configurations pour le service LLM
│   ├── cache/                          # Configurations pour le service de cache
│   └── crypto/                         # Configurations pour le service de cryptographie
└── error_cases/                        # Données pour simuler les cas d'erreur
```

## Détail des données préparées

### 1. Fichiers de définitions d'extraits

#### 1.1 Définitions valides
- **Fichier**: `extract_definitions/valid/valid_extract_definitions.json`
- **Contenu**: 3 sources avec un total de 8 extraits correctement définis
- **Cas couverts**: 
  - Extraits simples avec marqueurs de début et de fin
  - Extraits avec templates pour les marqueurs de début
  - Différents types de sources (discours, articles scientifiques)

#### 1.2 Définitions partiellement valides
- **Fichier**: `extract_definitions/partial/partial_extract_definitions.json`
- **Contenu**: 3 sources avec des extraits partiellement valides
- **Cas couverts**:
  - Extraits avec marqueur de fin manquant
  - Extraits avec marqueur de début manquant
  - Extraits avec template mais sans première lettre dans le marqueur

#### 1.3 Définitions invalides
- **Fichier**: `extract_definitions/invalid/invalid_extract_definitions.json`
- **Contenu**: 4 sources avec différents types d'erreurs
- **Cas couverts**:
  - Types de données incorrects (nombre au lieu de chaîne)
  - Champs obligatoires manquants
  - Structure JSON incorrecte (objet au lieu de tableau)

### 2. Textes sources

#### 2.1 Textes avec marqueurs valides
- **Fichiers**: 
  - `source_texts/with_markers/discours_politique.txt`
  - `source_texts/with_markers/discours_avec_template.txt`
- **Contenu**: Textes complets contenant tous les marqueurs définis
- **Cas couverts**:
  - Marqueurs simples (début et fin)
  - Marqueurs avec template (nécessitant une première lettre)

#### 2.2 Textes avec marqueurs partiellement présents
- **Fichier**: `source_texts/partial_markers/article_scientifique.txt`
- **Contenu**: Texte d'article scientifique avec certains marqueurs manquants ou incomplets
- **Cas couverts**:
  - Marqueurs de début présents mais pas de fin
  - Marqueurs partiellement présents (sans première lettre)

#### 2.3 Textes sans marqueurs
- **Fichier**: `source_texts/no_markers/texte_sans_marqueurs.txt`
- **Contenu**: Texte sur la pensée critique sans aucun marqueur
- **Cas couverts**:
  - Texte source valide mais sans marqueurs d'extraction

### 3. Configurations pour les services

#### 3.1 Configuration LLM
- **Fichier**: `service_configs/llm/llm_config.json`
- **Contenu**: Configuration complète pour le service LLM
- **Cas couverts**:
  - Configuration normale avec tous les paramètres
  - Modèles de fallback
  - Options de logging et de cache

#### 3.2 Configuration Cache
- **Fichier**: `service_configs/cache/cache_config.json`
- **Contenu**: Configuration pour le service de cache
- **Cas couverts**:
  - Options de taille et durée de vie du cache
  - Compression
  - Validation et réparation du cache

#### 3.3 Configuration Crypto
- **Fichier**: `service_configs/crypto/crypto_config.json`
- **Contenu**: Configuration pour le service de cryptographie
- **Cas couverts**:
  - Paramètres de chiffrement
  - Gestion des clés
  - Options de sécurité

### 4. Cas d'erreur

#### 4.1 Erreurs réseau
- **Fichier**: `error_cases/network_error.json`
- **Contenu**: Scénarios d'erreurs réseau
- **Cas couverts**:
  - Timeout de connexion
  - Échec de résolution DNS
  - Erreurs SSL
  - Connexion réinitialisée

#### 4.2 Erreurs de service
- **Fichier**: `error_cases/service_error.json`
- **Contenu**: Scénarios d'erreurs de service
- **Cas couverts**:
  - Limite de débit dépassée (LLM)
  - Clé API invalide
  - Erreurs de permission
  - Fichiers non trouvés

#### 4.3 Erreurs de validation
- **Fichier**: `error_cases/validation_error.json`
- **Contenu**: Scénarios d'erreurs de validation
- **Cas couverts**:
  - Champs obligatoires manquants
  - Types de données invalides
  - URL invalides
  - Noms d'extraits dupliqués

## Accès aux données via les fixtures pytest

Un fichier `conftest.py` a été créé dans le répertoire `test_data` pour faciliter l'accès aux données de test via des fixtures pytest. Ces fixtures peuvent être importées dans les tests unitaires et d'intégration.

Exemples d'utilisation:

```python
def test_valid_extract_definitions(valid_extract_definitions):
    # Utiliser les définitions d'extraits valides
    assert len(valid_extract_definitions) > 0

def test_extract_with_template(discours_avec_template_text, extract_with_template_missing_first_letter):
    # Tester la réparation d'un extrait avec template manquant la première lettre
    # ...
```

## Couverture des cas de test

Les données préparées couvrent l'ensemble des cas de test définis dans la spécification:

1. **Cas normaux**:
   - Extraits valides avec marqueurs présents
   - Configuration standard des services

2. **Cas limites**:
   - Extraits partiellement valides
   - Marqueurs partiellement présents
   - Templates avec première lettre manquante

3. **Cas d'erreur**:
   - Définitions d'extraits invalides
   - Erreurs réseau
   - Erreurs de service
   - Erreurs de validation

## Conclusion

Les données de test préparées fournissent une base solide pour tester l'ensemble des fonctionnalités du projet d'analyse d'argumentation. Elles sont organisées de manière logique, documentées et facilement accessibles via des fixtures pytest.

Ces données permettront de s'assurer que le code fonctionne correctement dans tous les scénarios, y compris les cas limites et les cas d'erreur, contribuant ainsi à la robustesse et à la fiabilité du projet.