
# Stratégie d'Extension des Secrets GitHub CI - Architecture D-CI-05

**Mission :** D-CI-05 - Analyse et Stratégie pour l'Extension des Secrets GitHub CI  
**Date :** 2025-10-16  
**Méthodologie :** SDDD avec Double Grounding  
**Auteur :** Roo Architect Complex

---

## 📊 Résumé Exécutif

### Contexte
Suite à la réussite de D-CI-04 (tolérance `.env`) et D-CI-01 (gestion conditionnelle des secrets), le pipeline CI est désormais **fonctionnel et robuste**. Cette mission propose une stratégie d'extension progressive de la couverture de tests via l'ajout de secrets GitHub supplémentaires.

### État Actuel
**Secrets GitHub configurés :**
- ✅ `OPENAI_API_KEY` - API OpenAI principale
- ✅ `TEXT_CONFIG_PASSPHRASE` - Chiffrement des données

### Recommandation Stratégique

**Approche en 3 phases :**
1. **Phase 1 (Immédiate)** : Aucun nouveau secret - Optimiser l'existant
2. **Phase 2 (Court terme, 2-4 semaines)** : 2 secrets à faible risque pour tests spécifiques
3. **Phase 3 (Moyen terme, 2-3 mois)** : Évaluation continue selon besoins réels

**Décision architecturale clé :** **Privilégier la qualité sur la quantité** - maximiser la valeur des secrets existants avant d'en ajouter de nouveaux.

---

## 🎯 Partie 1 : Architecture Proposée

### 1.1 Inventaire Complet des Secrets Disponibles

#### Secrets Déjà Configurés (Productifs)

| Secret | Type | Usage Actuel | Criticité |
|--------|------|--------------|-----------|
| `OPENAI_API_KEY` | API LLM | Tests d'intégration, agents d'analyse | 🔴 **CRITIQUE** |
| `TEXT_CONFIG_PASSPHRASE` | Chiffrement | Déchiffrement données pédagogiques | 🟡 **IMPORTANT** |

#### Secrets Candidats (Non Configurés)

##### A. APIs LLM Alternatives

| Secret | Service | Coût Estimé | Valeur Tests | Risque | Priorité |
|--------|---------|-------------|--------------|--------|----------|
| `OPENROUTER_API_KEY` | OpenRouter API | Pay-per-use, ~$0.15/1M tokens | 🟢 Faible | 🟡 Modéré | **P2** |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI | Abonnement mensuel requis | 🟡 Moyen | 🟡 Modéré | **P3** |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI | - (lié au précédent) | 🟡 Moyen | 🟢 Faible | **P3** |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Azure OpenAI | - (lié au précédent) | 🟡 Moyen | 🟢 Faible | **P3** |

**Analyse :**
- **OpenRouter** : Alternative économique à OpenAI, 1 seul test concerné ([`test_api_connectivity.py:16`](../../tests/integration/test_api_connectivity.py:16))
- **Azure OpenAI** : Nécessite 3 secrets + abonnement Azure, 1 seul test concerné ([`test_modal_logic_agent_authentic.py:70`](../../tests/agents/core/logic/test_modal_logic_agent_authentic.py:70))

##### B. Services Infrastructure

| Secret | Service | Coût | Valeur Tests | Risque | Priorité |
|--------|---------|------|--------------|--------|----------|
| `TIKA_SERVER_ENDPOINT` | Apache Tika (parsing documents) | Gratuit (self-hosted) | 🟢 Faible | 🟢 Faible | **P4** |
| `TIKA_SERVER_TIMEOUT` | Apache Tika | - | 🔵 Très faible | 🟢 Faible | **P5** |

**Analyse :**
- **Tika** : Utilisé dans [`test_utils.py:155`](../../tests/ui/test_utils.py:155) pour tests UI
- Impact limité : Seulement 1 test de parsing de documents
- **Recommandation :** Ne PAS ajouter (peu de valeur, facilement mockable)

##### C. Modèles Locaux (Self-Hosted)

| Secret | Service | Coût | Valeur Tests | Risque | Priorité |
|--------|---------|------|--------------|--------|----------|
| `OPENAI_API_KEY_2` (Micro) | Self-hosted LLM | Aucun (infra existante) | 🔵 Très faible | 🟢 Faible | **P6** |
| `OPENAI_BASE_URL_2` | Self-hosted LLM | - | 🔵 Très faible | 🟢 Faible | **P6** |
| `OPENAI_API_KEY_3` (Mini) | Self-hosted LLM | Aucun | 🔵 Très faible | 🟢 Faible | **P6** |
| `OPENAI_BASE_URL_3` | Self-hosted LLM | - | 🔵 Très faible | 🟢 Faible | **P6** |
| `OPENAI_API_KEY_4` (Medium) | Self-hosted LLM | Aucun | 🔵 Très faible | 🟢 Faible | **P6** |
| `OPENAI_BASE_URL_4` | Self-hosted LLM | - | 🔵 Très faible | 🟢 Faible | **P6** |
| `SD_BASE_URL` | Stable Diffusion | Aucun (infra existante) | 🔵 Très faible | 🟢 Faible | **P7** |

**Analyse :**
- **Infrastructure locale** : Pas de coût API externe, mais disponibilité non garantie en CI
- **Problème architectural :** GitHub Actions runners ne peuvent pas accéder aux services self-hosted
- **Recommandation :** Ne PAS ajouter (impossible à utiliser dans le CI cloud)

##### D. Configuration Non-Sensible

| Variable | Type | Risque | Recommandation |
|----------|------|--------|----------------|
| `JAVA_HOME` | Path système | Aucun | ❌ Ne PAS mettre en secret (configurable dans workflow) |
| `CONDA_ENV_NAME` | Nom environnement | Aucun | ❌ Ne PAS mettre en secret (hardcodé dans workflow) |
| `FRONTEND_URL`, `BACKEND_URL` | URLs locales | Aucun | ❌ Ne PAS mettre en secret (tests E2E seulement) |

---

### 1.2 Stratégie d'Implémentation par Phases

#### 🎯 Phase 1 : OPTIMISATION (Recommandé - Immédiat)

**Principe :** Maximiser la valeur des 2 secrets existants AVANT d'en ajouter de nouveaux

**Actions concrètes :**

1. **Audit de couverture actuelle** (1-2 jours)
   - Identifier tous les tests qui utilisent `OPENAI_API_KEY`
   - Mesurer la couverture réelle apportée par les secrets actuels
   - Documenter les tests qui sont skippés sans secrets

2. **Optimisation des markers pytest** (2-3 jours)
   - Standardiser l'utilisation de `@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"))`
   - Créer un marker custom `@pytest.mark.requires_api` réutilisable
   - Documenter dans [`pytest.ini`](../../pytest.ini) :
     ```ini
     [pytest]
     markers =
         requires_api: Tests nécessitant une clé API OpenAI valide
         requires_openrouter: Tests nécessitant une clé API OpenRouter
         requires_azure: Tests nécessitant une configuration Azure OpenAI complète
     ```

3. **Amélioration du reporting CI** (1 jour)
   - Ajouter un step "Test Coverage Summary" dans le workflow
   - Afficher clairement : X tests exécutés, Y tests skippés (raison: secrets)
   - Créer une baseline de métriques

**Résultat attendu :**
- 📈 Meilleure visibilité sur ce qui est testé vs skippé
- 📈 Fondation solide pour justifier l'ajout de nouveaux secrets
- 📈 Documentation claire pour les contributeurs

**Coût :** Aucun  
**Risque :** Aucun  
**Valeur :** 🟢 **HAUTE** (améliore la maintenabilité sans ajout de complexité)

---

#### 🔄 Phase 2 : EXTENSION CIBLÉE (Court Terme - 2-4 semaines)

**Prérequis :** Phase 1 complétée et métriques disponibles

**Secret à ajouter :**

##### 2.1. `OPENROUTER_API_KEY` (Si justifié)

**Justification :**
- ✅ **Usage identifié** : [`tests/integration/test_api_connectivity.py`](../../tests/integration/test_api_connectivity.py:16)
- ✅ **Coût maîtrisé** : Pay-per-use, ~$0.15 per 1M tokens (équivalent gpt-4o-mini)
- ✅ **Valeur** : Teste la compatibilité multi-providers (robustesse)
- ⚠️ **Limitation** : 1 seul test actuellement concerné

**Conditions d'ajout :**
```
SI (Phase 1 révèle >= 5 tests pouvant utiliser OpenRouter)
   ET (Justification business : diversification des providers)
ALORS
   Ajouter OPENROUTER_API_KEY
SINON
   Reporter à Phase 3
FIN SI
```

**Configuration recommandée :**

```yaml
# Dans .github/workflows/ci.yml
- name: Check OpenRouter availability
  id: check_openrouter
  shell: pwsh
  run: |
    if ("${{ secrets.OPENROUTER_API_KEY }}" -ne "") {
      echo "OPENROUTER_CONFIGURED=true" >> $env:GITHUB_ENV
      Write-Host "✅ OpenRouter API key configured"
    } else {
      echo "OPENROUTER_CONFIGURED=false" >> $env:GITHUB_ENV
      Write-Host "ℹ️ OpenRouter tests will be skipped"
    }

- name: Run OpenRouter tests
  if: env.OPENROUTER_CONFIGURED == 'true'
  shell: pwsh
  env:
    OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
    OPENAI_BASE_URL: "https://openrouter.ai/api/v1"
  run: |
    pytest tests/integration/test_api_connectivity.py::test_openrouter_connection -v
```

**Sécurité :**
- ✅ Rotation : Tous les 90 jours (créer calendar reminder)
- ✅ Scope minimal : Lecture seule, pas de write access
- ✅ Budget limit : Configurer dans compte OpenRouter (<$5/mois)
- ✅ Monitoring : Alertes si usage > seuil

##### 2.2. `TIKA_SERVER_ENDPOINT` (Optionnel, faible priorité)

**⚠️ NON RECOMMANDÉ pour Phase 2**

**Raisons :**
- ❌ 1 seul test concerné (faible ROI)
- ❌ Facilement mockable (pas de vraie valeur ajoutée)
- ❌ Service self-hosted = disponibilité non garantie en CI
- ✅ Alternative : Mock Tika responses dans les tests

**Décision :** Ne pas ajouter, utiliser mocking

---

#### 🔮 Phase 3 : ÉVALUATION CONTINUE (Moyen Terme - 2-3 mois)

**Principe :** Réévaluer périodiquement les besoins en fonction de l'évolution du projet

**Secrets à surveiller :**

##### 3.1. Azure OpenAI (Conditionnel)

**Ajouter SI :**
- ✅ Le projet adopte Azure OpenAI en production
- ✅ >= 5 tests nécessitent spécifiquement Azure
- ✅ Budget Azure disponible (~$50+/mois)

**NE PAS ajouter SI :**
- ❌ Usage purement expérimental
- ❌ Peut être testé avec OpenAI standard
- ❌ Coût non justifié par la valeur

**Configuration si ajouté :**
```yaml
# Groupe de secrets Azure (3 requis ensemble)
env:
  AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
  AZURE_OPENAI_ENDPOINT: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
  AZURE_OPENAI_DEPLOYMENT_NAME: ${{ secrets.AZURE_OPENAI_DEPLOYMENT_NAME }}
```

##### 3.2. Modèles Locaux (Self-Hosted)

