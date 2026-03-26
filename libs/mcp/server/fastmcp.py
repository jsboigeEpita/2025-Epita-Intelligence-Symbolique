import asyncio
import json
import logging
import sys
from unittest.mock import MagicMock

class Context:
    def __init__(self):
        self.request_context = MagicMock()
        self.request_context.session.lifespan_context = "mock_lifespan_context"

class FastMCP:
    def __init__(self, service_name, host, port, lifespan):
        self.service_name = service_name
        self.lifespan = lifespan
        self.tools = {}
        self.logger = logging.getLogger(f"FastMCP.{service_name}")

    def tool(self):
        def decorator(f):
            self.tools[f.__name__] = f
            return f
        return decorator

    async def _handle_request(self, request_data: dict, context: Context):
        method = request_data.get("method")
        params = request_data.get("params", {})
        request_id = request_data.get("id")

        if not method or not request_id:
            return {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": None}

        if method == "initialize":
            # La poignée de main est gérée, on retourne simplement les capacités (vides pour l'instant)
            return {"jsonrpc": "2.0", "result": {"capabilities": {}}, "id": request_id}
        
        if method == "list_tools":
            return {"jsonrpc": "2.0", "result": {"tools": list(self.tools.keys())}, "id": request_id}

        tool_func = self.tools.get(method)
        if not tool_func:
            return {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": request_id}

        try:
            # Gérer les arguments de la fonction. `context` est spécial.
            import inspect
            sig = inspect.signature(tool_func)
            if 'context' in sig.parameters:
                result = await tool_func(context=context, **params)
            else:
                result = await tool_func(**params)
            return {"jsonrpc": "2.0", "result": result, "id": request_id}
        except Exception as e:
            self.logger.error(f"Error calling tool {method}: {e}", exc_info=True)
            return {"jsonrpc": "2.0", "error": {"code": -32603, "message": "Internal error", "data": str(e)}, "id": request_id}


    async def run_stdio(self, reader, writer, lifespan_context):
        """Exécute le serveur en mode stdio."""
        self.logger.info("MCP Server started in stdio mode.")
        print("MCP Server started", file=sys.stderr, flush=True) # Signal pour le client de test

        context = Context()
        context.request_context.session.lifespan_context = lifespan_context

        while not reader.at_eof():
            try:
                line = await reader.readline()
                if not line:
                    continue
                
                self.logger.debug(f"Received raw: {line.strip()}")
                request_data = json.loads(line)
                
                response = await self._handle_request(request_data, context)
                
                response_json = json.dumps(response)
                self.logger.debug(f"Sending raw: {response_json}")
                writer.write(response_json.encode('utf-8') + b'\n')
                await writer.drain()

            except json.JSONDecodeError as e:
                self.logger.error(f"JSON Decode Error: {e}. Line: {line.strip()}")
                error_response = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}
                writer.write(json.dumps(error_response).encode('utf-8') + b'\n')
                await writer.drain()
            except Exception as e:
                self.logger.error(f"An unexpected error occurred: {e}", exc_info=True)


    def run(self, transport: str):
        """Point d'entrée pour lancer le serveur."""
        if transport != 'streamable-http': # Pour les tests, on force stdio
            self.logger.error(f"Transport '{transport}' non supporté par cette implémentation mock.")
            return

        async def main():
            self.logger.info("Initializing lifespan...")
            async with self.lifespan(self) as lifespan_context:
                reader = asyncio.StreamReader()
                writer_protocol = asyncio.StreamReaderProtocol(reader)
                
                loop = asyncio.get_running_loop()
                
                # Remplacer sys.stdin par un reader asyncio
                await loop.connect_read_pipe(lambda: writer_protocol, sys.stdin)
                
                # Remplacer sys.stdout par un writer asyncio
                writer_transport, writer_protocol = await loop.connect_write_pipe(
                    asyncio.streams.FlowControlMixin, sys.stdout
                )
                writer = asyncio.StreamWriter(writer_transport, writer_protocol, reader, loop)

                await self.run_stdio(reader, writer, lifespan_context)

        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            self.logger.info("Server stopped by user.")