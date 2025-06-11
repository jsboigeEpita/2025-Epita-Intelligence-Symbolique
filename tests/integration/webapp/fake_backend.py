import sys
import asyncio
import logging
from aiohttp import web

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def handle_health(request):
    """Handler for the /api/health endpoint."""
    logging.info(f"Received GET request for {request.path}")
    return web.json_response({'status': 'ok'})

async def handle_all(request):
    """Generic handler for any other endpoint."""
    logging.info(f"Received {request.method} request for {request.path}")
    return web.json_response({'status': 'mock_response'}, status=200)

async def main(port):
    """Main function to set up and run the aiohttp server."""
    app = web.Application()
    app.router.add_get('/api/health', handle_health)
    # Add a catch-all route to gracefully handle any other request
    app.router.add_route('*', '/{tail:.*}', handle_all)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', port)
    
    try:
        await site.start()
        logging.info(f"Fake aiohttp backend started on http://localhost:{port}")
        # Keep the server running indefinitely
        await asyncio.Event().wait()
    except Exception as e:
        logging.error(f"Error starting fake backend: {e}")
    finally:
        await runner.cleanup()
        logging.info("Fake backend stopped.")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            port_arg = int(sys.argv[1])
        except ValueError:
            logging.error(f"Invalid port '{sys.argv[1]}'. Must be an integer.")
            sys.exit(1)
    else:
        port_arg = 8000

    try:
        asyncio.run(main(port_arg))
    except KeyboardInterrupt:
        logging.info("Shutting down fake backend.")