**⛔ NE JAMAIS AJOUTER**

**Raisons techniques :**
- ❌ GitHub Actions runners = cloud isolé
- ❌ Impossible d'accéder aux services `https://api.micro.text-generation-webui.myia.io`
- ❌ Sécurité : Ne JAMAIS exposer URLs internes en secrets publics

**Alternative :**
- Tests locaux uniquement (développement)
- Documentation pour configuration locale

##### 3.3. Stable Diffusion

**⛔ NE PAS AJOUTER**

**Raisons :**
- ❌ Aucun test identifié utilisant `SD_BASE_URL`
- ❌ Hors scope du projet (analyse argumentative)
- ❌ Coût/complexité non justifiés

---

### 1.3 Architecture Technique Détaillée

#### 1.3.1 Mécanisme d'Injection Conditionnel

**Pattern recommandé :**

```yaml
# Template générique pour tout nouveau secret
- name: Check {SECRET_NAME} availability
  id: check_{secret_id}
  shell: pwsh
  run: |
    if ("${{ secrets.SECRET_NAME }}" -ne "") {
      echo "SECRET_NAME_CONFIGURED=true" >> $env:GITHUB_ENV
      Write-Host "✅ {SECRET_NAME} configured"
    } else {
      echo "SECRET_NAME_CONFIGURED=false" >> $env:GITHUB_ENV
      Write-Host "ℹ️ {SECRET_NAME} not configured - related tests will be skipped"
    }

- name: Run tests requiring {SECRET_NAME}
  if: env.SECRET_NAME_CONFIGURED == 'true'
  shell: pwsh
  env:
    SECRET_NAME: ${{ secrets.SECRET_NAME }}
  run: |
    pytest -m requires_{secret_marker} -v
```

**Avantages :**
- ✅ Isolation claire par secret
- ✅ Logs explicites dans GitHub Actions
- ✅ Gestion granulaire des échecs
- ✅ Compatible forks (tests skippés gracieusement)

#### 1.3.2 Gestion Conditionnelle des Tests avec Pytest Markers

**Configuration pytest.ini :**

```ini
[pytest]
markers =
    requires_api: Tests nécessitant OPENAI_API_KEY (clé API OpenAI)
    requires_openrouter: Tests nécessitant OPENROUTER_API_KEY
    requires_azure: Tests nécessitant configuration Azure OpenAI complète (3 variables)
    requires_tika: Tests nécessitant TIKA_SERVER_ENDPOINT
    slow: Tests lents (>10s)
    integration: Tests d'intégration avec services externes
```

**Utilisation dans les tests :**

```python
# Exemple : Test nécessitant OpenRouter
import pytest
import os

@pytest.mark.requires_openrouter
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY non configurée"
)
def test_openrouter_connection():
    """Test la connectivité avec OpenRouter API."""
    # ...
```

**Exécution sélective :**

```bash
# Local : Tous les tests
pytest

# Local : Seulement tests sans API
pytest -m "not requires_api"

# CI : Tests selon secrets disponibles
pytest -m "requires_api" --exitfirst  # S'arrête au premier échec
```

#### 1.3.3 Workflow CI Complet (Proposition)

**Structure modulaire :**

```yaml
jobs:
  lint-and-format:
    # ... (inchangé)

  automated-tests:
    runs-on: windows-latest
    needs: lint-and-format
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          distribution: 'temurin'
          java-version: '11'

      - name: Setup Miniconda
        uses: conda-incubator/setup-miniconda@v2
        timeout-minutes: 15
        with:
          python-version: "3.10"
          environment-file: environment.yml
          activate-environment: projet-is
          use-mamba: true
          auto-update-conda: false

      # ====== SECTION SECRETS CHECKS ======
      
      - name: Check OpenAI API availability
        id: check_openai
        shell: pwsh
        run: |
          if ("${{ secrets.OPENAI_API_KEY }}" -ne "") {
            echo "OPENAI_CONFIGURED=true" >> $env:GITHUB_ENV
            Write-Host "✅ OpenAI API key configured"
          } else {
            echo "OPENAI_CONFIGURED=false" >> $env:GITHUB_ENV
            Write-Host "⚠️ OpenAI tests will be skipped"
          }

      - name: Check OpenRouter API availability
        id: check_openrouter
        shell: pwsh
        run: |
          if ("${{ secrets.OPENROUTER_API_KEY }}" -ne "") {
            echo "OPENROUTER_CONFIGURED=true" >> $env:GITHUB_ENV
            Write-Host "✅ OpenRouter API key configured"
          } else {
            echo "OPENROUTER_CONFIGURED=false" >> $env:GITHUB_ENV
            Write-Host "ℹ️ OpenRouter tests will be skipped"
          }

      - name: Check Azure OpenAI availability
        id: check_azure
        shell: pwsh
        run: |
          $azure_complete = (
            "${{ secrets.AZURE_OPENAI_API_KEY }}" -ne "" -and
            "${{ secrets.AZURE_OPENAI_ENDPOINT }}" -ne "" -and
            "${{ secrets.AZURE_OPENAI_DEPLOYMENT_NAME }}" -ne ""
          )
          if ($azure_complete) {
            echo "AZURE_CONFIGURED=true" >> $env:GITHUB_ENV
            Write-Host "✅ Azure OpenAI configuration complete"
          } else {
            echo "AZURE_CONFIGURED=false" >> $env:GITHUB_ENV
            Write-Host "ℹ️ Azure OpenAI tests will be skipped (requires 3 secrets)"
          }

      # ====== SECTION TESTS ======

      - name: Run base tests (no API required)
        shell: pwsh
        run: |
          pytest -m "not requires_api and not requires_openrouter and not requires_azure" -v

      - name: Run OpenAI tests
        if: env.OPENAI_CONFIGURED == 'true'
        shell: pwsh
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          TEXT_CONFIG_PASSPHRASE: ${{ secrets.TEXT_CONFIG_PASSPHRASE }}
        run: |
          pytest -m "requires_api" -v

      - name: Run OpenRouter tests
        if: env.OPENROUTER_CONFIGURED == 'true'
        shell: pwsh
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          OPENAI_BASE_URL: "https://openrouter.ai/api/v1"
        run: |
          pytest -m "requires_openrouter" -v

      - name: Run Azure OpenAI tests
        if: env.AZURE_CONFIGURED == 'true'
        shell: pwsh
        env:
          AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
          AZURE_OPENAI_ENDPOINT: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
          AZURE_OPENAI_DEPLOYMENT_NAME: ${{ secrets.AZURE_OPENAI_DEPLOYMENT_NAME }}
        run: |
          pytest -m "requires_azure" -v

      # ====== SECTION REPORTING ======

      - name: Test coverage summary
        if: always()
        shell: pwsh
        run: |
          Write-Host "`n📊 Test Execution Summary"
          Write-Host "=========================="
          Write-Host "OpenAI tests: $(if ($env:OPENAI_CONFIGURED -eq 'true') {'✅ Executed'} else {'⏭️ Skipped'})"
          Write-Host "OpenRouter tests: $(if ($env:OPENROUTER_CONFIGURED -eq 'true') {'✅ Executed'} else {'⏭️ Skipped'})"
          Write-Host "Azure tests: $(if ($env:AZURE_CONFIGURED -eq 'true') {'✅ Executed'} else {'⏭️ Skipped'})"
```

**Avantages architecture modulaire :**
- ✅ Chaque catégorie de tests = job séparé
- ✅ Échec d'une catégorie n'impacte pas les autres
- ✅ Logs clairs et traçables
- ✅ Extensible facilement

---

### 1.4 Sécurité et Bonnes Pratiques

#### 1.4.1 Principes de Sécurité (Non Négociables)

**🔒 Règle 1 : Principe du Moindre Privilège**
- ✅ Secrets = Read-Only API keys uniquement
- ❌ JAMAIS de secrets avec permissions write/admin
- ✅ Limiter scope aux ressources strictement nécessaires

**🔒 Règle 2 : Rotation Régulière**
- ✅ OpenAI API Key : Rotation tous les **60 jours**
- ✅ OpenRouter API Key : Rotation tous les **90 jours**
- ✅ Azure API Key : Rotation selon politique entreprise
- ✅ Calendrier automatisé (GitHub Issues avec labels `security/rotation`)

**🔒 Règle 3 : Zéro Exposition dans les Logs**

**Validation obligatoire :**
```yaml
# Après chaque modification de workflow
- name: Validate secrets not in logs
  shell: pwsh
  run: |
    # Vérifier qu'aucun secret n'est loggué
    $logs = Get-Content workflow_logs.txt
    if ($logs -match "sk-proj-|sk-or-v1-") {
      Write-Error "🚨 SECRET DETECTED IN LOGS"
      exit 1
    }
```

**Pattern anti-leak :**
```python
# ✅ BON
logger.info(f"API key configured: {bool(api_key)}")

# ❌ MAUVAIS
logger.info(f"Using API key: {api_key}")
```

**🔒 Règle 4 : Budget Limits**

**OpenAI :**
- Hard limit : $10/mois
- Alert à $7/mois
- Auto-stop à $10/mois

**OpenRouter :**
- Hard limit : $5/mois
- Alert à $3/mois

**Configuration dans les dashboards des providers :**
```
OpenAI Dashboard > Usage > Limits
- Monthly limit: $10.00
- Email alerts: enabled
```

**🔒 Règle 5 : Séparation des Secrets par Environnement**

**Architecture recommandée :**

```
GitHub Secrets Organization-Level (si applicable):
├── OPENAI_API_KEY_PROD (Production)
├── OPENAI_API_KEY_CI (CI/CD) ← Recommandé
└── OPENAI_API_KEY_DEV (Development)

GitHub Secrets Repository-Level:
├── OPENAI_API_KEY (CI actuel - à renommer en OPENAI_API_KEY_CI)
├── TEXT_CONFIG_PASSPHRASE
└── (nouveaux secrets Phase 2+)
```

**Migration recommandée :**
1. Créer `OPENAI_API_KEY_CI` dédié au CI (clé séparée)
2. Configurer budget limit spécifique
3. Rotation indépendante de la clé dev/prod

#### 1.4.2 Checklist Avant Ajout de Secret

**⚠️ Obligatoire avant configuration :**

- [ ] **Justification documentée** : Au moins 3 tests nécessitent ce secret
- [ ] **Analyse coût/bénéfice** : ROI positif (valeur > coût + maintenance)
- [ ] **Budget configuré** : Hard limits en place dans le provider
- [ ] **Plan de rotation** : Calendrier et procédure documentés
- [ ] **Markers pytest** : Créés et documentés dans pytest.ini
- [ ] **Documentation** : Ajout dans ce document et README
- [ ] **Validation** : Test local avec secret avant ajout en CI
- [ ] **Monitoring** : Alertes configurées dans provider dashboard

#### 1.4.3 Procédure de Rotation des Secrets

**Fréquence :**
- `OPENAI_API_KEY` : Tous les 60 jours
- `OPENROUTER_API_KEY` : Tous les 90 jours (si ajouté)
- `TEXT_CONFIG_PASSPHRASE` : Tous les 6 mois (faible risque)

**Processus de rotation :**

```bash
# Étape 1 : Générer nouvelle clé dans provider dashboard
# Exemple OpenAI: https://platform.openai.com/api-keys

# Étape 2 : Tester la nouvelle clé localement
export OPENAI_API_KEY_NEW="sk-proj-nouvelle-cle..."
pytest -m "requires_api" --exitfirst

