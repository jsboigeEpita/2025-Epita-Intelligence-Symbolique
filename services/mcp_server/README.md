# Serveur MCP pour l'analyse argumentative

Ce MCP vous permet d'utiliser vos clients LLM préférés pour interagir avec les fonctionnalités d'analyse argumentative.
Il utilisera le [protocole](https://modelcontextprotocol.io/) MCP créé par Anthropic, qui met à disposition des outils que votre LLM peut appeler lorsque cela est pertinent.

## Comment utiliser le serveur MCP localement

### Par Docker

1. Lancez le serveur MCP avec la commande suivante :

    ```bash
    docker build -t argumentation_analysis_mcp .
    docker run -p 8000:8000 argumentation_analysis_mcp
    ```

2. Vous pouvez ensuite utiliser ce MCP dans votre client MCP préféré, voici une liste non exhaustive de clients MCP :
    - [Roo](https://github.com/RooCodeInc/Roo-Code)
    - [Cursor](https://www.cursor.com/)
    - [Claude Desktop](https://www.anthropic.com/products/claude-desktop)

   Vous pouvez insérer ce fichier de configuration suivant dans votre client MCP préféré pour utiliser le MCP :

    ```json
    {
      "mcpServers": {
        "argumentation_analysis_mcp": {
          "type": "streamable-http",
          "url": "http://127.0.0.1:8000/mcp"
        }
      }
    }
