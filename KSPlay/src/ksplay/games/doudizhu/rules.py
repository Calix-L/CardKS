"""Official-competition card patterns and legal move generation for Dou Dizhu."""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from itertools import combinations, combinations_with_replacement
from typing import Callable, Iterable, Iterator, Sequence

from .types import Card, RANK_VALUE, SUIT_VALUE

PASS_ACTION = ["PASS", "PASS", "PASS"]
FROZEN_PASS_ACTION = (("PASS", "PASS", ("PASS",)),)
SEQUENCE_RANKS = ("3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A")
BID_ACTIONS = [["Bid", str(value), []] for value in range(4)]
DOUBLE_ACTIONS = [["Double", "0", []], ["Double", "1", []]]
REDOUBLE_ACTIONS = [["Redouble", "0", []], ["Redouble", "1", []]]
SEQUENCE_INDEX = {rank: index for index, rank in enumerate(SEQUENCE_RANKS)}
ALL_RANK_SEQUENCES = tuple(
    SEQUENCE_RANKS[start:start + length]
    for length in range(2, len(SEQUENCE_RANKS) + 1)
    for start in range(0, len(SEQUENCE_RANKS) - length + 1)
)
RANK_SEQUENCES_BY_MIN_LENGTH = {
    min_length: tuple(sequence for sequence in ALL_RANK_SEQUENCES if len(sequence) >= min_length)
    for min_length in range(2, 6)
}
SEQUENCE_RANK_BIT = {rank: 1 << index for index, rank in enumerate(SEQUENCE_RANKS)}
LABEL_SORT_KEYS = {
    suit + rank: (RANK_VALUE[rank], SUIT_VALUE[suit])
    for rank in SEQUENCE_RANKS + ("2",)
    for suit in ("S", "H", "C", "D")
}
LABEL_SORT_KEYS.update({"SB": (RANK_VALUE["B"], SUIT_VALUE["S"]), "HR": (RANK_VALUE["R"], SUIT_VALUE["H"])})
LABEL_SORT_KEY = LABEL_SORT_KEYS.__getitem__
RANK_SEQUENCE_MASKS_BY_MIN_LENGTH = {
    min_length: tuple(
        (sequence, sum(SEQUENCE_RANK_BIT[rank] for rank in sequence))
        for sequence in sequences
    )
    for min_length, sequences in RANK_SEQUENCES_BY_MIN_LENGTH.items()
}
ACTION_ORDER = {
    "Single": 0, "Pair": 1, "Trips": 2, "ThreeWithOne": 3, "ThreeWithPair": 4,
    "Straight": 5, "PairStraight": 6, "Airplane": 7, "AirplaneWithSingles": 8,
    "AirplaneWithPairs": 9, "FourWithSingles": 10, "FourWithPairs": 11,
    "Bomb": 12, "Rocket": 13,
}


def bid_actions(highest_bid: int) -> list[list[object]]:
    return [BID_ACTIONS[0]] + [action for action in BID_ACTIONS[1:] if int(action[1]) > highest_bid]


def first_actions(hand_cards: Sequence[object]) -> list[list[object]]:
    labels = tuple(sorted(
        (card._label if type(card) is Card else str(card) for card in hand_cards),
        key=LABEL_SORT_KEY,
    ))
    return _thaw_actions(_cached_first_actions(labels))


def first_actions_readonly(hand_cards: Sequence[object]) -> list[list[object]]:
    """Return a shared cached action list for trusted read-only training code."""

    labels = tuple(sorted(
        (card._label if type(card) is Card else str(card) for card in hand_cards),
        key=LABEL_SORT_KEY,
    ))
    return _cached_first_actions_readonly(labels)


@lru_cache(maxsize=2048)
def _cached_first_actions(labels: tuple[str, ...]) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    return _freeze_generated_actions(_generate_actions(labels, hand_is_sorted=True))


@lru_cache(maxsize=2048)
def _cached_first_actions_readonly(labels: tuple[str, ...]) -> list[list[object]]:
    return _generate_actions(labels, hand_is_sorted=True)


