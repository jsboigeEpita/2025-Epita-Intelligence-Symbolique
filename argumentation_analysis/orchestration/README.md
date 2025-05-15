# ⚙️ Orchestration (`orchestration/`)

Ce répertoire contient la logique principale qui orchestre la conversation collaborative entre les différents agents IA.

[Retour au README Principal](../README.md)

## Point d'entrée pour instance VSCode dédiée

Ce README sert de point d'entrée pour une instance VSCode dédiée au développement et à la maintenance de l'orchestration des agents. Cette approche multi-instance permet de travailler spécifiquement sur l'orchestration sans avoir à gérer l'ensemble du projet.

## Contenu

### Composants Principaux

* **[`analysis_runner.py`](./analysis_runner.py)**: Définit la fonction asynchrone principale `run_analysis_conversation(texte_a_analyser, llm_service)`.
    * **Isolation :** Crée à chaque appel des instances *locales* et *neuves* de l'état (`RhetoricalAnalysisState`), du `StateManagerPlugin`, du `Kernel` Semantic Kernel, de tous les agents définis (`ChatCompletionAgent`), et des stratégies d'orchestration (`SimpleTerminationStrategy`, `DelegatingSelectionStrategy`).
    * **Configuration :** Initialise le kernel local avec le service LLM fourni et le `StateManagerPlugin` local. Appelle les fonctions `setup_*_kernel` de chaque agent pour enregistrer leurs plugins et fonctions spécifiques sur ce kernel local.
    * **Exécution :** Crée une instance `AgentGroupChat` en lui passant les agents et les stratégies locales. Lance la conversation via `local_group_chat.invoke()` et gère la boucle d'échanges de messages.
    * **Suivi & Résultat :** Logue et affiche les tours de conversation, y compris les appels d'outils. Affiche l'historique complet et l'état final de l'analyse (`RhetoricalAnalysisState` sérialisé en JSON) à la fin de la conversation.

* **[`__init__.py`](./__init__.py)** : Marque le dossier comme un package Python et expose les fonctions principales.

Cette fonction est le cœur de l'exécution de l'analyse et est conçue pour être appelée par le script principal (`main_orchestrator.py`) ou par le script d'orchestration dédié (`run_orchestration.py`).

### Fonctionnalités Avancées

* **Sélection dynamique des agents** : Possibilité de spécifier quels agents inclure dans l'analyse via le paramètre `agents_to_include`.
* **Contrôle de verbosité** : Niveau de détail des logs configurable via le paramètre `verbose`.
* **Persistance des résultats** : Option pour sauvegarder l'état final de l'analyse dans un fichier JSON.
* **Gestion des erreurs** : Mécanismes robustes pour gérer les erreurs des agents et assurer la continuité de l'analyse.
* **Métriques de performance** : Collecte de métriques sur le temps d'exécution et l'utilisation des ressources.

## Développement de l'orchestration

### Exécution indépendante

Pour tester l'orchestration de manière indépendante, vous pouvez utiliser le script `run_orchestration.py` à la racine du projet :

```bash
# Avec l'interface utilisateur
python ../run_orchestration.py --ui

# Avec un fichier texte
python ../run_orchestration.py --file chemin/vers/fichier.txt

# Avec du texte direct
python ../run_orchestration.py --text "Votre texte à analyser ici"

# Avec des agents spécifiques
python ../run_orchestration.py --ui --agents pm informal pl

# Avec logs détaillés
python ../run_orchestration.py --ui --verbose
```

### Création d'un script de test local

Pour tester l'orchestration de manière encore plus isolée, vous pouvez créer un script de test dans ce répertoire :

```python
# test_orchestration.py
import sys
import os
import asyncio
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
project_dir = current_dir.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

from dotenv import load_dotenv
load_dotenv(override=True)

# Import des modules nécessaires
from core.llm_service import create_llm_service
from analysis_runner import run_analysis_conversation

async def test_orchestration():
    """Fonction de test pour l'orchestration des agents"""
    # Texte de test
    test_text = """
    Tous les hommes sont mortels.
    Socrate est un homme.
    Donc Socrate est mortel.
    """
    
    print(f"Texte de test: {test_text}")
    
    # Créer le service LLM
    print("Création du service LLM...")
    llm_service = create_llm_service()
    
    # Exécuter l'orchestration
    print("Lancement de l'orchestration...")
    await run_analysis_conversation(
        texte_a_analyser=test_text,
        llm_service=llm_service
    )
    
    print("Test terminé.")

if __name__ == "__main__":
    asyncio.run(test_orchestration())
```