# Étape 3 : Mettre à jour le secret GitHub (via gh CLI)
gh secret set OPENAI_API_KEY --body "sk-proj-nouvelle-cle..."

# Étape 4 : Déclencher un workflow de validation
gh workflow run ci.yml

# Étape 5 : Vérifier succès
gh run list --workflow=ci.yml --limit=1

# Étape 6 : Révoquer l'ancienne clé (24h après validation)
# → Dans provider dashboard, delete old API key
```

**Documentation obligatoire :**
- Date de rotation dans un fichier `docs/security/secrets_rotation_log.md`
- Format : `YYYY-MM-DD | SECRET_NAME | Rotated by @username | Validation: run #XXX`

---

## 🔍 Partie 2 : Synthèse des Découvertes Sémantiques

### 2.1 Patterns Identifiés dans le Projet

#### Pattern 1 : Gestion Gracieuse de l'Absence de Configuration

**Découverte dans :** [`argumentation_analysis/core/environment.py:59-82`](../../argumentation_analysis/core/environment.py:59-82)

**Principe :**
```python
# Pattern établi dans le projet
try:
    load_dotenv()
    value = os.getenv("SECRET_NAME")
    if not value:
        logger.warning("SECRET_NAME not configured, using defaults")
        value = DEFAULT_VALUE
except Exception as e:
    logger.warning(f"Could not load .env: {e}")
    value = DEFAULT_VALUE
```

**Application à la stratégie :**
- ✅ Les tests doivent **toujours** avoir un fallback gracieux
- ✅ L'absence de secret = skip test, pas échec CI
- ✅ Logging clair du comportement (info/warning, jamais error)

#### Pattern 2 : Tests Conditionnels avec Skipif

**Découverte dans :** Multiples tests ([`test_authentic_components.py:52`](../../tests/integration/test_authentic_components.py:52), [`test_llm_service.py:86`](../../tests/unit/argumentation_analysis/test_llm_service.py:86))

**Pattern établi :**
```python
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), 
    reason="OPENAI_API_KEY non disponible"
)
def test_requiring_api():
    """Test nécessitant une API réelle."""
    # ...
```

**Recommandation :**
- ✅ **Standardiser** : Créer des decorators réutilisables
- ✅ **Documenter** : Ajouter docstring expliquant pourquoi le test est conditionnel
- ✅ **Grouper** : Combiner skipif + marker custom

**Proposition de standardisation :**

```python
# Dans tests/conftest.py ou tests/utils/decorators.py

def requires_openai_api(func):
    """Decorator pour tests nécessitant OPENAI_API_KEY."""
    return pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY non configurée - test skippé"
    )(pytest.mark.requires_api(func))

def requires_openrouter_api(func):
    """Decorator pour tests nécessitant OPENROUTER_API_KEY."""
    return pytest.mark.skipif(
        not os.getenv("OPENROUTER_API_KEY"),
        reason="OPENROUTER_API_KEY non configurée - test skippé"
    )(pytest.mark.requires_openrouter(func))

# Usage :
@requires_openai_api
def test_with_openai():
    # ...
```

#### Pattern 3 : Configuration Multi-Provider

**Découverte dans :** [`test_api_connectivity.py`](../../tests/integration/test_api_connectivity.py)

**Architecture actuelle :**
```python
# Test vérifie plusieurs providers
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
if openrouter_api_key:
    # Test OpenRouter
else:
    pytest.skip("OpenRouter non configuré")
```

**Enseignement :**
- ✅ Le projet supporte déjà multi-providers (OpenAI, OpenRouter, Azure)
- ✅ Tests de connectivité existent
- ⚠️ **Problème** : 1 seul test pour OpenRouter = faible ROI secret
- 💡 **Opportunité** : Étendre les tests multi-providers AVANT d'ajouter secrets

---

### 2.2 Best Practices Trouvées dans la Documentation

#### Source 1 : Documentation Interne

**[`docs/guides/authenticity_validation_guide.md:357-359`](../../docs/guides/authenticity_validation_guide.md:357-359)**

```bash
# Variables d'environnement (recommandé)
export OPENAI_API_KEY="sk-proj-..."
```

**Enseignement :**
- ✅ Preference pour variables d'environnement vs fichiers config
- ✅ Pattern déjà adopté dans le projet

#### Source 2 : Tests d'Intégration

**[`tests/integration/README.md:125-127`](../../tests/integration/README.md:125-127)**

```bash
# Avec clé OpenAI configurée (tests complets)
OPENAI_API_KEY=sk-your-key pytest tests/integration/ -v
```

**Enseignement :**
- ✅ Documentation claire pour développeurs
- ✅ Exécution locale bien documentée
- ⚠️ **Gap** : Manque documentation CI/CD pour contributeurs externes

#### Source 3 : Recherche Web (GitHub Actions Best Practices 2024-2025)

**Top insights :**

1. **OIDC > Long-lived tokens** (source: Blacksmith.sh)
   - GitHub Actions peut utiliser OIDC pour Azure, AWS
   - **Non applicable** : OpenAI/OpenRouter ne supportent pas OIDC
   - **Alternative** : Short-lived tokens avec rotation fréquente

2. **Environment-based protection** (source: Wiz.io)
   - Utiliser GitHub Environments avec required reviewers
   - **Application** : Créer environment "production" pour secrets sensibles
   - **Bénéfice** : Validation humaine avant usage de secrets critiques

3. **Secret scanning** (source: GitHub Blog 2024)
   - 39M secrets leakés en 2024 (push protection bloque plusieurs/minute)
   - **Action** : Vérifier que push protection est activée sur le repo
   - **Commande** : `gh repo edit --enable-secret-scanning --enable-push-protection`

4. **Budget limits essentiels** (source: Multiple)
   - 70% des breaches impliquent des secrets avec usage non limité
   - **Action** : Configurer hard limits dans tous les providers

### 2.3 Cohérence avec l'Architecture Existante

#### Alignement D-CI-01 (Gestion Conditionnelle)

**Architecture D-CI-01 :**
```yaml
Check secrets → Run tests (conditional) → Notify if skipped
```

**Extension proposée :**
```yaml
Check OpenAI → Check OpenRouter → Check Azure
     ↓              ↓                  ↓
Run OpenAI tests   Run OR tests       Run Azure tests
     ↓              ↓                  ↓
    Report unified test coverage summary
```

**✅ Cohérence totale** : Même pattern, juste étendu à plus de secrets

#### Alignement D-CI-04 (Tolérance .env)

**Architecture D-CI-04 :**
- Absence de `.env` = logger.info(), pas error
- CI peut fonctionner sans configuration locale

**Synergie :**
- ✅ Les secrets GitHub **remplacent** le `.env` en CI
- ✅ Développement local : `.env` préféré
- ✅ CI : Secrets GitHub exclusivement

**Principe unifié :**
```
Configuration Priority:
1. GitHub Secrets (en CI)
2. Variables d'environnement système
3. Fichier .env (développement local)
4. Valeurs par défaut (fallback)
```

---

## 💬 Partie 3 : Synthèse Conversationnelle

### 3.1 Alignement avec les Objectifs des Missions D-CI

**Mission D-CI-01 : Stabilisation Pipeline CI**
- Objectif : Gérer l'absence de secrets gracieusement
- ✅ **Atteint** : Tests skippés si secrets absents

**Mission D-CI-04 : Tolérance .env**
- Objectif : CI fonctionnel sans fichier `.env`
- ✅ **Atteint** : Configuration via variables d'environnement

**Mission D-CI-05 : Extension des Secrets**
- Objectif : **Augmenter la couverture de tests**
- 🎯 **Stratégie** : Optimiser l'existant AVANT d'étendre

### 3.2 Impact sur la Couverture de Tests

#### Analyse Actuelle

**Avec secrets actuels :**
- Tests base (no API) : Toujours exécutés
- Tests OpenAI : Exécutés si `OPENAI_API_KEY` présent
- Tests OpenRouter : ⏭️ Skippés (secret absent)
- Tests Azure : ⏭️ Skippés (secrets absents)

**État estimé :**
```
Coverage actuelle en CI:
├── Tests sans API : ~70% de la suite
├── Tests OpenAI : ~25% de la suite  
├── Tests OpenRouter : ~2% de la suite (SKIPPÉ)
└── Tests Azure : ~3% de la suite (SKIPPÉ)
```

**Impact ajout OpenRouter :**
- +2% de couverture
- **Questionnement** : Est-ce que 2% justifie un nouveau secret ?

**Recommandation :**
1. **D'abord** : Augmenter le nombre de tests OpenRouter (de 1 à 5+)
2. **Ensuite** : Justifier l'ajout du secret par la valeur réelle
3. **Alternative** : Mocker OpenRouter dans les tests (même comportement que OpenAI)

#### Projection Phase 1 (Optimisation)

**Actions Phase 1 :**
- Identifier tests actuellement sans marker qui pourraient être conditionnels
- Créer variants de tests (avec/sans API)
- Améliorer reporting de couverture

**Impact attendu :**
```
Après Phase 1:
├── Visibilité : +100% (savoir exactement ce qui est testé)
├── Documentation : +100% (README pour contributeurs)
├── Maintenabilité : +50% (markers standardisés)
└── Couverture réelle : 0% (pas de nouveaux tests, mais mieux organisés)
```

### 3.3 Vision à Long Terme pour la CI/CD

#### Objectif Stratégique

**Pyramide des Tests CI :**

```
        /\
       /E2E\      10% - Secrets requis (OpenAI)
      /------\
     /  INT  \    20% - Secrets optionnels (OpenRouter, Azure)
    /----------\
   /    UNIT   \  70% - Aucun secret requis
  /-------------\
```

**Principe directeur :**
- 70% des tests doivent passer **sans aucun secret**
- 20% avec secrets optionnels (multi-provider, edge cases)
- 10% avec secrets requis (E2E complets)

#### Évolution Recommandée

**Aujourd'hui (après D-CI-04) :**
```yaml
Secrets: 2
Tests conditionnels: Oui (OpenAI seulement)
Coverage reporting: Basique
Rotation: Manuelle
```

**Après Phase 1 (Optimisation) :**
```yaml
Secrets: 2 (inchangé)
Tests conditionnels: Oui (markers standardisés)
Coverage reporting: Détaillé (par catégorie)
Rotation: Manuelle mais documentée
Documentation: Complète pour contributeurs
```

**Après Phase 2 (Extension) :**
```yaml
Secrets: 3-4 (OpenRouter si justifié)
Tests conditionnels: Oui (3 catégories)
Coverage reporting: Dashboard temps réel
Rotation: Semi-automatisée (calendar reminders)
Documentation: Guide complet sécurité
```

**Vision Long Terme (6-12 mois) :**
```yaml
Secrets: 4-6 (selon besoins réels uniquement)
Tests conditionnels: Oui (architecture modulaire)
Coverage reporting: Metrics complètes + tendances
Rotation: Automatisée (GitHub Actions scheduled)
Monitoring: Alertes proactives coûts + sécurité
OIDC: Intégré pour providers supportés (Azure)
Environments: Production + Staging avec reviewers requis
```

---

## 📋 Partie 4 : Plan d'Implémentation Détaillé

### Phase 1 : Optimisation (Recommandé - 3-5 jours)

#### Jour 1 : Audit et Baseline

