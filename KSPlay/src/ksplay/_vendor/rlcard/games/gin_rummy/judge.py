'''
    File name: gin_rummy/judge.py
    Author: William Hale
    Date created: 2/12/2020
'''

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .game import GinRummyGame

from typing import List, Tuple

from .utils.action_event import *
from .utils.scorers import GinRummyScorer
from .utils import melding
from .utils.gin_rummy_error import GinRummyProgramError

from ksplay._vendor.rlcard.games.gin_rummy.utils import utils

_DEADWOOD_VALUE_BY_RANK = utils.rank_to_deadwood_value
_CARD_ID_BY_SUIT_AND_RANK = utils._card_id_by_suit_and_rank
def _action_ids_for_cards(cards, offset):
    if offset == discard_action_id:
        try:
            return [
                card._gin_rummy_discard_action_id for card in cards
            ]
        except AttributeError:
            pass
    elif offset == knock_action_id:
        try:
            return [
                card._gin_rummy_knock_action_id for card in cards
            ]
        except AttributeError:
            pass
    try:
        return [offset + card._gin_rummy_id for card in cards]
    except AttributeError:
        pass
    try:
        return [
            offset + _CARD_ID_BY_SUIT_AND_RANK[card.suit][card.rank]
            for card in cards
        ]
    except KeyError:
        # Preserve the public malformed-card exception behavior.
        return [offset + utils.get_card_id(card) for card in cards]


def _get_going_out_cards_cached_player(
        player, going_out_deadwood_count):
    """Match cluster enumeration using the player's maintained meld masks."""

    hand = player.hand
    hand_mask = player._hand_mask
    melds = []
    meld_masks = []
    meld_values = []
    for meld_group in player.meld_kinds_by_rank_id:
        for meld in meld_group:
            melds.append(meld)
            mask = 0
            value = 0
            for card in meld:
                mask |= card._gin_rummy_bit
                value += card._gin_rummy_deadwood_value
            meld_masks.append(mask)
            meld_values.append(value)
    for meld_group in player.meld_run_by_suit_id:
        for meld in meld_group:
            melds.append(meld)
            mask = 0
            value = 0
            for card in meld:
                mask |= card._gin_rummy_bit
                value += card._gin_rummy_deadwood_value
            meld_masks.append(mask)
            meld_values.append(value)
    hand_value = player._hand_deadwood_value
    knock_cards = set()
    gin_cards = set()

    def consider(indexes, covered_mask, covered_value):
        deadwood_mask = hand_mask & ~covered_mask
        deadwood_count = deadwood_mask.bit_count()
        if deadwood_count == 0:
            for index in indexes:
                meld = melds[index]
                if len(meld) >= 4:
                    # Preserve get_meld_clusters' frozenset-to-list choice.
                    gin_cards.add(list(frozenset(meld))[0])
                    break
            return
        if deadwood_count == 1:
            for card in hand:
                if deadwood_mask & card._gin_rummy_bit:
                    gin_cards.add(card)
                    break
            return
        total = hand_value - covered_value
        if total <= going_out_deadwood_count + 10:
            for card in hand:
                if (
                    deadwood_mask & card._gin_rummy_bit
                    and total - card._gin_rummy_deadwood_value
                    <= going_out_deadwood_count
                ):
                    knock_cards.add(card)

    for first_index, first_mask in enumerate(meld_masks):
        first_value = meld_values[first_index]
        consider((first_index,), first_mask, first_value)
        for second_index in range(first_index + 1, len(meld_masks)):
            second_mask = meld_masks[second_index]
            if first_mask & second_mask:
                continue
            covered = first_mask | second_mask
            covered_value = first_value + meld_values[second_index]
            consider(
                (first_index, second_index),
                covered,
                covered_value,
            )
            for third_index in range(second_index + 1, len(meld_masks)):
                third_mask = meld_masks[third_index]
                if covered & third_mask:
                    continue
                consider(
                    (first_index, second_index, third_index),
                    covered | third_mask,
                    covered_value + meld_values[third_index],
                )
    return list(knock_cards), list(gin_cards)


