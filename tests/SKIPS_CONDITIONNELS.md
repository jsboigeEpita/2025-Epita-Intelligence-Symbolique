# Documentation des Skips Conditionnels - Tests

Ce document documente tous les tests skippés conditionnellement, leurs raisons, et les conditions de réactivation.

**Dernière mise à jour** : 2025-10-16 (Phase D3.1.1-Batch2)

---

## 1. Tests PyTorch - Windows (2 tests)

### Tests concernés

1. `tests/unit/argumentation_analysis/test_baselogicagent_import_fix.py::test_service_manager_can_import_baselogicagent`
2. `tests/unit/argumentation_analysis/test_baselogicagent_import_fix.py::TestBaseLogicAgentImportFix::test_complete_import_resolution`

### Raison du skip

**Problème** : PyTorch `fbgemm.dll` ne peut pas charger ses dépendances sur Windows

**Erreur** : `OSError: [WinError 182] Le système d'exploitation ne peut pas exécuter %1. Error loading "...\torch\lib\fbgemm.dll" or one of its dependencies.`

**Cause racine** : 
- `fbgemm.dll` (Facebook's GEMM library) nécessite Visual C++ Redistributable
- Les dépendances natives Windows (vcruntime140.dll, msvcp140.dll) sont manquantes ou incompatibles
- Problème spécifique à Windows, les tests fonctionnent sous Linux

### Condition du skip

```python
@pytest.mark.skipif(
    sys.platform == "win32" and not PYTORCH_AVAILABLE,
    reason=f"PyTorch fbgemm.dll issue on Windows - {PYTORCH_ERROR}"
)
```

Le test est skippé si :
- Plateforme = Windows (`win32`)
- ET PyTorch ne peut pas être importé (OSError lors de `import torch`)

### Conditions de réactivation

**Option 1 : Installer Visual C++ Redistributable (recommandé)**
1. Télécharger : https://aka.ms/vs/17/release/vc_redist.x64.exe
2. Installer Visual C++ Redistributable 2015-2022 (x64)
3. Redémarrer le système
4. Vérifier : `python -c "import torch; print(torch.__version__)"`

**Option 2 : Réinstaller PyTorch CPU-only**
```bash
pip uninstall torch torchvision torchaudio -y
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

**Option 3 : Lazy import dans le code (fix définitif)**
Modifier `plugins/AnalysisToolsPlugin/logic/contextual_fallacy_analyzer.py` pour importer PyTorch uniquement quand nécessaire avec fallback gracieux.

**Option 4 : Migration Linux CI**
Exécuter les tests sur Linux où PyTorch fonctionne nativement.

### Impact

- **Tests affectés** : 2 tests d'import BaseLogicAgent
- **Fonctionnalités** : Tests de résolution des cycles d'import ServiceManager → BaseLogicAgent → PyTorch
- **Criticité** : Moyenne (tests d'intégration, pas de perte de fonctionnalité runtime)

---

## 2. Tests API Configuration (3 tests)

### Tests concernés

1. `tests/unit/api/test_api_direct_simple.py::test_environment_setup`
2. `tests/unit/api/test_api_direct_simple.py::test_api_startup_and_basic_functionality`
3. `tests/unit/api/test_api_direct.py::test_api_startup_and_basic_functionality`

### Raison du skip

**Problème** : Tests nécessitent environnement complet avec clé API OpenAI et fichiers de configuration

**Erreur(s)** :
- `AssertionError: OPENAI_API_KEY n'a pas été chargée dans l'environnement de test`
- `AssertionError: Fichier manquant: api/main_simple.py`

**Cause racine** :
1. Variable d'environnement `OPENAI_API_KEY` non définie ou invalide (<20 caractères)
2. Fichiers API manquants :
   - `api/main_simple.py`, `api/endpoints_simple.py`, `api/dependencies_simple.py` (test_api_direct_simple.py)
   - `api/main.py`, `api/endpoints.py`, `api/dependencies.py` (test_api_direct.py)
3. Les tests lancent un serveur FastAPI réel via subprocess et nécessitent l'infrastructure complète

### Condition du skip

```python
API_ENVIRONMENT_AVAILABLE = True
API_ENVIRONMENT_ERROR = None
API_FILES_REQUIRED = ["api/main.py", "api/endpoints.py", "api/dependencies.py"]

try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or len(api_key) < 20:
        API_ENVIRONMENT_AVAILABLE = False
        API_ENVIRONMENT_ERROR = "OPENAI_API_KEY non configurée ou invalide"
    
    missing_files = [f for f in API_FILES_REQUIRED if not Path(f).exists()]
    if missing_files:
        API_ENVIRONMENT_AVAILABLE = False
        API_ENVIRONMENT_ERROR = f"Fichiers API manquants: {', '.join(missing_files)}"
except Exception as e:
    API_ENVIRONMENT_AVAILABLE = False
    API_ENVIRONMENT_ERROR = str(e)

@pytest.mark.skipif(
    not API_ENVIRONMENT_AVAILABLE,
    reason=f"API test environment not configured - {API_ENVIRONMENT_ERROR}"
)
```

Le test est skippé si :
- `OPENAI_API_KEY` absente, vide ou <20 caractères
- OU fichiers API requis manquants
- OU erreur lors de la vérification

### Conditions de réactivation

**Étape 1 : Configurer OPENAI_API_KEY**

Créer/modifier le fichier `.env` à la racine du projet :
```bash
OPENAI_API_KEY=sk-votre-cle-api-openai-ici
```

Ou définir la variable d'environnement système :
```bash
# Windows
set OPENAI_API_KEY=sk-votre-cle-api-openai-ici

# Linux/Mac
export OPENAI_API_KEY=sk-votre-cle-api-openai-ici
```

**Étape 2 : Vérifier les fichiers API**

S'assurer que les fichiers suivants existent :
- `api/main.py` ou `api/main_simple.py`
- `api/endpoints.py` ou `api/endpoints_simple.py`
- `api/dependencies.py` ou `api/dependencies_simple.py`

Si les noms diffèrent, créer des liens symboliques ou corriger les noms attendus dans les tests.

**Étape 3 : Installer les dépendances**

```bash
pip install fastapi uvicorn[standard] requests python-dotenv
```

**Étape 4 : Tester manuellement**

```bash
# Test import
python -c "from api.main import app; print('OK')"

# Test démarrage serveur
python -m uvicorn api.main:app --host 127.0.0.1 --port 8001
```

**Étape 5 : Configurer pytest pour charger .env**

Ajouter dans `tests/conftest.py` si nécessaire :
```python
@pytest.fixture(scope="session", autouse=True)
def load_environment_variables():
    """Charge .env pour tous les tests."""
    from dotenv import load_dotenv
    load_dotenv(override=True)
    yield
```

### Impact

- **Tests affectés** : 3 tests de validation API FastAPI avec GPT-4o-mini
- **Fonctionnalités** : Tests d'intégration E2E de l'API de détection de sophismes
- **Criticité** : Moyenne (tests d'intégration, l'API peut fonctionner même si tests skippés)

---

## 3. Statistiques Globales

| Catégorie | Nombre tests | Plateforme | Dépendances | Criticité |
|-----------|--------------|------------|-------------|-----------|
| PyTorch Windows | 2 | Windows only | PyTorch + MSVC | Moyenne |
| API Config | 3 | Toutes | OPENAI_API_KEY + fichiers | Moyenne |
| **TOTAL** | **5** | - | - | - |

---

## 4. Workflow de Réactivation Globale

### Pour développeur local

1. **Installer Visual C++ Redistributable** (fix PyTorch)
2. **Configurer .env** avec `OPENAI_API_KEY`
3. **Vérifier structure API** (fichiers présents)
4. **Installer dépendances** : `pip install -r requirements.txt`
5. **Tester** : `pytest tests/unit/argumentation_analysis/test_baselogicagent_import_fix.py tests/unit/api/ -v`

### Pour CI/CD

**Option 1 : CI Linux (recommandé)**
- Pas de problème fbgemm.dll sous Linux
- Configure `OPENAI_API_KEY` via secrets GitHub
- Tests réactivés automatiquement

**Option 2 : CI Windows**
- Installer VC++ Redistributable dans image Docker/VM
- Configure `OPENAI_API_KEY` via secrets
- Vérifier structure fichiers API

---

## 5. Historique des Modifications

| Date | Version | Modification | Commit |
|------|---------|--------------|--------|
| 2025-10-16 | D3.1.1-Batch2 | Ajout skips PyTorch Windows (2 tests) | 8971dc6b |
| 2025-10-16 | D3.1.1-Batch2 | Ajout skips API Config (3 tests) | 91b76418 |
| 2025-10-16 | D3.1.1-Batch2 | Documentation initiale | (ce commit) |

---

## 6. Contact et Support

Pour toute question ou problème de réactivation :
1. Consulter cette documentation
2. Vérifier les logs d'erreur pytest détaillés
3. Tester manuellement les imports/configurations problématiques
4. Créer une issue si le problème persiste après avoir suivi les étapes

---

**Document maintenu par** : Équipe Validation Tests Phase D3.1.1
**Dernière révision** : 2025-10-16