Exécutez le test avec :
```bash
python orchestration/test_orchestration.py
```

## Modification de l'orchestration

### Ajout d'un nouvel agent à l'orchestration

Pour ajouter un nouvel agent à l'orchestration, suivez ces étapes :

1. Importez la fonction de configuration de l'agent dans `analysis_runner.py` :
   ```python
   from agents.new_agent.new_agent_definitions import setup_new_agent
   ```

2. Ajoutez l'agent à la fonction `setup_agents()` :
   ```python
   # Configurer le nouvel agent
   new_agent = await setup_new_agent(kernel, llm_service)
   agents.append(new_agent)
   ```

3. Mettez à jour la stratégie de sélection si nécessaire pour inclure le nouvel agent dans le flux de conversation.

### Modification de la stratégie d'orchestration

La stratégie d'orchestration est définie dans la fonction `setup_strategies()` de `analysis_runner.py`. Vous pouvez modifier cette fonction pour changer la façon dont les agents sont sélectionnés et comment la conversation se termine.

Exemple de modification pour une stratégie de sélection aléatoire :
```python
def setup_strategies(agents):
    """Configure les stratégies d'orchestration pour la conversation."""
    # Stratégie de terminaison simple (s'arrête quand un agent le demande)
    termination_strategy = SimpleTerminationStrategy()
    
    # Stratégie de sélection aléatoire
    selection_strategy = RandomSelectionStrategy(agents)
    
    return termination_strategy, selection_strategy
```

## Développement avec l'approche multi-instance

1. Ouvrez ce répertoire (`orchestration/`) comme dossier racine dans une instance VSCode dédiée
2. Travaillez sur l'orchestration sans être distrait par les autres parties du projet
3. Testez vos modifications avec le script de test indépendant
4. Une fois les modifications validées, intégrez-les dans le projet principal

## Bonnes pratiques

- Gardez la logique d'orchestration séparée de la logique des agents
- Documentez clairement les stratégies d'orchestration
- Testez l'orchestration avec différents textes et combinaisons d'agents
- Utilisez des logs détaillés pour suivre le flux de la conversation
- Gérez correctement les erreurs et les cas limites
- Maintenez une séparation claire entre l'état partagé et la logique d'orchestration

## Exemples d'utilisation avancée

### Orchestration avec agents spécifiques

```python
import asyncio
from core.llm_service import create_llm_service
from orchestration.analysis_runner import run_analysis_conversation

async def run_custom_analysis():
    # Créer le service LLM
    llm_service = create_llm_service()
    
    # Texte à analyser
    text = "La Terre est plate car l'horizon semble plat. Cependant, les photos satellites montrent clairement que la Terre est sphérique."
    
    # Exécuter l'analyse avec seulement certains agents
    result = await run_analysis_conversation(
        texte_a_analyser=text,
        llm_service=llm_service,
        agents_to_include=["pm", "informal"],  # Seulement PM et Informal
        verbose=True
    )
    
    return result

# Exécuter l'analyse personnalisée
asyncio.run(run_custom_analysis())
```

### Orchestration avec sauvegarde des résultats

```python
import asyncio
import json
from datetime import datetime
from core.llm_service import create_llm_service
from orchestration.analysis_runner import run_analysis_conversation

async def run_and_save_analysis():
    # Créer le service LLM
    llm_service = create_llm_service()
    
    # Texte à analyser
    text = "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."
    
    # Exécuter l'analyse
    result = await run_analysis_conversation(
        texte_a_analyser=text,
        llm_service=llm_service
    )
    
    # Sauvegarder les résultats
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analysis_result_{timestamp}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"Résultats sauvegardés dans {filename}")
    
    return result

# Exécuter l'analyse et sauvegarder les résultats
asyncio.run(run_and_save_analysis())
```

## Fonctionnalités avancées supplémentaires

- **Support pour l'orchestration à grande échelle** : Capacité à traiter des lots de textes en parallèle
- **Métriques de performance** : Collecte et analyse des temps d'exécution et de l'utilisation des ressources
- **Intégration avec les outils d'optimisation** : Utilisation des résultats d'analyse pour améliorer les agents
- **Gestion améliorée des erreurs** : Mécanismes robustes pour gérer les erreurs des agents et assurer la continuité de l'analyse