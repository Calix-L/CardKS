'''
    File name: gin_rummy/utils.py
    Author: William Hale
    Date created: 2/12/2020
'''

from typing import List, Iterable

import numpy as np

from ksplay._vendor.rlcard.games.base import Card

from .gin_rummy_error import GinRummyProgramError

valid_rank = ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K']
valid_suit = ['S', 'H', 'D', 'C']
_rank_id_by_value = {rank: index for index, rank in enumerate(Card.valid_rank)}
_suit_id_by_value = {suit: index for index, suit in enumerate(Card.valid_suit)}
_card_id_by_suit_and_rank = {
    suit: {
        rank: rank_index + 13 * suit_index
        for rank_index, rank in enumerate(valid_rank)
    }
    for suit_index, suit in enumerate(valid_suit)
}

rank_to_deadwood_value = {"A": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
                          "T": 10, "J": 10, "Q": 10, "K": 10}


def card_from_card_id(card_id: int) -> Card:
    ''' Make card from its card_id

    Args:
        card_id: int in range(0, 52)
     '''
    if not (0 <= card_id < 52):
        raise GinRummyProgramError("card_id is {}: should be 0 <= card_id < 52.".format(card_id))
    rank_id = card_id % 13
    suit_id = card_id // 13
    rank = Card.valid_rank[rank_id]
    suit = Card.valid_suit[suit_id]
    return Card(rank=rank, suit=suit)


# deck is always in order from AS, 2S, ..., AH, 2H, ..., AD, 2D, ..., AC, 2C, ... QC, KC
_deck = [card_from_card_id(card_id) for card_id in range(52)]  # want this to be read-only


def _set_gin_rummy_metadata(card: Card, card_id: int):
    rank_id = card_id % 13
    suit_id = card_id // 13
    card._gin_rummy_id = card_id
    card._gin_rummy_rank_id = rank_id
    card._gin_rummy_suit_id = suit_id
    card._gin_rummy_bit = 1 << card_id
    card._gin_rummy_discard_action_id = 6 + card_id
    card._gin_rummy_knock_action_id = 58 + card_id
    card._gin_rummy_hash = rank_id + 100 * suit_id
    card._gin_rummy_deadwood_value = min(rank_id + 1, 10)
    card._gin_rummy_top_offset = 52 + card_id
    card._gin_rummy_discard_offset = 104 + card_id
    card._gin_rummy_known_offset = 156 + card_id
    card._gin_rummy_unknown_offset = 208 + card_id
    card._gin_rummy_index = card.suit + card.rank


for _card_id, _card in enumerate(_deck):
    # Canonical Gin cards are reused by the dealer and decoded actions.  The
    # cached integer removes two string-dictionary lookups from hot paths;
    # equal-value Card objects supplied by callers still use the fallback.
    _set_gin_rummy_metadata(_card, _card_id)


def card_from_text(text: str) -> Card:
    if len(text) != 2:
        raise GinRummyProgramError("len(text) is {}: should be 2.".format(len(text)))
    return Card(rank=text[0], suit=text[1])


def get_deck() -> List[Card]:
    return _deck.copy()


def get_card(card_id: int):
    return _deck[card_id]


def get_card_id(card: Card) -> int:
    try:
        return card._gin_rummy_id
    except AttributeError:
        pass
    try:
        return _card_id_by_suit_and_rank[card.suit][card.rank]
    except KeyError:
        # Preserve list.index's public ValueError for malformed cards.
        return get_rank_id(card) + 13 * get_suit_id(card)


def get_rank_id(card: Card) -> int:
    try:
        return card._gin_rummy_rank_id
    except AttributeError:
        pass
    try:
        return _rank_id_by_value[card.rank]
    except KeyError:
        # Preserve list.index's public ValueError for malformed cards.
        return Card.valid_rank.index(card.rank)


def get_suit_id(card: Card) -> int:
    try:
        return card._gin_rummy_suit_id
    except AttributeError:
        pass
    try:
        return _suit_id_by_value[card.suit]
    except KeyError:
        # Preserve list.index's public ValueError for malformed cards.
        return Card.valid_suit.index(card.suit)


def get_deadwood_value(card: Card) -> int:
    try:
        return card._gin_rummy_deadwood_value
    except AttributeError:
        pass
    rank = card.rank
    deadwood_value = rank_to_deadwood_value.get(rank, 10)  # default to 10 is key does not exist
    return deadwood_value


def get_deadwood(hand: Iterable[Card], meld_cluster: List[Iterable[Card]]) -> List[Card]:
    if len(list(hand)) != 10:
        raise GinRummyProgramError("Hand contain {} cards: should be 10 cards.".format(len(list(hand))))
    meld_cards = [card for meld_pile in meld_cluster for card in meld_pile]
    deadwood = [card for card in hand if card not in meld_cards]
    return deadwood


def get_deadwood_count(hand: List[Card], meld_cluster: List[Iterable[Card]]) -> int:
    if len(hand) != 10:
        raise GinRummyProgramError("Hand contain {} cards: should be 10 cards.".format(len(hand)))
    deadwood = get_deadwood(hand=hand, meld_cluster=meld_cluster)
    deadwood_values = [get_deadwood_value(card) for card in deadwood]
    return sum(deadwood_values)


def decode_cards(env_cards: np.ndarray) -> List[Card]:
    result = []  # type: List[Card]
    if len(env_cards) != 52:
        raise GinRummyProgramError("len(env_cards) is {}: should be 52.".format(len(env_cards)))
    for i in range(52):
        if env_cards[i] == 1:
            card = _deck[i]
            result.append(card)
    return result


def encode_cards(cards: List[Card]) -> np.ndarray:
    plane = np.zeros(52, dtype=int)
    for card in cards:
        card_id = get_card_id(card)
        plane[card_id] = 1
    return plane
