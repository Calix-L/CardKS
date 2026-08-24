'''
    File name: gin_rummy/player.py
    Author: William Hale
    Date created: 2/12/2020
'''

from typing import List

from ksplay._vendor.rlcard.games.base import Card

from .utils import utils

from .utils import melding

_RANK_CARD_MASKS = tuple(
    sum(1 << (rank_id + 13 * suit_id) for suit_id in range(4))
    for rank_id in range(13)
)


class GinRummyPlayer:

    def __init__(self, player_id: int, np_random):
        ''' Initialize a GinRummy player class

        Args:
            player_id (int): id for the player
        '''
        self.np_random = np_random
        self.player_id = player_id
        self.hand = []  # type: List[Card]
        self.known_cards = []  # type: List[Card]  # opponent knows cards picked up by player and not yet discarded
        # memoization for speed
        self.meld_kinds_by_rank_id = [[] for _ in range(13)]  # type: List[List[List[Card]]]
        self.meld_run_by_suit_id = [[] for _ in range(4)]  # type: List[List[List[Card]]]
        self._meld_count = 0
        self._hand_mask = 0
        self._known_mask = 0
        self._hand_deadwood_value = 0

    def get_player_id(self) -> int:
        ''' Return player's id
        '''
        return self.player_id

    def get_meld_clusters(self) -> List[List[List[Card]]]:
        result = []  # type: List[List[List[Card]]]
        all_run_melds = [frozenset(meld_kind) for meld_kinds in self.meld_kinds_by_rank_id for meld_kind in meld_kinds]
        all_set_melds = [frozenset(meld_run) for meld_runs in self.meld_run_by_suit_id for meld_run in meld_runs]
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

    def did_populate_hand(self):
        self.meld_kinds_by_rank_id = [[] for _ in range(13)]
        self.meld_run_by_suit_id = [[] for _ in range(4)]
        try:
            self._hand_mask = sum(
                card._gin_rummy_bit for card in self.hand
            )
        except AttributeError:
            self._hand_mask = None
        if self._hand_mask is None:
            all_set_melds = melding.get_all_set_melds(hand=self.hand)
            for set_meld in all_set_melds:
                rank_id = utils.get_rank_id(set_meld[0])
                self.meld_kinds_by_rank_id[rank_id].append(set_meld)
            all_run_melds = melding.get_all_run_melds(hand=self.hand)
            for run_meld in all_run_melds:
                suit_id = utils.get_suit_id(run_meld[0])
                self.meld_run_by_suit_id[suit_id].append(run_meld)
        else:
            for rank_id, rank_mask in enumerate(_RANK_CARD_MASKS):
                rank_count = (
                    self._hand_mask & rank_mask
                ).bit_count()
                if rank_count >= 3:
                    cards = [
                        card for card in self.hand
                        if card._gin_rummy_rank_id == rank_id
                    ]
                    melds = [cards]
                    if rank_count == 4:
                        melds.extend(
                            [other for other in cards if other != card]
                            for card in cards
                        )
                    self.meld_kinds_by_rank_id[rank_id] = melds
            for suit_id in range(4):
                ranks = (
                    self._hand_mask >> (13 * suit_id)
                ) & 0x1FFF
                if ranks & (ranks >> 1) & (ranks >> 2):
                    self.meld_run_by_suit_id[suit_id] = (
                        melding._get_all_run_melds_for_suit_mask(
                            self._hand_mask, suit_id
                        )
                    )
        self._meld_count = (
            sum(map(len, self.meld_kinds_by_rank_id))
            + sum(map(len, self.meld_run_by_suit_id))
        )
        self._hand_deadwood_value = sum(
            utils.get_deadwood_value(card) for card in self.hand
        )

    def add_card_to_hand(self, card: Card):
        self.hand.append(card)
        self._hand_deadwood_value += utils.get_deadwood_value(card)
        if self._hand_mask is not None:
            try:
                self._hand_mask |= card._gin_rummy_bit
            except AttributeError:
                self._hand_mask = None
        self._increase_meld_kinds_by_rank_id(card=card)
        self._increase_run_kinds_by_suit_id(card=card)

    def remove_card_from_hand(self, card: Card):
        for index, hand_card in enumerate(self.hand):
            if hand_card is card:
                del self.hand[index]
                break
        else:
            # Preserve equal-value Card support for callers outside the
            # canonical deck/action path.
            self.hand.remove(card)
        self._hand_deadwood_value -= utils.get_deadwood_value(card)
        if self._hand_mask is not None:
            try:
                card_bit = card._gin_rummy_bit
            except AttributeError:
                card_bit = 1 << utils.get_card_id(card)
            self._hand_mask &= ~card_bit
        self._reduce_meld_kinds_by_rank_id(card=card)
        self._reduce_run_kinds_by_suit_id(card=card)

    def remove_known_card(self, card: Card, trusted=False):
        if not self.known_cards:
            return
        if trusted and self._known_mask is not None:
            try:
                card_bit = card._gin_rummy_bit
            except AttributeError:
                card_bit = None
            if card_bit is not None and not self._known_mask & card_bit:
                return
        for index, known_card in enumerate(self.known_cards):
            if known_card is card:
                del self.known_cards[index]
                break
        else:
            try:
                self.known_cards.remove(card)
            except ValueError:
                return
        if self._known_mask is not None:
            try:
                self._known_mask &= ~card._gin_rummy_bit
            except AttributeError:
                self._known_mask = None

    def __str__(self):
        return "N" if self.player_id == 0 else "S"

    @staticmethod
    def short_name_of(player_id: int) -> str:
        return "N" if player_id == 0 else "S"

    @staticmethod
    def opponent_id_of(player_id: int) -> int:
        return (player_id + 1) % 2

    # private methods

    def _increase_meld_kinds_by_rank_id(self, card: Card):
        try:
            rank_id = card._gin_rummy_rank_id
        except AttributeError:
            rank_id = utils.get_rank_id(card)
        meld_kinds = self.meld_kinds_by_rank_id[rank_id]
        old_count = len(meld_kinds)
        if len(meld_kinds) == 0:
            card_rank = card.rank
            if (
                self._hand_mask is None
                or (self._hand_mask & _RANK_CARD_MASKS[rank_id]).bit_count()
                >= 3
            ):
                meld_kind = [
                    card for card in self.hand
                    if card.rank == card_rank
                ]
                if len(meld_kind) >= 3:
                    self.meld_kinds_by_rank_id[rank_id].append(
                        meld_kind
                    )
        else:  # must have all cards of given rank
            max_kind_meld = [
                hand_card for hand_card in self.hand
                if hand_card._gin_rummy_rank_id == rank_id
            ]
            self.meld_kinds_by_rank_id[rank_id] = [
                max_kind_meld,
                *[
                    [
                        other for other in max_kind_meld
                        if other is not omitted
                    ]
                    for omitted in max_kind_meld
                ],
            ]
        self._meld_count += (
            len(self.meld_kinds_by_rank_id[rank_id]) - old_count
        )

    def _reduce_meld_kinds_by_rank_id(self, card: Card):
        try:
            rank_id = card._gin_rummy_rank_id
        except AttributeError:
            rank_id = utils.get_rank_id(card)
        meld_kinds = self.meld_kinds_by_rank_id[rank_id]
        old_count = len(meld_kinds)
        if len(meld_kinds) > 1:
            self.meld_kinds_by_rank_id[rank_id] = [[
                hand_card for hand_card in self.hand
                if hand_card._gin_rummy_rank_id == rank_id
            ]]
        else:
            self.meld_kinds_by_rank_id[rank_id] = []
        self._meld_count += (
            len(self.meld_kinds_by_rank_id[rank_id]) - old_count
        )

    def _increase_run_kinds_by_suit_id(self, card: Card):
        try:
            suit_id = card._gin_rummy_suit_id
        except AttributeError:
            suit_id = utils.get_suit_id(card=card)
        old_count = len(self.meld_run_by_suit_id[suit_id])
        if self._hand_mask is None:
            meld_runs = melding.get_all_run_melds_for_suit(
                cards=self.hand, suit=card.suit
            )
        else:
            ranks = (self._hand_mask >> (13 * suit_id)) & 0x1FFF
            if ranks & (ranks >> 1) & (ranks >> 2):
                meld_runs = melding._get_all_run_melds_for_suit_mask(
                    self._hand_mask, suit_id
                )
            else:
                meld_runs = []
        self.meld_run_by_suit_id[suit_id] = meld_runs
        self._meld_count += (
            len(self.meld_run_by_suit_id[suit_id]) - old_count
        )

    def _reduce_run_kinds_by_suit_id(self, card: Card):
        try:
            suit_id = card._gin_rummy_suit_id
        except AttributeError:
            suit_id = utils.get_suit_id(card=card)
        meld_runs = self.meld_run_by_suit_id[suit_id]
        self.meld_run_by_suit_id[suit_id] = [meld_run for meld_run in meld_runs if card not in meld_run]
        self._meld_count += (
            len(self.meld_run_by_suit_id[suit_id]) - len(meld_runs)
        )
