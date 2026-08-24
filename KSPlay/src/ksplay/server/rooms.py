"""Connection-bound rooms shared by all game adapters."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from secrets import token_urlsafe
from typing import Any, Protocol

from ksplay import Session, make


class Connection(Protocol):
    async def send_json(self, message: dict[str, Any]) -> None: ...


@dataclass(slots=True)
class Room:
    id: str
    session: Session
    players: list[str]
    opening_messages: list[Any]
    seats: dict[int, Connection] = field(default_factory=dict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class RoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}
        self._bindings: dict[Connection, tuple[str, int]] = {}

    async def create_room(self, game: str, players: list[str], *, seed: int | None = None) -> Room:
        session = make(game, seed=seed)
        opening_messages = session.reset(players)
        room = Room(token_urlsafe(9), session, list(players), opening_messages)
        self.rooms[room.id] = room
        return room

    async def join(self, room_id: str, seat: int, connection: Connection) -> Room:
        room = self._room(room_id)
        if not isinstance(seat, int) or isinstance(seat, bool) or seat not in range(room.session.player_count):
            raise ValueError("seat is out of range")
        if seat in room.seats and room.seats[seat] is not connection:
            raise PermissionError("seat is already occupied")
        old = self._bindings.get(connection)
        if old is not None and old != (room_id, seat):
            raise PermissionError("connection is already bound to another seat")
        room.seats[seat] = connection
        self._bindings[connection] = (room_id, seat)
        for message in room.opening_messages:
            if int(message.seat) == seat:
                await connection.send_json(message.body)
        return room

    async def act(
        self, connection: Connection, room_id: str, *, seat: int, action_index: int
    ) -> list[Any]:
        room = self._room(room_id)
        if self._bindings.get(connection) != (room_id, seat):
            raise PermissionError("connection is not bound to this seat")
        if len(room.seats) != room.session.player_count:
            raise RuntimeError("all players must join before play begins")
        if not isinstance(action_index, int) or isinstance(action_index, bool):
            raise ValueError("action_index must be a legal action index")
        if action_index < 0 or action_index >= len(room.session.legal_actions):
            raise ValueError("action_index must be a legal action index")
        async with room.lock:
            messages = room.session.step(seat, action_index)
            await self._deliver(room, messages)
            return messages

    def leave(self, connection: Connection) -> None:
        binding = self._bindings.pop(connection, None)
        if binding is not None:
            room = self.rooms.get(binding[0])
            if room is not None:
                room.seats.pop(binding[1], None)

    def _room(self, room_id: str) -> Room:
        try:
            return self.rooms[room_id]
        except KeyError as error:
            raise KeyError("room does not exist") from error

    @staticmethod
    async def _deliver(room: Room, messages: list[Any]) -> None:
        for message in messages:
            connection = room.seats.get(int(message.seat))
            if connection is not None:
                await connection.send_json(message.body)