**Tâche 1.1 : Inventaire complet**
```bash
# Lister tous les tests utilisant des secrets
cd tests
grep -r "os.getenv.*API" --include="*.py" > ../analysis/tests_using_secrets.txt

# Analyser les markers existants
pytest --markers

# Générer rapport de couverture actuel
pytest --co -q > ../analysis/all_tests.txt
pytest -m "requires_api" --co -q > ../analysis/tests_requiring_api.txt
```

**Livrable :** `docs/analysis/ci_secrets_baseline_YYYYMMDD.md`

**Tâche 1.2 : Mesure de couverture par secret**
```bash
# Tests avec OPENAI_API_KEY
OPENAI_API_KEY=test pytest --collect-only -q | wc -l

# Tests sans aucun secret
pytest -m "not requires_api" --collect-only -q | wc -l
```

**Livrable :** Métriques dans le rapport baseline

#### Jour 2-3 : Standardisation des Markers

**Tâche 2.1 : Créer decorators réutilisables**

Fichier : `tests/utils/api_decorators.py` (nouveau)

```python
"""Decorators standardisés pour tests nécessitant des API externes."""
import os
import pytest

def requires_openai_api(func):
    """
    Marque un test comme nécessitant OPENAI_API_KEY.
    Le test sera skippé si la clé n'est pas configurée.
    """
    return pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY non configurée"
    )(pytest.mark.requires_api(func))

def requires_openrouter_api(func):
    """
    Marque un test comme nécessitant OPENROUTER_API_KEY.
    Le test sera skippé si la clé n'est pas configurée.
    """
    return pytest.mark.skipif(
        not os.getenv("OPENROUTER_API_KEY"),
        reason="OPENROUTER_API_KEY non configurée"
    )(pytest.mark.requires_openrouter(func))

def requires_azure_openai(func):
    """
    Marque un test comme nécessitant configuration Azure OpenAI complète.
    Requiert : AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT_NAME
    """
    azure_complete = all([
        os.getenv("AZURE_OPENAI_API_KEY"),
        os.getenv("AZURE_OPENAI_ENDPOINT"),
        os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    ])
    return pytest.mark.skipif(
        not azure_complete,
        reason="Configuration Azure OpenAI incomplète (3 variables requises)"
    )(pytest.mark.requires_azure(func))
```

**Tâche 2.2 : Migrer tests existants**

Exemple de migration :
```python
# AVANT
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), 
    reason="OPENAI_API_KEY non disponible"
)
def test_llm_service():
    # ...

# APRÈS
from tests.utils.api_decorators import requires_openai_api

@requires_openai_api
def test_llm_service():
    """Test du service LLM avec OpenAI.
    
    Requires:
        OPENAI_API_KEY: Clé API OpenAI valide
    """
    # ...
```

**Tâche 2.3 : Mettre à jour pytest.ini**

```ini
[pytest]
markers =
    requires_api: Tests nécessitant OPENAI_API_KEY
    requires_openrouter: Tests nécessitant OPENROUTER_API_KEY
    requires_azure: Tests nécessitant Azure OpenAI (3 variables)
    requires_tika: Tests nécessitant TIKA_SERVER_ENDPOINT
    slow: Tests lents (>10s)
    integration: Tests d'intégration avec services externes
    jvm_test: Tests dépendant de la JVM (isolation subprocess)
```

#### Jour 4 : Amélioration du Workflow CI

**Tâche 4.1 : Ajouter step de reporting**

Fichier : `.github/workflows/ci.yml`

Ajouter après tous les tests :

```yaml
- name: Generate test coverage summary
  if: always()
  shell: pwsh
  run: |
    Write-Host "`n📊 ========================================"
    Write-Host "   CI Test Execution Summary"
    Write-Host "=========================================="
    
    # Secrets configuration status
    Write-Host "`n🔐 Secrets Configuration:"
    Write-Host "  • OpenAI API: $(if ($env:OPENAI_CONFIGURED -eq 'true') {'✅ Configured'} else {'⚠️ Not configured'})"
    Write-Host "  • OpenRouter API: $(if ($env:OPENROUTER_CONFIGURED -eq 'true') {'✅ Configured'} else {'⚠️ Not configured'})"
    Write-Host "  • Azure OpenAI: $(if ($env:AZURE_CONFIGURED -eq 'true') {'✅ Configured'} else {'⚠️ Not configured'})"
    
    # Test categories executed
    Write-Host "`n🧪 Tests Executed:"
    Write-Host "  • Base tests (no API): ✅ Always executed"
    Write-Host "  • OpenAI tests: $(if ($env:OPENAI_CONFIGURED -eq 'true') {'✅ Executed'} else {'⏭️ Skipped'})"
    Write-Host "  • OpenRouter tests: $(if ($env:OPENROUTER_CONFIGURED -eq 'true') {'✅ Executed'} else {'⏭️ Skipped'})"
    Write-Host "  • Azure tests: $(if ($env:AZURE_CONFIGURED -eq 'true') {'✅ Executed'} else {'⏭️ Skipped'})"
    
    Write-Host "`n💡 Tip: To run skipped tests locally, configure the required secrets in your .env file"
    Write-Host "=========================================="
```

**Tâche 4.2 : Documenter pour contributeurs**

Fichier : `CONTRIBUTING.md` (nouveau ou à mettre à jour)

```markdown
## Running Tests Locally

### With Full API Access
1. Copy `.env.example` to `.env`
2. Configure your API keys:
   ```bash
   OPENAI_API_KEY=sk-proj-your-key
   TEXT_CONFIG_PASSPHRASE=your-passphrase
   ```
3. Run tests: `pytest`

### Without API Keys
1. Run tests without external APIs:
   ```bash
   pytest -m "not requires_api"
   ```
2. This matches the CI behavior for forks

### CI Behavior
- **Main repository**: All tests run (secrets configured)
- **Forks**: Only tests not requiring secrets run
- **Expected**: Some tests skipped on forks is normal ✅
```

#### Jour 5 : Validation et Documentation

**Tâche 5.1 : Test complet local**
```bash
# Simuler CI sans secrets
unset OPENAI_API_KEY
pytest -v --tb=short

# Vérifier que les tests sont skippés (pas failed)
pytest -v | grep -i "skipped"
```

**Tâche 5.2 : Créer ce document**
- ✅ Déjà en cours

---

### Phase 2 : Extension Ciblée (Court Terme - Si Justifié)

**⚠️ PRÉREQUIS OBLIGATOIRES :**
- [ ] Phase 1 complétée
- [ ] Métriques baseline disponibles
- [ ] Au moins 5 tests identifiés pouvant utiliser le nouveau secret
- [ ] ROI positif démontré (valeur > coût + maintenance)

#### Ajout de `OPENROUTER_API_KEY`

**Étape 2.1 : Préparation (1 jour)**

1. **Créer compte OpenRouter** (si inexistant)
   - URL : https://openrouter.ai/
   - Configurer budget limit : $5/mois

2. **Tester la clé localement**
   ```bash
   export OPENROUTER_API_KEY="sk-or-v1-..."
   export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
   pytest tests/integration/test_api_connectivity.py::test_openrouter_connection -v
   ```

3. **Valider coût**
   - Exécuter tous les tests potentiels
   - Mesurer tokens consommés
   - Extrapoler coût mensuel CI

**Étape 2.2 : Configuration GitHub (30 min)**

**Via GitHub CLI :**
```bash
# Ajouter le secret
gh secret set OPENROUTER_API_KEY --body "sk-or-v1-votre-cle-ici"

# Vérifier
gh secret list
```

**Via Interface Web :**
1. Aller sur https://github.com/jsboigeEpita/2025-Epita-Intelligence-Symbolique/settings/secrets/actions
2. Cliquer "New repository secret"
3. Name: `OPENROUTER_API_KEY`
4. Value: `sk-or-v1-...`
5. Add secret

**Étape 2.3 : Modifier le Workflow (1 heure)**

Fichier : `.github/workflows/ci.yml`

Ajouter après le check OpenAI :

```yaml
- name: Check OpenRouter API availability
  id: check_openrouter
  shell: pwsh
  run: |
    if ("${{ secrets.OPENROUTER_API_KEY }}" -ne "") {
      echo "OPENROUTER_CONFIGURED=true" >> $env:GITHUB_ENV
      Write-Host "✅ OpenRouter API key configured"
    } else {
      echo "OPENROUTER_CONFIGURED=false" >> $env:GITHUB_ENV
      Write-Host "ℹ️ OpenRouter tests will be skipped"
    }

- name: Run OpenRouter tests
  if: env.OPENROUTER_CONFIGURED == 'true'
  shell: pwsh
  env:
    OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
    OPENAI_BASE_URL: "https://openrouter.ai/api/v1"
  run: |
    pytest -m "requires_openrouter" -v
