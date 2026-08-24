'''
    File name: gin_rummy/melding.py
    Author: William Hale
    Date created: 2/12/2020
'''

from typing import List
from functools import lru_cache

from ksplay._vendor.rlcard.games.base import Card

from ksplay._vendor.rlcard.games.gin_rummy.utils import utils
from ksplay._vendor.rlcard.games.gin_rummy.utils.gin_rummy_error import GinRummyProgramError

# ===============================================================
#    Terminology:
#        run_meld - three or more cards of same suit in sequence
#        set_meld - three or more cards of same rank
#        meld_pile - a run_meld or a set_meld
#        meld_piles - a list of meld_pile
#        meld_cluster - same as meld_piles, but usually with the piles being mutually disjoint
#        meld_clusters - a list of meld_cluster
# ===============================================================


def get_meld_clusters(hand: List[Card]) -> List[List[List[Card]]]:
    result = []  # type: List[List[List[Card]]]
    all_run_melds = [frozenset(x) for x in get_all_run_melds(hand)]
    all_set_melds = [frozenset(x) for x in get_all_set_melds(hand)]
    all_melds = all_run_melds + all_set_melds
    all_melds_count = len(all_melds)
    for i in range(0, all_melds_count):
        first_meld = all_melds[i]
        first_meld_list = list(first_meld)
        meld_cluster_1 = [first_meld_list]
        result.append(meld_cluster_1)
        for j in range(i + 1, all_melds_count):
            second_meld = all_melds[j]
            if not second_meld.isdisjoint(first_meld):
                continue
            second_meld_list = list(second_meld)
            meld_cluster_2 = [first_meld_list, second_meld_list]
            result.append(meld_cluster_2)
            for k in range(j + 1, all_melds_count):
                third_meld = all_melds[k]
                if not third_meld.isdisjoint(first_meld) or not third_meld.isdisjoint(second_meld):
                    continue
                third_meld_list = list(third_meld)
                meld_cluster_3 = [first_meld_list, second_meld_list, third_meld_list]
                result.append(meld_cluster_3)
    return result


def get_best_meld_clusters(hand: List[Card]) -> List[List[List[Card]]]:
    if len(hand) != 10:
        raise GinRummyProgramError("Hand contain {} cards: should be 10 cards.".format(len(hand)))
    result = []  # type: List[List[List[Card]]]
    meld_clusters = get_meld_clusters(hand=hand)  # type: List[List[List[Card]]]
    meld_clusters_count = len(meld_clusters)
    if meld_clusters_count > 0:
        deadwood_counts = [utils.get_deadwood_count(hand=hand, meld_cluster=meld_cluster)
                           for meld_cluster in meld_clusters]
        best_deadwood_count = min(deadwood_counts)
        for i in range(meld_clusters_count):
            if deadwood_counts[i] == best_deadwood_count:
                result.append(meld_clusters[i])
    return result


def get_all_run_melds(hand: List[Card]) -> List[List[Card]]:
    card_count = len(hand)
    hand_by_suit = sorted(hand, key=utils.get_card_id)
    max_run_melds = []

    i = 0
    while i < card_count - 2:
        card_i = hand_by_suit[i]
        j = i + 1
        card_j = hand_by_suit[j]
        while utils.get_rank_id(card_j) == utils.get_rank_id(card_i) + j - i and card_j.suit == card_i.suit:
            j += 1
            if j < card_count:
                card_j = hand_by_suit[j]
            else:
                break
        max_run_meld = hand_by_suit[i:j]
        if len(max_run_meld) >= 3:
            max_run_melds.append(max_run_meld)
        i = j

    result = []
    for max_run_meld in max_run_melds:
        max_run_meld_count = len(max_run_meld)
        for i in range(max_run_meld_count - 2):
            for j in range(i + 3, max_run_meld_count + 1):
                result.append(max_run_meld[i:j])
    return result


def get_all_set_melds(hand: List[Card]) -> List[List[Card]]:
    max_set_melds = []
    hand_by_rank = sorted(hand, key=lambda x: x.rank)
    set_meld = []
    current_rank = None
    for card in hand_by_rank:
        if current_rank is None or current_rank == card.rank:
            set_meld.append(card)
        else:
            if len(set_meld) >= 3:
                max_set_melds.append(set_meld)
            set_meld = [card]
        current_rank = card.rank
    if len(set_meld) >= 3:
        max_set_melds.append(set_meld)
    result = []
    for max_set_meld in max_set_melds:
        result.append(max_set_meld)
        if len(max_set_meld) == 4:
            for meld_card in max_set_meld:
                result.append([card for card in max_set_meld if card != meld_card])
    return result


def get_all_run_melds_for_suit(cards: List[Card], suit: str) -> List[List[Card]]:
    cards_for_suit = [card for card in cards if card.suit == suit]
    # All cards here have the same suit, so rank order is exactly the same as
    # full card-id order and avoids a redundant suit lookup per comparison.
    cards_for_suit = sorted(cards_for_suit, key=utils.get_rank_id)
    cards_for_suit_count = len(cards_for_suit)
    max_run_melds = []

    i = 0
    while i < cards_for_suit_count - 2:
        card_i = cards_for_suit[i]
        j = i + 1
        card_j = cards_for_suit[j]
        while utils.get_rank_id(card_j) == utils.get_rank_id(card_i) + j - i:
            j += 1
            if j < cards_for_suit_count:
                card_j = cards_for_suit[j]
            else:
                break
        max_run_meld = cards_for_suit[i:j]
        if len(max_run_meld) >= 3:
            max_run_melds.append(max_run_meld)
        i = j

    result = []
    for max_run_meld in max_run_melds:
        max_run_meld_count = len(max_run_meld)
        for i in range(max_run_meld_count - 2):
            for j in range(i + 3, max_run_meld_count + 1):
                result.append(max_run_meld[i:j])
    return result


@lru_cache(maxsize=1024)
def _run_ranges_for_ranks(ranks: int):
    """Return the ordered half-open rank ranges for one suit mask."""
    if not ranks & (ranks >> 1) & (ranks >> 2):
        return ()
    max_run_ranges = []
    i = 0
    while i < 11:
        while i < 13 and not (ranks >> i) & 1:
            i += 1
        if i >= 11:
            break
        j = i + 1
        while j < 13 and (ranks >> j) & 1:
            j += 1
        if j - i >= 3:
            max_run_ranges.append((i, j))
        i = j

    result = []
    for start, stop in max_run_ranges:
        for i in range(start, stop - 2):
            for j in range(i + 3, stop + 1):
                result.append((i, j))
    return tuple(result)


@lru_cache(maxsize=2048)
def _run_melds_for_suit_ranks(ranks: int, suit_id: int):
    """Return immutable canonical-card melds for a suit/rank mask."""
    card_id_base = 13 * suit_id
    return tuple(
        tuple(
            utils.get_card(card_id_base + rank_id)
            for rank_id in range(start, stop)
        )
        for start, stop in _run_ranges_for_ranks(ranks)
    )


def _get_all_run_melds_for_suit_mask(
        hand_mask: int, suit_id: int) -> List[List[Card]]:
    """Build the same ordered run sequence from a canonical-card hand mask."""
    ranks = (hand_mask >> (13 * suit_id)) & 0x1FFF
    return _run_melds_for_suit_ranks(ranks, suit_id)
