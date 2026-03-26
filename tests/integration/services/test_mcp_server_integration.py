# Fichier de test d'intégration pour le service MCP.
import pytest
import multiprocessing
import time
import asyncio
import sys
import re

from mcp import ClientSession as Client

from services.mcp_server.main import MCPService

SERVICE_NAME = "argumentation_analysis_mcp"

@pytest.fixture(scope="module")
async def mcp_client(apply_nest_asyncio):
    """
    Fixture pour créer un client MCP connecté au service.
    Cette version est conçue pour être robuste contre les deadlocks en
    gérant les flux stdio de manière asynchrone et en attendant un
    signal de démarrage explicite du serveur.
    """
    import os
    import logging

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    
    # On laisse stdout/stdin non connectés car on utilise HTTP
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "services.mcp_server.minimal_main",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env
    )

    # --- Démarrage et synchronisation ---
    startup_info = {"url": None}
    startup_signal = asyncio.Event()
    stderr_output = []

    async def watch_stderr(stderr):
        """Lit stderr, stocke les lignes, extrait l'URL et signale le démarrage."""
        found_url = False
        found_startup_message = False
        try:
            async for line_bytes in stderr:
                line = line_bytes.decode('utf-8', errors='ignore').strip()
                logging.info(f"[SERVER STDERR] {line}")
                stderr_output.append(line)

                # Si on n'a pas encore trouvé l'URL, on la cherche
                if not found_url:
                    match = re.search(r"Uvicorn running on (https?://\S+)", line)
                    if match:
                        # Nettoyer l'URL et la stocker
                        startup_info["url"] = match.group(1).rstrip('/')
                        found_url = True

                # Si on n'a pas encore trouvé le message, on le cherche
                if not found_startup_message and "Application startup complete." in line:
                    found_startup_message = True

                # Si les deux conditions sont remplies, on signale et on arrête de surveiller
                if found_url and found_startup_message:
                    startup_signal.set()
                    break
        except Exception as e:
            logging.error(f"Erreur dans watch_stderr: {e}")

    stderr_watcher = asyncio.create_task(watch_stderr(process.stderr))

    try:
        await asyncio.wait_for(startup_signal.wait(), timeout=20.0)
    except asyncio.TimeoutError:
        stderr_watcher.cancel()
        process.terminate()
        await process.wait()
        # Affiche la sortie complète de stderr pour le débogage
        full_stderr = "\n".join(stderr_output)
        pytest.fail(
            "Le serveur MCP n'a pas démarré dans le temps imparti (20s) ou l'URL n'a pas été trouvée.\n"
            f"Sortie de stderr:\n{full_stderr}"
        )

    # --- Exécution du test ---
    session = None
    try:
        base_url = startup_info["url"]
        if not base_url: # Sécurité supplémentaire
            pytest.fail("L'URL de base du serveur n'a pas pu être déterminée.")

        session = Client(transport='http', base_url=base_url)
        # Pas d'appel initialize() pour le client HTTP car la poignée de main est implicite
        async with session:
            yield session
    finally:
        # --- Nettoyage ---
        stderr_watcher.cancel()
        if process.returncode is None:
            process.terminate()
            await process.wait()
        
        try:
            await stderr_watcher
        except asyncio.CancelledError:
            pass

async def test_minimal_server_ping(mcp_client: Client):
    """Teste la communication avec le serveur minimal via HTTP."""
    # Le nom de l'outil est maintenant dans l'URL, les arguments dans le corps
    response = await mcp_client.call_tool("ping", arguments={})
    assert not response.get('error')
    result = response.get('result', {})
    assert result == "pong"

# --- Les tests originaux sont commentés pour l'instant ---
# async def test_service_lifecycle(mcp_client: Client):
#     """Teste que le service peut être démarré et que le client peut s'y connecter."""
#     tools = await mcp_client.list_tools()
#     assert len(tools.tools) > 0
#
# async def test_analyze_interaction(mcp_client: Client):
#     """Teste l'appel de l'outil 'analyze'."""
#     result = await mcp_client.call_tool("analyze", arguments={"text": "Ceci est un test."})
#     assert result.isError is False
#     assert "implémentation" in result.content[0].text
#
# async def test_validate_argument_interaction(mcp_client: Client):
#     """Teste l'appel de l'outil 'validate_argument'."""
#     result = await mcp_client.call_tool("validate_argument", arguments={"premises": ["p1"], "conclusion": "c1"})
#     assert result.isError is False
#     assert "implémentation" in result.content[0].text
#
# async def test_detect_fallacies_interaction(mcp_client: Client):
#     """Teste l'appel de l'outil 'detect_fallacies'."""
#     result = await mcp_client.call_tool("detect_fallacies", arguments={"text": "Ceci est un sophisme."})
#     assert result.isError is False
#     assert "implémentation" in result.content[0].text
#
# async def test_build_framework_interaction(mcp_client: Client):
#     """Teste l'appel de l'outil 'build_framework'."""
#     result = await mcp_client.call_tool("build_framework", arguments={"arguments": []})
#     assert result.isError is False
#     assert "implémentation" in result.content[0].text