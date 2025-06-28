# Agent de Génération de Contre-Arguments

Ce projet implémente un agent intelligent capable d'analyser des arguments, d'identifier leurs vulnérabilités, et de générer des contre-arguments pertinents et logiquement valides.

## Fonctionnalités

- **Analyse d'arguments** : Extraction des prémisses, de la conclusion et du type d'argument.
- **Identification de vulnérabilités** : Détection des faiblesses logiques et rhétoriques.
- **Génération de contre-arguments** : Production de contre-arguments adaptés aux vulnérabilités détectées.
- **Validation logique** : Vérification de la validité formelle des contre-arguments via TweetyProject.
- **Évaluation qualitative** : Évaluation des contre-arguments selon plusieurs critères (pertinence, force logique, etc.).
- **Interface utilisateur web** : Interface conviviale pour interagir avec l'agent.

## Architecture

Le projet est organisé en plusieurs modules principaux :

- **agent** : Composants fondamentaux de l'agent (définitions, parseur, stratégies, agent principal).
- **llm** : Intégration avec les grands modèles de langage (LLMs) pour la génération de contre-arguments.
- **logic** : Validation logique des arguments et contre-arguments via TweetyProject.
- **evaluation** : Évaluation de la qualité des contre-arguments générés.
- **ui** : Interface utilisateur web pour interagir avec l'agent.

## Installation

### Prérequis

- Python 3.9 ou supérieur
- Pip
- Java JDK 11 ou supérieur (pour TweetyProject)

### Installation des dépendances

```bash
pip install -r requirements.txt
```

### Configuration

Pour utiliser l'intégration avec OpenAI, vous devez disposer d'une clé API valide. Vous pouvez la configurer de deux façons :

1. **Variable d'environnement** : Définissez la variable `OPENAI_API_KEY` avec votre clé.
2. **Fichier .env** : Créez un fichier `.env` à la racine du projet avec le contenu suivant :
   ```
   OPENAI_API_KEY=votre_cle_api_openai
   ```

## Utilisation

### Interface utilisateur web

Lancez l'interface web avec la commande suivante :

```bash
python run_app.py
```

Cela démarre un serveur web local accessible à l'adresse http://localhost:5000.

Options disponibles :
- `--host` : Spécifie l'hôte d'écoute (défaut : 127.0.0.1)
- `--port` : Spécifie le port d'écoute (défaut : 5000)
- `--debug` : Active le mode debug
- `--log-level` : Définit le niveau de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Utilisation programmatique

Voici un exemple simple d'utilisation de l'agent dans votre code :

```python
from counter_agent.agent.counter_agent import CounterArgumentAgent
from counter_agent.agent.definitions import CounterArgumentType, RhetoricalStrategy

# Initialiser l'agent
agent = CounterArgumentAgent()

# Générer un contre-argument
argument_text = "Tous les étudiants qui travaillent dur réussissent. Marie travaille dur, donc Marie réussira."
result = agent.generate_counter_argument(argument_text)

# Accéder aux résultats
counter_argument = result['counter_argument']
evaluation = result['evaluation']
validation = result['validation']

print(f"Contre-argument : {counter_argument.counter_content}")
print(f"Score global : {evaluation.overall_score}")
```

### Exemple de démonstration

Pour tester rapidement l'agent avec des exemples prédéfinis, exécutez :

```bash
python example.py
```

Cela générera des contre-arguments pour plusieurs arguments de test et affichera les résultats.

## Composants principaux

### Agent de contre-arguments

Le cœur du système est la classe `CounterArgumentAgent` qui coordonne les différents composants pour :
1. Analyser les arguments via le `ArgumentParser`
2. Identifier les vulnérabilités
3. Générer des contre-arguments adaptés avec le `LLMGenerator`
4. Évaluer la qualité des contre-arguments avec le `CounterArgumentEvaluator`
5. Valider la cohérence logique avec le `CounterArgumentValidator`

### Intégration LLM

L'intégration avec les LLMs est gérée par la classe `LLMGenerator` qui utilise l'API OpenAI pour :
- Analyser la structure des arguments
- Identifier les vulnérabilités de manière plus sophistiquée
- Générer des contre-arguments adaptés au contexte
- Évaluer la qualité des contre-arguments

### Validation logique

La validation logique est assurée par `TweetyBridge` qui utilise JPype pour interagir avec TweetyProject, permettant :
- La création de frameworks d'argumentation de Dung
- La vérification de la validité des attaques
- L'évaluation de la force résiduelle des arguments après contre-argumentation

### Évaluation de la qualité

L'évaluation est réalisée par `CounterArgumentEvaluator` qui note les contre-arguments selon plusieurs critères :
- Pertinence par rapport à l'argument original
- Force logique
- Pouvoir de persuasion
- Originalité
- Clarté

## Contributions

Ce projet a été développé par [Votre nom] dans le cadre du cours d'Intelligence Symbolique à l'EPITA.

## Licence

MIT