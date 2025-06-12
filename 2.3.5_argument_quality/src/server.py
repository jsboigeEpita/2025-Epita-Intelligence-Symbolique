import asyncio
import websockets
import json

class Server:
    def __init__(self):
        self.active_connections = set()
    
    async def start_server(self, host="localhost", port=8765):
        async def handler(websocket, path):
            try:
                await self.handle_connection(websocket)
            except:
                pass

        # Start the server
        server = await websockets.serve(handler, host, port)
        print(f"Serveur démarré sur {host}:{port}")
        
        # Keep the server running forever
        await asyncio.Future()  # Run forever
    
    async def handle_connection(self, websocket):
        self.active_connections.add(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)

                if data['type'] == 'analyze_argument':
                    response = {
                        'type': 'analysis_result',
                        'request_id': data.get('request_id'),
                        'result': 'Mock result'
                    }
                    await websocket.send(json.dumps(response))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.active_connections.remove(websocket)

async def start():
    server = Server()
    await server.start_server()

asyncio.run(start())

