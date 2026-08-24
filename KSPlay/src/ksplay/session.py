"""Stable adapter over the three native table state machines."""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Any


GAME_ALIASES = {
    "guandan": "guandan",
    "guan-dan": "guandan",
    "doudizhu": "doudizhu",
    "dou-dizhu": "doudizhu",
    "gin-rummy": "gin-rummy",
    "gin_rummy": "gin-rummy",
    "rummy": "gin-rummy",
}
PLAYER_COUNTS = {"guandan": 4, "doudizhu": 3, "gin-rummy": 2}


def _make_table(game: str, seed: int | None, fast: bool) -> Any:
    rng = Random(seed)
    if game == "guandan":
        from .games.guandan import Environment

        return Environment(seed=seed)
    if game == "doudizhu":
        from .games.doudizhu import Environment
        from .games.doudizhu.types import fmt

        deck = Environment._standard_deck()
        rng.shuffle(deck)
        return Environment(
            deck_data=fmt(deck), first_bidder=rng.randrange(3), training_fast_path=fast
        )
    from .games.gin_rummy import Environment

    return Environment(seed=seed, record_trace=not fast, training_fast_path=fast)


@dataclass(slots=True)
class Session:
    """A lightweight in-process game session with no network work in ``step``."""

    game: str
    seed: int | None = None
    training_fast_path: bool = False
    table: Any = field(init=False, repr=False)
    _started: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        self.table = _make_table(self.game, self.seed, self.training_fast_path)

    @property
    def player_count(self) -> int:
        return PLAYER_COUNTS[self.game]

    @property
    def current_seat(self) -> int:
        seat = int(self.table.state.current_pos)
        if seat < 0:
            pending = getattr(self.table, "pending_double", None)
            if pending:
                return min(pending)
        return seat

    @property
    def legal_actions(self) -> list[list[Any]]:
        return self.table.legal_moves.action_list

    def reset(self, players: list[str]) -> list[Any]:
        if len(players) != self.player_count:
            raise ValueError(f"{self.game} requires {self.player_count} players")
        self.table = _make_table(self.game, self.seed, self.training_fast_path)
        for seat, name in enumerate(players):
            self.table.add_player(str(name), seat)
        self._started = True
        return self.table.start()

    def step(self, seat: int, action_index: int) -> list[Any]:
        if not self._started:
            raise RuntimeError("reset() must be called before step()")
        if not isinstance(action_index, int) or isinstance(action_index, bool):
            raise ValueError("action_index must be an integer")
        if action_index < 0 or action_index >= len(self.legal_actions):
            raise ValueError("action_index is not a legal action")
        if self.game == "guandan":
            payload = {"actIndex": action_index, "player": seat}
            if not self.table.validate(seat, payload):
                raise ValueError("seat cannot act now")
            messages = self.table.loop(payload)
            return self._advance_guandan(messages)
        if self.game == "gin-rummy" and self.training_fast_path:
            return self.table.training_action(seat, action_index)
        return self.table.action(seat, action_index)

    def _advance_guandan(self, messages: list[Any]) -> list[Any]:
        """Run phase boundaries that require no player decision."""

        automatic = {"enter_tribute_stage", "start_new_episode_back_2", "start"}
        while self.table.results is None and self.table.loop.__name__ in automatic:
            messages.extend(self.table.loop())
        return messages

    def close(self) -> None:
        close = getattr(self.table, "close", None)
        if close is not None:
            close()


def make(game: str, *, seed: int | None = None, training_fast_path: bool = False) -> Session:
    """Create a session for GuanDan, DouDizhu, or Gin Rummy."""

    normalized = GAME_ALIASES.get(game.strip().lower()) if isinstance(game, str) else None
    if normalized is None:
        raise ValueError("game must be one of: guandan, doudizhu, gin-rummy")
    return Session(normalized, seed=seed, training_fast_path=training_fast_path)
