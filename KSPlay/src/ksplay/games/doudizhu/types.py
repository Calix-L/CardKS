"""Cards, moves, players, trick state and wire payloads for competitive Dou Dizhu."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

RANKS = ("3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A", "2", "B", "R")
RANK_VALUE = {rank: index for index, rank in enumerate(RANKS, start=3)}
SUIT_VALUE = {"S": 0, "H": 1, "C": 2, "D": 3}


class Phase:
    BID = "bid"
    DOUBLE = "double"
    REDOUBLE = "redouble"
    PLAY = "play"
    GAME_OVER = "gameOver"


@dataclass(frozen=True, order=False)
class Card:
    suit: str
    rank: str
    _label: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.rank in ("B", "R"):
            expected = "S" if self.rank == "B" else "H"
            if self.suit != expected:
                raise ValueError(f"joker {self.rank} must use suit {expected}")
        elif self.suit not in SUIT_VALUE or self.rank not in RANK_VALUE:
            raise ValueError(f"invalid card: {self.suit}{self.rank}")
        object.__setattr__(self, "_label", self.suit + self.rank)

    @classmethod
    def from_label(cls, label: str) -> "Card":
        if not isinstance(label, str) or len(label) != 2:
            raise ValueError(f"invalid card label: {label!r}")
        return cls(label[0], label[1])

    def __str__(self) -> str:
        return self._label

    def __repr__(self) -> str:
        return str(self)


def card_sort_key(card: Card | str) -> tuple[int, int]:
    card = card if isinstance(card, Card) else Card.from_label(card)
    return RANK_VALUE[card.rank], SUIT_VALUE.get(card.suit, 9)


def parse(labels: list[str]) -> list[Card]:
    return [Card.from_label(label) for label in labels]


def fmt(cards: list[Card]) -> list[str]:
    return [card._label for card in cards]


class Move:
    PASS = "PASS"

    def __init__(self, move_type: str | None = None, rank: str | None = None, cards: list[str] | None = None):
        self._type = move_type
        self._rank = rank
        self._cards = cards

    @property
    def type(self) -> str | None:
        return self._type

    @property
    def rank(self) -> str | None:
        return self._rank

    @property
    def cards(self) -> list[str] | None:
        return self._cards

    def to_json(self) -> list[Any]:
        return [self._type, self._rank, self._cards]

    def clear(self) -> None:
        self._type = None
        self._rank = None
        self._cards = None


@dataclass(frozen=True)
class Msg:
    seat: int
    body: dict[str, Any]


class Trick:
    def __init__(self) -> None:
        self.current_pos = -1
        self.current_action = Move()
        self.greater_pos = -1
        self.greater_action = Move()
        self.pass_count = 0

    def clear(self) -> None:
        self.current_action = Move()
        self.greater_pos = -1
        self.greater_action = Move()
        self.pass_count = 0

    def action_info(self) -> tuple[int, list[Any], int, list[Any]]:
        return (
            self.current_pos,
            self.current_action.to_json(),
            self.greater_pos,
            self.greater_action.to_json(),
        )


class Player:
    def __init__(self, name: str, index: int):
        self.name = name
        self.pos = index
        self.hand_cards: list[Card] = []
        self.play_area: Move | None = None
        self.score = 0
        self.successful_plays = 0

    def hand2json(self) -> list[str]:
        return fmt(self.hand_cards)

    def public_info(self) -> dict[str, Any]:
        return {
            "rest": len(self.hand_cards),
            "playArea": self.play_area.to_json() if self.play_area else None,
            "score": self.score,
        }

    def reset_hand(self) -> None:
        self.hand_cards = []
        self.play_area = None
        self.successful_plays = 0

    def sort_hand(self) -> None:
        self.hand_cards.sort(key=card_sort_key)

    def add_cards(self, labels: list[str]) -> None:
        self.hand_cards.extend(parse(labels))
        self.sort_hand()

    def play_cards(self, labels: list[str]) -> None:
        for label in labels:
            for index, card in enumerate(self.hand_cards):
                if card._label == label:
                    self.hand_cards.pop(index)
                    break
            else:
                raise ValueError(f"card {label} is not in player {self.pos}'s hand")


class Wire:
    @staticmethod
    def notify_beginning(hand_cards: list[str], seat: int, hand_no: int, rounds: int, first_bidder: int) -> dict[str, Any]:
        return {
            "type": "notify",
            "stage": "beginning",
            "handCards": hand_cards,
            "myPos": seat,
            "handNo": hand_no,
            "rounds": rounds,
            "firstBidder": first_bidder,
        }

    @staticmethod
    def notify_bid(cur_pos: int, bid: int, highest_bid: int, highest_pos: int) -> dict[str, Any]:
        return {
            "type": "notify", "stage": "bid", "curPos": cur_pos, "bid": bid,
            "highestBid": highest_bid, "highestPos": highest_pos,
        }

    @staticmethod
    def notify_landlord(landlord: int, base_score: int) -> dict[str, Any]:
        return {"type": "notify", "stage": "landlord", "landlord": landlord, "baseScore": base_score}

    @staticmethod
    def notify_double(doubles: dict[int, bool]) -> dict[str, Any]:
        return {"type": "notify", "stage": "double", "result": {str(k): v for k, v in doubles.items()}}

    @staticmethod
    def notify_redouble(landlord: int, redouble: bool) -> dict[str, Any]:
        return {"type": "notify", "stage": "redouble", "landlord": landlord, "redouble": redouble}

    @staticmethod
    def notify_bottom(landlord: int, bottom_cards: list[str]) -> dict[str, Any]:
        return {"type": "notify", "stage": "bottom", "landlord": landlord, "bottomCards": bottom_cards}

    @staticmethod
    def notify_play(cur_pos: int, cur_action: list[Any], greater_pos: int, greater_action: list[Any]) -> dict[str, Any]:
        return {
            "type": "notify", "stage": "play", "curPos": cur_pos, "curAction": cur_action,
            "greaterPos": greater_pos, "greaterAction": greater_action,
        }

    @staticmethod
    def notify_report(pos: int, rest: int) -> dict[str, Any]:
        return {"type": "notify", "stage": "report", "player": pos, "rest": rest}

    @staticmethod
    def notify_redeal() -> dict[str, Any]:
        return {"type": "notify", "stage": "redeal", "reason": "all-pass"}

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
        stage: str,
        hand_cards: list[str],
        public_info: list[dict[str, Any]],
        cur_pos: int,
        action_list: list[list[Any]],
        **context: Any,
    ) -> dict[str, Any]:
        return {
            "type": "act",
            "stage": stage,
            "handCards": hand_cards,
            "publicInfo": public_info,
            "curPos": cur_pos,
            "actionList": action_list,
            "indexRange": len(action_list) - 1,
            **context,
        }