class GinRummyJudge:

    '''
        Judge decides legal actions for current player
    '''

    def __init__(self, game: 'GinRummyGame'):
        ''' Initialize the class GinRummyJudge
        :param game: GinRummyGame
        '''
        self.game = game
        self.scorer = GinRummyScorer()

    def get_legal_actions(self) -> List[ActionEvent]:
        """
        :return: List[ActionEvent] of legal actions
        """
        legal_actions = []  # type: List[ActionEvent]
        last_action = self.game.get_last_action()
        if last_action is None or \
                isinstance(last_action, DrawCardAction) or \
                isinstance(last_action, PickUpDiscardAction):
            current_player = self.game.get_current_player()
            going_out_deadwood_count = self.game.settings.going_out_deadwood_count
            hand = current_player.hand
            meld_clusters = current_player.get_meld_clusters()  # improve speed 2020-Apr
            knock_cards, gin_cards = _get_going_out_cards(meld_clusters=meld_clusters,
                                                          hand=hand,
                                                          going_out_deadwood_count=going_out_deadwood_count)
            if self.game.settings.is_allowed_gin and gin_cards:
                legal_actions = [GinAction()]
            else:
                cards_to_discard = [card for card in hand]
                if isinstance(last_action, PickUpDiscardAction):
                    if not self.game.settings.is_allowed_to_discard_picked_up_card:
                        picked_up_card = self.game.round.move_sheet[-1].card
                        cards_to_discard.remove(picked_up_card)
                discard_actions = [DiscardAction(card=card) for card in cards_to_discard]
                legal_actions = discard_actions
                if self.game.settings.is_allowed_knock:
                    if current_player.player_id == 0 or not self.game.settings.is_south_never_knocks:
                        if knock_cards:
                            knock_actions = [KnockAction(card=card) for card in knock_cards]
                            if not self.game.settings.is_always_knock:
                                legal_actions.extend(knock_actions)
                            else:
                                legal_actions = knock_actions
        elif isinstance(last_action, DeclareDeadHandAction):
            legal_actions = [ScoreNorthPlayerAction()]
        elif isinstance(last_action, GinAction):
            legal_actions = [ScoreNorthPlayerAction()]
        elif isinstance(last_action, DiscardAction):
            can_draw_card = len(self.game.round.dealer.stock_pile) > self.game.settings.stockpile_dead_card_count
            if self.game.settings.max_drawn_card_count < 52:  # NOTE: this
                drawn_card_actions = [action for action in self.game.actions if isinstance(action, DrawCardAction)]
                if len(drawn_card_actions) >= self.game.settings.max_drawn_card_count:
                    can_draw_card = False
            move_count = len(self.game.round.move_sheet)
            if move_count >= self.game.settings.max_move_count:
                legal_actions = [DeclareDeadHandAction()]  # prevent unlimited number of moves in a game
            elif can_draw_card:
                legal_actions = [DrawCardAction()]
                if self.game.settings.is_allowed_pick_up_discard:
                    legal_actions.append(PickUpDiscardAction())
            else:
                legal_actions = [DeclareDeadHandAction()]
                if self.game.settings.is_allowed_pick_up_discard:
                    legal_actions.append(PickUpDiscardAction())
        elif isinstance(last_action, KnockAction):
            legal_actions = [ScoreNorthPlayerAction()]
        elif isinstance(last_action, ScoreNorthPlayerAction):
            legal_actions = [ScoreSouthPlayerAction()]
        elif isinstance(last_action, ScoreSouthPlayerAction):
            pass
        else:
            raise Exception('get_legal_actions: unknown last_action={}'.format(last_action))
        return legal_actions

    def get_legal_action_ids(self) -> List[int]:
        """Return the same legal actions without allocating ActionEvents."""
        game = self.game
        round_ = game.round
        settings = game.settings
        actions = game.actions
        last_action = actions[-1] if actions else None
        last_action_id = (
            None if last_action is None else last_action.action_id
        )
        if last_action_id is None or last_action_id in (
            draw_card_action_id, pick_up_discard_action_id
        ):
            current_player = round_.players[round_.current_player_id]
            meld_count = current_player._meld_count
            if meld_count == 1:
                meld = None
                for melds in current_player.meld_kinds_by_rank_id:
                    if melds:
                        meld = melds[0]
                        break
                if meld is None:
                    for melds in current_player.meld_run_by_suit_id:
                        if melds:
                            meld = melds[0]
                            break
                knock_cards, gin_cards = (
                    _get_going_out_cards_single_meld(
                        meld=meld,
                        hand=current_player.hand,
                        going_out_deadwood_count=(
                            settings.going_out_deadwood_count
                        ),
                    )
                )
            elif meld_count:
                knock_cards, gin_cards = _get_going_out_cards_cached_player(
                    current_player,
                    settings.going_out_deadwood_count,
                )
            else:
                knock_cards = gin_cards = ()
            if settings.is_allowed_gin and gin_cards:
                return [gin_action_id]

            hand = current_player.hand
            if (
                last_action_id == pick_up_discard_action_id
                and not settings.is_allowed_to_discard_picked_up_card
            ):
                picked_up_card = round_.move_sheet[-1].card
                try:
                    action_ids = [
                        card._gin_rummy_discard_action_id
                        for card in hand if card is not picked_up_card
                    ]
                except AttributeError:
                    cards_to_discard = list(hand)
                    cards_to_discard.remove(picked_up_card)
                    action_ids = _action_ids_for_cards(
                        cards_to_discard, discard_action_id
                    )
                if len(action_ids) == len(hand):
                    cards_to_discard = list(hand)
                    cards_to_discard.remove(picked_up_card)
                    action_ids = _action_ids_for_cards(
                        cards_to_discard, discard_action_id
                    )
            else:
                action_ids = _action_ids_for_cards(
                    hand, discard_action_id
                )
            if (
                settings.is_allowed_knock
                and (
                    current_player.player_id == 0
                    or not settings.is_south_never_knocks
                )
                and knock_cards
            ):
                knock_ids = _action_ids_for_cards(
                    knock_cards, knock_action_id
                )
                if settings.is_always_knock:
                    return knock_ids
                action_ids.extend(knock_ids)
            return action_ids

        if last_action_id in (
            declare_dead_hand_action_id, gin_action_id
        ):
            return [score_player_0_action_id]
        if discard_action_id <= last_action_id < knock_action_id:
            can_draw_card = (
                len(round_.dealer.stock_pile)
                > settings.stockpile_dead_card_count
            )
            if settings.max_drawn_card_count < 52:
                drawn_card_count = sum(
                    action.action_id == draw_card_action_id
                    for action in actions
                )
                if drawn_card_count >= settings.max_drawn_card_count:
                    can_draw_card = False
            if (
                len(round_.move_sheet)
                >= settings.max_move_count
            ):
                return [declare_dead_hand_action_id]
            if can_draw_card:
                action_ids = [draw_card_action_id]
                if settings.is_allowed_pick_up_discard:
                    action_ids.append(pick_up_discard_action_id)
                return action_ids
            action_ids = [declare_dead_hand_action_id]
            if settings.is_allowed_pick_up_discard:
                action_ids.append(pick_up_discard_action_id)
            return action_ids
        if last_action_id >= knock_action_id:
            return [score_player_0_action_id]
        if last_action_id == score_player_0_action_id:
            return [score_player_1_action_id]
        if last_action_id == score_player_1_action_id:
            return []
        raise Exception(
            'get_legal_actions: unknown last_action={}'.format(last_action)
        )


