# Exécute les tests unitaires et d'intégration pour le service MCP en utilisant le wrapper d'activation.

# Lance les tests pytest sur les fichiers de test du service MCP via le script d'activation.
powershell -File ./activate_project_env.ps1 -CommandToRun "pytest tests/unit/services/test_mcp_server.py tests/integration/services/test_mcp_server_integration.py"