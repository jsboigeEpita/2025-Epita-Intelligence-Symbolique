# Exemples d'Utilisation des Agents et Outils

Ce document fournit des exemples concrets d'utilisation des agents et des outils dans la nouvelle structure du répertoire `agents/`. Ces exemples sont destinés à aider les développeurs à comprendre comment utiliser efficacement les différents composants du système.

## Utilisation des Agents Principaux

### Agent d'Analyse Informelle

```python
import asyncio
from agents.core.informal.informal_definitions import setup_informal_agent
from core.llm_service import create_llm_service

async def analyze_text_with_informal_agent(text):
    """Analyse un texte avec l'agent d'analyse informelle."""
    # Créer le service LLM
    llm_service = create_llm_service()
    
    # Initialiser l'agent
    kernel, agent = await setup_informal_agent(llm_service)
    
    # Analyser le texte
    result = await agent.analyze_text(text)
    
    # Afficher les résultats
    print(f"Arguments identifiés: {len(result['arguments'])}")
    print(f"Sophismes identifiés: {len(result['fallacies'])}")
    
    return result

# Exemple d'utilisation
if __name__ == "__main__":
    text = """
    Tous les politiciens sont corrompus. Jean est un politicien, donc Jean est corrompu.
    De plus, comme Jean est corrompu, il ne faut pas voter pour lui.
    """
    asyncio.run(analyze_text_with_informal_agent(text))
```

### Agent Project Manager

```python
import asyncio
from agents.core.pm.pm_definitions import setup_pm_agent
from core.llm_service import create_llm_service
from core.shared_state import SharedState

async def orchestrate_analysis(text):
    """Orchestre l'analyse d'un texte avec l'agent PM."""
    # Créer le service LLM
    llm_service = create_llm_service()
    
    # Initialiser l'état partagé
    shared_state = SharedState()
    shared_state.set("source_text", text)
    
    # Initialiser l'agent PM
    kernel, agent = await setup_pm_agent(llm_service, shared_state)
    
    # Lancer l'orchestration
    result = await agent.orchestrate_analysis()
    
    return result

# Exemple d'utilisation
if __name__ == "__main__":
    text = """
    Tous les chats sont des mammifères. Félix est un chat, donc Félix est un mammifère.
    Les mammifères ont besoin d'oxygène pour vivre. Donc Félix a besoin d'oxygène pour vivre.
    """
    asyncio.run(orchestrate_analysis(text))
```

### Agent de Logique Propositionnelle

```python
import asyncio
from agents.core.pl.pl_definitions import setup_pl_agent
from core.llm_service import create_llm_service

async def formalize_argument(argument):
    """Formalise un argument avec l'agent de logique propositionnelle."""
    # Créer le service LLM
    llm_service = create_llm_service()
    
    # Initialiser l'agent
    kernel, agent = await setup_pl_agent(llm_service)
    
    # Formaliser l'argument
    formalization = await agent.formalize_argument(argument)
    
    # Vérifier la validité
    validity = await agent.check_validity(formalization)
    
    return {
        "formalization": formalization,
        "validity": validity
    }

# Exemple d'utilisation
if __name__ == "__main__":
    argument = {
        "premises": [
            "Si il pleut, alors la route est mouillée",
            "Il pleut"
        ],
        "conclusion": "La route est mouillée"
    }
    asyncio.run(formalize_argument(argument))
```

### Agent d'Extraction

```python
import asyncio
from agents.core.extract.extract_definitions import setup_extract_agent
from core.llm_service import create_llm_service

async def extract_arguments(text):
    """Extrait les arguments d'un texte avec l'agent d'extraction."""
    # Créer le service LLM
    llm_service = create_llm_service()
    
    # Initialiser l'agent
    kernel, agent = await setup_extract_agent(llm_service)
    
    # Extraire les arguments
    extracts = await agent.extract_arguments(text)
    
    return extracts

# Exemple d'utilisation
if __name__ == "__main__":
    text = """
    La liberté d'expression est un droit fondamental. Sans elle, la démocratie ne peut pas fonctionner.
    Cependant, cette liberté doit être encadrée pour éviter les abus.
    """
    asyncio.run(extract_arguments(text))
```

## Utilisation des Outils

### Outils d'Optimisation

