"""Two-player Gin Rummy table with a stable CardKS wire protocol."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np
from ksplay._vendor.rlcard.games.gin_rummy.game import GinRummyGame
from ksplay._vendor.rlcard.games.gin_rummy.utils.action_event import (
    DeclareDeadHandAction,
    GinAction,
    KnockAction,
)
from ksplay._vendor.rlcard.games.gin_rummy.utils.move import ScoreNorthMove, ScoreSouthMove

from .moves import Moves
from .types import (
    Msg,
    Phase,
    Player,
    State,
    Wire,
    action_from_id,
    action_id_to_text,
    action_id_to_wire,
    action_to_wire,
)

_PHASE_BY_ACTION_ID = tuple(
    Phase.SCORE if action_id < 2
    else Phase.DRAW if action_id < 5
    else Phase.DISCARD
    for action_id in range(110)
)


def _copy_protocol(value: Any) -> Any:
    if isinstance(value, list):
        return [_copy_protocol(item) for item in value]
    if isinstance(value, dict):
        return {key: _copy_protocol(item) for key, item in value.items()}
    return value


def _copy_play_notification(body: dict[str, Any]) -> dict[str, Any]:
    """Copy the fixed high-frequency ``notify/play`` protocol shape."""
    action = body["curAction"]
    return {
        "type": body["type"],
        "stage": body["stage"],
        "phase": body["phase"],
        "curPos": body["curPos"],
        "curAction": [action[0], action[1], list(action[2])],
        "topDiscard": list(body["topDiscard"]),
        "stockPileNum": body["stockPileNum"],
    }


def _copy_actions(actions: list[list[Any]]) -> list[list[Any]]:
    """Copy the fixed ``[kind, rank, cards]`` action wire shape."""
    return [[action[0], action[1], list(action[2])] for action in actions]


def _copy_action_record(records: list[list[Any]]) -> list[list[Any]]:
    """Copy the fixed ``[player, action_text]`` history wire shape."""
    return [[record[0], record[1]] for record in records]


class Table:
    """CardKS table facade over the bundled Gin Rummy mechanics."""

    PLAYER_COUNT = 2

    def __init__(
        self,
        rounds: int = 1,
        seed: int | None = None,
        allow_step_back: bool = False,
        record_trace: bool = True,
        training_fast_path: bool = False,
    ):
        if not isinstance(rounds, int) or isinstance(rounds, bool) or rounds <= 0:
            raise ValueError("rounds must be a positive integer")
        if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
            raise ValueError("seed must be an integer or null")
        if not isinstance(training_fast_path, bool):
            raise ValueError("training_fast_path must be a boolean")
        self.rounds = rounds
        self.seed = seed
        self.allow_step_back = allow_step_back
        self.record_trace = bool(record_trace)
        self.training_fast_path = training_fast_path
        self.players: list[Player] = []
        self.state = State()
        self.legal_moves = Moves(readonly_actions=training_fast_path)
        self.phase = Phase.DISCARD
        self.loop: Callable[[dict[str, Any]], list[Msg]] = self.play
        self.game = GinRummyGame(allow_step_back=False)
        self.game.np_random = np.random.RandomState(seed)
        self.completed_hands = 0
        self.action_record: list[list[Any]] = []
        self._action_record_window: list[list[Any]] = []
        self.results: list[int] | None = None
        self.trace: list[dict[str, Any]] = []
        self.going_out_card: str | None = None
        self._legal_fresh = False
        self._discard_labels: list[str] = []
        self._top_discard_labels: list[str] = []
        self._dead_labels: list[str] = []
        self._hand_labels: list[list[str]] = [[], []]
        self._known_labels: list[list[str]] = [[], []]
        self._public_info: list[dict[str, int]] = [
            {"rest": 0, "score": 0},
            {"rest": 0, "score": 0},
        ]

    def add_player(self, name: str, index: int) -> None:
        if index != len(self.players) or index not in range(self.PLAYER_COUNT):
            raise ValueError("players must be added in seat order 0, 1")
        self.players.append(Player(name, index))

    def start(self) -> list[Msg]:
        if len(self.players) != self.PLAYER_COUNT:
            raise ValueError("table requires exactly two players")
        self.completed_hands = 0
        self.results = None
        self.trace = []
        for player in self.players:
            player.score = 0
        messages: list[Msg] = []
        self._start_hand(messages)
        return messages

    def _start_hand(self, messages: list[Msg]) -> None:
        _, current = self.game.init_game(return_state=False)
        self.action_record = []
        self._action_record_window = []
        self.going_out_card = None
        self._discard_labels = [
            card._gin_rummy_index
            for card in self.game.round.dealer.discard_pile
        ]
        self._top_discard_labels = self._discard_labels[-1:]
        self._dead_labels = self._discard_labels[:-1]
        self._hand_labels = [
            [card._gin_rummy_index for card in player.hand]
            for player in self.game.round.players
        ]
        self._known_labels = [
            [card._gin_rummy_index for card in player.known_cards]
            for player in self.game.round.players
        ]
        self._public_info = [
            {
                "rest": len(self._hand_labels[position]),
                "score": self.players[position].score,
            }
            for position in range(self.PLAYER_COUNT)
        ]
        self._legal_fresh = False
        self.state.current_pos = int(current)
        self._refresh_legal()
        hand_no = self.completed_hands + 1
        dealer = int(self.game.round.dealer_id)
        for position in range(self.PLAYER_COUNT):
            hand = self._hand_labels[position].copy()
            messages.append(Msg(
                position,
                Wire.notify_beginning(hand, position, dealer, hand_no, self.rounds),
            ))
        self._act(messages)

    def play(self, content: dict[str, Any]) -> list[Msg]:
        index = content.get("actIndex")
        if not isinstance(index, int) or isinstance(index, bool) or index not in self.legal_moves.valid_range:
            raise ValueError("actIndex is not legal")
        return self._play_index(index)

    def _play_index(self, index: int) -> list[Msg]:
        self._push_trace()
        player = self.state.current_pos
        action_id = self.legal_moves[index]
        event = action_from_id(action_id)
        wire_action = (
            self.legal_moves.action_list[index]
            if self.training_fast_path
            else action_id_to_wire(action_id)
        )
        hand_before = (
            list(self.game.round.players[player].hand)
            if action_id == 5 else None
        )
        self._legal_fresh = False
        self.game._step_action_id(action_id, event)
        is_over = self.game.round.is_over
        if action_id == 3:
            picked_up_label = self._discard_labels.pop()
            self._top_discard_labels.clear()
            if self._dead_labels:
                self._top_discard_labels.append(self._dead_labels.pop())
            self._hand_labels[player].append(picked_up_label)
            self._known_labels[player].append(picked_up_label)
        elif action_id == 2:
            self._hand_labels[player].append(
                self.game.round.players[player].hand[-1]._gin_rummy_index
            )
        elif 6 <= action_id < 58:
            discarded_label = event.card._gin_rummy_index
            self._discard_labels.append(discarded_label)
            if self._top_discard_labels:
                self._dead_labels.append(self._top_discard_labels[0])
                self._top_discard_labels[0] = discarded_label
            else:
                self._top_discard_labels.append(discarded_label)
            self._hand_labels[player].remove(discarded_label)
            if discarded_label in self._known_labels[player]:
                self._known_labels[player].remove(discarded_label)
        if action_id == 5 or action_id >= 58:
            if action_id >= 58:
                outgoing = event.card
            else:
                hand_after = self.game.round.players[player].hand
                removed = [
                    card for card in hand_before if card not in hand_after
                ]
                if len(removed) != 1:
                    raise RuntimeError(
                        "going-out action must remove exactly one card"
                    )
                outgoing = removed[0]
            # RLCard 1.2.0 removes the going-out card from the hand but does not
            # place it in the discard pile. Restore the physical/public card
            # zone invariant without changing legal actions or RLCard payoffs.
            self.game.round.dealer.discard_pile.append(outgoing)
            outgoing_label = outgoing._gin_rummy_index
            self._discard_labels.append(outgoing_label)
            if self._top_discard_labels:
                self._dead_labels.append(self._top_discard_labels[0])
                self._top_discard_labels[0] = outgoing_label
            else:
                self._top_discard_labels.append(outgoing_label)
            self._hand_labels[player].remove(outgoing_label)
            if outgoing_label in self._known_labels[player]:
                self._known_labels[player].remove(outgoing_label)
            self.going_out_card = outgoing_label
        self._public_info[player]["rest"] = len(
            self._hand_labels[player]
        )
        record = [player, action_id_to_text(action_id)]
        self.action_record.append(record)
        self._action_record_window.append(record)
        if len(self._action_record_window) > 20:
            del self._action_record_window[0]
        messages: list[Msg] = []
        play_body = {
            "type": "notify",
            "stage": "play",
            "phase": self.phase if not is_over else Phase.GAME_OVER,
            "curPos": player,
            "curAction": wire_action,
            "topDiscard": (
                self._top_discard_labels
                if self.training_fast_path
                else self._top_discard_labels.copy()
            ),
            "stockPileNum": len(self.game.round.dealer.stock_pile),
        }
        if self.training_fast_path:
            messages.append(Msg(self.players[0].pos, play_body))
            messages.append(Msg(self.players[1].pos, play_body))
        else:
            self._broadcast(messages, play_body)
        if is_over:
            self._finish_hand(messages)
            return messages
        self.state.current_pos = int(self.game.round.current_player_id)
        self._refresh_legal()
        self._act(messages)
        return messages

    def validate(self, pos: int, action: dict[str, Any]) -> bool:
        index = action.get("actIndex")
        return (
            self.phase != Phase.GAME_OVER
            and isinstance(index, int)
            and not isinstance(index, bool)
            and index in self.legal_moves.valid_range
            and pos == self.state.current_pos
        )

    def action(self, pos: int, act_index: int) -> list[Msg]:
        if (
            self.phase == Phase.GAME_OVER
            or not isinstance(act_index, int)
            or isinstance(act_index, bool)
            or act_index not in self.legal_moves.valid_range
            or pos != self.state.current_pos
        ):
            raise ValueError("invalid action")
        return self._play_index(act_index)

    def training_action(self, pos: int, act_index: int) -> list[Msg]:
        """Apply an index obtained from this table's current read-only act."""
        if not self.training_fast_path:
            raise RuntimeError(
                "training_action requires training_fast_path=True"
            )
        if pos != self.state.current_pos:
            raise ValueError("invalid action player")
        return self._play_index(act_index)

    def timeout_action(self, pos: int) -> list[Msg]:
        if pos != self.state.current_pos or not self.legal_moves.action_list:
            raise ValueError("invalid timeout player")
        # Forced choices stay forced; otherwise prefer stock draw and the first
        # deterministic discard. Tournament clients should supply a real policy.
        preferred = ["Draw", "stock", []]
        index = self.legal_moves.action_list.index(preferred) if preferred in self.legal_moves.action_list else 0
        return self.action(pos, index)

    def close(self) -> None:
        """Release the Game/Judge reference cycle after the table is retired."""
        game = self.game
        judge = getattr(game, "judge", None)
        if judge is not None and getattr(judge, "game", None) is game:
            judge.game = None

    def _refresh_legal(self) -> None:
        if self._legal_fresh:
            return
        action_ids = self.game.judge.get_legal_action_ids()
        if not action_ids:
            self.phase = Phase.GAME_OVER
            self.legal_moves.set_action_ids(())
            self._legal_fresh = True
            return
        self.legal_moves.set_action_ids(action_ids)
        self.phase = _PHASE_BY_ACTION_ID[action_ids[0]]
        self.loop = self.play
        self._legal_fresh = True

    def _phase_for_legal_actions(self) -> str:
        if not self.legal_moves.action_ids:
            return Phase.GAME_OVER
        action_id = self.legal_moves.action_ids[0]
        if action_id in (2, 3, 4):
            return Phase.DRAW
        if action_id in (0, 1):
            return Phase.SCORE
        return Phase.DISCARD

    def _act(self, messages: list[Msg]) -> None:
        pos = self.state.current_pos
        if self.training_fast_path:
            action_list = self.legal_moves.action_list
            action_record = self._action_record_window
            hand_cards = self._hand_labels[pos]
            opponent_known_cards = self._known_labels[(pos + 1) % 2]
            dead_cards = self._dead_labels
            public_info = self._public_info
        else:
            action_list = _copy_actions(self.legal_moves.action_list)
            action_record = _copy_action_record(self.action_record[-20:])
            hand_cards = self._hand_labels[pos].copy()
            opponent_known_cards = (
                self._known_labels[(pos + 1) % 2].copy()
            )
            dead_cards = self._dead_labels.copy()
            public_info = [
                {
                    "rest": len(self._hand_labels[0]),
                    "score": self.players[0].score,
                },
                {
                    "rest": len(self._hand_labels[1]),
                    "score": self.players[1].score,
                },
            ]
        body = {
            "type": "act",
            "stage": self.phase,
            "handCards": hand_cards,
            "publicInfo": public_info,
            "curPos": pos,
            "actionList": action_list,
            "indexRange": len(action_list) - 1,
            "topDiscard": (
                self._top_discard_labels
                if self.training_fast_path
                else self._top_discard_labels.copy()
            ),
            "deadCards": dead_cards,
            "opponentKnownCards": opponent_known_cards,
            "stockPileNum": len(self.game.round.dealer.stock_pile),
            "actionRecord": action_record,
            "dealer": int(self.game.round.dealer_id),
            "handNo": self.completed_hands + 1,
        }
        messages.append(Msg(pos, body))

    def _finish_hand(self, messages: list[Msg]) -> None:
        deadwood = self._deadwood_counts()
        hand_scores, winner = self._hand_scores(deadwood)
        payoffs = [float(value) for value in self.game.judge.scorer.get_payoffs(self.game)]
        for position, score in enumerate(hand_scores):
            self.players[position].score += score
        self.completed_hands += 1
        going_out = self.game.round.going_out_action
        result = {
            "winner": winner,
            "dealer": int(self.game.round.dealer_id),
            "goingOutPlayer": (
                None if self.game.round.going_out_player_id is None
                else int(self.game.round.going_out_player_id)
            ),
            "goingOutAction": None if going_out is None else action_to_wire(going_out),
            "goingOutCard": self.going_out_card,
            "deadwoodCounts": deadwood,
            "handScores": hand_scores,
            "totalScores": [player.score for player in self.players],
            "rlcardPayoffs": payoffs,
            "restCards": [
                [position, self._hand_labels[position].copy()]
                for position in range(self.PLAYER_COUNT)
            ],
        }
        self._broadcast(messages, Wire.notify_episode_over(result))
        if self.completed_hands >= self.rounds:
            self.phase = Phase.GAME_OVER
            self.state.current_pos = -1
            self.legal_moves.set_actions([])
            self.results = [player.score for player in self.players]
            self._broadcast(messages, Wire.notify_game_over(self.completed_hands, self.rounds))
            self._broadcast(messages, Wire.notify_game_result(self.results))
        else:
            self._start_hand(messages)

    def _deadwood_counts(self) -> list[int]:
        north = next(move for move in reversed(self.game.round.move_sheet) if isinstance(move, ScoreNorthMove))
        south = next(move for move in reversed(self.game.round.move_sheet) if isinstance(move, ScoreSouthMove))
        return [int(north.deadwood_count), int(south.deadwood_count)]

    def _hand_scores(self, deadwood: list[int]) -> tuple[list[int], int | None]:
        going_out = self.game.round.going_out_action
        raw_going_pos = self.game.round.going_out_player_id
        going_pos = None if raw_going_pos is None else int(raw_going_pos)
        if going_pos is None or isinstance(going_out, DeclareDeadHandAction):
            return [0, 0], None
        opponent = (going_pos + 1) % self.PLAYER_COUNT
        if isinstance(going_out, GinAction):
            points = deadwood[opponent] + 25
            winner = going_pos
        elif isinstance(going_out, KnockAction):
            difference = deadwood[opponent] - deadwood[going_pos]
            if difference > 0:
                points = difference
                winner = going_pos
            else:
                points = -difference + 25
                winner = opponent
        else:
            return [0, 0], None
        scores = [0, 0]
        scores[winner] = points
        scores[(winner + 1) % self.PLAYER_COUNT] = -points
        return scores, winner

    def _top_discard(self) -> list[str]:
        return self._top_discard_labels.copy()

    def _broadcast(self, messages: list[Msg], body: dict[str, Any]) -> None:
        if self.training_fast_path:
            messages.append(Msg(self.players[0].pos, body))
            messages.append(Msg(self.players[1].pos, body))
            return
        if body.get("stage") == "play":
            north_body = body
            south_body = _copy_play_notification(body)
        else:
            north_body, south_body = body, _copy_protocol(body)
        messages.append(Msg(self.players[0].pos, north_body))
        messages.append(Msg(self.players[1].pos, south_body))

    def _push_trace(self) -> None:
        if not self.record_trace:
            return
        self.trace.append({
            "phase": self.phase,
            "player": self.state.current_pos,
            "legal_actions": _copy_actions(self.legal_moves.action_list),
            "action_record": _copy_action_record(self.action_record),
        })