def get_going_out_cards(hand: List[Card], going_out_deadwood_count: int) -> Tuple[List[Card], List[Card]]:
    '''
    :param hand: List[Card] -- must have 11 cards
    :param going_out_deadwood_count: int
    :return List[Card], List[Card: cards in hand that be knocked, cards in hand that can be ginned
    '''
    if not len(hand) == 11:
        raise GinRummyProgramError("len(hand) is {}: should be 11.".format(len(hand)))
    meld_clusters = melding.get_meld_clusters(hand=hand)
    knock_cards, gin_cards = _get_going_out_cards(meld_clusters=meld_clusters,
                                                  hand=hand,
                                                  going_out_deadwood_count=going_out_deadwood_count)
    return list(knock_cards), list(gin_cards)


#
# private methods
#

def _get_going_out_cards(meld_clusters: List[List[List[Card]]],
                         hand: List[Card],
                         going_out_deadwood_count: int) -> Tuple[List[Card], List[Card]]:
    '''
    :param meld_clusters
    :param hand: List[Card] -- must have 11 cards
    :param going_out_deadwood_count: int
    :return List[Card], List[Card: cards in hand that be knocked, cards in hand that can be ginned
    '''
    if not len(hand) == 11:
        raise GinRummyProgramError("len(hand) is {}: should be 11.".format(len(hand)))
    knock_cards = set()
    gin_cards = set()
    for meld_cluster in meld_clusters:
        canonical_cards = True
        try:
            meld_card_ids = {
                card._gin_rummy_id
                for meld_pile in meld_cluster for card in meld_pile
            }
            hand_deadwood = [
                card for card in hand
                if card._gin_rummy_id not in meld_card_ids
            ]
        except AttributeError:
            canonical_cards = False
            try:
                meld_card_ids = {
                    _CARD_ID_BY_SUIT_AND_RANK[card.suit][card.rank]
                    for meld_pile in meld_cluster
                    for card in meld_pile
                }
                hand_deadwood = [
                    card for card in hand
                    if _CARD_ID_BY_SUIT_AND_RANK[card.suit][card.rank]
                    not in meld_card_ids
                ]
            except KeyError:
                meld_card_ids = {
                    utils.get_card_id(card)
                    for meld_pile in meld_cluster for card in meld_pile
                }
                hand_deadwood = [
                    card for card in hand
                    if utils.get_card_id(card) not in meld_card_ids
                ]
        if len(hand_deadwood) == 0:
            # all 11 cards are melded;
            # take gin_card as first card of first 4+ meld;
            # could also take gin_card as last card of 4+ meld, but won't do this.
            for meld_pile in meld_cluster:
                if len(meld_pile) >= 4:
                    gin_cards.add(meld_pile[0])
                    break
        elif len(hand_deadwood) == 1:
            card = hand_deadwood[0]
            gin_cards.add(card)
        else:
            if canonical_cards:
                hand_deadwood_values = [
                    card._gin_rummy_deadwood_value
                    for card in hand_deadwood
                ]
            else:
                hand_deadwood_values = [
                    _DEADWOOD_VALUE_BY_RANK.get(card.rank, 10)
                    for card in hand_deadwood
                ]
            hand_deadwood_count = sum(hand_deadwood_values)
            max_hand_deadwood_value = max(hand_deadwood_values, default=0)
            if hand_deadwood_count <= 10 + max_hand_deadwood_value:
                for card, deadwood_value in zip(
                        hand_deadwood, hand_deadwood_values):
                    next_deadwood_count = (
                        hand_deadwood_count - deadwood_value
                    )
                    if next_deadwood_count <= going_out_deadwood_count:
                        knock_cards.add(card)
    return list(knock_cards), list(gin_cards)


