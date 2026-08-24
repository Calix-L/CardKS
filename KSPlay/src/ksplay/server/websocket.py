"""JSON/WebSocket front end over the shared room manager."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from websockets.asyncio.server import ServerConnection, serve

from .rooms import RoomManager


class JsonConnection:
    def __init__(self, socket: ServerConnection):
        self.socket = socket

    async def send_json(self, message: dict[str, Any]) -> None:
        await self.socket.send(json.dumps(message, separators=(",", ":")))


async def run_server(host: str, port: int) -> None:
    manager = RoomManager()

    async def handler(socket: ServerConnection) -> None:
        connection = JsonConnection(socket)
        try:
            async for raw in socket:
                try:
                    request = json.loads(raw)
                    if not isinstance(request, dict):
                        raise ValueError("message must be a JSON object")
                    command = request.get("command")
                    if command == "create":
                        room = await manager.create_room(
                            request["game"], request["players"], seed=request.get("seed")
                        )
                        await connection.send_json({"ok": True, "room": room.id})
                    elif command == "join":
                        await manager.join(request["room"], request["seat"], connection)
                        await connection.send_json({"ok": True, "room": request["room"]})
                    elif command == "act":
                        await manager.act(
                            connection,
                            request["room"],
                            seat=request["seat"],
                            action_index=request["action"],
                        )
                    else:
                        raise ValueError("unknown command")
                except (
                    AttributeError,
                    KeyError,
                    PermissionError,
                    RuntimeError,
                    TypeError,
                    ValueError,
                ) as error:
                    await connection.send_json({"ok": False, "error": str(error)})
        finally:
            manager.leave(connection)

    async with serve(
        handler,
        host,
        port,
        max_size=1 << 20,
        ping_interval=20,
        ping_timeout=20,
        close_timeout=5,
    ):
        await asyncio.Future()
