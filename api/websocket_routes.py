"""WebSocket routes for real-time streaming.

Routes:
    ws://host/ws/analysis/{session_id}     — analysis phase streaming
    ws://host/ws/debate/{session_id}       — debate turn streaming
    ws://host/ws/deliberation/{session_id} — deliberation progress streaming
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from argumentation_analysis.services.websocket_manager import get_websocket_manager

logger = logging.getLogger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/ws/analysis/{session_id}")
async def ws_analysis(websocket: WebSocket, session_id: str):
    """Stream analysis workflow phase results in real time."""
    manager = get_websocket_manager()
    await manager.connect(session_id, websocket)
    try:
        # Keep connection alive — wait for client messages (ping/pong)
        while True:
            data = await websocket.receive_text()
            # Client can send "ping" to keep alive
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(session_id, websocket)


@ws_router.websocket("/ws/debate/{session_id}")
async def ws_debate(websocket: WebSocket, session_id: str):
    """Stream debate turns and scores in real time."""
    manager = get_websocket_manager()
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(session_id, websocket)


@ws_router.websocket("/ws/deliberation/{session_id}")
async def ws_deliberation(websocket: WebSocket, session_id: str):
    """Stream deliberation workflow progress in real time."""
    manager = get_websocket_manager()
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(session_id, websocket)
