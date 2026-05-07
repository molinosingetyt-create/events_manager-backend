"""Emite eventos a clientes conectados por WebSocket."""

from __future__ import annotations

from app.realtime.hub import hub


async def broadcast_data_changed(tables: list[str]) -> None:
    """Avisar que conviene refrescar listados (por recurso lógico)."""
    if not tables:
        return
    await hub.broadcast_json({"type": "data_changed", "tables": tables})