def _generate_actions(
    hand_cards: Sequence[object],
    allowed_types: set[str] | None = None,
    accept: Callable[[list[object]], bool] | None = None,
    *,
    hand_is_sorted: bool = False,
) -> list[list[object]]:
    labels = (
        list(hand_cards)
        if hand_is_sorted
        else sorted(
            (card._label if type(card) is Card else str(card) for card in hand_cards),
            key=LABEL_SORT_KEY,
        )
    )
    by_rank = _by_rank(labels, presorted=True)
    available_mask = 0
    for rank in by_rank:
        available_mask |= SEQUENCE_RANK_BIT.get(rank, 0)
    actions: list[list[object]] = []
    # Suits never participate in a competitive Dou Dizhu comparison.  Keeping
    # every physical-suit permutation would therefore create many actions with
    # exactly the same game effect (and can expand a 20-card hand to tens of
    # thousands of actions).  Retain the first, stable physical representative
    # for each move type and rank multiset instead.
    if accept is None:
        def add(move_type: str, rank: str, cards: Iterable[str]) -> None:
            actions.append([move_type, rank, sorted(cards, key=LABEL_SORT_KEY)])

        def add_presorted(move_type: str, rank: str, cards: Iterable[str]) -> None:
            actions.append([move_type, rank, list(cards)])
    else:
        def add(move_type: str, rank: str, cards: Iterable[str]) -> None:
            selected = sorted(cards, key=LABEL_SORT_KEY)
            action: list[object] = [move_type, rank, selected]
            if accept(action):
                actions.append(action)

        def add_presorted(move_type: str, rank: str, cards: Iterable[str]) -> None:
            action: list[object] = [move_type, rank, list(cards)]
            if accept(action):
                actions.append(action)

    if allowed_types is None or "Single" in allowed_types:
        for rank, cards in by_rank.items():
            add_presorted("Single", rank, cards[:1])

    pair_mask = 0
    trip_mask = 0
    for rank, cards in by_rank.items():
        card_count = len(cards)
        rank_bit = SEQUENCE_RANK_BIT.get(rank, 0)
        if card_count >= 2:
            pair_mask |= rank_bit
        if card_count >= 3:
            trip_mask |= rank_bit
        if card_count >= 2 and (allowed_types is None or "Pair" in allowed_types):
            add_presorted("Pair", rank, cards[:2])
        if card_count >= 3 and (allowed_types is None or "Trips" in allowed_types):
            add_presorted("Trips", rank, cards[:3])
        if card_count >= 4 and (allowed_types is None or "Bomb" in allowed_types):
            add_presorted("Bomb", rank, cards[:4])

    if (allowed_types is None or "Rocket" in allowed_types) and "B" in by_rank and "R" in by_rank:
        add_presorted("Rocket", "R", [by_rank["B"][0], by_rank["R"][0]])

    # Three with one / pair.
    if allowed_types is None or {"ThreeWithOne", "ThreeWithPair"} & allowed_types:
        for trip_rank, trip_cards in by_rank.items():
            if len(trip_cards) < 3:
                continue
            trips = tuple(trip_cards[:3])
            if allowed_types is None or "ThreeWithOne" in allowed_types:
                for kicker_rank, kicker_cards in by_rank.items():
                    if kicker_rank != trip_rank:
                        add("ThreeWithOne", trip_rank, trips + (kicker_cards[0],))
            if allowed_types is None or "ThreeWithPair" in allowed_types:
                for pair_rank, pair_cards in by_rank.items():
                    if pair_rank != trip_rank and len(pair_cards) >= 2:
                        add("ThreeWithPair", trip_rank, trips + tuple(pair_cards[:2]))

    # Straights.
    if allowed_types is None or "Straight" in allowed_types:
        for seq, seq_mask in RANK_SEQUENCE_MASKS_BY_MIN_LENGTH[5]:
            if available_mask & seq_mask == seq_mask:
                add_presorted("Straight", seq[-1], (by_rank[rank][0] for rank in seq))

    # Consecutive pairs.
    if allowed_types is None or "PairStraight" in allowed_types:
        for seq, seq_mask in RANK_SEQUENCE_MASKS_BY_MIN_LENGTH[3]:
            if pair_mask & seq_mask == seq_mask:
                picked = (by_rank[rank][:2] for rank in seq)
                add_presorted("PairStraight", seq[-1], _flatten(picked))

    # Airplanes, with optional single or pair wings.
    airplane_types = {"Airplane", "AirplaneWithSingles", "AirplaneWithPairs"}
    if allowed_types is None or airplane_types & allowed_types:
        for seq, seq_mask in RANK_SEQUENCE_MASKS_BY_MIN_LENGTH[2]:
            if trip_mask & seq_mask != seq_mask:
                continue
            picked = (by_rank[rank][:3] for rank in seq)
            body = tuple(_flatten(picked))
            if allowed_types is None or "Airplane" in allowed_types:
                add_presorted("Airplane", seq[-1], body)
            if allowed_types is not None and not ({"AirplaneWithSingles", "AirplaneWithPairs"} & allowed_types):
                continue
            eligible = [card for card in labels if card[1] not in seq]
            wing_count = len(seq)
            if allowed_types is None or "AirplaneWithSingles" in allowed_types:
                for wings in _unique_combinations(eligible, wing_count):
                    if _valid_single_wings(wings, seq):
                        add("AirplaneWithSingles", seq[-1], body + wings)

            if allowed_types is None or "AirplaneWithPairs" in allowed_types:
                pair_by_rank = _by_rank(eligible, presorted=True)
                pair_ranks = [rank for rank, cards in pair_by_rank.items() if rank not in ("B", "R") and len(cards) >= 2]
                for selected_ranks in combinations(pair_ranks, wing_count):
                    wings = tuple(card for rank in selected_ranks for card in pair_by_rank[rank][:2])
                    add("AirplaneWithPairs", seq[-1], body + wings)

    # Four with two singles / two pairs.
    if allowed_types is None or {"FourWithSingles", "FourWithPairs"} & allowed_types:
        for bomb_rank, bomb_cards in by_rank.items():
            if len(bomb_cards) < 4:
                continue
            bomb = tuple(bomb_cards[:4])
            eligible = [card for card in labels if card[1] != bomb_rank]
            if allowed_types is None or "FourWithSingles" in allowed_types:
                for wings in _unique_combinations(eligible, 2):
                    if set(wings) != {"SB", "HR"}:
                        add("FourWithSingles", bomb_rank, bomb + wings)

            if allowed_types is None or "FourWithPairs" in allowed_types:
                pair_by_rank = _by_rank(eligible)
                pair_ranks = [rank for rank, cards in pair_by_rank.items() if rank not in ("B", "R") and len(cards) >= 2]
                for left_rank, right_rank in combinations(pair_ranks, 2):
                    left = tuple(pair_by_rank[left_rank][:2])
                    right = tuple(pair_by_rank[right_rank][:2])
                    add("FourWithPairs", bomb_rank, bomb + left + right)

    actions.sort(key=_action_sort_key)
    return actions