```python
import asyncio
from agents.tools.optimization.informal.improve_informal_agent import improve_agent_prompts
from agents.core.informal.prompts import INFORMAL_INSTRUCTIONS

async def optimize_informal_agent():
    """Optimise les prompts de l'agent d'analyse informelle."""
    # Charger les prompts actuels
    current_prompts = INFORMAL_INSTRUCTIONS
    
    # Améliorer les prompts
    improved_prompts = await improve_agent_prompts(current_prompts)
    
    # Afficher les améliorations
    print("Prompts originaux:")
    print(current_prompts[:100] + "...")
    print("\nPrompts améliorés:")
    print(improved_prompts[:100] + "...")
    
    return improved_prompts

# Exemple d'utilisation
if __name__ == "__main__":
    asyncio.run(optimize_informal_agent())
```

### Outils d'Analyse

```python
from agents.tools.analysis.informal.analyse_traces_informal import analyze_agent_traces

def analyze_informal_agent_performance():
    """Analyse les performances de l'agent d'analyse informelle."""
    # Chemin vers les traces
    traces_path = "agents/traces/informal/informal_traces.json"
    
    # Analyser les traces
    analysis = analyze_agent_traces(traces_path)
    
    # Afficher les résultats
    print(f"Nombre total d'analyses: {analysis['total_analyses']}")
    print(f"Temps moyen d'analyse: {analysis['average_time']} secondes")
    print(f"Taux de détection des sophismes: {analysis['fallacy_detection_rate']}%")
    
    return analysis

# Exemple d'utilisation
if __name__ == "__main__":
    analyze_informal_agent_performance()
```

### Outils d'Encryption

```python
from agents.tools.encryption.create_complete_encrypted_config import encrypt_config
from agents.tools.encryption.load_complete_encrypted_config import load_encrypted_config

def manage_encrypted_config():
    """Gère la configuration encryptée."""
    # Données à encrypter
    config_data = {
        "api_key": "sk-1234567890abcdef",
        "endpoint": "https://api.example.com",
        "model": "gpt-4"
    }
    
    # Encrypter la configuration
    encrypted_path = encrypt_config(config_data, "my_secure_password")
    print(f"Configuration encryptée sauvegardée dans: {encrypted_path}")
    
    # Charger la configuration encryptée
    loaded_config = load_encrypted_config(encrypted_path, "my_secure_password")
    print(f"Configuration chargée: {loaded_config}")
    
    return loaded_config

# Exemple d'utilisation
if __name__ == "__main__":
    manage_encrypted_config()
```

## Utilisation des Scripts d'Exécution

### Scripts de Test

```bash
# Test de l'agent d'analyse informelle
python agents/runners/test/informal/test_informal_agent.py

# Test de l'agent PM
python agents/runners/test/orchestration/test_orchestration_complete.py

# Test à grande échelle
python agents/runners/test/orchestration/test_orchestration_scale.py
```

### Scripts de Déploiement

```bash
# Déploiement en environnement de développement
python agents/runners/deploy/deploy_dev.py

# Déploiement en environnement de production
python agents/runners/deploy/deploy_prod.py
```

### Scripts d'Intégration

```bash
# Test d'intégration complet
python agents/runners/integration/run_integration_test.py

# Test d'intégration avec simulation d'erreurs
python agents/runners/integration/run_integration_test.py --simulate-errors
```

## Utilisation des Templates

### Création d'un Nouvel Agent

```python
import shutil
import os

def create_new_agent(agent_name):
    """Crée un nouvel agent à partir du template étudiant."""
    # Chemins source et destination
    source_path = "agents/templates/student_template"
    dest_path = f"agents/core/{agent_name}"
    
    # Créer le répertoire de destination s'il n'existe pas
    os.makedirs(dest_path, exist_ok=True)
    
    # Copier les fichiers du template
    for file in os.listdir(source_path):
        if file.endswith(".py") or file == "README.md":
            source_file = os.path.join(source_path, file)
            dest_file = os.path.join(dest_path, file.replace("student_template", agent_name))
            shutil.copy(source_file, dest_file)
            
            # Remplacer les occurrences de "student_template" par le nom de l'agent
            with open(dest_file, "r") as f:
                content = f.read()
            
            content = content.replace("student_template", agent_name)
            content = content.replace("Student Template", agent_name.title())
            
            with open(dest_file, "w") as f:
                f.write(content)
    
    print(f"Nouvel agent '{agent_name}' créé dans {dest_path}")

# Exemple d'utilisation
if __name__ == "__main__":
    create_new_agent("my_new_agent")
```

## Conclusion

Ces exemples illustrent comment utiliser les différents composants de la nouvelle structure du répertoire `agents/`. Ils peuvent être adaptés et étendus selon vos besoins spécifiques. Pour plus de détails sur chaque composant, consultez la documentation correspondante dans les fichiers README.md des différents répertoires.