# Guide de Contribution

Merci de contribuer au projet **2025-Epita-Intelligence-Symbolique** ! 🎉

Ce guide vous aidera à configurer votre environnement de développement et à comprendre notre workflow de tests, particulièrement pour les tests nécessitant des clés API externes.

---

## 📋 Table des Matières

1. [Configuration de l'Environnement](#configuration-de-lenvironnement)
2. [Tests Nécessitant des API Keys](#tests-nécessitant-des-api-keys)
3. [Markers Pytest Disponibles](#markers-pytest-disponibles)
4. [Exécution Locale avec API Keys](#exécution-locale-avec-api-keys)
5. [Comportement en CI](#comportement-en-ci)
6. [Structure des Tests](#structure-des-tests)
7. [Best Practices](#best-practices)
8. [Ressources Utiles](#ressources-utiles)

---

## Configuration de l'Environnement

### Prérequis

- **Python 3.10+** via Miniconda/Anaconda
- **Java 15+** (pour Tweety/JPype) : `jvm_setup.py` ignore `JAVA_HOME` et télécharge un JDK 17 portable dans `portable_jdk/` s'il n'y en trouve pas
- **Git**

### Installation

```bash
# Cloner le dépôt
git clone https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique.git
cd 2025-Epita-Intelligence-Symbolique

# Créer l'environnement conda
conda env create -f environment.yml

# Activer l'environnement
conda activate projet-is

# Vérifier l'installation
pytest --version
```

---

## Tests Nécessitant des API Keys

Certains tests nécessitent des clés API pour tester des intégrations réelles avec des services externes. Ces tests sont **automatiquement skippés** si les clés ne sont pas configurées.

### Markers Pytest Disponibles

Le projet utilise des **markers pytest personnalisés** pour gérer les dépendances aux API keys :

| Marker | Description | Clé Requise |
|--------|-------------|-------------|
| `@pytest.mark.requires_api` | Test nécessite **au moins une** clé API | `OPENAI_API_KEY` OU `GITHUB_TOKEN` OU `OPENROUTER_API_KEY` |
| `@pytest.mark.requires_openai` | Test nécessite spécifiquement OpenAI | `OPENAI_API_KEY` |
| `@pytest.mark.requires_github` | Test nécessite spécifiquement GitHub | `GITHUB_TOKEN` |
| `@pytest.mark.requires_openrouter` | Test nécessite spécifiquement OpenRouter | `OPENROUTER_API_KEY` |

### Comment Ajouter un Test Nécessitant une API

**Exemple avec OpenAI :**

```python
import pytest

@pytest.mark.requires_openai
def test_openai_integration():
    """Test requiring OpenAI API key."""
    from openai import OpenAI
    
    client = OpenAI()  # Utilise automatiquement OPENAI_API_KEY
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello!"}],
        max_tokens=5
    )
    
    assert response.choices[0].message.content
```

**Exemple avec marker générique :**

```python
import pytest
import os

@pytest.mark.requires_api
def test_any_api_integration():
    """Test requiring at least one API key."""
    # Ce test sera skippé si AUCUNE clé API n'est disponible
    # Vous pouvez adapter le comportement selon les clés présentes
    
    if os.getenv("OPENAI_API_KEY"):
        # Test avec OpenAI
        pass
    elif os.getenv("GITHUB_TOKEN"):
        # Test avec GitHub
        pass
```

**⚠️ Important :**
- **Ne PAS** utiliser `pytest.skip()` manuellement dans le corps du test
- Utiliser les markers pytest pour que le comportement soit cohérent
- Les markers gèrent automatiquement le skip via le `conftest.py`

---

## Exécution Locale avec API Keys

### 1. Configurer les Secrets Localement

Créez un fichier **`.env`** à la racine du projet (ce fichier est dans `.gitignore` et ne sera **jamais commité**) :

```bash
# .env
OPENAI_API_KEY=sk-proj-...
GITHUB_TOKEN=ghp_...
OPENROUTER_API_KEY=sk-or-v1-...
```

💡 **Astuce :** Copiez `.env.example` si disponible :

```bash
cp .env.example .env
# Puis éditez .env avec vos clés
```

### 2. Obtenir des Clés API

| Service | URL | Coût |
|---------|-----|------|
| **OpenAI** | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | Free tier disponible |
| **OpenRouter** | [openrouter.ai/keys](https://openrouter.ai/keys) | Pay-as-you-go |
| **GitHub** | [github.com/settings/tokens](https://github.com/settings/tokens) | Gratuit |

### 3. Exécuter les Tests

```bash
# Activer l'environnement
conda activate projet-is

# Exécuter TOUS les tests (y compris ceux avec API)
pytest tests/

# Exécuter UNIQUEMENT les tests nécessitant OpenAI
pytest tests/ -m requires_openai

# Exécuter en EXCLUANT les tests nécessitant des API
pytest tests/ -m "not requires_api"

# Mode verbose avec détails
pytest tests/ -v

# Avec rapport de couverture
pytest tests/ --cov=. --cov-report=html
```

### 4. Vérifier Quels Tests Seront Skippés

```bash
# Lister tous les tests avec leur statut
pytest --collect-only -q

# Lister uniquement les tests nécessitant des API
pytest --collect-only -m requires_api -q
```

---

## Comportement en CI

### Sur GitHub Actions

Les tests s'exécutent automatiquement sur chaque **push** et **pull request** vers `main`.

**Avec Secrets Configurés (Repository Principal) :**
- ✅ Tests de linting et formatage
- ✅ Tests unitaires
- ✅ Tests d'intégration **avec API réelles**
- 📊 Résumé automatique des tests (passed/failed/skipped)
- 📦 Artefacts uploadés (rapports XML, logs)

**Sans Secrets (Forks) :**
- ✅ Tests de linting et formatage
- ✅ Tests unitaires
- ⏭️ Tests d'intégration **skippés gracieusement**
- ℹ️ Message clair expliquant pourquoi les tests sont skippés

**Exemple de sortie CI :**

```
═══════════════════════════════════════════════
📊 TEST EXECUTION SUMMARY
═══════════════════════════════════════════════
✅ Passed:  142 / 165
❌ Failed:  0 / 165
⏭️  Skipped: 23 / 165

ℹ️  Note: 23 tests were skipped (likely due to missing API keys)
   These tests require OPENAI_API_KEY or other API credentials.
   Configure secrets in GitHub repository settings to run them.
═══════════════════════════════════════════════
```

### Configuration des Secrets GitHub

Pour les **mainteneurs** du repository :

1. Aller dans **Settings** → **Secrets and variables** → **Actions**
2. Ajouter les secrets :
   - `OPENAI_API_KEY` : Clé OpenAI
   - `TEXT_CONFIG_PASSPHRASE` : Passphrase pour données éducatives
   - (Optionnel) `OPENROUTER_API_KEY`

---

## Structure des Tests

```
tests/
├── unit/              # Tests unitaires (PAS de dépendances externes)
│   ├── test_core.py
│   └── test_utils.py
├── integration/       # Tests d'intégration (peuvent nécessiter des API)
│   ├── test_openai_integration.py
│   └── test_github_integration.py
├── performance/       # Tests de performance (souvent avec API)
│   └── test_oracle_performance.py
└── e2e/              # Tests end-to-end (nécessitent souvent des API)
    └── test_full_workflow.py
```

### Conventions de Nommage

- Tests unitaires : `test_<module>_<fonction>.py`
- Tests d'intégration : `test_<service>_integration.py`
- Tests nécessitant API : **TOUJOURS** marquer avec `@pytest.mark.requires_*`

---

## Best Practices

### ✅ DO

1. **Toujours marquer** les tests nécessitant des API avec les markers appropriés
2. **Minimiser** les appels API dans les tests (utiliser des mocks quand possible)
3. **Documenter** les dépendances API dans les docstrings
4. **Tester localement** AVEC et SANS API keys avant de push
5. **Utiliser `.env`** pour les secrets locaux (jamais commit)

### ❌ DON'T

1. **Ne JAMAIS** committer le fichier `.env` ou des clés API
2. **Ne PAS** hardcoder des clés API dans le code
3. **Ne PAS** utiliser `pytest.skip()` manuellement (utiliser les markers)
4. **Ne PAS** faire de longs appels API sans timeout
5. **Ne PAS** assumer que les API keys sont toujours disponibles

### Exemple de Test Bien Structuré

```python
import pytest
import os
from openai import OpenAI

@pytest.mark.requires_openai
@pytest.mark.integration
def test_openai_chat_completion():
    """
    Test d'intégration avec l'API OpenAI GPT-4o-mini.
    
    Prérequis :
    - OPENAI_API_KEY configurée dans .env
    - Crédit disponible sur le compte OpenAI
    
    Ce test vérifie que :
    - La connexion à OpenAI fonctionne
    - Le modèle gpt-4o-mini répond correctement
    - La réponse est non-vide
    """
    client = OpenAI()  # Utilise OPENAI_API_KEY de l'environnement
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say 'test'"}],
        max_tokens=5,
        timeout=10  # Toujours définir un timeout !
    )
    
    assert response.choices[0].message.content.strip().lower() == "test"
```

---

## Ressources Utiles

### Documentation

- **Architecture CI/CD** : [`docs/architecture/ci_secrets_strategy.md`](docs/architecture/ci_secrets_strategy.md)
- **Configuration Pytest** : [`pytest.ini`](pytest.ini)
- **Workflow CI** : [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
- **README Principal** : [`README.md`](README.md)

### Markers Pytest

Voir tous les markers disponibles :

```bash
pytest --markers
```

### Aide Pytest

```bash
pytest --help                    # Aide générale
pytest --collect-only -q         # Lister tous les tests
pytest -k "test_name" -v         # Exécuter un test spécifique
pytest --lf                      # Relancer seulement les tests échoués
pytest --sw                      # Arrêter au premier échec
```

---

## Questions ?

- **Issues** : [github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique/issues](https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique/issues)
- **Discussions** : [github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique/discussions](https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique/discussions)
- **Email** : Jean-Sebastien.Boige@epita.fr

---

## Remerciements

Merci de contribuer à ce projet ! Votre aide est précieuse. 🙏

Si vous avez des suggestions pour améliorer ce guide, n'hésitez pas à ouvrir une issue ou une pull request.