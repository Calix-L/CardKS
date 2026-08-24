from __future__ import annotations

from dataclasses import dataclass

import pytest

from ksplay.server.rooms import RoomManager


@dataclass(eq=False)
class Connection:
    sent: list[dict]

    async def send_json(self, message: dict) -> None:
        self.sent.append(message)


@pytest.mark.asyncio
async def test_connection_cannot_act_for_another_seat() -> None:
    manager = RoomManager()
    room = await manager.create_room("guandan", ["a", "b", "c", "d"], seed=3)
    first = Connection([])
    second = Connection([])
    await manager.join(room.id, 0, first)
    await manager.join(room.id, 1, second)

    with pytest.raises(PermissionError, match="seat"):
        await manager.act(second, room.id, seat=0, action_index=0)


@pytest.mark.asyncio
async def test_action_index_must_be_legal() -> None:
    manager = RoomManager()
    room = await manager.create_room("gin-rummy", ["a", "b"], seed=3)
    connection = Connection([])
    await manager.join(room.id, room.session.current_seat, connection)
    other_seat = 1 - room.session.current_seat
    await manager.join(room.id, other_seat, Connection([]))

    with pytest.raises(ValueError, match="legal action"):
        await manager.act(
            connection,
            room.id,
            seat=room.session.current_seat,
            action_index=len(room.session.legal_actions),
        )


@pytest.mark.asyncio
async def test_joining_player_receives_their_opening_state() -> None:
    manager = RoomManager()
    room = await manager.create_room("gin-rummy", ["a", "b"], seed=3)
    connection = Connection([])

    await manager.join(room.id, 0, connection)

    assert any(message.get("stage") == "beginning" for message in connection.sent)


@pytest.mark.asyncio
async def test_room_waits_for_every_connection_before_play() -> None:
    manager = RoomManager()
    room = await manager.create_room("gin-rummy", ["a", "b"], seed=3)
    connection = Connection([])
    await manager.join(room.id, room.session.current_seat, connection)

    with pytest.raises(RuntimeError, match="all players"):
        await manager.act(
            connection,
            room.id,
            seat=room.session.current_seat,
            action_index=0,
        )
