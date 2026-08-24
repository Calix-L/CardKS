"""Three-player competitive Dou Dizhu table state machine.

The public shape follows KSPlay's Python ``Table`` contract:
``players``, ``state``, ``legal_moves``, a phase handler stored in ``loop``,
``start()``, ``validate()`` and lists of targeted ``Msg`` objects.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from random import randint, shuffle
from typing import Any, Callable

from .moves import Moves
from .types import Card, Move, Msg, Phase, Player, Trick, Wire, card_sort_key, fmt, parse


def _copy_actions(actions: list[list[object]]) -> list[list[object]]:
    """Copy the fixed three-field wire shape without generic deepcopy overhead."""

    return [
        [action[0], action[1], action[2].copy()] if type(action[2]) is list else action.copy()
        for action in actions
    ]


def _copy_wire(value: Any) -> Any:
    """Copy JSON-shaped wire data without deepcopy's memo/dispatch machinery."""

    value_type = type(value)
    if value_type is list:
        return [
            _copy_wire(item) if type(item) is list or type(item) is dict else item
            for item in value
        ]
    if value_type is dict:
        return {
            key: _copy_wire(item) if type(item) is list or type(item) is dict else item
            for key, item in value.items()
        }
    return value


def _copy_wire_three(value: Any) -> tuple[Any, Any, Any]:
    """Build three independent wire copies in one recursive traversal."""

    value_type = type(value)
    if value_type is list:
        left: list[Any] = []
        middle: list[Any] = []
        right: list[Any] = []
        for item in value:
            item_type = type(item)
            if item_type is list or item_type is dict:
                first, second, third = _copy_wire_three(item)
            else:
                first = second = third = item
            left.append(first)
            middle.append(second)
            right.append(third)
        return left, middle, right
    if value_type is dict:
        left_dict: dict[Any, Any] = {}
        middle_dict: dict[Any, Any] = {}
        right_dict: dict[Any, Any] = {}
        for key, item in value.items():
            item_type = type(item)
            if item_type is list or item_type is dict:
                first, second, third = _copy_wire_three(item)
            else:
                first = second = third = item
            left_dict[key] = first
            middle_dict[key] = second
            right_dict[key] = third
        return left_dict, middle_dict, right_dict
    return value, value, value


STANDARD_DECK = tuple(
    [Card(suit, rank) for suit in ("S", "H", "C", "D") for rank in (
        "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A", "2"
    )]
    + [Card("S", "B"), Card("H", "R")]
)


