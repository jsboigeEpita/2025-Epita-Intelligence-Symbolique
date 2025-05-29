# Serveur MCP pour l'analyse argumentative

Ce MCP vous permet d'utiliser vos clients LLM préférés pour interagir avec les fonctionnalités d'analyse argumentative.
Il utilisera le [protocole](https://modelcontextprotocol.io/) MCP créé par Anthropic, qui met à disposition des outils que votre LLM peut appeler lorsque cela est pertinent.

## Comment utiliser le serveur MCP localement

1. Lancez l'API principale du projet, vous pouvez consulter la [documentation](../argumentation_analysis/README.md)
2. Installez les packages nécessaires au fonctionnement du MCP

    ```bash
    cd mcp
    pip install -r requirements.txt
    ```

3. Consultez la documentation du client dans lequel vous souhaitez utiliser le MCP
    - [Roo](#comment-utiliser-dans-roo)
    - [Cursor](#comment-utiliser-dans-cursor--claude-desktop)
    - [Claude Desktop](#comment-utiliser-dans-cursor--claude-desktop)

### Comment utiliser dans Roo

Vous pouvez simplement ouvrir Roo lorsque votre éditeur est démarré à la racine du dépôt, il se lancera automatiquement via le [fichier de configuration](../.roo/mcp.json) du projet Roo.
Vous pouvez adapter la configuration pour pouvoir l'utiliser lorsque votre éditeur est ouvert dans un autre dossier.

### Comment utiliser dans Cursor / Claude Desktop

Vous pouvez utiliser la configuration suivante et remplacer `PATH` par le path du répertoire mcp à l'intérieur de ce dépôt.

Un exemple pourrait être :
`PATH` = `/Users/username/2025-Epita-Intelligence-Symbolique/mcp`

```json
{
  "mcpServers": {
    "argumentation_analysis": {
      "command": "uv",
      "args": [
        "--directory",
        "PATH",
        "run",
        "main.py"
      ]
    }
  }
}

