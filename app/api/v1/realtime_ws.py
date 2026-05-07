from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.core.security import decode_token, verify_token_type
from app.realtime.hub import hub

router = APIRouter()


@router.websocket("/ws")
async def realtime_websocket(
    websocket: WebSocket,
    token: Annotated[str, Query(description="JWT access (mismo que Authorization Bearer)")],
) -> None:
    try:
        payload = decode_token(token)
        if not verify_token_type(payload, "access"):
            await websocket.close(code=4401)
            return
    except JWTError:
        await websocket.close(code=4401)
        return

    await hub.register(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await hub.unregister(websocket)