class Table:
    PLAYER_COUNT = 3

    def __init__(
        self,
        allow_step_back: bool = False,
        rounds: int = 1,
        deck_data: list[str] | None = None,
        first_bidder: int | None = None,
        first_player: int | None = None,
        training_fast_path: bool = False,
    ):
        if first_player is not None:
            if first_bidder is not None and first_bidder != first_player:
                raise ValueError("first_bidder and first_player disagree")
            first_bidder = first_player
        if not isinstance(rounds, int) or isinstance(rounds, bool) or rounds <= 0:
            raise ValueError("rounds must be a positive integer")
        if first_bidder is not None and first_bidder not in range(self.PLAYER_COUNT):
            raise ValueError("first_bidder must be between 0 and 2")
        if not isinstance(training_fast_path, bool):
            raise ValueError("training_fast_path must be a boolean")

        self.rounds = rounds
        self.allow_step_back = allow_step_back
        self.training_fast_path = training_fast_path
        self.deck_data = list(deck_data) if deck_data is not None else None
        self.first_bidder = first_bidder
        self.players: list[Player] = []
        self.state = Trick()
        self.legal_moves = Moves(readonly_actions=training_fast_path)
        self.loop: Callable[[dict[str, Any]], list[Msg]] = self.start  # type: ignore[assignment]
        self.phase = Phase.BID

        self.bottom_cards: list[Card] = []
        self.deck: list[Card] = []
        self.landlord = -1
        self.base_score = 0
        self.highest_bid = 0
        self.highest_bidder = -1
        self.bid_count = 0
        self.bids: dict[int, int] = {}
        self.pending_double: set[int] = set()
        self.doubles: dict[int, bool] = {}
        self.redouble = False
        self.rocket_count = 0
        self.bomb_count = 0
        self.completed_hands = 0
        self.deal_attempt = 0
        self.results: list[int] | None = None
        self.trace: list[dict[str, Any]] = []

        self._fixed_deck_used = False
        if self.deck_data is not None:
            self._validate_deck(self.deck_data)

    # --- lifecycle ---------------------------------------------------------

    def add_player(self, name: str, index: int) -> None:
        if index != len(self.players) or index not in range(self.PLAYER_COUNT):
            raise ValueError("players must be added in seat order 0, 1, 2")
        self.players.append(Player(name, index))

    def start(self) -> list[Msg]:
        if len(self.players) != self.PLAYER_COUNT:
            raise ValueError("table requires exactly three players")
        self.completed_hands = 0
        self.results = None
        self.trace = []
        self._fixed_deck_used = False
        for player in self.players:
            player.score = 0
        messages: list[Msg] = []
        self._start_hand(messages, redeal=False)
        return messages

    def _start_hand(self, messages: list[Msg], redeal: bool) -> None:
        self.deal_attempt += 1
        for player in self.players:
            player.reset_hand()

        self.deck = self._next_deck()
        self.deal()

        self.landlord = -1
        self.base_score = 0
        self.highest_bid = 0
        self.highest_bidder = -1
        self.bid_count = 0
        self.bids = {}
        self.pending_double = set()
        self.doubles = {}
        self.redouble = False
        self.rocket_count = 0
        self.bomb_count = 0
        self.state = Trick()

        if self.first_bidder is None:
            bidder = randint(0, self.PLAYER_COUNT - 1) if not redeal else self.deal_attempt % self.PLAYER_COUNT
        else:
            bidder = (self.first_bidder + self.deal_attempt - 1) % self.PLAYER_COUNT
        self.state.current_pos = bidder
        self.phase = Phase.BID
        self.loop = self.bid
        self.legal_moves.parse_bid_action(0)

        hand_no = self.completed_hands + 1
        for player in self.players:
            messages.append(
                Msg(
                    player.pos,
                    Wire.notify_beginning(player.hand2json(), player.pos, hand_no, self.rounds, bidder),
                )
            )
        self._act(messages, bidder, Phase.BID)

    def reshuffle(self) -> list[str]:
        """Create and store a new shuffled 54-card deck."""

        self.deck = self._standard_deck()
        shuffle(self.deck)
        return fmt(self.deck)

    def deal(self) -> None:
        """Deal the stored deck round-robin into three 17-card hands and a bottom."""

        if len(self.deck) != 54:
            raise ValueError("deal requires a complete 54-card deck")
        for player in self.players:
            player.reset_hand()
        for index, card in enumerate(self.deck[:51]):
            self.players[index % self.PLAYER_COUNT].hand_cards.append(card)
        for player in self.players:
            player.sort_hand()
        self.bottom_cards = list(self.deck[51:])

    def _next_deck(self) -> list[Card]:
        if self.deck_data is not None and not self._fixed_deck_used:
            self._fixed_deck_used = True
            return parse(self.deck_data)
        deck = self._standard_deck()
        shuffle(deck)
        return deck

    @staticmethod
    def _standard_deck() -> list[Card]:
        # Card is frozen, so games can safely share the canonical instances
        # while mutating only their own deck and hand lists.
        return list(STANDARD_DECK)

    @classmethod
    def _validate_deck(cls, labels: list[str]) -> None:
        if len(labels) != 54:
            raise ValueError("deck_data must contain 54 cards")
        expected = Counter(fmt(cls._standard_deck()))
        actual = Counter(labels)
        if actual != expected:
            raise ValueError("deck_data must contain each standard card exactly once")

    # --- bid / double / redouble ------------------------------------------

    def bid(self, content: dict[str, Any]) -> list[Msg]:
        self._push_trace()
        action = self.legal_moves[content["actIndex"]]
        value = int(action.rank or 0)
        pos = self.state.current_pos
        self.bids[pos] = value
        self.bid_count += 1
        if value > self.highest_bid:
            self.highest_bid = value
            self.highest_bidder = pos

        messages: list[Msg] = []
        self._broadcast(messages, Wire.notify_bid(pos, value, self.highest_bid, self.highest_bidder))
        if value == 3 or self.bid_count == self.PLAYER_COUNT:
            if self.highest_bid == 0:
                self._broadcast(messages, Wire.notify_redeal())
                self._start_hand(messages, redeal=True)
                return messages
            self.landlord = self.highest_bidder
            self.base_score = self.highest_bid
            self._broadcast(messages, Wire.notify_landlord(self.landlord, self.base_score))
            self._enter_double(messages)
            return messages

        next_pos = (pos + 1) % self.PLAYER_COUNT
        self.state.current_pos = next_pos
        self.legal_moves.parse_bid_action(self.highest_bid)
        self._act(messages, next_pos, Phase.BID)
        return messages

    def _enter_double(self, messages: list[Msg]) -> None:
        self.phase = Phase.DOUBLE
        self.loop = self.double
        self.pending_double = {pos for pos in range(self.PLAYER_COUNT) if pos != self.landlord}
        self.doubles = {}
        self.state.current_pos = -1
        self.legal_moves.parse_double_action()
        for defender in sorted(self.pending_double):
            self._act(messages, defender, Phase.DOUBLE)

    def double(self, content: dict[str, Any]) -> list[Msg]:
        self._push_trace()
        pos = int(content.get("player", -1))
        action = self.legal_moves[content["actIndex"]]
        self.doubles[pos] = action.rank == "1"
        self.pending_double.remove(pos)
        messages: list[Msg] = []
        if self.pending_double:
            return messages

        self._broadcast(messages, Wire.notify_double(self.doubles))
        if any(self.doubles.values()):
            self.phase = Phase.REDOUBLE
            self.loop = self.redouble_action
            self.state.current_pos = self.landlord
            self.legal_moves.parse_redouble_action()
            self._act(messages, self.landlord, Phase.REDOUBLE)
        else:
            self._enter_play(messages)
        return messages

    def redouble_action(self, content: dict[str, Any]) -> list[Msg]:
        self._push_trace()
        action = self.legal_moves[content["actIndex"]]
        self.redouble = action.rank == "1"
        messages: list[Msg] = []
        self._broadcast(messages, Wire.notify_redouble(self.landlord, self.redouble))
        self._enter_play(messages)
        return messages

    # --- play --------------------------------------------------------------

    def _enter_play(self, messages: list[Msg]) -> None:
        bottom = fmt(self.bottom_cards)
        self.players[self.landlord].add_cards(bottom)
        self._broadcast(messages, Wire.notify_bottom(self.landlord, bottom))
        self.phase = Phase.PLAY
        self.loop = self.play
        self.state.clear()
        self.state.current_pos = self.landlord
        self.first_action(self.landlord)
        self._act(messages, self.landlord, Phase.PLAY)

    def play(self, content: dict[str, Any]) -> list[Msg]:
        self._push_trace()
        action = self.legal_moves[content["actIndex"]]
        pos = self.state.current_pos
        self.state.current_action = action
        self.players[pos].play_area = action
        messages: list[Msg] = []

        if action.type == Move.PASS:
            self.state.pass_count += 1
            self._broadcast(messages, Wire.notify_play(*self.state.action_info()))
            if self.state.pass_count == 2:
                next_pos = self.state.greater_pos
                self.state.clear()
                self.state.current_pos = next_pos
                self.first_action(next_pos)
            else:
                next_pos = (pos + 1) % self.PLAYER_COUNT
                self.state.current_pos = next_pos
                self.second_action(next_pos)
            self._act(messages, next_pos, Phase.PLAY)
            return messages

        cards = list(action.cards or [])
        self.players[pos].play_cards(cards)
        self.players[pos].successful_plays += 1
        if action.type == "Rocket":
            self.rocket_count += 1
        elif action.type == "Bomb":
            self.bomb_count += 1
        self.state.greater_pos = pos
        self.state.greater_action = action
        self.state.pass_count = 0
        self._broadcast(messages, Wire.notify_play(*self.state.action_info()))

        if not self.players[pos].hand_cards:
            self._finish_hand(messages, pos)
            return messages
        if len(self.players[pos].hand_cards) == 1:
            report = Wire.notify_report(pos, 1)
            for recipient in range(self.PLAYER_COUNT):
                if recipient != pos:
                    messages.append(
                        Msg(recipient, report if self.training_fast_path else _copy_wire(report))
                    )

        next_pos = (pos + 1) % self.PLAYER_COUNT
        self.state.current_pos = next_pos
        self.second_action(next_pos)
        self._act(messages, next_pos, Phase.PLAY)
        return messages

    # --- settlement --------------------------------------------------------

    def _finish_hand(self, messages: list[Msg], winner: int) -> None:
        defense_won = winner != self.landlord
        defenders = [pos for pos in range(self.PLAYER_COUNT) if pos != self.landlord]
        spring = winner == self.landlord and all(self.players[pos].successful_plays == 0 for pos in defenders)
        reverse_spring = defense_won and self.players[self.landlord].successful_plays == 1
        win_sign = 1 if defense_won else -1

        hand_scores = [0, 0, 0]
        exponents: dict[int, int] = {}
        for defender in defenders:
            doubled = int(self.doubles.get(defender, False))
            redoubled = int(bool(doubled and self.redouble))
            exponent = self.rocket_count + self.bomb_count + int(spring) + int(reverse_spring) + doubled + redoubled
            exponents[defender] = exponent
            hand_scores[defender] = self.base_score * win_sign * (2 ** exponent)
        hand_scores[self.landlord] = -sum(hand_scores[pos] for pos in defenders)

        for pos, score in enumerate(hand_scores):
            self.players[pos].score += score
        self.completed_hands += 1
        result = {
            "winner": winner,
            "winningSide": "defenders" if defense_won else "landlord",
            "landlord": self.landlord,
            "baseScore": self.base_score,
            "bombs": self.bomb_count,
            "rockets": self.rocket_count,
            "spring": spring,
            "reverseSpring": reverse_spring,
            "doubles": {str(k): v for k, v in self.doubles.items()},
            "redouble": self.redouble,
            "exponents": {str(k): v for k, v in exponents.items()},
            "handScores": hand_scores,
            "totalScores": [player.score for player in self.players],
            "restCards": [[player.pos, player.hand2json()] for player in self.players if player.hand_cards],
        }
        self._broadcast(messages, Wire.notify_episode_over(result))

        if self.completed_hands >= self.rounds:
            self.phase = Phase.GAME_OVER
            self.loop = self._game_over
            totals = [player.score for player in self.players]
            self.results = totals
            self._broadcast(messages, Wire.notify_game_over(self.completed_hands, self.rounds))
            self._broadcast(messages, Wire.notify_game_result(totals))
        else:
            self._start_hand(messages, redeal=False)

    def _game_over(self, _content: dict[str, Any]) -> list[Msg]:
        return []

    # --- wire and validation ----------------------------------------------

    def _broadcast(self, messages: list[Msg], body: dict[str, Any]) -> None:
        if self.training_fast_path:
            messages.append(Msg(self.players[0].pos, body))
            messages.append(Msg(self.players[1].pos, body))
            messages.append(Msg(self.players[2].pos, body))
            return
        left, middle, right = _copy_wire_three(body)
        messages.append(Msg(self.players[0].pos, left))
        messages.append(Msg(self.players[1].pos, middle))
        messages.append(Msg(self.players[2].pos, right))

    def _act(self, messages: list[Msg], pos: int, stage: str) -> None:
        context: dict[str, Any] = {
            "landlord": self.landlord,
            "baseScore": self.base_score,
            "highestBid": self.highest_bid,
            "bids": {str(k): v for k, v in self.bids.items()},
            "doubles": {str(k): v for k, v in self.doubles.items()},
            "redouble": self.redouble,
            "bombs": self.bomb_count,
            "rockets": self.rocket_count,
            "bottomCards": fmt(self.bottom_cards) if self.phase == Phase.PLAY else None,
            "greaterPos": self.state.greater_pos,
            "greaterAction": self.state.greater_action.to_json(),
        }
        messages.append(
            Msg(
                pos,
                Wire.act(
                    stage,
                    self.players[pos].hand2json(),
                    [player.public_info() for player in self.players],
                    pos,
                    (
                        self.legal_moves.action_list
                        if self.training_fast_path
                        else _copy_actions(self.legal_moves.action_list)
                    ),
                    **context,
                ),
            )
        )

    def act(self, messages: list[Msg], cur_pos: int, stage: str) -> None:
        """Public action-request helper for room and simulation adapters."""

        self._act(messages, cur_pos, stage)

    def validate(self, pos: int, action: dict[str, Any]) -> bool:
        index = action.get("actIndex")
        if not isinstance(index, int) or isinstance(index, bool) or index not in self.legal_moves.valid_range:
            return False
        if self.phase == Phase.DOUBLE:
            return pos in self.pending_double
        if self.phase == Phase.GAME_OVER:
            return False
        return pos == self.state.current_pos

    def action(self, pos: int, act_index: int) -> list[Msg]:
        """Convenience API for direct simulations, parallel to room dispatch."""

        payload = {"actIndex": act_index, "player": pos}
        if not self.validate(pos, payload):
            raise ValueError("invalid action")
        return self.loop(payload)

    def timeout_action(self, pos: int) -> list[Msg]:
        """Apply the official default choice for an expired 25-second timer.

        Scheduling the timer belongs to the host/server. This method keeps the
        deterministic rule decision inside the table so training and network
        front ends use the same behavior.
        """

        if self.phase == Phase.BID:
            wanted = ["Bid", "0", []]
        elif self.phase == Phase.DOUBLE:
            wanted = ["Double", "0", []]
        elif self.phase == Phase.REDOUBLE:
            wanted = ["Redouble", "0", []]
        elif self.phase == Phase.PLAY:
            if self.state.greater_pos >= 0:
                wanted = ["PASS", "PASS", "PASS"]
            else:
                singles = [action for action in self.legal_moves.action_list if action[0] == "Single"]
                if not singles:
                    raise ValueError("lead timeout has no legal single")
                wanted = min(singles, key=lambda action: card_sort_key(action[2][0]))
        else:
            raise ValueError("game is already over")
        return self.action(pos, self.legal_moves.action_list.index(wanted))

    def _push_trace(self) -> None:
        if not self.allow_step_back:
            return
        self.trace.append({
            "phase": self.phase,
            "players": deepcopy(self.players),
            "state": deepcopy(self.state),
            "legal_moves": deepcopy(self.legal_moves),
            "deck": deepcopy(self.deck),
            "bottom_cards": deepcopy(self.bottom_cards),
            "landlord": self.landlord,
            "base_score": self.base_score,
            "highest_bid": self.highest_bid,
            "highest_bidder": self.highest_bidder,
            "bid_count": self.bid_count,
            "bids": deepcopy(self.bids),
            "pending_double": deepcopy(self.pending_double),
            "doubles": deepcopy(self.doubles),
            "redouble": self.redouble,
            "rocket_count": self.rocket_count,
            "bomb_count": self.bomb_count,
            "completed_hands": self.completed_hands,
            "deal_attempt": self.deal_attempt,
            "results": deepcopy(self.results),
            "fixed_deck_used": self._fixed_deck_used,
        })

    def loop_back(self) -> tuple[str, int, list[list[object]], list[str]]:
        """Undo one submitted action for reversible training simulations."""

        if not self.allow_step_back or not self.trace:
            raise AssertionError("no action to undo")
        snapshot = self.trace.pop()
        self.phase = snapshot["phase"]
        self.players = snapshot["players"]
        self.state = snapshot["state"]
        self.legal_moves = snapshot["legal_moves"]
        self.deck = snapshot["deck"]
        self.bottom_cards = snapshot["bottom_cards"]
        self.landlord = snapshot["landlord"]
        self.base_score = snapshot["base_score"]
        self.highest_bid = snapshot["highest_bid"]
        self.highest_bidder = snapshot["highest_bidder"]
        self.bid_count = snapshot["bid_count"]
        self.bids = snapshot["bids"]
        self.pending_double = snapshot["pending_double"]
        self.doubles = snapshot["doubles"]
        self.redouble = snapshot["redouble"]
        self.rocket_count = snapshot["rocket_count"]
        self.bomb_count = snapshot["bomb_count"]
        self.completed_hands = snapshot["completed_hands"]
        self.deal_attempt = snapshot["deal_attempt"]
        self.results = snapshot["results"]
        self._fixed_deck_used = snapshot["fixed_deck_used"]
        self.loop = {
            Phase.BID: self.bid,
            Phase.DOUBLE: self.double,
            Phase.REDOUBLE: self.redouble_action,
            Phase.PLAY: self.play,
            Phase.GAME_OVER: self._game_over,
        }[self.phase]
        pos = self.state.current_pos
        hand = self.players[pos].hand2json() if pos in range(self.PLAYER_COUNT) else []
        return self.phase, pos, _copy_actions(self.legal_moves.action_list), hand

    def generate_action_list(self, stage: str, pos: int | None = None) -> tuple[list[list[object]], range]:
        """Regenerate legal actions for inspection/undo-style tooling."""

        if stage == Phase.BID:
            self.legal_moves.parse_bid_action(self.highest_bid)
        elif stage == Phase.DOUBLE:
            self.legal_moves.parse_double_action()
        elif stage == Phase.REDOUBLE:
            self.legal_moves.parse_redouble_action()
        elif stage == Phase.PLAY:
            target_pos = self.state.current_pos if pos is None else pos
            if self.state.greater_pos < 0:
                self.legal_moves.parse_first_action(self.players[target_pos].hand_cards)
            else:
                self.legal_moves.parse_second_action(self.players[target_pos].hand_cards, self.state.greater_action)
        return _copy_actions(self.legal_moves.action_list), deepcopy(self.legal_moves.valid_range)

    def first_action(self, cur_pos: int) -> None:
        self.legal_moves.parse_first_action(self.players[cur_pos].hand_cards)

    def second_action(self, cur_pos: int) -> None:
        self.legal_moves.parse_second_action(self.players[cur_pos].hand_cards, self.state.greater_action)

    def next_player_second_action(self, messages: list[Msg]) -> int:
        next_pos = (self.state.current_pos + 1) % self.PLAYER_COUNT
        self.state.current_pos = next_pos
        self.second_action(next_pos)
        self._act(messages, next_pos, Phase.PLAY)
        return next_pos

    def get_hand_card(self) -> list[list[str]]:
        return [player.hand2json() for player in self.players]

    def change_hand_card(self, hand_card_all: list[list[str]]) -> tuple[list[list[str]], list[list[object]]]:
        if len(hand_card_all) != self.PLAYER_COUNT:
            raise ValueError("hand_card_all must contain three hands")
        for player, labels in zip(self.players, hand_card_all):
            player.hand_cards = sorted(parse(labels), key=card_sort_key)
        actions, _ = self.generate_action_list(self.phase)
        return self.get_hand_card(), actions
