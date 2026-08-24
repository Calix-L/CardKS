"""Legal-action container used by the CardKS Rummy table."""

from __future__ import annotations

from typing import Iterable

from ksplay._vendor.rlcard.games.gin_rummy.utils.action_event import ActionEvent

from .types import action_id_to_wire, readonly_action_wire_templates


class Moves:
    def __init__(self, readonly_actions: bool = False) -> None:
        self.action_ids: list[int] = []
        self.action_list: list[list[object]] = []
        self.valid_range = range(0)
        self._wire_templates = (
            readonly_action_wire_templates() if readonly_actions else None
        )
        self._readonly_actions = readonly_actions
        self._small_action_lists: dict[
            tuple[int, ...], list[list[object]]
        ] = {}

    def set_actions(self, actions: Iterable[ActionEvent]) -> None:
        self.set_action_ids(int(action.action_id) for action in actions)

    def set_action_ids(self, action_ids: Iterable[int]) -> None:
        ids = (
            action_ids
            if self._readonly_actions and type(action_ids) is list
            else list(action_ids)
        )
        self.action_ids = ids
        templates = self._wire_templates
        if templates is None:
            self.action_list = [
                action_id_to_wire(action_id) for action_id in ids
            ]
        else:
            if len(ids) <= 2:
                key = tuple(ids)
                cached = self._small_action_lists.get(key)
                if cached is None:
                    cached = [templates[action_id] for action_id in ids]
                    self._small_action_lists[key] = cached
                self.action_list = cached
            else:
                self.action_list = [
                    templates[action_id] for action_id in ids
                ]
        self.valid_range = range(len(ids))

    def __getitem__(self, index: int) -> int:
        return self.action_ids[index]