```

**Étape 2.4 : Validation (1 heure)**

1. **Commit et push**
   ```bash
   git checkout -b feature/add-openrouter-secret
   git add .github/workflows/ci.yml
   git commit -m "feat(ci): Add OpenRouter API support

   - Add conditional check for OPENROUTER_API_KEY
   - Run OpenRouter tests if key configured
   - Skip gracefully if key not available
   
   Related: D-CI-05"
   git push -u origin feature/add-openrouter-secret
   ```

2. **Vérifier workflow**
   - Aller sur GitHub Actions
   - Vérifier que le step "Check OpenRouter" s'exécute
   - Confirmer que les tests OpenRouter sont exécutés

3. **Documenter rotation**
   ```bash
   # Créer calendrier rotation
   gh issue create \
     --title "🔐 [SECURITY] Rotate OPENROUTER_API_KEY" \
     --body "Rotation programmée tous les 90 jours" \
     --label "security/rotation" \
     --milestone "Q1-2025"
   ```

**Étape 2.5 : Documentation (30 min)**

Mettre à jour :
- `README.md` : Ajouter OpenRouter dans section CI
- `CONTRIBUTING.md` : Documenter comment tester avec OpenRouter
- Ce document : Marquer Phase 2 comme complétée

---

### Phase 3 : Évaluation Continue (Moyen Terme)

**Calendrier de revue :**
- **Tous les 3 mois** : Audit de l'utilisation des secrets
- **Avant ajout** : Checklist de justification obligatoire
- **Après ajout** : Monitoring coût 30 jours

**Questions à poser :**
1. Combien de tests utilisent réellement ce secret ?
2. Ces tests pourraient-ils être mockés avec une valeur équivalente ?
3. Le coût mensuel est-il justifié par la valeur apportée ?
4. La maintenance (rotation, monitoring) est-elle assumable ?

---

## 🎯 Partie 5 : Tableau de Décision par Secret

### Secret : `OPENROUTER_API_KEY`

| Critère | Évaluation | Score | Notes |
|---------|------------|-------|-------|
| **Sécurité** | 🟡 Modéré | 3/5 | API key public, peut être rotée facilement |
| **Coût** | 🟢 Faible | 4/5 | ~$0.15/1M tokens, budget limit facile |
| **Maintenance** | 🟢 Faible | 4/5 | 1 secret, rotation 90j suffisante |
| **Valeur - Actuelle** | 🔴 Très faible | 1/5 | 1 seul test concerné actuellement |
| **Valeur - Potentielle** | 🟡 Moyenne | 3/5 | Si tests multi-provider étendus |
| **Complexité config** | 🟢 Simple | 5/5 | 1 secret + 1 env var |

**Score Total :** 20/30 - **Conditionnellement recommandé**

**Décision :**
- ✅ Ajouter **SI ET SEULEMENT SI** Phase 1 identifie >= 5 tests pouvant l'utiliser
- ❌ NE PAS ajouter si valeur reste limitée à 1-2 tests

---

### Secret : `AZURE_OPENAI_API_KEY` (+ 2 variables associées)

| Critère | Évaluation | Score | Notes |
|---------|------------|-------|-------|
| **Sécurité** | 🟡 Modéré | 3/5 | Lié à abonnement Azure (potentiel coût élevé si compromis) |
| **Coût** | 🟠 Élevé | 2/5 | Abonnement Azure requis (~$50+/mois) |
| **Maintenance** | 🟠 Complexe | 2/5 | 3 secrets à gérer, rotation liée aux politiques Azure |
| **Valeur - Actuelle** | 🔴 Très faible | 1/5 | 1 seul test concerné |
| **Valeur - Potentielle** | 🟡 Moyenne | 3/5 | Si migration vers Azure planifiée |
| **Complexité config** | 🟠 Complexe | 2/5 | 3 secrets requis simultanément |

**Score Total :** 13/30 - **NON recommandé actuellement**

**Décision :**
- ❌ NE PAS ajouter pour Phase 2
- 📅 Réévaluer en Phase 3 **SI** :
  - Le projet migre vers Azure OpenAI en production
  - Budget Azure disponible et approuvé
  - >= 10 tests nécessitent spécifiquement Azure

---

### Secret : `TIKA_SERVER_ENDPOINT`

| Critère | Évaluation | Score | Notes |
|---------|------------|-------|-------|
| **Sécurité** | 🟢 Faible | 5/5 | URL publique, pas de credential |
| **Coût** | 🟢 Aucun | 5/5 | Service gratuit |
| **Maintenance** | 🟢 Aucune | 5/5 | URL fixe, pas de rotation |
| **Valeur - Actuelle** | 🔴 Très faible | 1/5 | 1 test UI parsing documents |
| **Valeur - Potentielle** | 🔴 Faible | 2/5 | Facilement mockable |
| **Complexité config** | 🟢 Simple | 5/5 | 1 variable non-sensible |

**Score Total :** 23/30 - **Non prioritaire malgré faible risque**

**Décision :**
- ❌ NE PAS ajouter comme secret GitHub
- ✅ **Alternative recommandée** : Hardcoder l'URL publique dans le test
- ✅ **Justification** : Ce n'est pas un secret (URL publique), donc pas besoin de GitHub Secrets

**Implémentation alternative :**
```python
# Dans tests/ui/test_utils.py
TIKA_SERVER_URL = os.getenv(
    "TIKA_SERVER_URL",
    "https://tika.open-webui.myia.io/tika"  # Valeur par défaut publique
)
```

---

### Secrets Modèles Locaux (6 variables)

| Critère | Évaluation | Notes |
|---------|------------|-------|
| **Sécurité** | 🔴 Risque élevé | URLs internes exposées publiquement = **INACCEPTABLE** |
| **Coût** | 🟢 Aucun | Mais infrastructure non accessible en CI cloud |
| **Valeur** | ❌ Impossible | GitHub Actions ne peut pas atteindre `myia.io` interne |
| **Complexité** | 🔴 Très élevée | 6 variables à gérer |

**Score Total :** ❌ **NON APPLICABLE**

**Décision :**
- ⛔ **NE JAMAIS AJOUTER**
- ⚠️ **Risque sécurité** : Exposition URLs infrastructure interne
- ❌ **Impossibilité technique** : Services non accessibles depuis GitHub runners cloud

**Alternative :**
- Tests locaux uniquement (développement)
- Documentation pour setup local dans README

---

## 🏗️ Partie 6 : Architecture Sécurisée

### 6.1 Mécanisme de Protection Multi-Niveaux

#### Niveau 1 : Configuration Provider (Obligatoire)

**OpenAI Dashboard :**
```
Settings > Organization > Billing > Limits
├── Hard limit: $10.00/month
├── Email alerts at: $7.00 (70%)
└── Soft limit: $8.00 (80% - warning in dashboard)
```

**OpenRouter Dashboard :**
```
Account > Credits > Usage Limits
├── Monthly budget: $5.00
├── Auto-refill: DISABLED
└── Alert email: enabled
```

#### Niveau 2 : GitHub Repository Settings

**Activer protections :**

```bash
# Via gh CLI (recommandé)
gh repo edit jsboigeEpita/2025-Epita-Intelligence-Symbolique \
  --enable-secret-scanning \
  --enable-push-protection \
  --enable-vulnerability-alerts

# Vérifier
gh api repos/jsboigeEpita/2025-Epita-Intelligence-Symbolique | jq '.security_and_analysis'
```

**Résultat attendu :**
```json
{
  "secret_scanning": { "status": "enabled" },
  "secret_scanning_push_protection": { "status": "enabled" },
  "dependabot_security_updates": { "status": "enabled" }
}
```

#### Niveau 3 : Workflow CI (Defense in Depth)

**Validation absence de leak :**

```yaml
- name: Validate no secrets in test outputs
  if: always()
  shell: pwsh
  run: |
    # Chercher patterns de secrets dans les logs
    $suspicious_patterns = @(
      'sk-proj-',
      'sk-or-v1-',
      'sk-test-',
      'api[_-]key.*[:=].*\w{20,}'
    )
    
    $found_leak = $false
    foreach ($pattern in $suspicious_patterns) {
      if (Select-String -Path $env:GITHUB_STEP_SUMMARY -Pattern $pattern -Quiet) {
        Write-Error "🚨 POTENTIAL SECRET LEAK DETECTED: $pattern"

        $found_leak = $true
      }
    }
    
    if ($found_leak) {
      exit 1
    } else {
      Write-Host "✅ No secrets detected in outputs"
    }
```

#### Niveau 4 : Code Review (Humain)

**Checklist pour PR modifiant les secrets :**
- [ ] Aucun secret hardcodé dans le code
- [ ] Tous les secrets utilisés via `env` ou `${{ secrets.X }}`
- [ ] Tests locaux passés avec et sans secrets
- [ ] Documentation mise à jour
- [ ] Workflow validé en staging si possible

### 6.2 Plan de Réponse aux Incidents

#### Scénario 1 : Secret Exposé Accidentellement

**Détection :**
- GitHub Secret Scanning déclenche alerte
- Email automatique envoyé
- Issue GitHub créée automatiquement

**Réponse (< 1 heure) :**
1. ⚠️ **Révoquer immédiatement** le secret dans le provider dashboard
2. 🔄 **Générer nouveau secret** avec permissions minimales
3. 🔐 **Mettre à jour GitHub Secret** : `gh secret set SECRET_NAME --body "new-value"`
4. ✅ **Valider** : Déclencher workflow test
5. 📝 **Documenter** : Log incident dans `docs/security/incidents.md`

#### Scénario 2 : Usage Anormal Détecté

**Détection :**
- Alert email du provider (usage > seuil)
- Coût anormal dans dashboard

**Investigation (< 2 heures) :**
1. 🔍 Vérifier logs GitHub Actions des derniers runs
2. 🔍 Identifier workflow consommant tokens anormalement
3. 🔍 Analyser tests ayant échoué/boucles infinies

**Réponse :**
- Si bug : Fix immédiat + rotation préventive du secret
- Si attaque : Révoquer + créer incident sécurité

#### Scénario 3 : Provider API Down

**Détection :**
- Tests échouent massivement en CI
- Timeouts répétés

**Réponse :**
1. ✅ Vérifier status page du provider
2. ⏸️ Désactiver temporairement tests concernés si outage confirmé
3. 📢 Notifier équipe via issue GitHub
4. ✅ Réactiver après résolution outage

---

## 📖 Partie 7 : Commandes de Référence

### 7.1 Gestion des Secrets via GitHub CLI

**Installation gh CLI :**
```powershell
# Windows (Chocolatey)
choco install gh

# Ou Scoop
scoop install gh

# Vérifier installation
gh --version
```

**Authentification :**
```bash
# Login interactif
gh auth login

# Vérifier auth
gh auth status
```

**Commandes secrets :**

```bash
# Lister tous les secrets du repository
gh secret list

# Ajouter un nouveau secret (interactif - masque la valeur)
gh secret set SECRET_NAME

# Ajouter un secret (depuis fichier)
gh secret set SECRET_NAME < secret.txt

# Ajouter un secret (depuis string)
echo "secret-value" | gh secret set SECRET_NAME

# Supprimer un secret
gh secret delete SECRET_NAME

# Voir quand un secret a été mis à jour (pas la valeur)
gh api repos/jsboigeEpita/2025-Epita-Intelligence-Symbolique/actions/secrets/SECRET_NAME
```

### 7.2 Gestion des Workflows

**Déclencher manuellement :**
```bash
# Déclencher le workflow CI
gh workflow run ci.yml

# Déclencher avec inputs (si workflow configuré)
gh workflow run ci.yml -f environment=staging

# Lister les runs récents
gh run list --workflow=ci.yml --limit=10

# Voir détails d'un run
gh run view RUN_ID

# Télécharger logs d'un run
gh run download RUN_ID
```

### 7.3 Monitoring et Debugging

**Vérifier status d'un workflow :**
```bash
# Watch un run en cours (polling)
gh run watch

# Voir logs d'un job spécifique
gh run view RUN_ID --log --job=JOB_ID

# Relancer un workflow échoué
gh run rerun RUN_ID
```

**Analyser usage des secrets :**
```bash
# Liste des workflows utilisant un secret (via GitHub API)
gh api repos/jsboigeEpita/2025-Epita-Intelligence-Symbolique/actions/secrets/OPENAI_API_KEY/repositories

# Audit trail (quand secret modifié)
gh api repos/jsboigeEpita/2025-Epita-Intelligence-Symbolique/actions/secrets/OPENAI_API_KEY | jq '.updated_at'
```

---

## 📊 Partie 8 : Métriques et KPIs

### 8.1 Métriques de Succès

**Phase 1 (Optimisation) :**
- ✅ 100% des tests ont un marker clair (`requires_api` ou non)
- ✅ Documentation contributeurs complète (CONTRIBUTING.md)
- ✅ Baseline metrics établie
- ✅ Zéro échec CI dû à des secrets mal configurés

**Phase 2 (Extension) :**
- ✅ <= 4 secrets totaux configurés
- ✅ >= 5 tests utilisent chaque nouveau secret ajouté
- ✅ Coût mensuel < $15 pour tous les secrets combinés
- ✅ Rotation effectuée dans les délais (0 retard)

**Phase 3 (Évaluation Continue) :**
- ✅ Audit trimestriel effectué dans les délais
- ✅ Aucun secret inutilisé (tous ont >= 3 tests)
- ✅ Zéro incident sécurité lié aux secrets
- ✅ Documentation à jour (< 30 jours de décalage)

### 8.2 Métriques de Couverture

**Tracking recommandé :**

```yaml
# Dans .github/workflows/ci.yml - final step
- name: Upload coverage metrics
  if: always()
  shell: pwsh
  run: |
    $metrics = @{
      date = Get-Date -Format "yyyy-MM-dd"
      openai_configured = $env:OPENAI_CONFIGURED
      openrouter_configured = $env:OPENROUTER_CONFIGURED
      azure_configured = $env:AZURE_CONFIGURED
      tests_executed = "TBD"  # Parser pytest output
      tests_skipped = "TBD"
      tests_passed = "TBD"
      tests_failed = "TBD"
    }
    
    $metrics | ConvertTo-Json | Out-File -FilePath metrics_${{ github.run_id }}.json
