# Problèmes Connus - Projet Intelligence Symbolique

Ce document recense les problèmes connus du projet et leurs solutions.

---

## 🔴 PyTorch WinError 182 sur Windows (CRITIQUE)

**Date identification** : 2025-10-16
**Date résolution** : 2025-10-22
**Impact** : 2-11 tests crashent (dont F.6-F.7)
**Statut** : ✅ **RÉSOLU** (Solution A appliquée - PyTorch 2.9.0+cpu)

### Symptômes

```
OSError: [WinError 182] Le système d'exploitation ne peut pas exécuter %1. 
Error loading "...\torch\lib\fbgemm.dll" or one of its dependencies.

Windows fatal exception: code 0xc0000138
```

### Environnement Affecté

- **OS** : Windows 11
- **Python** : 3.10.19
- **PyTorch** : 2.2.2
- **Conda Env** : `projet-is-roo-new`

### Tests Impactés

| Test ID | Fichier | Statut |
|---------|---------|--------|
| F.6 | `tests/unit/argumentation_analysis/test_baselogicagent_import_fix.py::test_service_manager_can_import_baselogicagent` | ❌ CRASH |
| F.7 | `tests/unit/argumentation_analysis/test_baselogicagent_import_fix.py::TestBaseLogicAgentImportFix::test_complete_import_resolution` | ❌ CRASH |

### Fichiers Bloqués en Collection

Ces fichiers ne peuvent pas être collectés par pytest à cause du crash PyTorch :
1. `tests/agents/core/logic/test_abstract_logic_agent.py`
2. `tests/integration/test_orchestration_agentielle_complete_reel.py`
3. `tests/test_integration_success_validation.py`
4. `tests/test_orchestration_integration.py`

### Cause Racine

**NON lié à VC++ Redistributable** : Même avec VC++ 2015-2022 v14.44 installé, le problème persiste.

**Cause réelle** : Incompatibilité binaire PyTorch avec le système Windows :
- Build PyTorch CUDA sur machine CPU-only
- Instructions CPU manquantes (AVX2/AVX512)
- Bug connu PyTorch 2.2.2 sur Windows

### 🔧 Solution A : PyTorch CPU-Only (RECOMMANDÉE)

```bash
# 1. Activer environnement
conda activate projet-is-roo-new

# 2. Désinstaller PyTorch actuel
pip uninstall torch torchvision torchaudio -y

# 3. Installer PyTorch CPU-only officiel
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 4. Vérifier installation
python -c "import torch; print(f'PyTorch {torch.__version__} OK - CUDA: {torch.cuda.is_available()}')"
```

**Avantages** :
- ✅ Build optimisé pour CPU sans dépendances CUDA
- ✅ Compatible tous processeurs x86-64
- ✅ Résout WinError 182 définitivement

### 🔧 Solution B : PyTorch via Conda

```bash
conda install -n projet-is-roo-new pytorch torchvision torchaudio cpuonly -c pytorch
```

Conda gère mieux les dépendances binaires Windows.

### 🔧 Solution C : Downgrade PyTorch

```bash
# PyTorch 2.1.2 est plus stable sur Windows
pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu
```

### 🛡️ Solution D : Skip Conditionnel (WORKAROUND)

Si PyTorch non critique, ajouter dans `tests/conftest.py` :

```python
import pytest

def pytest_collection_modifyitems(config, items):
    """Skip tests requiring PyTorch if import fails."""
    skip_pytorch = pytest.mark.skip(reason="PyTorch not available (WinError 182)")
    
    for item in items:
        # Check if test imports torch
        if "torch" in str(item.fspath):
            try:
                import torch
            except (OSError, ImportError) as e:
                if "WinError 182" in str(e) or "fbgemm.dll" in str(e):
                    item.add_marker(skip_pytorch)
```

### Vérification Post-Installation

Après application d'une solution, vérifier :

```bash
# 1. Import PyTorch fonctionne
python -c "import torch; print('PyTorch OK')"

# 2. Tests peuvent être collectés
pytest tests/unit/argumentation_analysis/test_baselogicagent_import_fix.py --collect-only

# 3. Tests peuvent être exécutés
pytest tests/unit/argumentation_analysis/test_baselogicagent_import_fix.py -v
```

### Références

- **Rapport détaillé** : `.temp/cleanup_campaign_2025-10-03/02_phases/phase_D3/RAPPORT_SOUS_TACHE_3_PYTORCH_VCREDIST.md`
- **GitHub Issue PyTorch** : https://github.com/pytorch/pytorch/issues?q=WinError+182+fbgemm
- **PyTorch Windows Installation** : https://pytorch.org/get-started/locally/

---

## Autres Problèmes Connus

_(Ajouter ici les futurs problèmes identifiés)_

---

**Dernière mise à jour** : 2025-10-16  
**Mainteneur** : Équipe Projet Intelligence Symbolique