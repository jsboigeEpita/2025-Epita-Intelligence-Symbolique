# Guide de Migration vers la Nouvelle Structure

Ce document fournit des instructions pour adapter votre code à la nouvelle structure du répertoire `agents/`. Il est destiné aux développeurs qui travaillent déjà sur le projet et qui doivent migrer leur code existant.

## Changements Principaux

La réorganisation du répertoire `agents/` a introduit les changements suivants :

1. Les agents principaux sont maintenant dans le répertoire `core/`
2. Les outils et utilitaires sont maintenant dans le répertoire `tools/`
3. Les scripts d'exécution sont maintenant dans le répertoire `runners/`
4. Les traces d'exécution sont maintenant dans le répertoire `traces/`
5. Les templates sont maintenant dans le répertoire `templates/`

## Mise à Jour des Imports

### Anciens Imports

```python
# Imports des agents
from agents.informal import InformalAgent
from agents.pm import PMAgent
from agents.pl import PLAgent
from agents.extract import ExtractAgent

# Imports des outils
from agents.optimization import improve_agent
from agents.analysis import analyze_traces
from agents.encryption import encrypt_config

# Imports des scripts
from agents.test_scripts import test_informal_agent
from agents.run_scripts import run_complete_test
```

### Nouveaux Imports

```python
# Imports des agents
from agents.core.informal.informal_agent import InformalAgent
from agents.core.pm.pm_agent import PMAgent
from agents.core.pl.pl_agent import PLAgent
from agents.core.extract.extract_agent import ExtractAgent

# Imports des outils
from agents.tools.optimization.informal.improve_informal_agent import improve_agent
from agents.tools.analysis.informal.analyse_traces_informal import analyze_traces
from agents.tools.encryption.create_complete_encrypted_config import encrypt_config

# Imports des scripts
from agents.runners.test.informal.test_informal_agent import test_informal_agent
from agents.runners.test.orchestration.test_orchestration_complete import run_complete_test
```

## Mise à Jour des Chemins de Fichiers

### Anciens Chemins

```python
# Chemins des fichiers de configuration
config_path = "agents/config/informal_config.json"
prompts_path = "agents/informal/prompts.py"

# Chemins des traces
traces_path = "agents/traces/informal_traces.json"

# Chemins des scripts
script_path = "agents/test_scripts/test_informal.py"
```

### Nouveaux Chemins

```python
# Chemins des fichiers de configuration
config_path = "agents/core/informal/config/informal_config.json"
prompts_path = "agents/core/informal/prompts.py"

# Chemins des traces
traces_path = "agents/traces/informal/informal_traces.json"

# Chemins des scripts
script_path = "agents/runners/test/informal/test_informal.py"
```

## Mise à Jour des Scripts d'Exécution

### Anciens Scripts

```bash
# Exécution des tests
python agents/test_scripts/test_informal_agent.py

# Exécution des analyses
python agents/run_scripts/run_complete_test_and_analysis.py
```

### Nouveaux Scripts

```bash
# Exécution des tests
python agents/runners/test/informal/test_informal_agent.py

# Exécution des analyses
python agents/runners/test/orchestration/test_orchestration_complete.py
```

## Mise à Jour des Références aux Agents

### Ancienne Initialisation

```python
from agents.informal import setup_informal_agent
from agents.pm import setup_pm_agent

# Initialisation des agents
kernel_informal, informal_agent = await setup_informal_agent(llm_service)
kernel_pm, pm_agent = await setup_pm_agent(llm_service)
```

### Nouvelle Initialisation

```python
from agents.core.informal.informal_definitions import setup_informal_agent
from agents.core.pm.pm_definitions import setup_pm_agent

# Initialisation des agents
kernel_informal, informal_agent = await setup_informal_agent(llm_service)
kernel_pm, pm_agent = await setup_pm_agent(llm_service)
```

## Mise à Jour des Références aux Outils

### Ancienne Utilisation

```python
from agents.optimization.improve_informal_agent import improve_agent_prompts
from agents.analysis.analyse_traces_informal import analyze_agent_traces

# Utilisation des outils
improved_prompts = await improve_agent_prompts(current_prompts)
analysis_results = analyze_agent_traces(traces_path)
```

### Nouvelle Utilisation

```python
from agents.tools.optimization.informal.improve_informal_agent import improve_agent_prompts
from agents.tools.analysis.informal.analyse_traces_informal import analyze_agent_traces

# Utilisation des outils
improved_prompts = await improve_agent_prompts(current_prompts)
analysis_results = analyze_agent_traces(traces_path)
```

## Mise à Jour des Références aux Traces

### Ancienne Gestion des Traces

```python
# Sauvegarde des traces
with open("agents/traces/informal_traces.json", "w") as f:
    json.dump(traces, f, indent=2)

# Chargement des traces
with open("agents/traces/informal_traces.json", "r") as f:
    traces = json.load(f)
```

### Nouvelle Gestion des Traces

```python
# Sauvegarde des traces
with open("agents/traces/informal/informal_traces.json", "w") as f:
    json.dump(traces, f, indent=2)

# Chargement des traces
with open("agents/traces/informal/informal_traces.json", "r") as f:
    traces = json.load(f)
```

## Vérification de la Migration

Pour vérifier que votre code a été correctement migré vers la nouvelle structure, vous pouvez utiliser le script de vérification suivant :

```python
# agents/runners/verify_structure.py
import importlib
import os
import sys

def verify_imports():
    """Vérifie que les imports sont conformes à la nouvelle structure."""
    try:
        # Vérification des imports des agents
        from agents.core.informal.informal_agent import InformalAgent
        from agents.core.pm.pm_agent import PMAgent
        from agents.core.pl.pl_agent import PLAgent
        from agents.core.extract.extract_agent import ExtractAgent
        
        # Vérification des imports des outils
        from agents.tools.optimization.informal.improve_informal_agent import improve_agent_prompts
        from agents.tools.analysis.informal.analyse_traces_informal import analyze_agent_traces
        
        print("✅ Tous les imports sont conformes à la nouvelle structure.")
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        print("Veuillez vérifier vos imports et les adapter à la nouvelle structure.")

def verify_paths():
    """Vérifie que les chemins de fichiers sont conformes à la nouvelle structure."""
    paths_to_check = [
        "agents/core/informal/prompts.py",
        "agents/core/pm/prompts.py",
        "agents/core/pl/prompts.py",
        "agents/core/extract/prompts.py",
        "agents/tools/optimization/informal/improve_informal_agent.py",
        "agents/tools/analysis/informal/analyse_traces_informal.py",
        "agents/runners/test/informal/test_informal_agent.py",
        "agents/traces/informal/README.md",
    ]
    
    all_valid = True
    for path in paths_to_check:
        if not os.path.exists(path):
            print(f"❌ Chemin invalide: {path}")
            all_valid = False
    
    if all_valid:
        print("✅ Tous les chemins sont conformes à la nouvelle structure.")

if __name__ == "__main__":
    verify_imports()
    verify_paths()
```

## Conclusion

La migration vers la nouvelle structure du répertoire `agents/` nécessite principalement des mises à jour des imports et des chemins de fichiers. En suivant ce guide, vous devriez pouvoir adapter votre code existant à la nouvelle structure sans difficulté majeure.

Si vous rencontrez des problèmes lors de la migration, n'hésitez pas à consulter la documentation complète de la nouvelle structure dans le fichier `docs/structure_agents.md` ou à contacter l'équipe de développement pour obtenir de l'aide.