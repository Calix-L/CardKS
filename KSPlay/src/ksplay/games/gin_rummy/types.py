"""Public types and wire messages for the KSPlay Gin Rummy engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NamedTuple

from ksplay._vendor.rlcard.games.gin_rummy.utils.action_event import (
    ActionEvent,
    DeclareDeadHandAction,
    DiscardAction,
    DrawCardAction,
    GinAction,
    KnockAction,
    PickUpDiscardAction,
    ScoreNorthPlayerAction,
    ScoreSouthPlayerAction,
)


class Phase:
    DRAW = "draw"
    DISCARD = "discard"
    SCORE = "score"
    GAME_OVER = "gameOver"


@dataclass(slots=True)
class Player:
    name: str
    pos: int
    score: int = 0


@dataclass(slots=True)
class State:
    current_pos: int = -1


class Msg(NamedTuple):
    seat: int
    body: dict[str, Any]


def action_to_wire(action: ActionEvent) -> list[Any]:
    if isinstance(action, DrawCardAction):
        return ["Draw", "stock", []]
    if isinstance(action, PickUpDiscardAction):
        return ["Draw", "discard", []]
    if isinstance(action, DeclareDeadHandAction):
        return ["DeclareDead", "dead", []]
    if isinstance(action, GinAction):
        return ["Gin", "gin", []]
    if isinstance(action, DiscardAction):
        card = action.card.get_index()
        return ["Discard", action.card.rank, [card]]
    if isinstance(action, KnockAction):
        card = action.card.get_index()
        return ["Knock", action.card.rank, [card]]
    if isinstance(action, ScoreNorthPlayerAction):
        return ["Score", "N", []]
    if isinstance(action, ScoreSouthPlayerAction):
        return ["Score", "S", []]
    raise ValueError(f"unsupported Gin Rummy action: {action!r}")


# Table transitions repeatedly use the same 110 immutable action identities.
# Decode them once, and keep immutable wire/text templates beside them. Public
# callers still receive fresh nested lists through ``action_id_to_wire``.
_ACTION_EVENTS = tuple(
    ActionEvent.decode_action(action_id) for action_id in range(110)
)
_ACTION_WIRE_TEMPLATES = tuple(
    action_to_wire(action) for action in _ACTION_EVENTS
)
_ACTION_TEXT = tuple(str(action) for action in _ACTION_EVENTS)


def action_from_id(action_id: int) -> ActionEvent:
    return _ACTION_EVENTS[action_id]


def action_id_to_wire(action_id: int) -> list[Any]:
    template = _ACTION_WIRE_TEMPLATES[action_id]
    return [template[0], template[1], list(template[2])]


def readonly_action_wire_templates() -> tuple[list[Any], ...]:
    """Return all shared templates once for an internal trusted fast path."""
    return _ACTION_WIRE_TEMPLATES


def action_id_to_text(action_id: int) -> str:
    return _ACTION_TEXT[action_id]


class Wire:
    @staticmethod
    def notify_beginning(
        hand_cards: list[str], seat: int, dealer: int, hand_no: int, rounds: int,
    ) -> dict[str, Any]:
        return {
            "type": "notify",
            "stage": "beginning",
            "handCards": hand_cards,
            "myPos": seat,
            "dealer": dealer,
            "handNo": hand_no,
            "rounds": rounds,
        }

    @staticmethod
    def notify_play(
        player: int,
        action: list[Any],
        phase: str,
        top_discard: list[str],
        stock_count: int,
    ) -> dict[str, Any]:
        return {
            "type": "notify",
            "stage": "play",
            "phase": phase,
            "curPos": player,
            "curAction": action,
            "topDiscard": top_discard,
            "stockPileNum": stock_count,
        }

    @staticmethod
    def notify_episode_over(result: dict[str, Any]) -> dict[str, Any]:
        return {"type": "notify", "stage": "episodeOver", **result}

    @staticmethod
    def notify_game_over(completed: int, rounds: int) -> dict[str, Any]:
        return {"type": "notify", "stage": "gameOver", "curTimes": completed, "settingTimes": rounds}

    @staticmethod
    def notify_game_result(scores: list[int]) -> dict[str, Any]:
        return {"type": "notify", "stage": "gameResult", "scores": scores}

    @staticmethod
    def act(
        *,
        stage: str,
        hand_cards: list[str],
        public_info: list[dict[str, Any]],
        cur_pos: int,
        action_list: list[list[Any]],
        top_discard: list[str],
        dead_cards: list[str],
        opponent_known_cards: list[str],
        stock_count: int,
        action_record: list[list[Any]],
        dealer: int,
        hand_no: int,
    ) -> dict[str, Any]:
        return {
            "type": "act",
            "stage": stage,
            "handCards": hand_cards,
            "publicInfo": public_info,
            "curPos": cur_pos,
            "actionList": action_list,
            "indexRange": len(action_list) - 1,
            "topDiscard": top_discard,
            "deadCards": dead_cards,
            "opponentKnownCards": opponent_known_cards,
            "stockPileNum": stock_count,
            "actionRecord": action_record,
            "dealer": dealer,
            "handNo": hand_no,
        }
