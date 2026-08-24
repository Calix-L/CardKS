"""Legal move list facade for the bundled DouDizhu engine."""

from __future__ import annotations

from typing import Sequence

from .rules import (
    DOUBLE_ACTIONS,
    REDOUBLE_ACTIONS,
    bid_actions,
    first_actions,
    first_actions_readonly,
    second_actions,
    second_actions_readonly,
)
from .types import Move


class Moves:
    def __init__(self, readonly_actions: bool = False) -> None:
        self.action_list: list[list[object]] = []
        self.valid_range = range(0)
        self.readonly_actions = readonly_actions

    def __len__(self) -> int:
        return len(self.action_list)

    def __getitem__(self, item: int) -> Move:
        return Move(*self.action_list[item])

    def _set(self, actions: list[list[object]]) -> None:
        self.action_list = actions
        self.valid_range = range(len(actions))

    def parse_bid_action(self, highest_bid: int) -> None:
        self._set(bid_actions(highest_bid))

    def parse_double_action(self) -> None:
        self._set([list(action) for action in DOUBLE_ACTIONS])

    def parse_redouble_action(self) -> None:
        self._set([list(action) for action in REDOUBLE_ACTIONS])

    def parse_first_action(self, hand_cards: Sequence[object]) -> None:
        actions = (
            first_actions_readonly(hand_cards)
            if self.readonly_actions
            else first_actions(hand_cards)
        )
        self._set(actions)

    def parse_second_action(self, hand_cards: Sequence[object], greater_action: Move | Sequence[object]) -> None:
        target = greater_action.to_json() if isinstance(greater_action, Move) else list(greater_action)
        actions = (
            second_actions_readonly(hand_cards, target)
            if self.readonly_actions
            else second_actions(hand_cards, target)
        )
        self._set(actions)
