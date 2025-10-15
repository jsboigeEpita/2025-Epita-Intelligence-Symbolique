import sys
import asyncio
import logging
from aiohttp import web

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")


async def handle_health(request):
    """Handler for the /api/health endpoint."""
    logging.info(f"Received GET request for {request.path}")
    return web.json_response({"status": "ok"})


async def handle_all(request):
    """Generic handler for any other endpoint."""
    logging.info(f"Received {request.method} request for {request.path}")
    return web.json_response({"status": "mock_response"}, status=200)


async def main(port):
    """Main function to set up and run the aiohttp server."""
    app = web.Application()
    app.router.add_get("/api/health", handle_health)
    # Add a catch-all route to gracefully handle any other request
    app.router.add_route("*", "/{tail:.*}", handle_all)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", port)

    try:
        await site.start()
        logging.info(f"Fake aiohttp backend started on http://localhost:{port}")
        # THIS IS THE CRITICAL LINE THE ORCHESTRATOR IS WAITING FOR
        logging.info("Application startup complete.")
        # Keep the server running indefinitely
        await asyncio.Event().wait()
    except Exception as e:
        logging.error(f"Error starting fake backend: {e}")
    finally:
        await runner.cleanup()
        logging.info("Fake backend stopped.")


if __name__ == "__main__":
    import os

    # Priorité: variable d'environnement FLASK_RUN_PORT, puis argument CLI, puis 8000
    port_arg_str = os.environ.get("FLASK_RUN_PORT") or (
        sys.argv[1] if len(sys.argv) > 1 else "8000"
    )
    try:
        port_arg = int(port_arg_str)
    except (ValueError, TypeError):
        logging.error(f"Invalid port specified: '{port_arg_str}'.")
        sys.exit(1)

    try:
        asyncio.run(main(port_arg))
    except KeyboardInterrupt:
        logging.info("Shutting down fake backend.")