def _get_going_out_cards_single_meld(
        meld: List[Card],
        hand: List[Card],
        going_out_deadwood_count: int) -> Tuple[List[Card], List[Card]]:
    """One-meld specialization of ``_get_going_out_cards``."""
    try:
        meld_mask = sum(card._gin_rummy_bit for card in meld)
        hand_deadwood = [
            card for card in hand
            if not meld_mask & card._gin_rummy_bit
        ]
    except AttributeError:
        hand_deadwood = None
    if hand_deadwood is not None:
        deadwood_count = len(hand_deadwood)
        if deadwood_count == 0:
            if len(meld) >= 4:
                # Match list(frozenset(meld))[0] from get_meld_clusters.
                return [], [next(iter(frozenset(meld)))]
            return [], []
        if deadwood_count == 1:
            return [], [hand_deadwood[0]]
        values = [
            card._gin_rummy_deadwood_value
            for card in hand_deadwood
        ]
        total = sum(values)
        if total > 10 + max(values, default=0):
            return [], []
        knock_cards = {
            card
            for card, value in zip(hand_deadwood, values)
            if total - value <= going_out_deadwood_count
        }
        return list(knock_cards), []

    canonical_cards = True
    try:
        meld_card_ids = {
            card._gin_rummy_id for card in meld
        }
        hand_deadwood = [
            card for card in hand
            if card._gin_rummy_id not in meld_card_ids
        ]
    except AttributeError:
        canonical_cards = False
        try:
            meld_card_ids = {
                _CARD_ID_BY_SUIT_AND_RANK[card.suit][card.rank]
                for card in meld
            }
            hand_deadwood = [
                card for card in hand
                if _CARD_ID_BY_SUIT_AND_RANK[card.suit][card.rank]
                not in meld_card_ids
            ]
        except KeyError:
            meld_card_ids = {utils.get_card_id(card) for card in meld}
            hand_deadwood = [
                card for card in hand
                if utils.get_card_id(card) not in meld_card_ids
            ]
    deadwood_count = len(hand_deadwood)
    if deadwood_count == 0:
        if len(meld) >= 4:
            # Match list(frozenset(meld))[0] from get_meld_clusters.
            return [], [next(iter(frozenset(meld)))]
        return [], []
    if deadwood_count == 1:
        return [], [hand_deadwood[0]]

    if canonical_cards:
        values = [
            card._gin_rummy_deadwood_value
            for card in hand_deadwood
        ]
    else:
        values = [
            _DEADWOOD_VALUE_BY_RANK.get(card.rank, 10)
            for card in hand_deadwood
        ]
    total = sum(values)
    if total > 10 + max(values, default=0):
        return [], []
    knock_cards = {
        card
        for card, value in zip(hand_deadwood, values)
        if total - value <= going_out_deadwood_count
    }
    return list(knock_cards), []