def second_actions(hand_cards: Sequence[object], greater_action: Sequence[object]) -> list[list[object]]:
    labels = tuple(sorted(
        (card._label if type(card) is Card else str(card) for card in hand_cards),
        key=LABEL_SORT_KEY,
    ))
    target_cards = greater_action[2]
    frozen_target = (
        str(greater_action[0]),
        str(greater_action[1]),
        len(target_cards) if isinstance(target_cards, list) else 0,
    )
    return _thaw_actions(_cached_second_actions(labels, frozen_target))


def second_actions_readonly(
    hand_cards: Sequence[object],
    greater_action: Sequence[object],
) -> list[list[object]]:
    """Return a shared cached follow list for trusted read-only training code."""

    labels = tuple(sorted(
        (card._label if type(card) is Card else str(card) for card in hand_cards),
        key=LABEL_SORT_KEY,
    ))
    target_cards = greater_action[2]
    frozen_target = (
        str(greater_action[0]),
        str(greater_action[1]),
        len(target_cards) if isinstance(target_cards, list) else 0,
    )
    return _cached_second_actions_readonly(labels, frozen_target)


@lru_cache(maxsize=8192)
def _cached_second_actions(
    labels: tuple[str, ...],
    frozen_target: tuple[str, str, int],
) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    return FROZEN_PASS_ACTION + _freeze_generated_actions(
        _generate_beating_actions(labels, frozen_target)
    )


@lru_cache(maxsize=8192)
def _cached_second_actions_readonly(
    labels: tuple[str, ...],
    frozen_target: tuple[str, str, int],
) -> list[list[object]]:
    return [PASS_ACTION] + _generate_beating_actions(labels, frozen_target)


def _generate_beating_actions(
    labels: tuple[str, ...],
    frozen_target: tuple[str, str, int],
) -> list[list[object]]:
    target_type = frozen_target[0]
    if target_type == "Rocket":
        return []
    allowed_types = {"Bomb", "Rocket"}
    if target_type not in ("PASS", "None", ""):
        allowed_types.add(target_type)
    target_rank_value = RANK_VALUE.get(frozen_target[1], -1)
    target_count = frozen_target[2]

    def beats_target(action: list[object]) -> bool:
        action_type = action[0]
        if action_type == "Rocket":
            return True
        if action_type == "Bomb":
            return target_type != "Bomb" or RANK_VALUE.get(action[1], -1) > target_rank_value
        return (
            action_type == target_type
            and len(action[2]) == target_count
            and RANK_VALUE.get(action[1], -1) > target_rank_value
        )

    candidates = _generate_actions(
        labels,
        allowed_types=allowed_types,
        accept=beats_target,
        hand_is_sorted=True,
    )
    return candidates