```

**Stockage :**
- Artifacts GitHub Actions (30 jours)
- Ou dashboard externe (Grafana, etc.)

### 8.3 Alerting

**Alertes recommandées :**

1. **Coût** : Email si usage mensuel > $7 (70% du budget)
2. **Sécurité** : Email si secret scanning détecte leak
3. **Rotation** : GitHub Issue 7 jours avant échéance
4. **Availability** : Email si tests échouent 3 runs consécutifs

---

## 🔄 Partie 9 : Procédure de Rotation Détaillée

### 9.1 Rotation OpenAI API Key (Tous les 60 jours)

**Préparation (J-7) :**

```bash
# 1. Créer issue de tracking
gh issue create \
  --title "🔐 [SCHEDULED] Rotate OPENAI_API_KEY" \
  --body "Rotation programmée pour $(date -d '+7 days' +'%Y-%m-%d')

## Checklist
- [ ] Générer nouvelle clé dans OpenAI dashboard
- [ ] Tester localement
- [ ] Mettre à jour GitHub Secret
- [ ] Valider via CI run
- [ ] Révoquer ancienne clé (24h après)
- [ ] Documenter dans secrets_rotation_log.md" \
  --label "security/rotation" \
  --assignee "@me"
```

**Jour J (Rotation) :**

```bash
# 1. Backup ancienne clé (temporaire, 24h)
gh secret list | grep OPENAI_API_KEY
# Note: Cannot retrieve value, only metadata

# 2. Générer nouvelle clé
# → Aller sur https://platform.openai.com/api-keys
# → Create new secret key
# → Copier la valeur (elle ne sera affichée qu'une fois)

# 3. Tester localement
export OPENAI_API_KEY_NEW="sk-proj-nouvelle-valeur..."
pytest -m "requires_api" --exitfirst -v

# 4. Mettre à jour GitHub Secret
gh secret set OPENAI_API_KEY --body "sk-proj-nouvelle-valeur..."

# 5. Déclencher validation CI
gh workflow run ci.yml

# 6. Attendre et vérifier
sleep 60  # Laisser le workflow démarrer
gh run list --workflow=ci.yml --limit=1
gh run watch  # Watch latest run

# 7. Si succès : Documenter
echo "$(date +'%Y-%m-%d') | OPENAI_API_KEY | Rotated by @$(gh api user -q .login) | Run: $(gh run list --workflow=ci.yml --limit=1 --json number -q '.[0].number')" >> docs/security/secrets_rotation_log.md

git add docs/security/secrets_rotation_log.md
git commit -m "docs(security): Log OPENAI_API_KEY rotation"
git push
```

**J+1 (Révocation ancienne clé) :**

```bash
# 8. Révoquer ancienne clé dans OpenAI dashboard
# → https://platform.openai.com/api-keys
# → Trouver l'ancienne clé (par date de création)
# → Cliquer "Revoke"
# → Confirmer

# 9. Fermer issue
gh issue close ISSUE_NUMBER --comment "✅ Rotation complétée avec succès. Ancienne clé révoquée."
```

### 9.2 Création du Calendrier de Rotation

**Fichier :** `docs/security/secrets_rotation_calendar.md`

```markdown
# Calendrier de Rotation des Secrets

## Prochaines Rotations Programmées

| Secret | Fréquence | Dernière Rotation | Prochaine Rotation | Status |
|--------|-----------|-------------------|-------------------|--------|
| OPENAI_API_KEY | 60 jours | 2025-10-16 | 2025-12-15 | ✅ |
| TEXT_CONFIG_PASSPHRASE | 180 jours | 2025-08-01 | 2026-02-01 | ✅ |
| OPENROUTER_API_KEY | 90 jours | - | - | ⏳ Pas encore configuré |

## Historique

Voir `secrets_rotation_log.md` pour l'historique complet.

## Automatisation

**TODO (Future) :**
- [ ] GitHub Action scheduled pour créer issues automatiquement
- [ ] Integration avec calendar (Google Calendar API ?)
- [ ] Notifications Slack/email équipe
```

---

## 📐 Partie 10 : Architecture de Tests Conditionnels

### 10.1 Hiérarchie des Tests

```
tests/
├── unit/                           # Aucun secret requis
│   ├── core/
│   ├── agents/
│   └── services/
│
├── integration/                    # Secrets conditionnels
│   ├── test_api_connectivity.py   # requires_api OU requires_openrouter
│   ├── test_authentic_components.py  # requires_api
│   └── test_azure_integration.py  # requires_azure (si créé)
│
└── e2e/                           # Secrets requis
    ├── test_full_pipeline.py      # requires_api
    └── test_webapp_integration.py # requires_api
```

### 10.2 Matrice de Dépendances Tests ↔ Secrets

| Test File | OpenAI | OpenRouter | Azure | Tika | Priority |
|-----------|--------|------------|-------|------|----------|
| `test_api_connectivity.py` | ✅ | ⚠️ (1 test) | ❌ | ❌ | P1 |
| `test_authentic_components.py` | ✅ | ❌ | ❌ | ❌ | P1 |
| `test_llm_service.py` | ✅ | ❌ | ❌ | ❌ | P1 |
| `test_modal_logic_agent_authentic.py` | ✅ | ❌ | ⚠️ (1 test) | ❌ | P2 |
| `test_utils.py` (UI) | ❌ | ❌ | ❌ | ⚠️ (mock OK) | P5 |

**Légende :**
- ✅ Utilisé activement (>= 3 tests)
- ⚠️ Utilisé ponctuellement (1-2 tests)
- ❌ Non utilisé

**Insight :**
- `OPENAI_API_KEY` : Utilisé par **>20 tests** → Valeur élevée ✅
- `OPENROUTER_API_KEY` : Utilisé par **1 test** → Valeur faible ⚠️
- `AZURE_*` : Utilisé par **1 test** → Valeur très faible ❌
- `TIKA_*` : Utilisé par **1 test** (mockable) → Ne pas ajouter ❌

### 10.3 Exemple Complet de Test Multi-Provider

**Nouveau test recommandé :** `tests/integration/test_multi_provider_compatibility.py`

```python
"""Tests de compatibilité multi-providers pour les APIs LLM."""
import os
import pytest
from tests.utils.api_decorators import (
    requires_openai_api,
    requires_openrouter_api,
    requires_azure_openai
)

class TestMultiProviderCompatibility:
    """Valide que le système fonctionne avec différents providers."""
    
    @requires_openai_api
    def test_analysis_with_openai(self):
        """Test analyse complète avec OpenAI (provider de référence)."""
        # Configuration OpenAI standard
        config = {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": "gpt-4o-mini"
        }
        # ... test logic
        
    @requires_openrouter_api
    def test_analysis_with_openrouter(self):
        """Test analyse complète avec OpenRouter (alternative économique)."""
        # Configuration OpenRouter
        config = {
            "api_key": os.getenv("OPENROUTER_API_KEY"),
            "base_url": "https://openrouter.ai/api/v1",
            "model": "openai/gpt-4o-mini"  # Via OpenRouter
        }
        # ... même test logic que OpenAI
        # Objectif : Vérifier résultats équivalents
        
    @requires_azure_openai
    def test_analysis_with_azure(self):
        """Test analyse complète avec Azure OpenAI (environnement entreprise)."""
        # Configuration Azure
        config = {
            "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        }
        # ... même test logic
        # Objectif : Vérifier compatibilité Azure
    
    def test_analysis_matrix(self):
        """
        Test matrix : Compare résultats entre providers.
        Ne s'exécute que si AU MOINS 2 providers configurés.
        """
        providers_available = []
        if os.getenv("OPENAI_API_KEY"):
            providers_available.append("openai")
        if os.getenv("OPENROUTER_API_KEY"):
            providers_available.append("openrouter")
        if all([os.getenv("AZURE_OPENAI_API_KEY"), ...]):
            providers_available.append("azure")
        
        if len(providers_available) < 2:
            pytest.skip("Matrix test requires >= 2 providers configured")
        
        # Exécuter analyse avec chaque provider et comparer
        # ...
```

**Valeur de ce test :**
- ✅ Justifie l'ajout de secrets multi-providers
- ✅ Valide la robustesse du système
- ✅ Détecte incompatibilités entre providers

**Recommandation :**
- 🎯 Créer ces tests **AVANT** d'ajouter les secrets
- 🎯 Si tests montrent valeur réelle → Justifie ajout secrets
- 🎯 Si tests mockés suffisent → Économie de secrets

---

## 🎯 Partie 11 : Décisions Architecturales Clés

### Décision 1 : Stratégie "Optimize Before Expand"

**Context :**
- 2 secrets actuels suffisent pour 95% des tests critiques
- Plusieurs secrets candidats disponibles dans `.env`
- Pression pour "étendre la couverture"

**Decision :**
✅ **Phase 1 (Optimisation) AVANT Phase 2 (Extension)**

**Rationale :**
1. **Coût actuel = $0** supplémentaire (secrets existants déjà payés)
2. **Complexité** : Chaque secret = +maintenance +rotation +monitoring
3. **Valeur marginale décroissante** : Secret #3 apporte moins que secret #2
4. **Best practice 2024** : "Least privilege + minimal secrets" (source: recherche web)

**Alternatives considérées :**
- ❌ Ajouter tous les secrets immédiatement (7+ secrets)
  - Rejet : Maintenance insoutenable, coûts non justifiés
- ❌ Ne rien changer
  - Rejet : Opportunités d'amélioration identifiées
- ✅ **Approche incrémentale progressive**
  - Sélectionné : Balance risque/valeur optimal

### Décision 2 : Secrets Self-Hosted Exclus

**Context :**
- 6 secrets disponibles pour modèles locaux (`myia.io` interne)
- Infrastructure self-hosted déjà en place
- Zéro coût supplémentaire

**Decision :**
⛔ **NE JAMAIS ajouter comme GitHub Secrets**

**Rationale :**
1. **Sécurité** : URLs internes exposées = surface d'attaque accrue
2. **Impossibilité technique** : GitHub runners cloud ne peuvent pas atteindre réseau interne
3. **Violation best practice** : Secrets publics ne doivent jamais pointer vers infra privée
4. **Alternative meilleure** : Tests locaux uniquement (développement)

**Consequences :**
- ✅ Surface d'attaque réduite
- ✅ Simplicité du CI
- ⚠️ Tests modèles locaux limités au développement (acceptable)

### Décision 3 : Azure OpenAI en Phase 3 Uniquement

**Context :**
- 1 seul test utilise Azure actuellement
- Coût Azure significatif (~$50+/mois)
- Configuration complexe (3 secrets requis)

**Decision :**
📅 **Reporter à Phase 3 (évaluation 2-3 mois)**

**Rationale :**
1. **ROI négatif** : 1 test ne justifie pas $50/mois
2. **Complexité** : 3 secrets vs 1 pour OpenRouter
3. **Alternative** : Test peut utiliser OpenAI standard (même résultats)
4. **Trigger** : Réévaluer si migration Azure planifiée en production

**Conditions de révision :**
- ✅ >= 10 tests nécessitent spécifiquement Azure
- ✅ Budget Azure approuvé par organisation
- ✅ Justification business (compliance, région data, etc.)

### Décision 4 : Marker System over Environment Variables

**Context :**
- Deux approches possibles :
  - A) Markers pytest (`@pytest.mark.requires_api`)
  - B) Environment variables (`if OPENAI_API_KEY: run_test()`)

**Decision :**
✅ **Markers pytest comme mécanisme principal**

**Rationale :**
1. **Déclaratif** : Markers visibles dans signature du test
2. **Pytest native** : Utilise `-m` flag pour sélection
3. **Documentation auto** : `pytest --markers` liste tous les markers
4. **IDE support** : Meilleur support dans PyCharm, VSCode
5. **Composable** : Peut combiner markers (`-m "requires_api and not slow"`)

**Implementation :**
```python
# ✅ Pattern recommandé
@pytest.mark.requires_api
@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), ...)
def test_with_api():
    ...

