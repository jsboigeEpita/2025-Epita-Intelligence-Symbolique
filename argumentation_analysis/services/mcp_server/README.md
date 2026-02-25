# Serveur MCP pour l'analyse argumentative

Ce MCP vous permet d'utiliser vos clients LLM préférés pour interagir avec les fonctionnalités d'analyse argumentative. Il utilise le [protocole](https://modelcontextprotocol.io/) MCP créé par Anthropic, qui met à disposition des outils que votre LLM peut appeler lorsque cela est pertinent.

## Comment utiliser le serveur MCP localement

### Par Docker

1. Lancez le serveur MCP avec la commande suivante :

    ```bash
    docker build -t argumentation_analysis_mcp .
    docker run -p 8000:8000 argumentation_analysis_mcp
    ```

2. Vous pouvez ensuite utiliser ce MCP dans votre client MCP préféré. Voici une liste non exhaustive de clients MCP :
    - [Roo](https://github.com/RooCodeInc/Roo-Code)
    - [Cursor](https://www.cursor.com/)
    - [Claude Desktop](https://www.anthropic.com/products/claude-desktop)
    - [Claude Code](https://docs.anthropic.com/en/docs/claude-code/mcp)
    - [Gemini CLI](https://github.com/google-gemini/gemini-cli/)
    - [Github Copilot](https://docs.github.com/en/copilot/customizing-copilot/using-model-context-protocol/extending-copilot-chat-with-mcp)

    You can find an updated list of MCP clients [here](https://modelcontextprotocol.io/clients).

   Vous pouvez insérer le fichier de configuration suivant dans votre client MCP préféré pour utiliser le MCP :

    ```json
    {
      "mcpServers": {
        "argumentation_analysis_mcp": {
          "type": "streamable-http",
          "url": "http://127.0.0.1:8000/mcp"
        }
      }
    }
    ```

## Comment utiliser le serveur MCP en mode "remote"

1. Vous pouvez déployer un conteneur avec l'image `argumentation_analysis_mcp` sur un serveur distant.

2. Vous pouvez ensuite utiliser un fichier de configuration comme celui-ci :

    ```json
    {
      "mcpServers": {
        "argumentation_analysis_mcp": {
          "type": "streamable-http",
          "url": "http://<ip_serveur>:8000/mcp"
        }
      }
    }
    ```