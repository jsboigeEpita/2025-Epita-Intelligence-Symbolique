# Guide d'Intégration du Serveur MCP : Analyse et Plan d'Action

Bonjour l'équipe,

Merci pour votre soumission et le travail que vous avez accompli sur le serveur MCP. Nous avons analysé votre pull request et nous sommes impressionnés par la qualité du code, la clarté de votre `README.md` et l'utilisation d'outils modernes comme `FastMCP` et `uv`. C'est un excellent point de départ.

L'objectif de ce document est de vous fournir un retour constructif et un plan d'action clair pour finaliser l'intégration de votre service, en tenant compte des récentes évolutions de l'architecture de notre projet.

## 1. Analyse de votre approche actuelle

Votre serveur MCP est bien conçu, mais il repose sur une hypothèse architecturale qui n'est plus d'actualité.

**Le point clé :** Votre code dans [`mcp/main.py`](mcp/main.py:8) tente de contacter une API web à l'adresse `http://localhost:5000/api`.

```python
# mcp/main.py:8
WEB_API_URL = "http://localhost:5000/api" 
```

Cette approche était valable avec l'ancienne architecture du projet. Cependant, une refactorisation majeure a eu lieu pour centraliser et simplifier la manière dont les services sont gérés.

## 2. La Nouvelle Architecture : L'Orchestrateur Central

Le projet n'expose plus une multitude de services sur des ports différents. À la place, nous avons un **point d'entrée unique** :

- **[`project_core/webapp_from_scripts/unified_web_orchestrator.py`](project_core/webapp_from_scripts/unified_web_orchestrator.py)**

Cet orchestrateur est maintenant responsable du cycle de vie de toutes les applications et services. Il utilise une classe centrale, le `ServiceManager`, pour démarrer, arrêter et communiquer avec les différents composants, y compris les vôtres.

**Conséquence pour vous :** Votre serveur MCP ne doit plus faire d'appels HTTP vers un service externe. Il doit être intégré *directement* dans l'écosystème de l'orchestrateur.

## 3. Plan d'Action pour l'Intégration

Voici un plan étape par étape pour aligner votre serveur MCP avec la nouvelle architecture.

### Étape 1 : Rendre le MCP autonome (supprimer les appels HTTP)

Votre `main.py` ne doit plus être un simple "proxy" HTTP. Il doit devenir un véritable service qui utilise directement les fonctionnalités d'analyse du projet.

**Action :**
Modifiez les fonctions dans [`mcp/main.py`](mcp/main.py) pour qu'elles importent et appellent les classes et fonctions d'analyse du projet. Inspirez-vous de la manière dont le `ServiceManager` communique avec les autres services. Vous devrez probablement importer des éléments depuis `argumentation_analysis` ou `project_core`.

*Exemple (conceptuel) :*
```python
# Avant (dans mcp/main.py)
# url = f"{WEB_API_URL}/analyze"
# response = httpx.post(url, json={"text": text, "options": options})
# return response.json()

# Après (conceptuel)
from argumentation_analysis.main_analyzer import MainAnalyzer # L'import sera à adapter

analyzer = MainAnalyzer()
result = analyzer.analyze(text=text, options=options)
return result
```

### Étape 2 : Intégrer le lancement à l'Orchestrateur

L'[`UnifiedWebOrchestrator`](project_core/webapp_from_scripts/unified_web_orchestrator.py) doit connaître votre serveur MCP pour le lancer en tant que sous-processus.

**Action :**
Identifiez dans le script de l'orchestrateur l'endroit où les autres services sont démarrés et ajoutez le code nécessaire pour lancer votre serveur. La commande sera probablement similaire à celle que vous avez définie dans votre `README.md` : `uv run mcp/main.py`.

### Étape 3 : Gérer la Configuration avec `.roo/mcp.json`

Votre `README.md` mentionne un fichier `.roo/mcp.json`, et vous avez raison, il est essentiel pour l'intégration automatique avec l'IDE. Ce fichier était manquant dans votre PR.

**Action :**
1. Créez un répertoire `.roo` à la racine du projet.
2. Créez un fichier `mcp.json` à l'intérieur de `.roo/` avec le contenu suivant. Ce fichier indique à Roo comment lancer votre serveur MCP.

```json
{
  "$schema": "https://schemas.modelcontext.dev/mcp-v1.schema.json",
  "servers": {
    "argumentation_analysis_mcp": {
      "command": "python",
      "args": [
        "-m",
        "uv",
        "run",
        "--python",
        "{{env.PYTHON_PATH}}",
        "mcp/main.py"
      ],
      "transport": "stdio",
      "enable": true
    }
  }
}
```
*(Note : Nous utilisons `uv` ici, ce qui est une excellente idée. Assurez-vous que les dépendances sont installées dans l'environnement que `uv` utilisera).*

### Étape 4 : Gestion des Dépendances

Votre `README.md` mentionne un fichier `requirements.txt` qui semble manquant.

**Action :**
Veuillez créer un fichier `mcp/requirements.txt` et y lister toutes les dépendances Python nécessaires au fonctionnement de votre serveur (par ex. `fastmcp`, `httpx`, etc.). Cela permettra une installation automatisée et fiable.

### Étape 5 (Vision à long terme) : Conteneurisation

Votre idée d'utiliser Docker pour conteneuriser le service est très pertinente et nous l'encourageons. Cependant, nous vous suggérons de la mettre en œuvre *après* avoir réussi l'intégration de base suivant les étapes ci-dessus. Une fois que le service fonctionne correctement avec l'orchestrateur, le passage à Docker sera beaucoup plus simple.

## Conclusion

Nous sommes très enthousiastes à l'idée d'intégrer votre contribution. Le chemin que nous vous proposons ici est celui qui garantira que votre service s'intègre de manière robuste et pérenne dans l'écosystème du projet.

N'hésitez pas si vous avez des questions sur ce plan d'action. Nous sommes là pour vous aider.