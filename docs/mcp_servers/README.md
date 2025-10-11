# Documentation des Serveurs MCP

## Vue d'ensemble

Les Model-Context-Protocol (MCP) servers fournissent des outils spécialisés pour interagir avec GitHub, Git, et gérer l'état du projet. Ces serveurs étendent les capacités de l'assistant en lui donnant accès à des API externes et des fonctionnalités avancées.

## MCPs Disponibles

### 1. `github-projects-mcp` (Interne)

Serveur MCP personnalisé pour la gestion de projets GitHub et le monitoring des workflows CI/CD.

#### Outils de Monitoring des Workflows GitHub Actions

##### `list_repository_workflows`
- **Description :** Liste tous les workflows définis dans un dépôt GitHub
- **Paramètres :**
  - `owner: string` - Nom du propriétaire du dépôt (utilisateur ou organisation)
  - `repo: string` - Nom du dépôt
- **Retour :** Array de workflows avec id, nom, path, state, URLs

##### `get_workflow_runs`
- **Description :** Récupère les exécutions (runs) d'un workflow spécifique avec leur statut et leurs détails
- **Paramètres :**
  - `owner: string` - Nom du propriétaire du dépôt
  - `repo: string` - Nom du dépôt
  - `workflow_id: number | string` - ID du workflow (peut aussi accepter le nom du fichier .yml)
- **Retour :** Array d'exécutions avec status, conclusion, dates, branches

##### `get_workflow_run_status`
- **Description :** Obtient le statut détaillé d'une exécution de workflow spécifique
- **Paramètres :**
  - `owner: string` - Nom du propriétaire du dépôt
  - `repo: string` - Nom du dépôt
  - `run_id: number` - ID de l'exécution du workflow
- **Retour :** Détails complets de l'exécution (status, conclusion, logs, timestamps)

**États possibles :** `completed`, `in_progress`, `queued`, `requested`, `waiting`, `pending`

**Conclusions possibles :** `success`, `failure`, `cancelled`, `skipped`, `timed_out`, `action_required`, `neutral`

📖 **Documentation complète :** [`github-projects-mcp.md`](./github-projects-mcp.md)

---

### 2. `github` (Externe)

Serveur MCP officiel pour l'interaction avec l'API GitHub. Fournit des outils pour :
- Gestion des dépôts (création, recherche, fork)
- Gestion des fichiers (lecture, écriture, push multiple)
- Gestion des issues et pull requests
- Gestion des branches et commits
- Recherche de code, issues, utilisateurs

**Source :** `@modelcontextprotocol/server-github`

---

### 3. `roo-state-manager` (Interne)

Serveur MCP personnalisé pour la gestion de l'état des conversations Roo et l'analyse des tâches.

**Fonctionnalités principales :**
- Détection et analyse du stockage Roo
- Gestion des conversations et de leur hiérarchie
- Recherche sémantique dans les tâches
- Diagnostic et réparation des chemins de workspace
- Visualisation de l'arbre des conversations

**Outils notables :**
- `detect_roo_storage` - Détecte les emplacements de stockage Roo
- `list_conversations` - Liste toutes les conversations avec filtres
- `get_task_tree` - Récupère une vue arborescente des tâches
- `search_tasks_semantic` - Recherche sémantique dans les tâches
- `view_conversation_tree` - Vue condensée pour analyse rapide
- `diagnose_roo_state` - Audit des tâches Roo
- `repair_workspace_paths` - Réparation des chemins

---

### 4. Autres MCPs Disponibles

#### `jinavigator`
Convertit des pages web en Markdown via l'API Jina. Utile pour extraire du contenu web structuré.

#### `searxng`
Recherche web via l'API SearXNG. Permet des recherches générales et la lecture de contenu d'URLs.

#### `jupyter`
Gestion de notebooks Jupyter : lecture, écriture, exécution de cellules, gestion des kernels.

#### `markitdown`
Conversion de ressources (http/https/file/data URIs) en Markdown.

#### `playwright`
Automatisation de navigateur pour interactions web avancées (navigation, clicks, screenshots, etc.).

#### `quickfiles`
Opérations de fichiers avancées : lecture multiple, édition par diffs, recherche dans fichiers, copie/déplacement avec transformations.

---

## Utilisation

Les MCPs sont automatiquement disponibles via l'interface `use_mcp_tool` et `access_mcp_resource`. Pour utiliser un outil :

```typescript
use_mcp_tool(
  server_name: "github-projects-mcp",
  tool_name: "list_repository_workflows",
  arguments: {
    owner: "mon-org",
    repo: "mon-repo"
  }
)
```

## Notes Importantes

- Les MCPs internes nécessitent une configuration locale (tokens, environnements)
- Les MCPs externes sont gérés via npx et peuvent nécessiter des dépendances système
- La documentation de chaque MCP est maintenue dans ce répertoire pour faciliter la découvrabilité sémantique