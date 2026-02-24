# GitHub Projects MCP Server

This MCP server provides tools to interact with GitHub Projects.

## Prerequisites

- Node.js
- A GitHub Personal Access Token with `repo` and `project` scopes.

## Setup

1.  Install dependencies:
    ```bash
    npm install
    ```
2.  Create a `.env` file in the root of this server's directory (`mcps/internal/servers/github-projects-mcp`).
3.  Add your GitHub token to the `.env` file:
    ```
    GITHUB_TOKEN=your_personal_access_token
    ```

## Running the Server

To start the server for development or general use:

```bash
npm start
```

## Testing

The End-to-End (E2E) tests require the server to be running independently.

**1. Build the project:**

Make sure you have the latest code compiled:
```bash
npm run build
```

**2. Start the test server:**

In your first terminal, run:
```bash
npm run start:e2e
```
The server will start on the port specified in the `.env` file or on port 3000 by default. The E2E tests will connect to it on port 3001.

**3. Run the E2E tests:**

In a second terminal, run:
```bash
npm run test:e2e
```
Jest will execute the tests located in the `tests/` directory against the running server.

## Tools

### Monitoring des Workflows GitHub Actions

Cette section décrit les outils disponibles pour surveiller et analyser les workflows GitHub Actions d'un dépôt.

#### `list_repository_workflows`

Liste tous les workflows définis dans un dépôt GitHub.

**Paramètres :**
- `owner` (string) : Nom du propriétaire du dépôt (utilisateur ou organisation)
- `repo` (string) : Nom du dépôt

**Exemple de retour en cas de succès :**
```json
{
  "success": true,
  "workflows": [
    {
      "id": 161335,
      "node_id": "MDg6V29ya2Zsb3cxNjEzMzU=",
      "name": "CI",
      "path": ".github/workflows/ci.yml",
      "state": "active",
      "created_at": "2020-01-08T23:48:37.000Z",
      "updated_at": "2020-01-08T23:50:21.000Z",
      "url": "https://api.github.com/repos/octocat/Hello-World/actions/workflows/161335",
      "html_url": "https://github.com/octocat/Hello-World/blob/master/.github/workflows/ci.yml",
      "badge_url": "https://github.com/octocat/Hello-World/workflows/CI/badge.svg"
    }
  ]
}
```

#### `get_workflow_runs`

Récupère les exécutions (runs) d'un workflow spécifique, avec leur statut et leurs détails.

**Paramètres :**
- `owner` (string) : Nom du propriétaire du dépôt
- `repo` (string) : Nom du dépôt
- `workflow_id` (number) : ID du workflow (peut aussi accepter le nom du fichier .yml)

**Exemple de retour en cas de succès :**
```json
{
  "success": true,
  "workflow_runs": [
    {
      "id": 30433642,
      "name": "Build",
      "node_id": "MDExOldvcmtmbG93UnVuMzA0MzM2NDI=",
      "head_branch": "master",
      "head_sha": "acb5820ced9479c074f688cc328bf03f341a511d",
      "run_number": 562,
      "event": "push",
      "status": "completed",
      "conclusion": "success",
      "workflow_id": 161335,
      "created_at": "2020-01-22T19:33:08Z",
      "updated_at": "2020-01-22T19:33:08Z",
      "url": "https://api.github.com/repos/github/hello-world/actions/runs/30433642",
      "html_url": "https://github.com/github/hello-world/actions/runs/30433642"
    }
  ]
}
```

#### `get_workflow_run_status`

Obtient le statut détaillé d'une exécution de workflow spécifique.

**Paramètres :**
- `owner` (string) : Nom du propriétaire du dépôt
- `repo` (string) : Nom du dépôt
- `run_id` (number) : ID de l'exécution du workflow

**Exemple de retour en cas de succès :**
```json
{
  "success": true,
  "workflow_run": {
    "id": 30433642,
    "name": "Build",
    "node_id": "MDExOldvcmtmbG93UnVuMzA0MzM2NDI=",
    "head_branch": "master",
    "head_sha": "acb5820ced9479c074f688cc328bf03f341a511d",
    "run_number": 562,
    "event": "push",
    "status": "completed",
    "conclusion": "success",
    "workflow_id": 161335,
    "created_at": "2020-01-22T19:33:08Z",
    "updated_at": "2020-01-22T19:33:08Z",
    "url": "https://api.github.com/repos/github/hello-world/actions/runs/30433642",
    "html_url": "https://github.com/github/hello-world/actions/runs/30433642"
  }
}
```

**États possibles pour `status` :**
- `completed` : L'exécution est terminée
- `in_progress` : L'exécution est en cours
- `queued` : L'exécution est en file d'attente
- `requested` : L'exécution a été demandée
- `waiting` : L'exécution attend
- `pending` : L'exécution est en attente

**Conclusions possibles pour `conclusion` (si status = "completed") :**
- `success` : L'exécution s'est terminée avec succès
- `failure` : L'exécution a échoué
- `cancelled` : L'exécution a été annulée
- `skipped` : L'exécution a été ignorée
- `timed_out` : L'exécution a expiré
- `action_required` : Une action manuelle est requise
- `neutral` : L'exécution s'est terminée de manière neutre