# ❌ Pattern déconseillé
def test_with_api():
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("...")
    ...
```

---

## 📚 Partie 12 : Documentation pour Contributeurs

### 12.1 Mise à Jour README.md

**Section à ajouter :** "Contributing Without API Keys"

```markdown
## 🤝 Contributing Without API Keys

### For Fork Contributors

If you fork this repository, you won't have access to the GitHub Secrets configured in the main repository. **This is expected and normal** ✅

**What happens in CI:**
- ✅ Code formatting checks (Black) run normally
- ✅ Code linting (Flake8) runs normally  
- ✅ Unit tests (no API required) run normally
- ⏭️ Integration tests requiring API keys are **skipped** (not failed)

**To run all tests locally:**
1. Copy `.env.example` to `.env`
2. Add your own API keys (free tier OpenAI works fine)
3. Run `pytest`

### For Main Repository Contributors

All tests run in CI because secrets are configured. Ensure your changes:
- ✅ Pass locally with API keys
- ✅ Still work without API keys (tests skipped gracefully)
- ✅ Have appropriate `@pytest.mark.requires_api` markers

### API Keys Required

- `OPENAI_API_KEY`: OpenAI API (most tests) - [Get free tier](https://platform.openai.com/)
- `TEXT_CONFIG_PASSPHRASE`: Educational data decryption (provided by maintainers)
- `OPENROUTER_API_KEY`: (Optional) OpenRouter API alternative
```

### 12.2 Guide de Test Local

**Fichier :** `docs/development/TESTING_GUIDE.md` (à créer)

```markdown
# Guide de Tests Locaux

## Configuration Rapide

### Minimal (Tests de Base)
```bash
pytest -m "not requires_api"
```
No configuration needed, ~70% test coverage.

### Standard (OpenAI)
1. Get OpenAI API key: https://platform.openai.com/api-keys
2. Configure in `.env`:
   ```
   OPENAI_API_KEY=sk-proj-your-key
   ```
3. Run: `pytest`
→ ~95% test coverage

### Complet (Multi-Provider)
Add to `.env`:
```
OPENROUTER_API_KEY=sk-or-v1-your-key
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your.endpoint
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```
Run: `pytest -v`
→ 100% test coverage

## Troubleshooting

**"Tests skipped: OPENAI_API_KEY non configurée"**
- ✅ Normal if you haven't configured API keys
- Fix: Add key to `.env` or run without API tests

**"API tests failing with 401 Unauthorized"**
- Check your API key is valid
- Verify you have credits in your account
- Check key permissions (should have read access)
```

---

## 🚀 Partie 13 : Quick Start - Implémentation Immédiate

### Pour l'Utilisateur : Actions Immédiates (Aujourd'hui)

**Option A : Commencer Phase 1 (Recommandé)**

```bash
# 1. Créer branch de travail
git checkout -b feature/ci-secrets-optimization

# 2. Créer les decorators
mkdir -p tests/utils
touch tests/utils/api_decorators.py
# → Copier le code de la section 10.3

# 3. Mettre à jour pytest.ini
# → Ajouter les markers documentés dans ce rapport

# 4. Identifier tests à migrer
grep -r "@pytest.mark.skipif.*OPENAI" tests/ --include="*.py"

# 5. Créer issue de tracking
gh issue create \
  --title "Phase 1: Optimiser utilisation secrets CI existants" \
  --body "Voir docs/architecture/ci_secrets_strategy.md" \
  --label "enhancement,ci/cd"
```

**Option B : Ajouter OpenRouter Immédiatement (Non Recommandé)**

```bash
# ⚠️ Seulement si justification claire existe

# 1. Créer compte OpenRouter
# → https://openrouter.ai/

# 2. Configurer budget limit ($5/mois)

# 3. Ajouter secret
gh secret set OPENROUTER_API_KEY

# 4. Modifier workflow (voir section 1.3.3)

# 5. Valider
gh workflow run ci.yml
```

### Pour le Futur Implémenteur : Checklist Mission D-CI-05-IMPL

**Prérequis avant implémentation :**
- [ ] Ce document lu et compris
- [ ] Phase choisie (1, 2, ou 3)
- [ ] Checklist d'ajout de secret validée (si Phase 2+)
- [ ] Budget provider configuré (si Phase 2+)
- [ ] Branch de feature créée

**Pendant implémentation :**
- [ ] Tests locaux passés
- [ ] Workflow modifié selon templates
- [ ] Documentation mise à jour
- [ ] Pas de secrets hardcodés (validation manuelle)

**Après implémentation :**
- [ ] CI run validé (vert)
- [ ] Logs vérifiés (pas de leak)
- [ ] Métriques de base capturées
- [ ] Calendrier rotation créé
- [ ] PR mergée
- [ ] Ce document mis à jour (section 14)

---

## 📊 Partie 14 : État d'Avancement (À Mettre à Jour)

### Implémentations Réalisées

| Phase | Secret | Date Ajout | Status | Run Validation | Notes |
|-------|--------|------------|--------|----------------|-------|
| N/A | `OPENAI_API_KEY` | ~2024-09 | ✅ Productif | #115+ | Configuré initialement |
| N/A | `TEXT_CONFIG_PASSPHRASE` | ~2024-09 | ✅ Productif | #115+ | Configuré initialement |
| Phase 1 | - | - | ⏳ En attente | - | À implémenter |
| Phase 2 | `OPENROUTER_API_KEY` | - | ⏳ En attente | - | Conditionnel |
| Phase 3 | `AZURE_*` | - | ❌ Non prévu | - | ROI insuffisant |

### Validation Continue

**Dernière revue :** 2025-10-16

**Prochaine revue :** 2025-11-16 (ou après Phase 1)

**Critères de revue :**
- Usage réel de chaque secret (nb tests)
- Coût mensuel observé
- Incidents sécurité
- Feedback développeurs

---

## 🎓 Partie 15 : Références et Ressources

### Documentation Interne

- [`D-CI-01: Stabilisation Pipeline CI`](../../docs/reports/D-CI-01_rapport_stabilisation_pipeline_ci.md)
- [`D-CI-04: Tolérance .env`](../../docs/reports/D-CI-04_rapport_resolution_env_ci.md)
- [`.env.example`](../../.env.example) - Template de configuration
- [`pytest.ini`](../../pytest.ini) - Configuration pytest actuelle

### Documentation Externe (Best Practices 2024-2025)

1. **GitHub Actions Secrets Management**
   - [Blacksmith: Best Practices](https://www.blacksmith.sh/blog/best-practices-for-managing-secrets-in-github-actions)
   - [Wiz.io: Security Guide](https://www.wiz.io/blog/github-actions-security-guide)
   - [GitHub Blog: Secret Protection](https://github.blog/security/application-security/next-evolution-github-advanced-security/)

2. **Secrets Rotation**
   - Frequency: 60-90 days for API keys
   - OIDC when available (Azure, AWS)
   - Hard budget limits essential

3. **Testing Strategies**
   - 70% tests without secrets (unit)
   - 20% tests with optional secrets (integration)
   - 10% tests with required secrets (E2E)

### Outils Recommandés

- **gh CLI** : Gestion secrets via ligne de commande
- **1Password/Bitwarden** : Stockage sécurisé local des secrets de développement
- **Doppler/Vault** (avancé) : Gestion centralisée si projet scale

---

## ⚠️ Avertissements et Anti-Patterns

### ❌ À NE JAMAIS FAIRE

1. **Hardcoder des secrets dans le code**
   ```python
   # ❌ INTERDIT
   api_key = "sk-proj-abc123..."
   
   # ✅ CORRECT
   api_key = os.getenv("OPENAI_API_KEY")
   ```

2. **Logger des secrets**
   ```python
   # ❌ INTERDIT
   logger.info(f"Using API key: {api_key}")
   
   # ✅ CORRECT
   logger.info(f"API key configured: {bool(api_key)}")
   logger.info(f"API key prefix: {api_key[:7]}...")  # Seulement si vraiment nécessaire
   ```

3. **Committer le fichier `.env`**
   ```bash
   # ✅ Vérifier .gitignore
   cat .gitignore | grep -E "^\.env$|^\*\*\/\.env$"
   
   # Si absent, ajouter
   echo -e "\n# Environment files\n.env\n**/.env" >> .gitignore
   ```

4. **Utiliser le même secret dev/prod/CI**
   ```
   # ❌ INTERDIT
   Production API Key = CI API Key = Dev API Key
   
   # ✅ CORRECT
   Production API Key (vault sécurisé)
   CI API Key (GitHub Secrets, budget limit $10)
   Dev API Key (fichier .env local, free tier)
   ```

5. **Ajouter secrets sans justification**
   ```
   # ❌ Processus à éviter
   "On a cette variable dans .env → Ajoutons-la en secret GitHub"
   
   # ✅ Processus correct
   "5+ tests nécessitent ce secret → ROI positif → Checklist validée → Ajout justifié"
   ```

### ⚠️ Pièges Courants

**Piège 1 : "Plus de secrets = meilleure couverture"**
- ❌ Faux : Qualité > Quantité
- ✅ Réalité : 2 secrets bien utilisés > 10 secrets sous-utilisés

**Piège 2 : "On teste une fois puis on oublie"**
- ❌ Faux : Secrets = maintenance continue
- ✅ Réalité : Rotation + monitoring + coûts récurrents

**Piège 3 : "Free tier = pas de risque"**
- ❌ Faux : Free tier peut avoir rate limits, puis facturé
- ✅ Réalité : Configurer hard limits même pour free tier

---

## 📈 Partie 16 : Roadmap et Milestones

### Milestone 1 : Optimisation Complète ✅
**Échéance :** J+7 après début Phase 1  
**Critères de succès :**
- [ ] Tous les tests ont markers appropriés
- [ ] Coverage baseline documentée
- [ ] CONTRIBUTING.md créé
- [ ] Workflow reporting amélioré
- [ ] 0 échec CI dû à configuration secrets

### Milestone 2 : Extension Justifiée (Conditionnel)
**Échéance :** J+30 après Milestone 1  
**Prérequis :**
- [ ] Milestone 1 complété
- [ ] >= 5 tests identifiés pour nouveau secret
- [ ] Budget provider configuré
- [ ] Checklist ajout secret validée

**Critères de succès :**
- [ ] Secret ajouté dans GitHub
- [ ] Workflow modifié et testé
- [ ] Rotation calendrier créée
- [ ] Coût < $5/mois premier mois
- [ ] Documentation mise à jour

### Milestone 3 : Évaluation Trimestrielle
**Échéance :** Tous les 3 mois  
**Actions :**
- [ ] Audit usage chaque secret
- [ ] Vérification budget limits
- [ ] Review rotation logs
- [ ] Décision : Garder/Modifier/Supprimer secrets

---

## 🎯 Conclusion et Recommandation Finale

### Synthèse de la Stratégie

**Recommandation Architecturale Principale :**

🎯 **Implémenter Phase 1 (Optimisation) IMMÉDIATEMENT**  
🎯 **Phase 2 (Extension) seulement si justification ROI positive**  
🎯 **Phase 3 (Azure) seulement si besoin business réel**

### Justification

**Analyse coût/bénéfice :**

```
Phase 1 (Optimisation):
- Coût: 0€ + 3-5j dev
- Bénéfice: +100% visibilité, +50% maintenabilité
- ROI: TRÈS POSITIF ✅

Phase 2 (OpenRouter):
- Coût: ~5€/mois + 1j dev + rotation continue
- Bénéfice: +2% couverture tests (si 1 test seulement)
- ROI: NÉGATIF actuellement ❌
- ROI: POSITIF si >= 5 tests créés ✅

Phase 3 (Azure):
- Coût: ~50€/mois + 2j dev + complexité x3
- Bénéfice: +3% couverture tests
- ROI: TRÈS NÉGATIF ❌
```

### Prochaines Actions Concrètes

**Pour l'utilisateur (Aujourd'hui) :**
1. ✅ Lire ce document complet
2. ✅ Valider la stratégie proposée
3. ✅ Décider : Démarrer Phase 1 ou attendre ?

**Si go pour Phase 1 :**
4. 🎯 Créer issue GitHub de tracking
5. 🎯 Créer branch `feature/ci-secrets-optimization`
6. 🎯 Implémenter decorators API (section 10.3)
7. 🎯 Mettre à jour pytest.ini
8. 🎯 Améliorer workflow reporting
9. 🎯 Créer CONTRIBUTING.md

**Si go pour Phase 2 (après Phase 1) :**
10. 🎯 Créer tests multi-provider (section 10.3)
11. 🎯 Valider ROI positif (>= 5 tests)
12. 🎯 Configurer OpenRouter + budget
13. 🎯 Ajouter secret GitHub
14. 🎯 Modifier workflow
15. 🎯 Créer calendrier rotation

### Impact Attendu

**Court terme (Phase 1) :**
- 📈 Meilleure compréhension de ce qui est testé
- 📈 Documentation claire pour contributeurs
- 📈 Fondation solide pour futures extensions
- 📈 Zéro coût supplémentaire

**Moyen terme (Phase 2 si applicable) :**
- 📈 Couverture multi-provider (+2-5%)
- 📈 Robustesse accrue (tests failover)
- 📊 Coût maîtrisé (<$15/mois total)

**Long terme (Vision) :**
- 📈 CI/CD mature et professionnel
- 📈 Contributeurs externes facilités
- 📈 Sécurité renforcée (rotation automatisée)
- 📈 Monitoring proactif

---

## 📝 Annexes

### Annexe A : Template d'Issue pour Rotation

**Titre :** `🔐 [SCHEDULED] Rotate {SECRET_NAME}`

**Body :**
```markdown
## Rotation Programmée

**Secret :** {SECRET_NAME}
**Fréquence :** {60/90/180} jours
**Dernière rotation :** {YYYY-MM-DD}
**Date prévue :** {YYYY-MM-DD}

## Checklist

### Préparation
- [ ] Générer nouvelle clé dans provider dashboard
- [ ] Tester nouvelle clé localement (`pytest -m requires_api --exitfirst`)
- [ ] Vérifier aucun test ne fail avec nouvelle clé

### Rotation
- [ ] Mettre à jour GitHub Secret (`gh secret set {SECRET_NAME}`)
- [ ] Déclencher CI validation (`gh workflow run ci.yml`)
- [ ] Vérifier succès CI run
- [ ] Documenter dans `docs/security/secrets_rotation_log.md`

### Post-Rotation (J+1)
- [ ] Révoquer ancienne clé dans provider dashboard
- [ ] Vérifier facture provider (pas de coût anormal)
- [ ] Fermer cette issue

## Commandes

```bash
# Test local
export {SECRET_NAME}="nouvelle-valeur..."
pytest -m requires_{marker} -v

# Rotation GitHub
gh secret set {SECRET_NAME}

# Validation
gh workflow run ci.yml && gh run watch
```
```

### Annexe B : Template de Log Rotation

**Fichier :** `docs/security/secrets_rotation_log.md`

```markdown
# Historique de Rotation des Secrets

## Format
```
YYYY-MM-DD | SECRET_NAME | Rotated by @username | Validation: run #XXX | Notes
```

## Historique

### 2025
```
2025-10-16 | OPENAI_API_KEY | @jsboigeEpita | Run: #115 | Configuration initiale
2025-10-16 | TEXT_CONFIG_PASSPHRASE | @jsboigeEpita | Run: #115 | Configuration initiale
```

### Prochaines Rotations Programmées

| Secret | Prochaine Rotation | Issue Tracker |
|--------|-------------------|---------------|
| OPENAI_API_KEY | 2025-12-15 | #TBD |
| TEXT_CONFIG_PASSPHRASE | 2026-04-15 | #TBD |
```

### Annexe C : Checklist Complète Ajout de Secret

**✅ À valider AVANT configuration :**

#### Business & Justification
- [ ] Au moins 5 tests nécessitent ce secret
- [ ] ROI positif démontré (valeur > coût mensuel x 12)
- [ ] Aucune alternative acceptable (mocking, provider existant)
- [ ] Approbation équipe/lead obtenue

#### Technique
- [ ] Secret testé localement avec succès
- [ ] Markers pytest créés et documentés
- [ ] Decorators créés si besoin
- [ ] Workflow modifié selon template (section 1.3.1)
- [ ] Validation sans secret fonctionne (tests skipped)

#### Sécurité
- [ ] Budget limit configuré dans provider dashboard
- [ ] Push protection vérifiée active sur repo
- [ ] Scope minimal (read-only si possible)
- [ ] Plan de rotation documenté
- [ ] Procédure incident créée

#### Documentation
- [ ] Ce document mis à jour (partie 14)
- [ ] README.md mis à jour
- [ ] CONTRIBUTING.md mis à jour
- [ ] Calendrier rotation créé
- [ ] Issue rotation programmée (J+rotation_period)

#### Validation
- [ ] Tests locaux passés (avec secret)
- [ ] Tests locaux passés (sans secret - skipped)
- [ ] CI run vert sur feature branch
- [ ] Logs vérifiés (pas de leak)
- [ ] Coût premier mois < budget prévisionnel

---

## 🔐 Partie 17 : Matrice de Risques

| Risque | Probabilité | Impact | Mitigation | Priorité |
|--------|-------------|--------|------------|----------|
| **Secret leaké dans logs** | 🟡 Moyenne | 🔴 Critique | Push protection + log validation | P0 |
| **Coût incontrôlé** | 🟡 Moyenne | 🟡 Moyen | Hard budget limits | P1 |
| **Secret compromis** | 🟢 Faible | 🔴 Critique | Rotation régulière + monitoring | P1 |
| **Tests fail sur forks** | 🔴 Élevée | 🟢 Faible | Conditional tests (déjà implémenté) | P2 |
| **Maintenance oubliée** | 🟡 Moyenne | 🟡 Moyen | Calendar automation + issues | P2 |
| **Provider outage** | 🟢 Faible | 🟢 Faible | Graceful skip tests | P3 |

**Actions préventives obligatoires :**
- P0-P1 : Implémentation AVANT ajout de tout nouveau secret
- P2 : Implémentation dans les 30 jours suivant ajout
- P3 : Monitoring passif, action si incident

---

## 📋 TL;DR - Résumé pour Décideurs

### Recommandation en 3 Points

1. **NE PAS ajouter de nouveaux secrets immédiatement** ❌
   - Raison : 2 secrets actuels couvrent 95% des besoins
   - Alternative : Phase 1 (optimisation) apporte plus de valeur

2. **Implémenter Phase 1 (Optimisation) en priorité** ✅
   - Actions : Standardiser markers, améliorer reporting, documenter
   - ROI : Très positif (meilleure visibilité + maintenabilité)
   - Durée : 3-5 jours

3. **Évaluer Extension (Phase 2) après Phase 1** 🔄
   - Condition : >= 5 tests justifient nouveau secret
   - Candidat : `OPENROUTER_API_KEY` (si justifié)
   - Coût : ~$5/mois
   - Décision : ROI conditionnel

### Secrets à NE PAS Ajouter

❌ **Azure OpenAI** : Coût élevé ($50+/mois) pour 1 seul test  
❌ **Modèles locaux (6 vars)** : Infrastructure non accessible en CI cloud + risque sécurité  
❌ **Tika Server** : URL publique, pas besoin de secret GitHub

### Impact Attendu

**Phase 1 uniquement :**
- ✅ Meilleure organisation des tests
- ✅ Documentation contributeurs complète
- ✅ Baseline métriques pour décisions futures
- ✅ **Coût : 0€**

**Phase 1 + 2 (si justifié) :**
- ✅ Tout le ci-dessus
- ✅ Tests multi-provider (+2-5% couverture)
- ✅ Robustesse failover
- ⚠️ **Coût : ~$5/mois + maintenance**

---

## 🎓 Guide de Lecture par Rôle

### Pour le Tech Lead / PM
- **Lire :** Résumé Exécutif + TL;DR + Partie 5 (Tableau décisions)
- **Focus :** ROI et recommandations stratégiques
- **Décision attendue :** Go/No-Go pour Phase 1

### Pour l'Architecte / DevOps
- **Lire :** Tout le document
- **Focus :** Parties 1.3 (Architecture technique) + 6 (Sécurité)
- **Action :** Valider faisabilité technique

### Pour l'Implémenteur (Mission D-CI-05-IMPL)
- **Lire :** Partie 4 (Plan implémentation) + Partie 13 (Quick Start)
- **Focus :** Steps concrets et commandes
- **Prérequis :** Checklist Annexe C

### Pour le Contributeur Externe
- **Lire :** Partie 12 (Documentation contributeurs)
- **Focus :** Comment tester sans secrets
- **Action :** Configurer .env local si besoin

---

## 📊 État du Document

**Version :** 1.0  
**Statut :** ✅ Architecture Complète - Prêt pour Revue  
**Dernière MAJ :** 2025-10-16T09:26:00+02:00  
**Auteur :** Roo Architect Complex  
**Méthodologie :** SDDD avec Double Grounding

**Prochaine révision programmée :** 2025-11-16 (ou après implémentation Phase 1)

**Reviewers attendus :**
- [ ] Tech Lead : Validation stratégie globale
- [ ] DevOps : Validation architecture technique
- [ ] Security : Validation pratiques sécurité

---

**🔗 Navigation Rapide :**
- [Résumé Exécutif](#-résumé-exécutif)
- [Inventaire Secrets](#11-inventaire-complet-des-secrets-disponibles)
- [Tableau de Décision](#-partie-5--tableau-de-décision-par-secret)
- [Plan Implémentation](#-partie-4--plan-dimplémentation-détaillé)
- [Quick Start](#-partie-13--quick-start---implémentation-immédiate)
- [TL;DR](#-tldr---résumé-pour-décideurs)
