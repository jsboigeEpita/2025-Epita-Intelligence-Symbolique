import asyncio
import json
import sys
import httpx
from typing import Any, Dict, Optional

class ClientSession:
    def __init__(self, transport: str = 'stdio', reader=None, writer=None, base_url: Optional[str] = None):
        if transport not in ['stdio', 'http']:
            raise ValueError("Transport must be 'stdio' or 'http'")
        self._transport = transport
        
        if self._transport == 'stdio' and (reader is None or writer is None):
            raise ValueError("Reader and writer must be provided for stdio transport")
        
        if self._transport == 'http' and base_url is None:
            raise ValueError("base_url must be provided for http transport")

        self._reader = reader
        self._writer = writer
        self._base_url = base_url
        self._http_client = None

        self._loop = asyncio.get_running_loop()
        self._request_id = 0
        self._futures = {}
        self._reader_task = None

    async def _reader_loop(self):
        """Tâche de fond pour lire en continu les réponses du serveur (stdio seulement)."""
        try:
            while not self._reader.at_eof():
                response_data = await self._reader.readline()
                if not response_data:
                    break
                response = json.loads(response_data)
                request_id = response.get("id")
                if request_id in self._futures:
                    future = self._futures.pop(request_id)
                    future.set_result(response)
        except Exception as e:
            for future in self._futures.values():
                if not future.done():
                    future.set_exception(e)

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Any:
        self._request_id += 1
        request_id = self._request_id
        
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id,
        }
        
        if self._transport == 'stdio':
            future = self._loop.create_future()
            self._futures[request_id] = future
            
            request_json = json.dumps(request)
            self._writer.write(request_json.encode('utf-8') + b'\n')
            await self._writer.drain()
            
            return await future
        
        elif self._transport == 'http':
            try:
                # L'implémentation réelle du serveur attend probablement une seule route
                # avec un préfixe commun comme /jsonrpc.
                url = f"{self._base_url}/jsonrpc"
                response = await self._http_client.post(url, json=request, timeout=10)
                response.raise_for_status()
                # La réponse devrait être un objet JSON-RPC valide.
                return response.json()
            except httpx.HTTPStatusError as e:
                return {"jsonrpc": "2.0", "error": {"code": e.response.status_code, "message": str(e)}, "id": request_id}
            except Exception as e:
                return {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": request_id}


    async def __aenter__(self):
        if self._transport == 'stdio':
            self._reader_task = self._loop.create_task(self._reader_loop())
        elif self._transport == 'http':
            self._http_client = httpx.AsyncClient()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._transport == 'stdio':
            if self._reader_task:
                self._reader_task.cancel()
                try:
                    await self._reader_task
                except asyncio.CancelledError:
                    pass
            if self._writer and not self._writer.is_closing():
                self._writer.close()
                await self._writer.wait_closed()
        elif self._transport == 'http' and self._http_client:
            await self._http_client.aclose()

    async def initialize(self):
        """Gère la poignée de main d'initialisation."""
        # La réponse à initialize est spéciale et nous l'attendons ici.
        await self._send_request("initialize", {"capabilities": {}})

    async def list_tools(self):
        response = await self._send_request("list_tools", {})
        class MockTools:
            def __init__(self, tools):
                self.tools = tools
        return MockTools(response.get('result', {}).get('tools', []))

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        # On passe directement la méthode (tool_name) et les arguments à _send_request
        # La gestion de la réponse (stdio vs http) est déjà dans _send_request
        response = await self._send_request(tool_name, arguments)

        # Pour le transport HTTP, la réponse est déjà un dict. Pour stdio, on garde l'ancien comportement
        # pour la rétro-compatibilité, même si cela devra être harmonisé plus tard.
        if self._transport == 'stdio':
            class MockResult:
                def __init__(self, content):
                    self.isError = 'error' in content
                    if self.isError:
                        self.content = []
                    else:
                        self.content = [MockContent(content.get('result'))]

            class MockContent:
                def __init__(self, content):
                    self.text = str(content)
            
            return MockResult(response)
        
        # La réponse de _send_request est maintenant directement le dictionnaire JSON-RPC
        return response