def can_beat(action: Sequence[object], greater_action: Sequence[object]) -> bool:
    action_type = str(action[0])
    greater_type = str(greater_action[0])
    if action_type == "PASS":
        return False
    if not greater_type or greater_type == "PASS" or greater_type == "None":
        return True
    if action_type == "Rocket":
        return greater_type != "Rocket"
    if greater_type == "Rocket":
        return False
    if action_type == "Bomb":
        if greater_type != "Bomb":
            return True
        return _rank_value(str(action[1])) > _rank_value(str(greater_action[1]))
    if greater_type == "Bomb":
        return False
    if action_type != greater_type:
        return False
    if _card_count(action) != _card_count(greater_action):
        return False
    return _rank_value(str(action[1])) > _rank_value(str(greater_action[1]))


def classify(cards: Sequence[str]) -> list[object] | None:
    """Return the canonical action represented by ``cards``, if it is legal.

    Classification uses the same authoritative generator as gameplay, avoiding a
    second rule implementation that could drift from legal action generation.
    """

    wanted = Counter(cards)
    for action in first_actions(cards):
        if Counter(action[2]) == wanted and len(action[2]) == len(cards):
            return action
    return None


def _rank_value(rank: str) -> int:
    return RANK_VALUE.get(rank, -1)


def _label_sort_key(label: str) -> tuple[int, int]:
    """Fast key for already-validated two-character card labels."""

    return LABEL_SORT_KEYS[label]


def _freeze_generated_actions(
    actions: Sequence[Sequence[object]],
) -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    return tuple(
        (action[0], action[1], tuple(action[2]))
        for action in actions
    )


def _thaw_actions(actions: Sequence[tuple[str, str, tuple[str, ...]]]) -> list[list[object]]:
    # Always return fresh lists: callers and wire encoders are free to mutate
    # their copy without corrupting the shared cache.
    return [
        [move_type, rank, "PASS" if move_type == "PASS" else list(cards)]
        for move_type, rank, cards in actions
    ]


def _card_count(action: Sequence[object]) -> int:
    cards = action[2]
    return len(cards) if isinstance(cards, list) else 0


def _by_rank(labels: Iterable[str], *, presorted: bool = False) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for label in labels:
        rank = label[1]
        cards = result.get(rank)
        if cards is None:
            result[rank] = [label]
        else:
            cards.append(label)
    if not presorted:
        for cards in result.values():
            cards.sort(key=LABEL_SORT_KEY)
    return result


def _rank_sequences(min_length: int) -> Iterator[tuple[str, ...]]:
    yield from RANK_SEQUENCES_BY_MIN_LENGTH[min_length]


def _flatten(groups: Iterable[Iterable[str]]) -> list[str]:
    return [card for group in groups for card in group]


def _unique_combinations(cards: Sequence[str], size: int) -> Iterator[tuple[str, ...]]:
    """Yield one stable physical representative per rank multiset.

    Enumerating physical card combinations and deduplicating afterwards is
    needlessly exponential because suits have no rule meaning.  Enumerate rank
    multisets directly, then select the lowest-suit cards for each rank.
    """

    by_rank = _by_rank(cards, presorted=True)
    ranks = list(by_rank)
    if size == 2:
        for index, left_rank in enumerate(ranks):
            left_cards = by_rank[left_rank]
            if len(left_cards) >= 2:
                yield tuple(left_cards[:2])
            left_card = left_cards[0]
            for right_rank in ranks[index + 1:]:
                yield left_card, by_rank[right_rank][0]
        return

    for picked_ranks in combinations_with_replacement(ranks, size):
        counts: dict[str, int] = {}
        valid = True
        for rank in picked_ranks:
            count = counts.get(rank, 0) + 1
            if count > len(by_rank[rank]):
                valid = False
                break
            counts[rank] = count
        if not valid:
            continue
        picked: list[str] = []
        for rank in ranks:
            picked.extend(by_rank[rank][:counts.get(rank, 0)])
        yield tuple(picked)


def _valid_single_wings(wings: Sequence[str], body_sequence: Sequence[str]) -> bool:
    if "SB" in wings and "HR" in wings:
        return False
    if len(wings) < 3:
        return True
    counts = Counter(card[1] for card in wings)
    if max(counts.values(), default=0) >= 4:
        return False
    start = SEQUENCE_INDEX[body_sequence[0]]
    end = SEQUENCE_INDEX[body_sequence[-1]]
    adjacent = set()
    if start > 0:
        adjacent.add(SEQUENCE_RANKS[start - 1])
    if end + 1 < len(SEQUENCE_RANKS):
        adjacent.add(SEQUENCE_RANKS[end + 1])
    return not any(counts[rank] >= 3 for rank in adjacent)


def _action_sort_key(action: Sequence[object]) -> tuple[int, int, int, list[str]]:
    # The cards field is already a list of strings and Python compares lists
    # lexicographically, so allocating an equivalent tuple per sort key is
    # unnecessary.
    return ACTION_ORDER[action[0]], len(action[2]), RANK_VALUE.get(action[1], -1), action[2]
